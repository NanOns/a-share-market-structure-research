from __future__ import annotations

"""Verify or bounded-capture sources named by a phase source-request manifest."""

import argparse
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]


def atomic_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def checked_url(value: str, allowed_hosts: set[str]) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in allowed_hosts or parsed.username or parsed.password:
        raise ValueError("SOURCE_URL_SCHEME_OR_HOST_NOT_ALLOWED")
    return parsed


def safe_project_path(relative: str) -> Path:
    target = (ROOT / relative).resolve()
    if not target.is_relative_to(ROOT.resolve()) or target == ROOT.resolve():
        raise ValueError("SOURCE_CAPTURE_PATH_OUTSIDE_PROJECT")
    return target


def digest_file(path: Path, max_bytes: int) -> tuple[str, int, bytes]:
    h, size, head = hashlib.sha256(), 0, b""
    with path.open("rb") as stream:
        while block := stream.read(min(1024 * 1024, max_bytes + 1 - size)):
            size += len(block)
            if size > max_bytes:
                raise ValueError("SOURCE_CAPTURE_EXCEEDS_MAXIMUM_BYTES")
            if len(head) < 8:
                head += block[:8 - len(head)]
            h.update(block)
    return h.hexdigest(), size, head


class AllowlistedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: set[str]):
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl, self.allowed_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def bounded_fetch(url: str, *, allowed_hosts: set[str], timeout: int, max_bytes: int, content_type: str) -> bytes:
    checked_url(url, allowed_hosts)
    opener = urllib.request.build_opener(AllowlistedRedirectHandler(allowed_hosts))
    request = urllib.request.Request(url, headers={"User-Agent": "V4-02-special-phase-capture/1.0"})
    with opener.open(request, timeout=timeout) as response:
        final = response.geturl()
        checked_url(final, allowed_hosts)
        actual_type = response.headers.get_content_type().lower()
        if actual_type != content_type.lower():
            raise ValueError("SOURCE_CAPTURE_CONTENT_TYPE_INVALID")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("SOURCE_CAPTURE_EXCEEDS_MAXIMUM_BYTES")
    if content_type.lower() == "application/pdf" and not payload.startswith(b"%PDF-"):
        raise ValueError("SOURCE_RESPONSE_NOT_PDF")
    return payload


def atomic_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError("SOURCE_CAPTURE_IMMUTABLE_PATH_CONFLICT")
        return
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise FileExistsError("SOURCE_CAPTURE_IMMUTABLE_PATH_CONFLICT")
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(manifest: Path, policy_path: Path, receipt: Path, mode: str) -> dict:
    config = json.loads(policy_path.read_text(encoding="utf-8"))
    allowed_hosts = {str(x).lower() for x in config["allowed_hosts"]}
    policy_cap = int(config["maximum_request_bytes"])
    timeout = int(config["timeout_seconds"])
    expected_type = str(config["expected_content_type"])
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    findings, failed = [], []
    for row in rows:
        item = {"event_id": row.get("event_id"), "source_ref": row.get("source_ref"), "status": "VERIFIED"}
        try:
            checked_url(str(row["source_ref"]), allowed_hosts)
            cap = min(policy_cap, int(row.get("max_bytes") or policy_cap))
            if str(row.get("expected_content_type") or expected_type).lower() != expected_type.lower():
                raise ValueError("SOURCE_REQUEST_CONTENT_TYPE_CONTRACT_MISMATCH")
            target = safe_project_path(str(row["source_capture_path"]))
            if mode == "verify-existing":
                actual_hash, size, head = digest_file(target, cap)
                if expected_type == "application/pdf" and not head.startswith(b"%PDF-"):
                    raise ValueError("SOURCE_CAPTURE_NOT_PDF")
                if actual_hash.lower() != str(row["source_capture_sha256"]).lower():
                    raise ValueError("SOURCE_CAPTURE_HASH_MISMATCH")
            else:
                payload = bounded_fetch(str(row["source_ref"]), allowed_hosts=allowed_hosts, timeout=timeout,
                                        max_bytes=cap, content_type=expected_type)
                actual_hash, size = hashlib.sha256(payload).hexdigest(), len(payload)
                if row.get("source_capture_sha256") and actual_hash.lower() != str(row["source_capture_sha256"]).lower():
                    raise ValueError("SOURCE_CAPTURE_EXPECTED_HASH_MISMATCH")
                atomic_immutable(target, payload)
            item.update(bytes=size, sha256=actual_hash, path=str(target.relative_to(ROOT)).replace("\\", "/"))
        except Exception as exc:
            item.update(status="FAILED", reason=type(exc).__name__ + ":" + str(exc))
            failed.append(item)
        findings.append(item)
    result = {"contract_id": "SPECIAL_PHASE_SOURCE_CAPTURE_RECEIPT_R5", "version": "1.0.0",
              "mode": mode, "status": "PASS" if not failed else "BLOCKED", "request_count": len(rows),
              "verified_count": len(rows) - len(failed), "failures": failed, "findings": findings,
              "source_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
              "capture_policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
              "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    atomic_json(receipt, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/v4/bootstrap/special_phase_source_requests_r4.jsonl")
    parser.add_argument("--policy", type=Path, default=ROOT / "config/special_phase_source_capture_v1.json")
    parser.add_argument("--receipt", type=Path, default=ROOT / "reports/v4_02/V4_02_R5_SOURCE_CAPTURE_VERIFY.json")
    parser.add_argument("--mode", choices=("verify-existing", "capture"), default="verify-existing")
    args = parser.parse_args()
    result = run(args.manifest, args.policy, args.receipt, args.mode)
    print(json.dumps({k: result[k] for k in ("status", "mode", "request_count", "verified_count")}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
