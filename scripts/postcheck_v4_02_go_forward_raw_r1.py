"""Independent read-only verification of the R1 source blocker."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from struct import unpack


ROOT = Path(__file__).resolve().parents[1]
TDX = Path("D:/new_tdx/vipdoc")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_RAW_SOURCE_SNAPSHOT_R1.json").read_text(encoding="utf-8"))
    assert source["status"] == "V4_02_GO_FORWARD_BLOCKED_NO_COMPLETE_20260928_RAW"
    assert source["target_trade_date"] == "2026-09-28"
    assert source["valid_project_controlled_20260928_package_count"] == 0
    attempt = source["official_capture_attempt"]
    assert digest(ROOT / attempt["path"]) == attempt["sha256"]
    assert attempt["result"] == {"status": "BLOCKED_TDX_SOURCE_CAPTURE", "reason": "TDX_ZIP_INVALID"}
    info = source["observed_official_info"]
    assert digest(ROOT / info["path"]) == info["sha256"]
    assert "2026-09-28 15:58:05" in (ROOT / info["path"]).read_text(encoding="utf-8")
    assert not list((ROOT / "data/v4/source_snapshots/tdx/20260928").glob("sha256-*/hsjday.zip"))
    for market in ("sh", "sz"):
        found = 0
        for path in (TDX / market / "lday").glob("*.day"):
            if path.stat().st_size < 32 or path.stat().st_size % 32:
                continue
            with path.open("rb") as stream:
                stream.seek(-32, 2)
                found += unpack("<I", stream.read(4))[0] == 20260928
        assert found == source["local_tdx_read_only_last_record_counts"][market]["files_with_last_record_20260928"] == 0
    gbbq = json.loads((ROOT / "reports/v4_02/V4_02_GBBQ_FORWARD_SNAPSHOT_FREEZE_20260926.json").read_text(encoding="utf-8"))
    assert digest(ROOT / gbbq["manifest_path"]) == source["gbbq_manifest_sha256"]
    assert source["historical_as_recorded_adjusted_price"] == "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"
    print("INDEPENDENT_POSTCHECK_PASS_FOR_BLOCK: no complete Sep-28 raw snapshot; GBBQ hash intact")


if __name__ == "__main__":
    main()
