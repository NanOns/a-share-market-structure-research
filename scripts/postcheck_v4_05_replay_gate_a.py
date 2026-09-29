"""Independent, read-only crosscheck of V4-05 blocked gate evidence."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "reports/v4_05/V4_05_REPLAY_GATE_A_AUDIT_R1.json"
MATRIX = ROOT / "reports/v4_05/V4_05_REPLAY_DATE_MATRIX_R1.json"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    head = json.loads((ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    assert digest(ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json") == matrix["authority"]["global_head_sha256"]
    assert digest(ROOT / head["v4_04_binding"]["path"]) == matrix["authority"]["v4_04_accepted_head_sha256"]
    accepted = json.loads((ROOT / head["v4_04_binding"]["path"]).read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / accepted["accepted_manifest"]["path"]).read_text(encoding="utf-8"))
    production = json.loads((ROOT / manifest["evidence"]["production"]["path"]).read_text(encoding="utf-8"))
    source = production["sources"]["daily"]
    daily = ROOT / source["path"]
    assert digest(daily) == source["sha256"] == matrix["input_hashes"]["daily"]
    counts = duckdb.connect().execute(
        "SELECT knowledge_lineage, count(*) FROM read_parquet(?) GROUP BY 1", [str(daily)]
    ).fetchall()
    assert counts == [("DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT", 4026611)]
    assert audit["gates"]["G03_ADJUSTMENT_REPRODUCIBILITY"]["status"] == "BLOCKED"
    assert audit["gates"]["G03_ADJUSTMENT_REPRODUCIBILITY"]["lineage_counts"][0]["rows"] == counts[0][1]
    assert all(audit["gates"][k]["status"] == "NOT_RUN_BLOCKED_BY_G03" for k in audit["gates"] if k.startswith(("G04", "G05", "G06", "G07", "G08")))
    assert audit["data_factor_replay_pass"] is False
    assert audit["status"] == "V4_05_BLOCKED_UPSTREAM_DEFECT_HISTORICAL_ADJUSTED_PRICE_PIT_LINEAGE"
    print("INDEPENDENT_POSTCHECK_PASS: accepted hash chain, 4026611 diagnostic rows, G03 block and downstream halt")


if __name__ == "__main__":
    main()
