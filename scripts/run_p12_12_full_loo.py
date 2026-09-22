from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from production.release import atomic_write_json
from tdx.security_master import current_a_stock_ids, read_industry_assignments
from workbench_analysis.full_loo_v3_3 import CONTRACT_ID, recompute_full_current_loo
from workbench_analysis.sector_attention import build_sector_current
from workbench_service.research_bundle_v3_3 import read_active
from workbench_service.research_builder import _market_universe_metadata_path
from workbench_service.universe import is_workbench_statistical_security_id


DB = Path(os.environ.get("WORKBENCH_COMPUTE_DUCKDB", str(ROOT / "data/database/market_research.duckdb"))).resolve()
POINTER = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
OUT = ROOT / "reports/p12_12/p12_12_full_loo.json"


def _equal_number(left, right, tolerance=1e-12):
    if pd.isna(left) and pd.isna(right):
        return True
    return not pd.isna(left) and not pd.isna(right) and abs(float(left) - float(right)) <= tolerance


def _truth(value):
    return None if value is None or pd.isna(value) else bool(value)


def main() -> None:
    active = read_active(POINTER)
    bundle_path = Path(active["bundle_path"])
    candidates = json.loads((bundle_path / "results.json").read_text(encoding="utf-8"))
    targets = sorted({str(row["security_id"]) for row in candidates})
    config = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))
    with duckdb.connect(str(DB), read_only=True) as connection:
        identity = active["identity"]
        legacy = connection.execute(
            """select run_id,publication_id,trade_date,snapshot_id,dependency_bindings
                 from research_runs where publication_id=? and trade_date=? and status='COMPLETE'
                 order by completed_at desc limit 1""",
            [identity["publication_id"], identity["trade_date"]],
        ).fetchone()
        if not legacy:
            raise RuntimeError("P12_12_BOUND_RESEARCH_RUN_MISSING")
        run_id, publication_id, trade_date, snapshot_id, dependency_bindings = legacy
        dependencies = json.loads(dependency_bindings) if isinstance(dependency_bindings, str) else dependency_bindings
        source_path = connection.execute(
            "select source_path from publications where publication_id=?", [publication_id]
        ).fetchone()[0]
        source_bundle_id = Path(str(source_path)).name
        source_scope, revision, attribute_version_id = connection.execute(
            "select source_scope,revision_no,attribute_version_id from relation_publication_bindings where publication_id=?",
            [publication_id],
        ).fetchone()
        members = connection.execute(
            """select e.sector_id,e.security_id,a.name sector_name,a.type sector_type,a.role sector_role
                 from relation_edge_intervals e
                 join sector_attribute_revisions ar on ar.source_scope=e.source_scope
                  and ('attrset-' || substr(ar.attribute_set_hash,1,24))=?
                 join sector_attribute_revision_bindings ab on ab.source_scope=e.source_scope and ab.sector_id=e.sector_id
                  and ab.from_attribute_revision<=ar.attribute_revision
                  and (ab.to_attribute_revision is null or ar.attribute_revision<ab.to_attribute_revision)
                 join sector_attribute_versions a on a.source_scope=ab.source_scope and a.sector_id=ab.sector_id
                  and a.attribute_version_id=ab.attribute_version_id
                where e.source_scope=? and e.from_revision<=? and (e.to_revision is null or ?<e.to_revision)""",
            [attribute_version_id, source_scope, revision, revision],
        ).fetchdf().drop_duplicates(["sector_id", "security_id"])
        start_date, end_date = dependencies["history_sessions"]
        adjusted = str((ROOT / "data/normalized/adjusted_daily.parquet").resolve())
        quotes = connection.execute(
            """with source as (
                   select security_id,date,raw_close,
                          lag(raw_close) over(partition by security_id order by date) previous_close,
                          data_observed
                     from read_parquet(?) where date between ? and ?)
               select security_id,
                      case when data_observed then raw_close/previous_close-1 else null end ret1
                 from source where date=?""",
            [adjusted, start_date, end_date, trade_date],
        ).fetchdf()
        stored = connection.execute(
            """select sector_id,current_eligible,m1,b1,rel1,p1,member_count,quote_valid_count
                 from research_sector_states where run_id=? order by sector_id""", [run_id]
        ).fetchdf()
    metadata = _market_universe_metadata_path(ROOT, source_bundle_id, trade_date)
    universe = sorted(current_a_stock_ids(read_industry_assignments(metadata)))
    universe = [security_id for security_id in universe if is_workbench_statistical_security_id(security_id, ROOT)]
    market = pd.DataFrame({"security_id": universe}).merge(quotes, on="security_id", how="left", validate="one_to_one")
    market["trade_date"] = trade_date
    member_quotes = members.merge(market[["security_id", "ret1"]], on="security_id", how="left", validate="many_to_one")
    member_quotes["trade_date"] = trade_date

    baseline = build_sector_current(member_quotes, market, config)
    joined = stored.merge(baseline, on="sector_id", suffixes=("_stored", "_rebuilt"), validate="one_to_one")
    parity_fields = {
        "m1_stored": "m1_rebuilt", "b1_stored": "b1_rebuilt", "rel1_stored": "rel1_rebuilt",
        "p1_stored": "p1_rebuilt", "member_count": "total_member_count",
        "quote_valid_count_stored": "quote_valid_count_rebuilt",
    }
    mismatches = []
    for row in joined.to_dict("records"):
        stored_current = _truth(row["current_eligible"])
        rebuilt_current = _truth(row["current"])
        bad = stored_current != rebuilt_current or any(not _equal_number(row[left], row[right]) for left, right in parity_fields.items())
        if bad:
            mismatches.append(row["sector_id"])
    if len(joined) != len(stored) or mismatches:
        raise RuntimeError("P12_12_BASELINE_PARITY_FAILED:" + ",".join(mismatches[:10]))

    audits = recompute_full_current_loo(targets, member_quotes, market, config)
    counts = {
        "true": sum(row["support"] is True for row in audits.values()),
        "false": sum(row["support"] is False for row in audits.values()),
        "unknown": sum(row["support"] is None for row in audits.values()),
    }
    payload = {
        "stage": "P12-12_FULL_LOO",
        "stage_contract": "P12-12_FULL_LOO_ACCEPTANCE_V1",
        "algorithm_contract": CONTRACT_ID,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_identity": {**identity, "legacy_research_run_id": run_id},
        "source_bindings": {
            "relation_source_scope": source_scope, "relation_revision": revision,
            "attribute_version_id": attribute_version_id,
            "market_universe_contract": dependencies["market_universe"],
            "market_universe_hash": dependencies["market_universe_hash"],
            "market_universe_count": len(universe),
            "adjusted_daily_sha256": dependencies["adjusted_daily_sha256"],
        },
        "baseline_parity": {"sector_count": len(joined), "mismatch_count": 0, "fields": ["CURRENT", *parity_fields]},
        "candidate_count": len(targets),
        "support_counts": counts,
        "audits": audits,
        "qualification_or_rank_changed": False,
        "usage": "SHADOW_EVIDENCE_ONLY_UNTIL_INCREMENTAL_EFFECT_AUDIT",
        "acceptance": "FULL_PASS",
        "tdx_modified": False,
        "next_stage": "P12-13_HISTORY_MATERIALIZATION_PILOT",
    }
    payload["audit_sha256"] = hashlib.sha256(json.dumps(audits, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    atomic_write_json(OUT, payload)
    print(json.dumps({key: payload[key] for key in ("stage", "acceptance", "candidate_count", "support_counts", "audit_sha256", "next_stage")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
