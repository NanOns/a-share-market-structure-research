from __future__ import annotations

"""Bounded capture of official primary-source notices used by R4 phase rows."""

import hashlib
import gzip
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/v4/source_evidence/v4_02_r4"
EVENTS_OUT = ROOT / "reports/v4_02/V4_02_SPECIAL_PRICE_PHASE_EVENTS_R4.jsonl"
CAPTURE_INDEX = ROOT / "reports/v4_02/V4_02_R4_OFFICIAL_SOURCE_CAPTURE_INDEX.json"
AUDIT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json"
MAX_BYTES = 8 * 1024 * 1024
TIMEOUT_SECONDS = 20

# Each tuple is security key, effective first session, official primary-source URL.
EVENTS = [
    ("SZ.002089", "2024-03-26", "https://disc.static.szse.cn/disc/disk03/finalpage/2024-03-25/c08ea022-30dc-4d90-a3f7-11c514bbc2ba.PDF"),
    ("SH.600306", "2024-05-29", "https://static.cninfo.com.cn/finalpage/2024-05-22/1220123086.PDF"),
    ("SZ.000996", "2024-06-06", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2024-06-12/fe247eec-8ef9-495e-beca-0a08b20a842f.PDF"),
    ("SZ.002087", "2024-06-06", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2024-06-12/a9fea7ce-8869-42ac-9003-add883db1d4d.PDF"),
    ("SZ.002433", "2024-06-14", "https://disc.static.szse.cn/disc/disk03/finalpage/2024-07-05/4dcf022c-f8be-4cb7-9f95-92ea0a43a215.PDF"),
    ("SZ.300282", "2024-06-27", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2024-06-19/036f4c2f-5c7f-4f3d-86e6-203b200a951c.PDF"),
    ("SZ.300742", "2024-07-01", "https://disc.static.szse.cn/disc/disk03/finalpage/2024-07-18/b70be163-2311-4be0-9684-fb11389dc08e.PDF"),
    ("SZ.300799", "2024-07-08", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2024-07-23/f89b1793-c2e7-402e-9c04-0ba5acf0ab23.PDF"),
    ("SH.600225", "2025-02-07", "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-01-23/600225_20250123_J43G.pdf"),
    ("SZ.002750", "2025-06-06", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-05-28/6f1d2aa7-c851-48bb-bb68-40ee8722152a.PDF"),
    ("SH.600804", "2025-06-10", "https://static.cninfo.com.cn/finalpage/2025-06-27/1224000143.PDF"),
    ("SZ.002336", "2025-06-13", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-06-05/a738c06e-1ab3-4ebc-9cba-69c1d096fa99.PDF"),
    ("SH.600387", "2025-06-16", "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-07-05/600387_20250705_IHOT.pdf"),
    ("SH.600462", "2025-06-24", "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-06-17/600462_20250617_IVSV.pdf"),
    ("SZ.000622", "2025-06-25", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-07-07/ced3b8e1-aa35-4ec4-a86d-9fac1715b689.PDF"),
    ("SZ.300208", "2025-06-30", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-07-18/50367678-fd5f-4fd0-8d4c-cbb4bbe5cbd0.PDF"),
    ("SH.600190", "2025-06-30", "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-07-15/600190_20250715_QCG8.pdf"),
    ("SZ.300280", "2025-09-15", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-09-29/31509ed2-ccfa-457a-8143-0cf932c0ad79.PDF"),
    ("SZ.300379", "2025-12-30", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-12-30/f6b7a196-25e5-460b-b63d-acae106b49c4.PDF"),
    ("SZ.300391", "2026-03-20", "https://disc.static.szse.cn/disc/disk03/finalpage/2026-03-20/3475068f-8133-413b-8e59-4793fbf96d85.PDF"),
    ("SH.600696", "2026-06-01", "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-05-23/600696_20260523_19HN.pdf"),
    ("SZ.002808", "2026-06-23", "https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-07-13/31425c3f-8bd0-48de-a9f4-4106a2686109.PDF"),
]


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 V4-02-R4-audit/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("SOURCE_CAPTURE_EXCEEDS_8_MIB")
    # urllib does not decode a gzip Content-Encoding response for us. Store the
    # actual PDF entity and hash it, while keeping each bounded response under
    # the request-size limit above.
    if data.startswith(b"\x1f\x8b"):
        data = gzip.decompress(data)
    if len(data) > MAX_BYTES:
        raise ValueError("DECOMPRESSED_SOURCE_CAPTURE_EXCEEDS_8_MIB")
    if not data.startswith(b"%PDF-"):
        raise ValueError("SOURCE_RESPONSE_NOT_PDF")
    return data


def main() -> int:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    rows = {row["source_security_key"]: row for row in audit.get("r3_findings", [])}
    observed = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    captures, events, failures = {}, [], []
    for source_key, day, url in EVENTS:
        try:
            payload = fetch(url)
            digest = hashlib.sha256(payload).hexdigest()
            file_name = f"{source_key.replace('.', '_')}_{day}_delisting_phase.pdf"
            relative = f"data/v4/source_evidence/v4_02_r4/{file_name}"
            atomic_write(ROOT / relative, payload)
            captures[url] = {"path": relative, "sha256": digest, "bytes": len(payload), "status": "CAPTURED"}
            match = rows.get(source_key)
            if match is None or match.get("trade_date") != day:
                raise ValueError("SOURCE_EVENT_DOES_NOT_BIND_TO_R3_EXCEPTION");
            events.append({
                "security_id": match["security_id"], "source_security_key": source_key,
                "board_scope": match["board_scope"], "trade_date": day,
                "phase": "DELISTING_FIRST_DAY", "event_type": "EXCHANGE_DELISTING_PERIOD_START",
                "source_ref": url, "source_capture_path": relative,
                "source_capture_sha256": digest, "effective_date": day, "observed_at": observed,
                "official_reference_price": None, "official_reference_formula": None,
            })
        except Exception as exc:
            failures.append({"source_security_key": source_key, "trade_date": day, "source_ref": url,
                             "status": "CAPTURE_FAILED", "reason": type(exc).__name__ + ":" + str(exc)})
    event_bytes = b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for row in events)
    atomic_write(EVENTS_OUT, event_bytes)
    index = {"contract_id": "V4_02_R4_OFFICIAL_SOURCE_CAPTURE_INDEX", "version": "1.0.0",
             "status": "CAPTURED_WITH_ROW_SCOPED_FAILURES" if failures else "CAPTURED",
             "captures": captures, "events_emitted": len(events), "failures": failures,
             "max_bytes_per_request": MAX_BYTES, "timeout_seconds": TIMEOUT_SECONDS,
             "observed_at_utc": observed}
    atomic_write(CAPTURE_INDEX, (json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"events": len(events), "captures": len(captures), "failures": len(failures), "event_sha256": hashlib.sha256(event_bytes).hexdigest()}))
    return 0 if events else 2


if __name__ == "__main__":
    raise SystemExit(main())
