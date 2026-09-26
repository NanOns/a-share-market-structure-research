from __future__ import annotations

"""Capture a bounded set of official exchange calendar/rule pages as evidence."""

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/v4_official_exchange_calendar_v1.json"


class BoundedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_hosts: set[str]) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, request, fp, code, message, headers, new_url):
        parsed = urlparse(new_url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise ValueError(f"REDIRECT_OUTSIDE_ALLOWLIST:{new_url}")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    capture_contract = contract["source_capture"]
    allowed = set(capture_contract["allowed_hosts"])
    max_page = int(capture_contract["maximum_response_bytes_per_page"])
    max_total = int(capture_contract["maximum_total_response_bytes"])
    timeout = int(capture_contract["timeout_seconds"])
    rules = contract["rules"]
    notices = contract["annual_closure_notices"]
    sources = []
    for index, item in enumerate(rules, start=1):
        sources.append({"source_id": f"rule_{item['market'].lower()}_{item['effective_from']}_{index}", **item})
    for item in notices:
        sources.append({"source_id": f"closures_{item['market'].lower()}_{item['year']}", **item})
    if len(sources) > int(capture_contract["maximum_requests_per_run"]):
        raise ValueError("SOURCE_REQUEST_BUDGET_EXCEEDED")

    capture_id = datetime.now(timezone.utc).strftime("capture_%Y%m%dT%H%M%SZ")
    output_root = ROOT / capture_contract["store_under"] / capture_id
    if output_root.exists():
        raise ValueError("CAPTURE_ID_ALREADY_EXISTS")
    opener = build_opener(BoundedRedirectHandler(allowed))
    evidence = []
    total_bytes = 0
    for item in sources:
        source_url = item["source_url"] if "source_url" in item else item["source_url"]
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or parsed.hostname not in allowed:
            raise ValueError(f"SOURCE_URL_OUTSIDE_ALLOWLIST:{source_url}")
        request = Request(source_url, headers={"User-Agent": "V4-02-Official-Calendar-Source-Capture/1.0", "Accept": "text/html,application/xhtml+xml"})
        try:
            with opener.open(request, timeout=timeout) as response:
                final_url = response.geturl()
                final = urlparse(final_url)
                if final.scheme != "https" or final.hostname not in allowed:
                    raise ValueError(f"FINAL_URL_OUTSIDE_ALLOWLIST:{final_url}")
                data = response.read(max_page + 1)
                if len(data) > max_page:
                    raise ValueError(f"PAGE_SIZE_LIMIT_EXCEEDED:{item['source_id']}")
                status = int(response.status)
                content_type = response.headers.get("Content-Type", "")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"SOURCE_CAPTURE_FAILED:{item['source_id']}:{type(exc).__name__}") from exc
        if status != 200 or not data:
            raise ValueError(f"SOURCE_RESPONSE_NOT_ACCEPTED:{item['source_id']}:{status}")
        total_bytes += len(data)
        if total_bytes > max_total:
            raise ValueError("TOTAL_SOURCE_SIZE_LIMIT_EXCEEDED")
        filename = f"{item['source_id']}.html"
        atomic_bytes(output_root / filename, data)
        evidence.append({
            "source_id": item["source_id"],
            "source_url": source_url,
            "final_url": final_url,
            "http_status": status,
            "content_type": content_type,
            "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source_published_date": item.get("notice_date"),
            "relative_path": filename,
            "byte_count": len(data),
            "sha256": sha256_bytes(data),
        })
        time.sleep(0.2)

    manifest = {
        "contract_id": "V4_OFFICIAL_EXCHANGE_CALENDAR_SOURCE_CAPTURE_V1",
        "capture_id": capture_id,
        "calendar_contract_sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "request_count": len(evidence),
        "total_response_bytes": total_bytes,
        "sources": evidence,
        "calendar_capability": "SOURCE_EVIDENCE_CAPTURED_PARSE_AND_INDEPENDENT_ACCEPTANCE_PENDING",
        "next_stage": "PARSE_CLOSURES_AND_COMPARE_EXCHANGE_SESSIONS",
    }
    atomic_bytes(output_root / "source_capture_manifest.json", (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"capture_id": capture_id, "source_count": len(evidence), "total_bytes": total_bytes, "path": output_root.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
