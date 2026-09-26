from __future__ import annotations

"""Append R6.2 normalized membership intervals and corrected lifecycle revisions."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.apply_v4_phase0_schema import dsn  # noqa: E402
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402

CONTRACT = "DATED_ROSTER_MEMBERSHIP_BOUNDARY_V1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        with temp.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as stream:
                    for row in rows:
                        stream.write(canonical(row) + "\n")
        with temp.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def revision_id(prefix: str, fact_key: str, content_sha: str) -> str:
    return prefix + hashlib.sha256(f"{fact_key}\0{content_sha}".encode("utf-8")).hexdigest()[:48]


def latest_revision(pg: psycopg.Connection, fact_key: str) -> tuple[str, int] | None:
    row = pg.execute(
        "select source_revision_id,revision_no from v4.source_revisions where logical_fact_id=%s order by revision_no desc limit 1 for update",
        (fact_key,),
    ).fetchone()
    return (row[0].strip(), int(row[1])) if row else None


def insert_source_revision(pg: psycopg.Connection, *, fact_key: str, revision: str, payload: dict[str, Any],
                           effective_from: str | None, effective_to: str | None,
                           observed_at: datetime, ingested_at: datetime, parent: tuple[str, int] | None,
                           content_sha: str) -> None:
    pg.execute(
        """insert into v4.source_revisions(source_revision_id,logical_fact_id,revision_no,payload,digest,
             effective_from,effective_to,provider_available_at,observed_at,ingested_at,system_available_at,
             supersedes_revision_id,tombstone)
           values (%s,%s,%s,%s::jsonb,%s,%s,%s,null,%s,%s,%s,%s,false)""",
        (revision, fact_key, parent[1] + 1 if parent else 1, canonical(payload), content_sha,
         effective_from, effective_to, observed_at, ingested_at, max(observed_at, ingested_at), parent[0] if parent else None),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    ap.add_argument("--provider-facts", default="reports/v4_01/baostock_lifecycle_facts_R4_20260925.json")
    ap.add_argument("--provider-fact-contract", default="config/v4_provider_lifecycle_fact_v1.json")
    ap.add_argument("--intervals", default="data/v4/artifact_store/v4_01/security_membership_intervals_R6_2_20260926.jsonl.gz")
    ap.add_argument("--boundary-receipt", default="reports/v4_01/V4_01_LIFECYCLE_BOUNDARY_RESOLUTION_R6_2.json")
    ap.add_argument("--receipt", default="reports/v4_01/security_lifecycle_materialization_receipt_R6_2_20260926.json")
    ap.add_argument("--current-intervals", default="data/v4/artifact_store/v4_01/security_membership_intervals_current_R6_2_20260926.jsonl.gz")
    args = ap.parse_args()
    map_path, facts_path, interval_path = ROOT / args.identity_map, ROOT / args.provider_facts, ROOT / args.intervals
    provider_contract_path = ROOT / args.provider_fact_contract
    boundary_path = ROOT / args.boundary_receipt
    boundary = json.loads(boundary_path.read_text("utf-8"))
    if boundary.get("status") != "PASS" or boundary.get("resolution", {}).get("unresolved_boundary_count") != 0:
        raise SystemExit("R6_2_BOUNDARY_RESOLUTION_NOT_PASS")
    if boundary.get("all_day_coverage", {}).get("total_missing_required_identity_rows") != 0:
        raise SystemExit("R6_2_ALL_DAY_COVERAGE_NOT_PASS")
    identity_doc = json.loads(map_path.read_text("utf-8"))
    raw_facts = json.loads(facts_path.read_text("utf-8"))
    provider_contract = json.loads(provider_contract_path.read_text("utf-8"))
    if provider_contract.get("contract_id") != "PROVIDER_LIFECYCLE_FACT_V1":
        raise SystemExit("R6_2_PROVIDER_LIFECYCLE_FACT_CONTRACT_INVALID")
    fact_by_key = {str(row.get("source_security_key", "")).lower(): row for row in raw_facts["facts"]}
    intervals: list[dict[str, Any]] = []
    with gzip.open(interval_path, "rt", encoding="utf-8") as stream:
        intervals = [json.loads(line) for line in stream]
    intervals_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in intervals:
        intervals_by_key.setdefault(row["source_security_key"].lower(), []).append(row)
    resolver_path = ROOT / "scripts/v4_01_lifecycle_boundary_resolution_r6_2.py"
    evidence = {
        "roster_sha256": boundary["inputs"]["roster_sha256"],
        "r6_1_coverage_sha256": boundary["inputs"]["r6_1_coverage_sha256"],
        "provider_lifecycle_facts_sha256": boundary["inputs"]["provider_lifecycle_facts_sha256"],
        "resolver_script_sha256": boundary["inputs"]["resolver_script_sha256"],
        "normalized_interval_artifact_sha256": digest(interval_path),
        "boundary_receipt_sha256": digest(boundary_path),
        "provider_fact_contract_sha256": digest(provider_contract_path),
    }
    if evidence["resolver_script_sha256"] != digest(resolver_path):
        raise SystemExit("R6_2_RESOLVER_SCRIPT_CHANGED_AFTER_BOUNDARY_RECEIPT")

    observed_at = datetime.now(timezone.utc).replace(microsecond=0)
    ingested_at = datetime.now(timezone.utc).replace(microsecond=0)
    inserted_provider_facts = inserted_intervals = inserted_lifecycle = skipped = 0
    provider_fact_skipped = 0
    provider_raw_value_mismatch_count = 0
    lifecycle_revision_ids: list[str] = []
    interval_revision_ids: list[str] = []
    interval_fact_keys: set[str] = set()
    with psycopg.connect(dsn()) as pg:
        with pg.transaction():
            for raw_fact in raw_facts.get("facts", []):
                source_key = str(raw_fact.get("source_security_key", "")).upper()
                if not source_key:
                    raise SystemExit("R6_2_PROVIDER_LIFECYCLE_FACT_SOURCE_KEY_MISSING")
                fact_key = f"BAOSTOCK|provider_lifecycle|{source_key}"
                payload = {"provider": "BAOSTOCK", "source_security_key": source_key,
                           "provider_ipo_date": raw_fact.get("listed_from"),
                           "provider_out_date": raw_fact.get("listed_to_provider_reported"),
                           "provider_status": raw_fact.get("provider_status_observed"),
                           "raw_provider_contract_id": raw_facts.get("contract_id"),
                           "source_contract_id": provider_contract["contract_id"],
                           "source_capture_date": "2026-09-25", "raw_provider_fact": raw_fact,
                           "evidence": evidence}
                content_sha = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
                src_id = revision_id("PROV-R62-", fact_key, content_sha)
                if pg.execute("select 1 from v4.source_revisions where source_revision_id=%s", (src_id,)).fetchone():
                    provider_fact_skipped += 1
                    continue
                parent = latest_revision(pg, fact_key)
                insert_source_revision(pg, fact_key=fact_key, revision=src_id, payload=payload,
                                       effective_from=None, effective_to=None, observed_at=observed_at,
                                       ingested_at=ingested_at, parent=parent, content_sha=content_sha)
                pg.execute(
                    """insert into v4.provider_lifecycle_fact_history(provider_fact_key,provider,source_security_key,
                         provider_ipo_date,provider_out_date,provider_status,source_observation_date,
                         source_observation_time_quality,source_contract_id,raw_provider_contract_id,raw_provider_payload,
                         evidence,observed_at,ingested_at,system_available_at,source_revision_id,supersedes_revision_id,source_identity)
                       values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s)""",
                    (fact_key, "BAOSTOCK", source_key, raw_fact.get("listed_from"),
                     raw_fact.get("listed_to_provider_reported"), raw_fact.get("provider_status_observed"),
                     "2026-09-25", "DATE_ONLY_FROM_ARTIFACT_PROVENANCE", provider_contract["contract_id"],
                     raw_facts.get("contract_id"), canonical(raw_fact), canonical(evidence), observed_at,
                     ingested_at, max(observed_at, ingested_at), src_id, parent[0] if parent else None,
                     f"PROVIDER_LIFECYCLE_FACT_V1:{source_key}"),
                )
                inserted_provider_facts += 1

            for row in intervals:
                fact_key = f"{row['security_id']}|membership|{row['source_security_key']}|{row['roster_run_index']}"
                if fact_key in interval_fact_keys:
                    raise SystemExit("R6_2_INTERVAL_FACT_KEY_COLLISION")
                interval_fact_keys.add(fact_key)
                payload = {**row, "evidence": evidence}
                content_sha = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
                src_id = revision_id("MEM-R62-", fact_key, content_sha)
                if pg.execute("select 1 from v4.source_revisions where source_revision_id=%s", (src_id,)).fetchone():
                    skipped += 1
                    continue
                parent = latest_revision(pg, fact_key)
                insert_source_revision(pg, fact_key=fact_key, revision=src_id, payload=payload,
                                       effective_from=row["normalized_effective_from"],
                                       effective_to=row["normalized_effective_to"], observed_at=observed_at,
                                       ingested_at=ingested_at, parent=parent, content_sha=content_sha)
                pg.execute(
                    """insert into v4.security_membership_interval_history(membership_fact_key,security_id,source_security_key,
                         normalized_effective_from,normalized_effective_to,from_boundary_basis,to_boundary_basis,
                         provider_ipo_date,provider_out_date,first_observed_roster_date,last_observed_roster_date,
                         boundary_quality,source_contract_id,evidence,observed_at,ingested_at,system_available_at,
                         source_revision_id,supersedes_revision_id,source_identity)
                       values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s)""",
                    (fact_key, row["security_id"], row["source_security_key"], row["normalized_effective_from"],
                     row["normalized_effective_to"], row["from_boundary_basis"], row["to_boundary_basis"],
                     row.get("provider_ipo_date"), row.get("provider_out_date"), row.get("first_observed_roster_date"),
                     row.get("last_observed_roster_date"), row["boundary_quality"], CONTRACT, canonical(evidence),
                     observed_at, ingested_at, max(observed_at, ingested_at), src_id, parent[0] if parent else None,
                     f"{CONTRACT}:{row['security_identity_source_revision_id']}:{row['source_security_key']}"),
                )
                inserted_intervals += 1
                interval_revision_ids.append(src_id)

            # Add normalized R6.2 lifecycle revisions for every Required identity with an in-window outDate.
            changed_keys = {key for key, rows in intervals_by_key.items()
                            if any(row.get("provider_out_date") and "2023-07-04" <= row["provider_out_date"] <= "2026-09-24"
                                   for row in rows)}
            identities_by_key = {str(row.get("source_security_key", "")).lower(): row
                                 for row in identity_doc.get("records", [])}
            for key in sorted(changed_keys):
                identity = identities_by_key[key]
                raw_fact = fact_by_key[key]
                last_interval = max(intervals_by_key[key], key=lambda item: item["roster_run_index"])
                effective_from = identity.get("symbol_effective_from") or identity.get("list_date")
                lifecycle_fact_key = f"{identity['security_id']}|lifecycle|{identity['symbol']}|{effective_from}"
                prior_row = pg.execute(
                    """select source_revision_id,effective_from,effective_to,supersedes_revision_id
                       from v4.security_lifecycle_history where lifecycle_fact_key=%s
                       order by system_available_at desc limit 1 for update""", (lifecycle_fact_key,)
                ).fetchone()
                if not prior_row:
                    raise SystemExit(f"R6_2_CURRENT_LIFECYCLE_REVISION_MISSING:{key}")
                normalized_to = last_interval["normalized_effective_to"]
                payload = {
                    "security_id": identity["security_id"], "symbol": identity["symbol"],
                    "security_type": identity["security_type"], "board": identity.get("board"),
                    "list_date": raw_fact.get("listed_from"),
                    "delist_date": raw_fact.get("listed_to_provider_reported"),
                    "effective_from": effective_from, "effective_to": normalized_to,
                    "provider_out_date": raw_fact.get("listed_to_provider_reported"),
                    "to_boundary_basis": last_interval["to_boundary_basis"],
                    "status": "DATED_ROSTER_MEMBERSHIP_INTERVAL_CONFIRMED",
                    "quality": last_interval["boundary_quality"], "source_contract_id": CONTRACT,
                    "source_identity": f"{CONTRACT}:{identity['source_revision_id']}:{key}",
                    "evidence": evidence,
                }
                content_sha = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
                src_id = revision_id("LIFE-R62-", lifecycle_fact_key, content_sha)
                if pg.execute("select 1 from v4.source_revisions where source_revision_id=%s", (src_id,)).fetchone():
                    skipped += 1
                    continue
                parent = latest_revision(pg, lifecycle_fact_key)
                if not parent or parent[0] != prior_row[0].strip():
                    raise SystemExit(f"R6_2_LIFECYCLE_SUPERSESSION_RACE:{key}")
                insert_source_revision(pg, fact_key=lifecycle_fact_key, revision=src_id, payload=payload,
                                       effective_from=effective_from, effective_to=normalized_to,
                                       observed_at=observed_at, ingested_at=ingested_at, parent=parent,
                                       content_sha=content_sha)
                pg.execute(
                    """insert into v4.security_lifecycle_history(lifecycle_fact_key,security_id,symbol,security_type,
                         board,list_date,delist_date,effective_from,effective_to,status,quality,source_contract_id,
                         provider_available_at,observed_at,ingested_at,system_available_at,source_revision_id,
                         supersedes_revision_id,source_identity)
                       values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,null,%s,%s,%s,%s,%s,%s)""",
                    (lifecycle_fact_key, identity["security_id"], identity["symbol"], identity["security_type"],
                     identity.get("board"), raw_fact.get("listed_from"), raw_fact.get("listed_to_provider_reported"),
                     effective_from, normalized_to, payload["status"], payload["quality"], CONTRACT,
                     observed_at, ingested_at, max(observed_at, ingested_at), src_id, parent[0], payload["source_identity"]),
                )
                inserted_lifecycle += 1
                lifecycle_revision_ids.append(src_id)

    with psycopg.connect(dsn()) as pg:
        provider_fact_count = pg.execute("select count(*) from v4.provider_lifecycle_fact_history").fetchone()[0]
        current_provider_rows = pg.execute(
            """select h.source_security_key,h.provider_ipo_date,h.provider_out_date,h.provider_status,h.raw_provider_payload
               from (select distinct on (h.provider_fact_key) h.*
                     from v4.provider_lifecycle_fact_history h
                     join v4.source_revisions s using(source_revision_id)
                     order by h.provider_fact_key,s.revision_no desc) h"""
        ).fetchall()
        expected_provider = {str(row["source_security_key"]).upper(): row for row in raw_facts.get("facts", [])}
        current_provider = {str(row[0]).upper(): row for row in current_provider_rows}
        if set(expected_provider) != set(current_provider):
            provider_raw_value_mismatch_count += len(set(expected_provider) ^ set(current_provider))
        for key in set(expected_provider) & set(current_provider):
            expected = expected_provider[key]
            actual = current_provider[key]
            expected_ipo = expected.get("listed_from")
            expected_out = expected.get("listed_to_provider_reported")
            actual_ipo = actual[1].isoformat() if actual[1] else None
            actual_out = actual[2].isoformat() if actual[2] else None
            if (actual_ipo != expected_ipo or actual_out != expected_out
                    or actual[3] != expected.get("provider_status_observed")
                    or actual[4] != expected):
                provider_raw_value_mismatch_count += 1
        provider_source_binding_invalid = pg.execute(
            """select count(*) from v4.provider_lifecycle_fact_history h join v4.source_revisions s using(source_revision_id)
               where s.logical_fact_id<>h.provider_fact_key or s.supersedes_revision_id is distinct from h.supersedes_revision_id
                  or h.system_available_at<>greatest(h.observed_at,h.ingested_at)"""
        ).fetchone()[0]
        provider_append_only_trigger_count = pg.execute(
            "select count(*) from pg_trigger where tgrelid='v4.provider_lifecycle_fact_history'::regclass and not tgisinternal and tgname='v4_provider_lifecycle_fact_append_only'"
        ).fetchone()[0]
        interval_count = pg.execute("select count(*) from v4.security_membership_interval_history").fetchone()[0]
        interval_fact_count = pg.execute("select count(distinct membership_fact_key) from v4.security_membership_interval_history").fetchone()[0]
        invalid_interval_binding = pg.execute(
            """select count(*) from v4.security_membership_interval_history h join v4.source_revisions s using(source_revision_id)
               where s.logical_fact_id<>h.membership_fact_key or s.supersedes_revision_id is distinct from h.supersedes_revision_id
                  or s.effective_from is distinct from h.normalized_effective_from or s.effective_to is distinct from h.normalized_effective_to
                  or h.system_available_at<>greatest(h.observed_at,h.ingested_at)"""
        ).fetchone()[0]
        append_only_trigger_count = pg.execute(
            "select count(*) from pg_trigger where tgrelid='v4.security_membership_interval_history'::regclass and not tgisinternal and tgname='v4_security_membership_interval_append_only'"
        ).fetchone()[0]
        lifecycle_normalized_count = pg.execute(
            """select count(*) from (select distinct on (h.lifecycle_fact_key) h.lifecycle_fact_key,h.source_contract_id
                 from v4.security_lifecycle_history h join v4.source_revisions s using(source_revision_id)
                 order by h.lifecycle_fact_key,s.revision_no desc) current_facts where source_contract_id=%s""",
            (CONTRACT,),
        ).fetchone()[0]
        lifecycle_history_revision_count = pg.execute(
            "select count(*) from v4.security_lifecycle_history where source_contract_id=%s", (CONTRACT,)
        ).fetchone()[0]
        lifecycle_supersession_invalid = pg.execute(
            """select count(*) from v4.security_lifecycle_history h join v4.source_revisions s using(source_revision_id)
               where h.source_contract_id=%s and (s.logical_fact_id<>h.lifecycle_fact_key
                  or s.supersedes_revision_id is distinct from h.supersedes_revision_id
                  or s.effective_to is distinct from h.effective_to)""", (CONTRACT,)
        ).fetchone()[0]
        current_rows = pg.execute(
            """select h.membership_fact_key,h.security_id,h.source_security_key,h.normalized_effective_from,
                      h.normalized_effective_to,h.from_boundary_basis,h.to_boundary_basis,h.provider_ipo_date,
                      h.provider_out_date,h.first_observed_roster_date,h.last_observed_roster_date,h.boundary_quality,
                      h.source_contract_id,h.evidence,h.source_revision_id,h.supersedes_revision_id
               from (select distinct on (h.membership_fact_key) h.*
                     from v4.security_membership_interval_history h
                     join v4.source_revisions s using(source_revision_id)
                     order by h.membership_fact_key,s.revision_no desc) h
               order by h.source_security_key,h.normalized_effective_from,h.membership_fact_key"""
        ).fetchall()
    current_interval_rows = []
    for row in current_rows:
        current_interval_rows.append({
            "membership_fact_key": row[0], "security_id": row[1], "source_security_key": row[2],
            "normalized_effective_from": row[3].isoformat(),
            "normalized_effective_to": row[4].isoformat() if row[4] else None,
            "from_boundary_basis": row[5], "to_boundary_basis": row[6],
            "provider_ipo_date": row[7].isoformat() if row[7] else None,
            "provider_out_date": row[8].isoformat() if row[8] else None,
            "first_observed_roster_date": row[9].isoformat() if row[9] else None,
            "last_observed_roster_date": row[10].isoformat() if row[10] else None,
            "boundary_quality": row[11], "source_contract_id": row[12], "evidence": row[13],
            "source_revision_id": row[14].strip(),
            "supersedes_revision_id": row[15].strip() if row[15] else None,
        })
    current_interval_path = ROOT / args.current_intervals
    write_jsonl_gz(current_interval_path, current_interval_rows)
    receipt = {
        "stage": "V4-01-R6_2-APPEND-ONLY-LIFECYCLE-MATERIALIZATION",
        "contract_id": "SECURITY_MEMBERSHIP_INTERVAL_V1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if provider_fact_count == len(raw_facts.get("facts", []))
                  and provider_raw_value_mismatch_count == 0 and provider_source_binding_invalid == 0 and provider_append_only_trigger_count == 1
                  and interval_fact_count == len(intervals)
                  and invalid_interval_binding == 0 and append_only_trigger_count == 1
                  and lifecycle_normalized_count == 129 and lifecycle_supersession_invalid == 0 else "BLOCKED",
        "stage_completion_authorized": False,
        "append_only": True,
        "provider_facts": {"newly_appended_revision_rows": inserted_provider_facts,
                           "already_present_revision_rows": provider_fact_skipped,
                           "database_revision_rows": provider_fact_count,
                           "raw_provider_value_mismatch_count": provider_raw_value_mismatch_count,
                           "source_revision_binding_violation_count": provider_source_binding_invalid,
                           "append_only_trigger_present": provider_append_only_trigger_count == 1,
                           "source_contract_id": provider_contract["contract_id"],
                           "source_sample_keys": [row.get("source_security_key") for row in raw_facts.get("facts", [])[:8]]},
        "intervals": {"newly_appended_revision_rows": inserted_intervals, "already_present_revision_rows": skipped,
                      "database_revision_rows": interval_count, "distinct_fact_keys": interval_fact_count,
                      "current_fact_count": interval_fact_count,
                      "source_revision_binding_violation_count": invalid_interval_binding,
                      "append_only_trigger_present": append_only_trigger_count == 1,
                      "current_interval_artifact_path": args.current_intervals,
                      "current_interval_artifact_sha256": digest(current_interval_path),
                      "current_interval_artifact_row_count": len(current_interval_rows),
                      "source_revision_sample_ids": interval_revision_ids[:8]},
        "lifecycle_revisions": {"newly_appended_revision_rows": inserted_lifecycle,
                                "expected_in_window_outdate_resolution_count": 129,
                                "database_normalized_revision_rows": lifecycle_normalized_count,
                                "database_normalized_history_revision_rows": lifecycle_history_revision_count,
                                "supersession_binding_violation_count": lifecycle_supersession_invalid,
                                "source_revision_sample_ids": lifecycle_revision_ids[:8]},
        "evidence": evidence,
        "input": {"identity_map_path": args.identity_map, "identity_map_sha256": digest(map_path),
                  "provider_facts_path": args.provider_facts, "provider_facts_sha256": digest(facts_path),
                  "provider_fact_contract_path": args.provider_fact_contract,
                  "provider_fact_contract_sha256": digest(provider_contract_path),
                  "intervals_path": args.intervals, "intervals_sha256": digest(interval_path),
                  "boundary_receipt_path": args.boundary_receipt, "boundary_receipt_sha256": digest(boundary_path)},
        "execution_identity": {"code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()},
        "next_stage": "V4_01_R6_2_REBUILD_HISTORICAL_UNIVERSE" if interval_count == len(intervals) and lifecycle_normalized_count == 129 else "V4_01_REMEDIATE_R6_2_MATERIALIZATION",
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "intervals": receipt["intervals"],
                      "lifecycle_revisions": receipt["lifecycle_revisions"], "receipt": args.receipt}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
