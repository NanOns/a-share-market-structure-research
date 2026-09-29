"""Read-only source gate for the 2026-09-28 PIT amendment candidate."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
from struct import unpack
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TDX = Path("D:/new_tdx/vipdoc")
OUT = ROOT / "reports/v4_02/V4_02_GO_FORWARD_RAW_SOURCE_SNAPSHOT_R1.json"
GBBQ_RECEIPT = ROOT / "reports/v4_02/V4_02_GBBQ_FORWARD_SNAPSHOT_FREEZE_20260926.json"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    gbbq = json.loads(GBBQ_RECEIPT.read_text(encoding="utf-8"))
    manifest = ROOT / gbbq["manifest_path"]
    assert digest(manifest) == gbbq["manifest_sha256"]
    for name, expected in gbbq["file_hashes"].items():
        assert digest(manifest.parent / name) == expected
    captures = sorted((ROOT / "data/v4/source_snapshots/tdx/20260928").glob("capture-*/update_info.js"))
    current = captures[-1]
    attempt_path = ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R1.json"
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert attempt["captured_update_info"] == current.relative_to(ROOT).as_posix()
    counts = {}
    for market in ("sh", "sz", "bj"):
        rows = Counter()
        invalid = 0
        for path in (TDX / market / "lday").glob("*.day"):
            size = path.stat().st_size
            if size < 32 or size % 32:
                invalid += 1
                continue
            with path.open("rb") as stream:
                stream.seek(-32, 2)
                day = unpack("<I", stream.read(4))[0]
            rows[day] += 1
        counts[market] = {"files": sum(rows.values()) + invalid, "invalid_files": invalid,
                          "latest_last_record_date": max(rows) if rows else None,
                          "files_with_last_record_20260928": rows[20260928]}
    target_ready = all(counts[m]["files_with_last_record_20260928"] > 0 for m in ("sh", "sz"))
    package_dirs = list((ROOT / "data/v4/source_snapshots/tdx/20260928").glob("sha256-*/hsjday.zip"))
    result = {
        "contract_id": "V4_02_GO_FORWARD_RAW_SOURCE_SNAPSHOT_GATE_R1",
        "status": "RAW_SOURCE_CANDIDATE_AVAILABLE" if target_ready and package_dirs else "V4_02_GO_FORWARD_BLOCKED_NO_COMPLETE_20260928_RAW",
        "target_trade_date": "2026-09-28",
        "observed_official_info": {"path": current.relative_to(ROOT).as_posix(), "sha256": digest(current), "text": current.read_text(encoding="utf-8")},
        "official_capture_attempt": {"path": attempt_path.relative_to(ROOT).as_posix(),
                                     "sha256": digest(attempt_path), "result": attempt["result"]},
        "valid_project_controlled_20260928_package_count": len(package_dirs),
        "local_tdx_read_only_last_record_counts": counts,
        "gbbq_snapshot_id": gbbq["snapshot_id"],
        "gbbq_manifest_sha256": gbbq["manifest_sha256"],
        "gbbq_system_available_at": gbbq["system_available_at"],
        "gbbq_file_hashes_verified": gbbq["file_hashes"],
        "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE",
        "tdx_root_write_count": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=OUT.parent, encoding="utf-8", delete=False) as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        temp = Path(stream.name)
    os.replace(temp, OUT)
    print(result["status"])


if __name__ == "__main__":
    main()
