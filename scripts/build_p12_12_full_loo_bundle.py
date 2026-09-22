from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from production.release import atomic_write_json
from workbench_analysis.today_research_rank_loo_v3_3 import rank
from workbench_service.research_bundle_v3_3 import activate_bundle, build_bundle, read_active
from workbench_service.research_registry_v3_3 import register_active_bundle


BUNDLE_CONTRACT = "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO"
POINTER = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
REPORT = ROOT / "reports/p12_12/p12_12_full_loo.json"
OUT = ROOT / "reports/p12_12/p12_12_full_loo_bundle_gate.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    active = read_active(POINTER)
    if active["contract_id"] != "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02":
        if active["contract_id"] == BUNDLE_CONTRACT:
            print(json.dumps({"stage": "P12-12_FULL_LOO_BUNDLE", "acceptance": "FULL_PASS", "reused": True, "output_digest": active["output_digest"]}, ensure_ascii=False, indent=2))
            return
        raise RuntimeError("P12_12_BASE_BUNDLE_CONTRACT_MISMATCH")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("acceptance") != "FULL_PASS" or report["input_identity"]["publication_id"] != active["identity"]["publication_id"] or report["input_identity"]["trade_date"] != active["identity"]["trade_date"]:
        raise RuntimeError("P12_12_FULL_LOO_REPORT_IDENTITY_MISMATCH")
    source = json.loads((Path(active["bundle_path"]) / "results.json").read_text(encoding="utf-8"))
    rows = []
    removed = []
    for row in source:
        audit = report["audits"][row["security_id"]]
        matched = [category for category in row.get("matched_categories", []) if category != "TREND_CONTINUE" or audit["support"] is True]
        if not matched:
            removed.append(row["security_id"])
            continue
        rows.append({
            **row,
            "matched_categories": matched,
            "selection_mode": "SUPPORTED" if audit["support"] is True else "INDEPENDENT",
            "sector_support_status": "CONFIRMED" if audit["support"] is True else "UNKNOWN" if audit["support"] is None else "NOT_CONFIRMED",
            "full_loo_audit": audit,
            "support_method": "FULL_CURRENT_TRACK_LOO_V1",
            "full_track_recomputed_without_target": True,
        })
    ranked = rank(rows)
    source_hashes = {"base_bundle": active["output_digest"], "full_loo_report": sha(REPORT)}
    identity = {
        **active["identity"],
        "research_run_id": "p12-12-" + hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()[:24],
        "parameter_hash": hashlib.sha256(b"parameters-v3_3-candidate-03-full-current-track-loo").hexdigest(),
    }
    contracts = json.loads((Path(active["bundle_path"]) / "contracts.json").read_text(encoding="utf-8"))
    contracts.update({"bundle": BUNDLE_CONTRACT, "full_loo": report["algorithm_contract"], "source_hashes_p12_12": source_hashes})
    built = build_bundle(ROOT / "data/research_bundles_v3_3", identity, ranked, contracts, bundle_contract=BUNDLE_CONTRACT)
    activated = activate_bundle(Path(built["path"]), POINTER)
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb")) as connection:
        registered = register_active_bundle(connection, POINTER)
    receipt = {
        "stage": "P12-12_FULL_LOO_BUNDLE", "acceptance": "FULL_PASS",
        "base_rows": len(source), "published_rows": len(ranked), "removed_trend_only": removed,
        "supported_rows": sum(row["selection_mode"] == "SUPPORTED" for row in ranked),
        "independent_rows": sum(row["selection_mode"] == "INDEPENDENT" for row in ranked),
        "bundle": built, "database_registration": registered,
        "pointer_verified": read_active(POINTER)["output_digest"] == activated["output_digest"],
        "tdx_modified": False, "next_stage": "P12-13_HISTORY_MATERIALIZATION_PILOT",
    }
    atomic_write_json(OUT, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
