"""Build a dated Sep-28 candidate from the accepted Sep-24 universe and alias map."""

from __future__ import annotations

from collections import Counter
import gzip
import json
import os
from pathlib import Path
from struct import unpack_from
import zipfile
from src.v4.go_forward_r3 import target_identity

ROOT = Path(__file__).resolve().parents[1]
TARGET = "2026-09-28"


def main() -> None:
    capture = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json").read_text(encoding="utf-8"))
    identity = json.loads((ROOT / "data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json").read_text(encoding="utf-8"))
    accepted = {}
    with gzip.open(ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] == "2026-09-24":
                accepted[row["source_security_key"]] = row
    target_bars = set()
    with zipfile.ZipFile(ROOT / capture["package_path"]) as archive:
        for info in archive.infolist():
            name = Path(info.filename).stem.lower()
            if len(name) != 8 or name[:2] not in ("sh", "sz"):
                continue
            code = name[2:]
            if not (code.startswith(("60", "68")) if name[:2] == "sh" else code.startswith(("00", "30"))):
                continue
            if info.file_size < 32:
                continue
            data = archive.read(info)
            if unpack_from("<I", data, len(data) - 32)[0] == 20260928:
                target_bars.add(f"{name[:2].upper()}.{code}")
    active_map, unknown = target_identity(set(accepted), target_bars, identity["records"], TARGET)
    new = sorted(target_bars - accepted.keys())
    dropped = sorted(set(accepted) - active_map.keys())
    preserved = sorted(set(accepted) & active_map.keys())
    board = Counter(("STAR" if key.startswith("SH.68") else "SH_MAIN" if key.startswith("SH.") else "CHINEXT" if key.startswith("SZ.30") else "SZ_MAIN") for key in active_map)
    status = "PASS_CANDIDATE" if not unknown and not dropped else "V4_02_GO_FORWARD_BLOCKED_UNIVERSE_IDENTITY"
    result = {"contract_id": "V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R3", "status": status,
              "target_trade_date": TARGET, "accepted_cutoff": "2026-09-24", "package_sha256": capture["package_sha256"],
              "accepted_security_count": len(accepted), "preserved_security_count": len(preserved),
              "target_actual_bar_count": len(target_bars), "board_counts": dict(board),
              "new_source_keys": new, "unresolved_target_source_keys": unknown,
              "new_source_key_identity": {key: {"security_id": active_map[key]["security_id"], "list_date": active_map[key].get("list_date"), "source_revision_id": active_map[key].get("source_revision_id")} for key in new if key in active_map},
              "candidate_security_count": len(active_map),
              "unexplained_dropped_source_keys": dropped,
              "no_target_bar_count": len(set(preserved) - target_bars),
              "code_change_identity": [dict(security_id=row["security_id"], successor=row["source_security_key"], effective_from=row.get("symbol_effective_from")) for row in identity["records"] if row.get("alias_role") == "SUCCESSOR" and row.get("symbol_effective_from") and row["symbol_effective_from"] <= TARGET],
              "membership_basis": "ACCEPTED_20260924_UNIVERSE_PLUS_DATED_ACCEPTED_ALIAS_MAP_AND_T0_OFFICIAL_BARS",
              "source_revision": capture["package_sha256"]}
    path = ROOT / "reports/v4_02/V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R3.json"
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)
    print(status, len(accepted), len(target_bars), len(new), len(unknown), len(dropped))


if __name__ == "__main__":
    main()
