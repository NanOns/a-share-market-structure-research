from __future__ import annotations

"""Capture the two official 2023 annual closure notices under frozen bounds."""

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
CONTRACT_PATH = ROOT / "config/v4_official_calendar_2023_h2_source_capture_v1.json"


class AllowlistedRedirect(HTTPRedirectHandler):
    def __init__(self, allowed: set[str]) -> None:
        super().__init__()
        self.allowed = allowed

    def redirect_request(self, request, fp, code, message, headers, new_url):
        parsed = urlparse(new_url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed:
            raise ValueError("REDIRECT_OUTSIDE_ALLOWLIST")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main() -> int:
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract = json.loads(contract_bytes)
    budget = contract["source_capture"]
    sources = contract["sources"]
    if len(sources) > int(budget["maximum_requests_per_run"]):
        raise ValueError("REQUEST_BUDGET_EXCEEDED")
    allowed = set(budget["allowed_hosts"])
    capture_id = datetime.now(timezone.utc).strftime("capture_%Y%m%dT%H%M%SZ")
    out = ROOT / budget["store_under"] / capture_id
    if out.exists():
        raise ValueError("CAPTURE_ID_ALREADY_EXISTS")
    opener = build_opener(AllowlistedRedirect(allowed))
    total = 0
    records = []
    for item in sources:
        url = item["source_url"]
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in allowed:
            raise ValueError(f"SOURCE_URL_OUTSIDE_ALLOWLIST:{item['source_id']}")
        req = Request(url, headers={"User-Agent": "V4-02-Official-Calendar-2023H2-Capture/1.0", "Accept": "text/html,application/xhtml+xml"})
        try:
            with opener.open(req, timeout=int(budget["timeout_seconds"])) as response:
                final_url = response.geturl()
                final = urlparse(final_url)
                if final.scheme != "https" or final.hostname not in allowed:
                    raise ValueError("FINAL_URL_OUTSIDE_ALLOWLIST")
                data = response.read(int(budget["maximum_response_bytes_per_page"]) + 1)
                status = int(response.status)
                content_type = response.headers.get("Content-Type", "")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"SOURCE_CAPTURE_FAILED:{item['source_id']}:{type(exc).__name__}") from exc
        if status != 200 or not data or len(data) > int(budget["maximum_response_bytes_per_page"]):
            raise ValueError(f"SOURCE_RESPONSE_NOT_ACCEPTED:{item['source_id']}:{status}")
        total += len(data)
        if total > int(budget["maximum_total_response_bytes"]):
            raise ValueError("TOTAL_RESPONSE_SIZE_LIMIT_EXCEEDED")
        filename = f"{item['source_id']}.html"
        atomic_write(out / filename, data)
        records.append({
            **item,
            "final_url": final_url,
            "http_status": status,
            "content_type": content_type,
            "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "relative_path": filename,
            "byte_count": len(data),
            "sha256": sha256(data),
        })
        time.sleep(0.2)
    manifest = {
        "contract_id": "V4_OFFICIAL_CALENDAR_2023_H2_CAPTURE_RECEIPT_V1",
        "capture_id": capture_id,
        "source_contract_sha256": sha256(contract_bytes),
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "request_count": len(records),
        "total_response_bytes": total,
        "sources": records,
        "status": "SOURCE_CAPTURED_PARSE_AND_POSTCHECK_PENDING",
    }
    atomic_write(out / "capture_manifest.json", (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"capture_id": capture_id, "request_count": len(records), "total_bytes": total, "path": out.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
