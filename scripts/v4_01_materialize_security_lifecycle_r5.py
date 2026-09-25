from __future__ import annotations

"""Append candidate, revisionable V4-01 lifecycle facts into the formal schema."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.apply_v4_phase0_schema import dsn  # noqa: E402
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_revision_id(fact_key: str, content_sha: str) -> str:
    return "LIFE-R5-" + hashlib.sha256(f"{fact_key}\0{content_sha}".encode("utf-8")).hexdigest()[:48]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    ap.add_argument("--receipt", default="reports/v4_01/security_lifecycle_materialization_receipt_R5_20260925.json")
    args = ap.parse_args()
    map_path = ROOT / args.identity_map
    identity_doc = json.loads(map_path.read_text(encoding="utf-8"))
    lifecycle_rows = [row for row in identity_doc["records"] if row.get("security_type") == "A_STOCK"]
    inserted = 0
    skipped_existing = 0
    observed_at = datetime.now(timezone.utc).replace(microsecond=0)
    inserted_ids: list[str] = []
    with psycopg.connect(dsn()) as pg:
        with pg.transaction():
            for identity in lifecycle_rows:
                effective_from = identity.get("symbol_effective_from") or identity.get("list_date")
                if not effective_from:
                    continue
                symbol = identity["symbol"]
                fact_key = f"{identity['security_id']}|lifecycle|{symbol}|{effective_from}"
                payload = {
                    "security_id": identity["security_id"], "symbol": symbol,
                    "security_type": identity["security_type"], "board": identity.get("board"),
                    "list_date": identity.get("list_date"), "delist_date": identity.get("delist_date"),
                    "effective_from": effective_from, "effective_to": identity.get("symbol_effective_to"),
                    "status": "LISTED_INTERVAL_CANDIDATE", "quality": identity.get("identity_quality"),
                    "source_contract_id": identity["source_contract_id"],
                    "source_identity": f"{identity['source_contract_id']}:{identity['source_revision_id']}:{identity['source_security_key']}",
                }
                content_sha = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
                revision_id = source_revision_id(fact_key, content_sha)
                prior = pg.execute(
                    "select source_revision_id, revision_no from v4.source_revisions where logical_fact_id=%s order by revision_no desc limit 1 for update",
                    (fact_key,),
                ).fetchone()
                existing = pg.execute(
                    "select 1 from v4.source_revisions where source_revision_id=%s", (revision_id,)
                ).fetchone()
                if existing:
                    skipped_existing += 1
                    continue
                parent_id = prior[0].strip() if prior else None
                revision_no = int(prior[1]) + 1 if prior else 1
                ingested_at = datetime.now(timezone.utc).replace(microsecond=0)
                system_available_at = max(observed_at, ingested_at)
                pg.execute(
                    """insert into v4.source_revisions(source_revision_id,logical_fact_id,revision_no,payload,digest,
                         effective_from,effective_to,provider_available_at,observed_at,ingested_at,system_available_at,
                         supersedes_revision_id,tombstone)
                       values (%s,%s,%s,%s::jsonb,%s,%s,%s,null,%s,%s,%s,%s,false)""",
                    (revision_id, fact_key, revision_no, canonical(payload), content_sha, effective_from,
                     identity.get("symbol_effective_to"), observed_at, ingested_at, system_available_at, parent_id),
                )
                pg.execute(
                    """insert into v4.security_lifecycle_history(lifecycle_fact_key,security_id,symbol,security_type,
                         board,list_date,delist_date,effective_from,effective_to,status,quality,source_contract_id,
                         provider_available_at,observed_at,ingested_at,system_available_at,source_revision_id,
                         supersedes_revision_id,source_identity)
                       values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,null,%s,%s,%s,%s,%s,%s)""",
                    (fact_key, identity["security_id"], symbol, identity["security_type"], identity.get("board"),
                     identity.get("list_date"), identity.get("delist_date"), effective_from,
                     identity.get("symbol_effective_to"), "LISTED_INTERVAL_CANDIDATE",
                     identity.get("identity_quality", "IDENTITY_QUALITY_UNKNOWN"), identity["source_contract_id"],
                     observed_at, ingested_at, system_available_at, revision_id, parent_id, payload["source_identity"]),
                )
                inserted += 1
                inserted_ids.append(revision_id)

    with psycopg.connect(dsn()) as pg:
        table_count, security_count, fact_count = pg.execute(
            "select count(*), count(distinct security_id), count(distinct lifecycle_fact_key) from v4.security_lifecycle_history"
        ).fetchone()
        invalid_timestamps = pg.execute(
            "select count(*) from v4.security_lifecycle_history where system_available_at<>greatest(observed_at,ingested_at)"
        ).fetchone()[0]
        invalid_source = pg.execute(
            """select count(*) from v4.security_lifecycle_history h join v4.source_revisions s using(source_revision_id)
               where s.logical_fact_id<>h.lifecycle_fact_key or s.supersedes_revision_id is distinct from h.supersedes_revision_id"""
        ).fetchone()[0]
    receipt = {
        "stage": "V4-01-FORMAL-LIFECYCLE-FACTS-R5",
        "contract_id": "SECURITY_LIFECYCLE_HISTORY_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "BLOCKED" if identity_doc["unresolved"] or identity_doc["non_core_candidates"] or invalid_timestamps or invalid_source else "CANDIDATE_ACCEPTANCE_PENDING",
        "stage_completion_authorized": False,
        "lineage": "RECONSTRUCTED_CORRECTED candidate facts; pre-V4 history is never labeled AS_RECORDED",
        "input": {"identity_map_path": args.identity_map,
                  "identity_map_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
                  "identity_map_status": identity_doc["status"]},
        "materialization": {"inserted_revision_rows": inserted, "already_materialized_rows_skipped": skipped_existing,
                            "database_lifecycle_fact_rows": table_count,
                            "unique_security_ids": security_count, "unique_lifecycle_fact_keys": fact_count,
                            "timestamp_rule_violation_count": invalid_timestamps,
                            "source_revision_binding_violation_count": invalid_source,
                            "append_only": True},
        "source_revision_sample_ids": inserted_ids[:10],
        "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()},
        "next_stage": "V4_01_FINAL_HISTORICAL_UNIVERSE_R5",
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], **receipt["materialization"], "receipt": args.receipt}, ensure_ascii=False))
    return 0 if receipt["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
