from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from production.release import atomic_write_json
from workbench_service.research_bundle_v3_3 import read_active
from workbench_service.research_registry_v3_3 import register_active_bundle


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def main() -> None:
    database = ROOT / "data/database/market_research.duckdb"
    pointer = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
    active = read_active(pointer)
    bundle_path = Path(active["bundle_path"])
    expected = json.loads((bundle_path / "results.json").read_text(encoding="utf-8"))
    expected_by_id = {row["security_id"]: canonical(row) for row in expected}
    with duckdb.connect(str(database)) as connection:
        legacy_before = connection.execute("select count(*) from research_runs").fetchone()[0]
        v33_before = connection.execute("select count(*) from research_runs_v3_3").fetchone()[0]
        candidates_before = connection.execute("select count(*) from research_candidates_v3_3").fetchone()[0]
        replay = register_active_bundle(connection, pointer)
        legacy_after = connection.execute("select count(*) from research_runs").fetchone()[0]
        v33_after = connection.execute("select count(*) from research_runs_v3_3").fetchone()[0]
        candidates_after = connection.execute("select count(*) from research_candidates_v3_3").fetchone()[0]
        run = connection.execute(
            """select bundle_digest,research_run_id,cast(trade_date as varchar),publication_id,
                      snapshot_id,membership_snapshot_id,bundle_contract_id,result_count,status
                 from research_runs_v3_3 where bundle_digest=?""", [active["output_digest"]]
        ).fetchone()
        stored = dict(connection.execute(
            "select security_id,result_payload from research_candidates_v3_3 where bundle_digest=? order by security_id",
            [active["output_digest"]],
        ).fetchall())
    payload_match = stored == expected_by_id
    identity = active["identity"]
    identity_match = bool(run) and run[0] == active["output_digest"] and run[1] == identity["research_run_id"] and run[2] == identity["trade_date"] and run[3] == identity["publication_id"] and run[4] == identity["snapshot_id"] and run[5] == identity["membership_snapshot_id"] and run[6] == active["contract_id"] and run[7] == len(expected) and run[8] == "COMPLETE"
    idempotent = replay["reused"] and (legacy_before, v33_before, candidates_before) == (legacy_after, v33_after, candidates_after)
    acceptance = "FULL_PASS" if payload_match and identity_match and idempotent and len(stored) == len(expected) else "BLOCKED"
    receipt = {
        "stage": "P12-11_V3_3_DATABASE_REGISTRY",
        "contract_id": "P12-11_V3_3_DATABASE_REGISTRY_ACCEPTANCE_V1",
        "acceptance": acceptance,
        "bundle_digest": active["output_digest"],
        "trade_date": identity["trade_date"],
        "publication_id": identity["publication_id"],
        "research_run_id": identity["research_run_id"],
        "bundle_rows": len(expected),
        "database_rows": len(stored),
        "identity_match": identity_match,
        "payload_match": payload_match,
        "idempotent_replay": idempotent,
        "legacy_research_runs_unchanged": legacy_before == legacy_after,
        "payload_set_sha256": hashlib.sha256(canonical(expected_by_id).encode()).hexdigest(),
        "tdx_modified": False,
        "next_stage": "P12-12_FULL_LOO",
    }
    atomic_write_json(ROOT / "reports/p12_11/p12_11_stage_gate.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    if acceptance != "FULL_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
