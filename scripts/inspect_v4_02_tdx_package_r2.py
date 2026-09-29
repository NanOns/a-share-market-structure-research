"""Validate frozen TDX ZIP target-date content and project-owned extraction."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
from struct import unpack_from
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.tdx_official_daily_source import _zip_validate  # noqa: E402

CAPTURE = ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json"
OUT = ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_PACKAGE_RECEIPT_R2.json"
DAY_BYTES = 32


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    capture = json.loads(CAPTURE.read_text(encoding="utf-8"))
    if capture["status"] != "TDX_PACKAGE_READY":
        raise ValueError("TDX_PACKAGE_NOT_READY")
    archive_path = ROOT / capture["package_path"]
    if digest(archive_path) != capture["package_sha256"]:
        raise ValueError("PACKAGE_HASH_MISMATCH")
    validation = _zip_validate(archive_path)
    extract_root = ROOT / "data/v4/source_snapshot_store/tdx_daily" / f"sha256-{capture['package_sha256']}"
    counts = Counter()
    max_date = 0
    future = 0
    files = 0
    bytes_total = 0
    identity = sha256()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            parts = name.split("/")
            if len(parts) not in (3, 4) or parts[-2].lower() != "lday" or parts[-3].lower() not in ("sh", "sz", "bj"):
                raise ValueError(f"UNEXPECTED_PACKAGE_LAYOUT:{name}")
            market = parts[-3].lower()
            raw = archive.read(info)
            if not raw or len(raw) % DAY_BYTES:
                counts[f"{market}_invalid_or_empty_day_files"] += 1
                # Official packages can contain empty non-equity entries. They
                # are inventoried but cannot supply a stock or target-date bar.
                continue
            last = unpack_from("<I", raw, len(raw) - DAY_BYTES)[0]
            first = unpack_from("<I", raw, 0)[0]
            if last > 20260928:
                future += sum(unpack_from("<I", raw, offset)[0] > 20260928 for offset in range(0, len(raw), DAY_BYTES))
            counts[f"{market}_files"] += 1
            counts[f"{market}_files_with_20260928_bar"] += last == 20260928
            counts[f"{market}_files_first_after_20260928"] += first > 20260928
            max_date = max(max_date, last)
            file_sha = sha256(raw).hexdigest()
            identity.update(f"{name}\0{file_sha}\0{len(raw)}\n".encode())
            target = extract_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if digest(target) != file_sha:
                    raise ValueError(f"EXTRACTION_IMMUTABLE_COLLISION:{name}")
            else:
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                    stream.write(raw)
                    temp = Path(stream.name)
                os.replace(temp, target)
            files += 1
            bytes_total += len(raw)
    if max_date != 20260928 or future or not counts["sh_files_with_20260928_bar"] or not counts["sz_files_with_20260928_bar"]:
        status = "V4_02_GO_FORWARD_BLOCKED_TARGET_DATE_CONTENT"
    else:
        status = "TARGET_DATE_CONTENT_PASS"
    result = {"contract_id": "V4_02_GO_FORWARD_TDX_PACKAGE_RECEIPT_R2", "status": status,
              "package_path": capture["package_path"], "package_sha256": capture["package_sha256"],
              "package_bytes": archive_path.stat().st_size, "zip_validation": validation,
              "extraction_root": extract_root.relative_to(ROOT).as_posix(),
              "extraction_file_count": files, "extraction_uncompressed_bytes": bytes_total,
              "extraction_manifest_digest": identity.hexdigest(), "market_counts": dict(counts),
              "target_date_total_bars": sum(counts[f"{m}_files_with_20260928_bar"] for m in ("sh", "sz", "bj")),
              "max_raw_trade_date": max_date, "future_date_bar_count": future, "tdx_root_write_count": 0}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, OUT)
    print(status, result["target_date_total_bars"])


if __name__ == "__main__":
    main()
