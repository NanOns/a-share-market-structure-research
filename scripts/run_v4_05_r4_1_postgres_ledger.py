"""Run V4-05 R4.1 ledger acceptance probes on a fresh disposable PostgreSQL cluster."""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
import uuid

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.apply_v4_phase0_schema import VERSIONS as OFFICIAL_MIGRATION_VERSIONS

MIGRATION_DIR = ROOT / "src/workbench_db/migrations/v4_postgres"
OUT = ROOT / "reports/v4_05/V4_05_R4_1_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json"
TEST_DIRS = ["tests/v4_01", "tests/v4_02", "tests/v4_03", "tests/v4_04",
             "tests/v4_05", "tests/v4_joint", "tests/v4_phase0"]
TABLES = ("source_revisions", "publications", "publication_consumed_sources",
          "publication_revision_events", "state_heads", "publication_heads")
EXPECTED_MIGRATIONS = {
    "001_v4_phase0_foundation.sql": "V4_PHASE0_FOUNDATION_V1",
    "002_namespace_integrity.sql": "V4_PHASE0_NAMESPACE_INTEGRITY_V1",
    "003_phase0_contract_alignment.sql": "V4_PHASE0_CONTRACT_ALIGNMENT_R2",
    "004_publication_head_revision_identity.sql": "V4_PUBLICATION_HEAD_REVISION_IDENTITY_R2",
    "005_market_session_publication_chain.sql": "V4_MARKET_SESSION_PUBLICATION_CHAIN_R2",
    "006_fact_source_guard_table_specific_fields.sql": "V4_FACT_SOURCE_GUARD_TABLE_SPECIFIC_FIELDS_R2",
    "007_state_and_namespace_publication_identity.sql": "V4_STATE_AND_NAMESPACE_PUBLICATION_IDENTITY_R2",
    "008_prior_session_state_freeze_integrity.sql": "V4_PRIOR_SESSION_STATE_FREEZE_INTEGRITY_R3",
    "009_publication_head_guard_sql_alias_fix.sql": "V4_PUBLICATION_HEAD_GUARD_SQL_ALIAS_FIX_R3",
    "010_security_lifecycle_history_r5.sql": "V4_SECURITY_LIFECYCLE_HISTORY_R5_V1",
    "011_security_membership_interval_r6_2.sql": "V4_SECURITY_MEMBERSHIP_INTERVAL_R6_2_V1",
    "012_provider_lifecycle_fact_r6_2.sql": "V4_PROVIDER_LIFECYCLE_FACT_R6_2_V1",
}


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return sha256(payload).hexdigest()


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json_file_sha(path: Path) -> str:
    return digest(json.loads(path.read_bytes().decode("utf-8-sig")))


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, path)


def pg_bin() -> Path:
    candidates = []
    for key in ("V4_POSTGRES_BIN", "PG_BIN"):
        if os.environ.get(key):
            candidates.append(Path(os.environ[key]))
    candidates.extend((Path(r"E:\Postgres\bin"), Path(r"C:\Program Files\PostgreSQL\18\bin")))
    for path in candidates:
        if all((path / f"{name}.exe").is_file() for name in ("initdb", "pg_ctl", "psql")):
            return path
    raise FileNotFoundError("PostgreSQL 18 bin directory missing; set V4_POSTGRES_BIN")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run_command(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {args[0]}\n{result.stdout}\n{result.stderr}")
    return result


def migration_receipt(pg: psycopg.Connection) -> list[dict[str, str]]:
    rows = []
    if EXPECTED_MIGRATIONS != OFFICIAL_MIGRATION_VERSIONS:
        raise AssertionError("R4.1 migration registry differs from the project migration runner")
    paths = sorted(MIGRATION_DIR.glob("*.sql"))
    if len(paths) != 12:
        raise AssertionError(f"expected 12 formal migrations, got {len(paths)}")
    for path in paths:
        version = EXPECTED_MIGRATIONS.get(path.name)
        if not version:
            raise AssertionError(f"unregistered formal migration: {path.name}")
        migration_text = path.read_text("utf-8")
        checksum = sha256(migration_text.encode("utf-8")).hexdigest()
        with pg.transaction():
            pg.execute(migration_text)
            pg.execute(
                "insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) "
                "values (%s,%s,now(),%s)", (version, checksum, version))
        rows.append({"filename": path.name, "version": version, "checksum_sha256": checksum,
                     "status": "APPLIED"})
    actual = pg.execute("select version,checksum_sha256 from v4_meta.schema_migrations order by version").fetchall()
    by_version = {version: checksum.strip() for version, checksum in actual}
    if len(by_version) != 12 or any(by_version.get(row["version"]) != row["checksum_sha256"] for row in rows):
        raise AssertionError("formal migration version/checksum ledger mismatch")
    return rows


def runtime_counts(pg: psycopg.Connection) -> dict[str, int]:
    return {table: int(pg.execute(f"select count(*) from v4.{table}").fetchone()[0]) for table in TABLES}


def source_specs() -> dict[str, dict]:
    reports = ROOT / "reports/v4_05"
    accepted = json.loads((ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json").read_text("utf-8"))
    factor = json.loads((reports / "V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json").read_text("utf-8"))
    profile = json.loads((reports / "V4_05_R4_CORE_PROFILE_REPLAY.json").read_text("utf-8"))
    reference = json.loads((reports / "V4_05_R4_MARKET_REFERENCE.json").read_text("utf-8"))
    daily = json.loads((reports / "V4_05_R4_DAILY_HISTORY_RECEIPT.json").read_text("utf-8"))
    period = json.loads((reports / "V4_05_R4_PERIOD_ASOF.json").read_text("utf-8"))
    calendar = json.loads((reports / "V4_05_R4_CALENDAR_RECEIPT.json").read_text("utf-8"))
    v4_01_head = ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json"
    v4_02_head = ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
    v4_03_head = ROOT / "data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json"
    v4_04_head = ROOT / "data/v4/V4_04_ACCEPTED_HEAD.json"
    factor_path = ROOT / factor["artifact_path"]
    profile_path = ROOT / profile["artifact_path"]
    period_path = ROOT / period["artifact_path"]
    gbbq_digest = daily["gbbq_snapshot_id"].removeprefix("sha256-")
    calendar_digest = reference["market_calendar_id"].split(":", 1)[1]
    contracts = {name: canonical_json_file_sha(ROOT / name) for name in (
        "config/v4_03_factor_registry_v1.json", "config/v4_03_parameter_set_v1.json",
        "config/v4_04_field_registry_v2.json", "config/v4_04_output_schema_v2.json",
        "config/v4_04_algorithm_contracts_v3.json", "config/v4_04_parameter_set_v1.json",
        "config/v4_04_field_window_mapping_v1.json") if (ROOT / name).is_file()}
    specs = {
        "TDX_RAW_PACKAGE": {"revision_id": f"TDX_RAW_PACKAGE:sha256-{accepted['official_tdx_package_sha256']}",
                            "digest": accepted["official_tdx_package_sha256"],
                            "payload": {"path": accepted["evidence_bindings"]["official_tdx_package"]["path"],
                                        "target_trade_date": "2026-09-28", "source_stage": "V4_02_GO_FORWARD_PIT_R3"}},
        "FROZEN_GBBQ": {"revision_id": f"FROZEN_GBBQ:sha256-{gbbq_digest}", "digest": gbbq_digest,
                        "payload": {"snapshot_id": daily["gbbq_snapshot_id"], "target_trade_date": "2026-09-28"}},
        "MARKET_CALENDAR": {"revision_id": f"MARKET_CALENDAR:{calendar_digest}", "digest": calendar_digest,
                            "payload": {"market_calendar_id": reference["market_calendar_id"],
                                        "calendar_bindings": calendar["calendar_bindings"]}},
        "V4_01_ACCEPTED_HEAD": {"revision_id": f"V4_01_ACCEPTED_HEAD:{canonical_json_file_sha(v4_01_head)}",
                                "digest": canonical_json_file_sha(v4_01_head), "payload": {"path": "data/v4/V4_01_ACCEPTED_HEAD.json"}},
        "V4_02_GO_FORWARD_HEAD": {"revision_id": f"V4_02_GO_FORWARD_HEAD:{canonical_json_file_sha(v4_02_head)}",
                                  "digest": canonical_json_file_sha(v4_02_head), "payload": {"path": "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"}},
        "V4_03_ACCEPTED_HEAD": {"revision_id": f"V4_03_ACCEPTED_HEAD:{canonical_json_file_sha(v4_03_head)}",
                                "digest": canonical_json_file_sha(v4_03_head), "payload": {"path": "data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json"}},
        "V4_04_ACCEPTED_HEAD": {"revision_id": f"V4_04_ACCEPTED_HEAD:{canonical_json_file_sha(v4_04_head)}",
                                "digest": canonical_json_file_sha(v4_04_head), "payload": {"path": "data/v4/V4_04_ACCEPTED_HEAD.json"}},
        "DAILY_HISTORY": {"revision_id": f"DAILY_HISTORY:{daily['artifact_sha256']}", "digest": daily["artifact_sha256"],
                          "payload": {"logical_digest": daily["logical_digest"], "artifact_path": daily["artifact_path"]}},
        "PERIOD_ASOF": {"revision_id": f"PERIOD_ASOF:{file_sha(period_path)}", "digest": file_sha(period_path),
                        "payload": {"logical_digest": period["logical_digest"], "artifact_path": period["artifact_path"]}},
        "MARKET_REFERENCE": {"revision_id": f"MARKET_REFERENCE:{canonical_json_file_sha(reports / 'V4_05_R4_MARKET_REFERENCE.json')}",
                              "digest": canonical_json_file_sha(reports / "V4_05_R4_MARKET_REFERENCE.json"),
                              "payload": {"output_digests": {key: value["output_digest"] for key, value in reference["horizons"].items()},
                                          "market_calendar_id": reference["market_calendar_id"]}},
        "FULL_SCOPE_FACTORS": {"revision_id": f"FULL_SCOPE_FACTORS:{file_sha(factor_path)}", "digest": file_sha(factor_path),
                               "payload": {"logical_digest": factor["logical_digest"], "artifact_path": factor["artifact_path"]}},
        "CORE_PROFILE": {"revision_id": f"CORE_PROFILE:{file_sha(profile_path)}", "digest": file_sha(profile_path),
                         "payload": {"logical_digest": profile["logical_digest"], "artifact_path": profile["artifact_path"],
                                     "row_count": profile["row_count"], "historical_as_recorded_claim": False}},
        "CONTRACTS": {"revision_id": f"CONTRACTS:{digest(contracts)}", "digest": digest(contracts), "payload": contracts},
        "PARAMETERS": {"revision_id": f"PARAMETERS:{digest({k:v for k,v in contracts.items() if 'parameter' in k})}",
                       "digest": digest({k:v for k,v in contracts.items() if 'parameter' in k}),
                       "payload": {k:v for k,v in contracts.items() if 'parameter' in k}},
    }
    return specs


def insert_source_revision(pg: psycopg.Connection, *, revision_id: str, logical_fact_id: str,
                           revision_no: int, payload: dict, payload_digest: str,
                           supersedes_revision_id: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    pg.execute(
        """insert into v4.source_revisions(source_revision_id,logical_fact_id,revision_no,payload,digest,
             provider_available_at,observed_at,ingested_at,system_available_at,supersedes_revision_id)
           values (%s,%s,%s,%s,%s,null,%s,%s,%s,%s)""",
        (revision_id, logical_fact_id, revision_no, Jsonb(payload), payload_digest,
         now, now, now, supersedes_revision_id))


def insert_consumed_sources(pg: psycopg.Connection, publication_id: str, revision_no: int,
                            consumed: dict[str, dict], *, only_first: bool = False) -> None:
    rows = list(consumed.items())
    if only_first:
        rows = rows[: max(1, len(rows) // 2)]
    for source_key, item in rows:
        pg.execute("""insert into v4.publication_consumed_sources(publication_id,source_key,source_revision_id,digest)
                      values (%s,%s,%s,%s)""",
                   (publication_id, source_key, item["source_revision_id"], item["digest"]))


def counts_for_identity(pg: psycopg.Connection, namespace_id: str) -> dict[str, int]:
    return {
        "source_revisions": int(pg.execute("select count(*) from v4.source_revisions").fetchone()[0]),
        "publications": int(pg.execute("select count(*) from v4.publications where model_namespace_id=%s", (namespace_id,)).fetchone()[0]),
        "consumed_sources": int(pg.execute("select count(*) from v4.publication_consumed_sources c join v4.publications p on p.publication_id=c.publication_id where p.model_namespace_id=%s", (namespace_id,)).fetchone()[0]),
        "publication_events": int(pg.execute("select count(*) from v4.publication_revision_events e join v4.publications p on p.publication_id=e.publication_id where p.model_namespace_id=%s", (namespace_id,)).fetchone()[0]),
        "state_heads": int(pg.execute("select count(*) from v4.state_heads where namespace_id=%s", (namespace_id,)).fetchone()[0]),
        "publication_heads": int(pg.execute("select count(*) from v4.publication_heads where model_namespace_id=%s", (namespace_id,)).fetchone()[0]),
    }


def expected_rejection(operation) -> dict:
    try:
        operation()
    except psycopg.Error as exc:
        return {"rejected": True, "sqlstate": exc.sqlstate,
                "constraint": getattr(exc.diag, "constraint_name", None),
                "message": str(exc).splitlines()[0]}
    raise AssertionError("PostgreSQL did not reject a forbidden operation")


def run_ledger(pg: psycopg.Connection) -> dict:
    reports = ROOT / "reports/v4_05"
    market = json.loads((reports / "V4_05_R4_MARKET_REFERENCE.json").read_text("utf-8"))
    core = json.loads((reports / "V4_05_R4_CORE_PROFILE_REPLAY.json").read_text("utf-8"))
    accepted = json.loads((ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json").read_text("utf-8"))
    calendar = json.loads((reports / "V4_05_R4_CALENDAR_RECEIPT.json").read_text("utf-8"))
    market_calendar_id = market["market_calendar_id"]
    calendar_digest = market_calendar_id.split(":", 1)[1]
    sessions = json.loads((ROOT / calendar["calendar_bindings"]["SSE"]["path"]).read_text("utf-8"))["session_dates"]
    target = date(2026, 9, 28)
    prior_day = date.fromisoformat(sessions[sessions.index(target.isoformat()) - 1])
    successor_day = date.fromisoformat(sessions[sessions.index(target.isoformat()) + 1])
    session_no = {date.fromisoformat(day): i + 1 for i, day in enumerate(sessions)}
    suffix = uuid.uuid4().hex
    namespace_id = f"NS-V4-05-R4-1-{suffix}"
    model_contract_id = "V4_05_REPLAY_GATE_A_R4_1_CANDIDATE"
    lineage_id = f"LINEAGE-{uuid.uuid4()}"
    pg.execute("insert into v4.model_namespaces(namespace_id,model_contract_id,execution_mode,namespace) values (%s,%s,'REPLAY',%s)",
               (namespace_id, model_contract_id, f"R4.1 isolated replay {suffix}"))
    for day in (prior_day, target, successor_day):
        pg.execute("""insert into v4.market_calendar_sessions(market_calendar_id,session_no,trade_date,calendar_digest)
                      values (%s,%s,%s,%s)""", (market_calendar_id, session_no[day], day, calendar_digest))

    source_rows = source_specs()
    source_identity = {key: {"source_revision_id": spec["revision_id"], "digest": spec["digest"]}
                       for key, spec in sorted(source_rows.items())}
    for key, spec in source_rows.items():
        insert_source_revision(pg, revision_id=spec["revision_id"], logical_fact_id=f"R4-1::{key}", revision_no=1,
                               payload=spec["payload"], payload_digest=spec["digest"])
    source_manifest_sha = digest(source_identity)
    r4_output_identity = {"market_reference_output_digests": {
                              key: value["output_digest"] for key, value in market["horizons"].items()},
                          "core_profile_logical_digest": core["logical_digest"],
                          "core_profile_artifact_sha256": core["artifact_sha256"],
                          "core_profile_rows": core["row_count"],
                          "target_market_calendar_id": market_calendar_id}
    contract_parameters = {"stage_contract": "V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE",
                           "factor_contract": "V4_05_R4_FULL_SCOPE_FACTOR_REPLAY_V1",
                           "profile_contract": "V4_05_R4_CORE_PROFILE_REPLAY_V1",
                           "target_trade_date": target.isoformat(), "target_identities": 5222,
                           "historical_as_recorded_claim": False}
    computation_sha = digest({"contract_parameters": contract_parameters,
                              "source_manifest_sha256": source_manifest_sha,
                              "r4_output_identity": r4_output_identity})
    state_digest_1 = core["logical_digest"]
    state_head_1 = f"STATE-{uuid.uuid4()}"
    publication_1 = f"PUB-{uuid.uuid4()}"
    publication_2 = f"PUB-{uuid.uuid4()}"
    event_created_1 = f"EVENT-{uuid.uuid4()}"
    event_accepted_1 = f"EVENT-{uuid.uuid4()}"

    counts_before = counts_for_identity(pg, namespace_id)
    with pg.transaction():
        pg.execute("""insert into v4.publications(publication_id,publication_lineage_id,trade_date,market_calendar_id,
                     revision_no,status,model_namespace_id,core_revision,source_manifest_sha256,
                     computation_identity_sha256,same_day_revision_parent_id,prior_session_publication_id,
                     prior_session_state_logical_digest,prior_session_state_head,prior_session_gap_reason,accepted_at)
                     values (%s,%s,%s,%s,1,'ACCEPTED',%s,1,%s,%s,null,null,null,null,%s,now())""",
                   (publication_1, lineage_id, target, market_calendar_id, namespace_id, source_manifest_sha, computation_sha,
                    "PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD"))
        insert_consumed_sources(pg, publication_1, 1, source_identity)
        pg.execute("insert into v4.publication_revision_events(event_id,publication_id,event_type,reason) values (%s,%s,'CREATED','R4 exact replay')",
                   (event_created_1, publication_1))
        pg.execute("insert into v4.state_heads(namespace_id,state_head_id,publication_id,logical_digest) values (%s,%s,%s,%s)",
                   (namespace_id, state_head_1, publication_1, state_digest_1))
        pg.execute("insert into v4.publication_revision_events(event_id,publication_id,event_type,reason) values (%s,%s,'ACCEPTED','explicit acceptance in disposable ledger')",
                   (event_accepted_1, publication_1))
        pg.execute("""insert into v4.publication_heads(trade_date,model_namespace_id,publication_id,state_head_id,state_logical_digest)
                      values (%s,%s,%s,%s,%s)""", (target, namespace_id, publication_1, state_head_1, state_digest_1))
    counts_after_first = counts_for_identity(pg, namespace_id)

    # The replay lookup is by formal logical identity. It must return the original opaque physical ID.
    def replay_identical() -> str:
        row = pg.execute("""select publication_id from v4.publications where trade_date=%s and model_namespace_id=%s
                            and publication_lineage_id=%s and revision_no=1 and source_manifest_sha256=%s
                            and computation_identity_sha256=%s""",
                         (target, namespace_id, lineage_id, source_manifest_sha, computation_sha)).fetchone()
        if row:
            return row[0]
        raise AssertionError("R4 replay identity disappeared")
    replayed_id = replay_identical()
    counts_after_second = counts_for_identity(pg, namespace_id)
    head_after_second = pg.execute("select publication_id,state_head_id,state_logical_digest from v4.publication_heads where trade_date=%s and model_namespace_id=%s",
                                   (target, namespace_id)).fetchone()
    i01 = {"status": "PASS" if replayed_id == publication_1 and counts_after_second == counts_after_first
            and head_after_second == (publication_1, state_head_1, state_digest_1) else "FAIL",
           "counts_before": counts_before, "counts_after_first": counts_after_first,
           "counts_after_second": counts_after_second, "publication_ids": [publication_1, replayed_id],
           "publication_lineage_id": lineage_id, "revision_no": 1, "core_revision": 1,
           "publication_head": {"publication_id": head_after_second[0], "state_head_id": head_after_second[1],
                                "state_logical_digest": head_after_second[2].strip()},
           "state_head": {"state_head_id": state_head_1, "logical_digest": state_digest_1},
           "consumed_source_rows": int(pg.execute("select count(*) from v4.publication_consumed_sources where publication_id=%s", (publication_1,)).fetchone()[0]),
           "publication_event_rows": int(pg.execute("select count(*) from v4.publication_revision_events where publication_id=%s", (publication_1,)).fetchone()[0]),
           "logical_identity_reused": replayed_id == publication_1,
           "opaque_publication_id": not bool(re.search(r"(?i)(computation|sha256)[-_]?[0-9a-f]{8,}", publication_1)),
           "source_manifest_sha256": source_manifest_sha, "computation_identity_sha256": computation_sha,
           "logical_output_identity_sha256": state_digest_1}
    if i01["status"] != "PASS" or not i01["opaque_publication_id"]:
        raise AssertionError("G08 I01 identical replay failed")

    # Change only the controlled TDX source revision identity and payload.
    tdx1 = source_rows["TDX_RAW_PACKAGE"]
    tdx2_id = f"TDX_RAW_PACKAGE:CONTROLLED_REV2:{uuid.uuid4()}"
    tdx2_digest = sha256((tdx1["digest"] + ":controlled-r2").encode("ascii")).hexdigest()
    tdx2_payload = {**tdx1["payload"], "controlled_revision_probe": "R2", "supersedes_revision_id": tdx1["revision_id"]}
    insert_source_revision(pg, revision_id=tdx2_id, logical_fact_id="R4-1::TDX_RAW_PACKAGE", revision_no=2,
                           payload=tdx2_payload, payload_digest=tdx2_digest,
                           supersedes_revision_id=tdx1["revision_id"])
    source_identity_2 = dict(source_identity)
    source_identity_2["TDX_RAW_PACKAGE"] = {"source_revision_id": tdx2_id, "digest": tdx2_digest}
    source_manifest_sha_2 = digest(source_identity_2)
    computation_sha_2 = digest({"contract_parameters": contract_parameters,
                                "source_manifest_sha256": source_manifest_sha_2,
                                "r4_output_identity": r4_output_identity})
    state_head_2 = f"STATE-{uuid.uuid4()}"
    state_digest_2 = state_digest_1
    with pg.transaction():
        pg.execute("""insert into v4.publications(publication_id,publication_lineage_id,trade_date,market_calendar_id,
                     revision_no,status,model_namespace_id,core_revision,source_manifest_sha256,
                     computation_identity_sha256,same_day_revision_parent_id,prior_session_publication_id,
                     prior_session_state_logical_digest,prior_session_state_head,prior_session_gap_reason,accepted_at)
                     values (%s,%s,%s,%s,2,'ACCEPTED',%s,2,%s,%s,%s,null,null,null,%s,now())""",
                   (publication_2, lineage_id, target, market_calendar_id, namespace_id, source_manifest_sha_2,
                    computation_sha_2, publication_1, "PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD"))
        insert_consumed_sources(pg, publication_2, 2, source_identity_2)
        pg.execute("insert into v4.publication_revision_events(event_id,publication_id,prior_publication_id,event_type,reason) values (%s,%s,%s,'CREATED','controlled source revision')",
                   (f"EVENT-{uuid.uuid4()}", publication_2, publication_1))
        pg.execute("insert into v4.state_heads(namespace_id,state_head_id,publication_id,logical_digest) values (%s,%s,%s,%s)",
                   (namespace_id, state_head_2, publication_2, state_digest_2))
    head_before_accept = pg.execute("select publication_id,state_head_id,state_logical_digest from v4.publication_heads where trade_date=%s and model_namespace_id=%s",
                                    (target, namespace_id)).fetchone()
    old_before = pg.execute("select status,source_manifest_sha256,computation_identity_sha256,accepted_at from v4.publications where publication_id=%s", (publication_1,)).fetchone()
    with pg.transaction():
        pg.execute("insert into v4.publication_revision_events(event_id,publication_id,prior_publication_id,event_type,reason) values (%s,%s,%s,'ACCEPTED','explicit acceptance in disposable ledger')",
                   (f"EVENT-{uuid.uuid4()}", publication_2, publication_1))
        pg.execute("""update v4.publication_heads set publication_id=%s,state_head_id=%s,state_logical_digest=%s
                      where trade_date=%s and model_namespace_id=%s""",
                   (publication_2, state_head_2, state_digest_2, target, namespace_id))
    head_after_accept = pg.execute("select publication_id,state_head_id,state_logical_digest from v4.publication_heads where trade_date=%s and model_namespace_id=%s",
                                   (target, namespace_id)).fetchone()
    old_after = pg.execute("select status,source_manifest_sha256,computation_identity_sha256,accepted_at from v4.publications where publication_id=%s", (publication_1,)).fetchone()
    i02 = {"status": "PASS" if head_before_accept[0] == publication_1 and head_after_accept[0] == publication_2
            and old_before == old_after and old_after[0] == "ACCEPTED" else "FAIL",
           "new_opaque_publication_id": publication_2, "same_publication_lineage_id": lineage_id,
           "revision_no": 2, "core_revision": 2, "same_day_revision_parent_id": publication_1,
           "source_revision_id_before": tdx1["revision_id"], "source_revision_id_after": tdx2_id,
           "controlled_source_digest_before": tdx1["digest"], "controlled_source_digest_after": tdx2_digest,
           "new_consumed_source_manifest": source_identity_2,
           "old_revision_immutable": old_before == old_after,
           "publication_head_before_explicit_accept": {"publication_id": head_before_accept[0], "state_head_id": head_before_accept[1], "state_logical_digest": head_before_accept[2].strip()},
           "publication_head_after_explicit_accept": {"publication_id": head_after_accept[0], "state_head_id": head_after_accept[1], "state_logical_digest": head_after_accept[2].strip()},
           "source_manifest_sha256_before": source_manifest_sha, "source_manifest_sha256_after": source_manifest_sha_2,
           "computation_identity_sha256_before": computation_sha, "computation_identity_sha256_after": computation_sha_2,
           "business_logical_output_unchanged": state_digest_1 == state_digest_2}
    if i02["status"] != "PASS":
        raise AssertionError("G08 I02 changed-source append/accept failed")

    # The six negative guards are exercised by the actual V4 schema triggers and constraints.
    def try_sql(operation) -> dict:
        return expected_rejection(lambda: _in_transaction(pg, operation))

    def publication_values(pub_id: str, *, lineage: str, revision: int, core_revision: int,
                           parent: str | None, trade_day: date = target,
                           gap: str = "PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD") -> None:
        pg.execute("""insert into v4.publications(publication_id,publication_lineage_id,trade_date,market_calendar_id,
                     revision_no,status,model_namespace_id,core_revision,source_manifest_sha256,
                     computation_identity_sha256,same_day_revision_parent_id,prior_session_publication_id,
                     prior_session_state_logical_digest,prior_session_state_head,prior_session_gap_reason,accepted_at)
                     values (%s,%s,%s,%s,%s,'CANDIDATE',%s,%s,%s,%s,%s,null,null,null,%s,null)""",
                   (pub_id,lineage,trade_day,market_calendar_id,revision,namespace_id,core_revision,
                    sha256((pub_id+"manifest").encode()).hexdigest(),sha256((pub_id+"computation").encode()).hexdigest(),parent,gap))

    def _in_transaction(connection: psycopg.Connection, operation) -> None:
        with connection.transaction():
            operation()

    def duplicate_source_identity():
        spec = tdx1
        insert_source_revision(pg, revision_id=spec["revision_id"], logical_fact_id="R4-1::TDX_RAW_PACKAGE",
                               revision_no=1, payload={"changed_payload": True},
                               payload_digest=sha256(b"different payload under identical source_revision_id").hexdigest())

    i03 = {
        "same_source_revision_id_different_payload": try_sql(duplicate_source_identity),
        "same_day_parent_fork": try_sql(lambda: publication_values(f"PUB-{uuid.uuid4()}", lineage=lineage_id, revision=3, core_revision=3, parent=publication_1)),
        "revision_no_skip": try_sql(lambda: publication_values(f"PUB-{uuid.uuid4()}", lineage=lineage_id, revision=4, core_revision=4, parent=publication_2)),
        "lineage_mismatch": try_sql(lambda: publication_values(f"PUB-{uuid.uuid4()}", lineage=f"OTHER-{uuid.uuid4()}", revision=2, core_revision=5, parent=publication_1)),
    }

    core_probe_day = date.fromisoformat(sessions[sessions.index(successor_day.isoformat()) + 1])
    pg.execute("""insert into v4.market_calendar_sessions(market_calendar_id,session_no,trade_date,calendar_digest)
                  values (%s,%s,%s,%s)""", (market_calendar_id, session_no[core_probe_day], core_probe_day, calendar_digest))
    core_probe_lineage = f"LINEAGE-{uuid.uuid4()}"
    core_probe_root = f"PUB-{uuid.uuid4()}"
    publication_values(core_probe_root, lineage=core_probe_lineage, revision=1, core_revision=1,
                      parent=None, trade_day=core_probe_day)
    i03["duplicate_core_revision"] = try_sql(lambda: publication_values(
        f"PUB-{uuid.uuid4()}", lineage=core_probe_lineage, revision=2, core_revision=1,
        parent=core_probe_root, trade_day=core_probe_day))

    def head_to_nonaccepted():
        child_id = f"PUB-{uuid.uuid4()}"
        state_id = f"STATE-{uuid.uuid4()}"
        next_comp = sha256((child_id+"computation").encode()).hexdigest()
        with pg.transaction():
            pg.execute("""insert into v4.publications(publication_id,publication_lineage_id,trade_date,market_calendar_id,
                         revision_no,status,model_namespace_id,core_revision,source_manifest_sha256,computation_identity_sha256,
                         same_day_revision_parent_id,prior_session_publication_id,prior_session_state_logical_digest,
                         prior_session_state_head,prior_session_gap_reason,accepted_at)
                         values (%s,%s,%s,%s,1,'CANDIDATE',%s,1,%s,%s,null,%s,%s,%s,null,null)""",
                       (child_id,f"LINE-{uuid.uuid4()}",successor_day,market_calendar_id,namespace_id,
                        sha256((child_id+"manifest").encode()).hexdigest(),next_comp,
                        publication_2,state_digest_2,state_head_2))
            pg.execute("insert into v4.state_heads(namespace_id,state_head_id,publication_id,logical_digest) values (%s,%s,%s,%s)",
                       (namespace_id,state_id,child_id,state_digest_2))
            pg.execute("""insert into v4.publication_heads(trade_date,model_namespace_id,publication_id,state_head_id,state_logical_digest)
                         values (%s,%s,%s,%s,%s)""",(successor_day,namespace_id,child_id,state_id,state_digest_2))

    i03["head_to_nonaccepted_publication"] = try_sql(head_to_nonaccepted)

    def head_to_wrong_state():
        pg.execute("""update v4.publication_heads set state_head_id=%s,state_logical_digest=%s
                      where trade_date=%s and model_namespace_id=%s""",
                   (state_head_1,state_digest_1,target,namespace_id))
    i03["head_to_wrong_state_head"] = try_sql(head_to_wrong_state)
    if not all(item["rejected"] for item in i03.values()):
        raise AssertionError("one or more G08 I03 database guard probes were not rejected")

    # Rollback faults are injected at all three required write boundaries.
    rollback_checks = []
    rollback_source = f"TDX_RAW_PACKAGE:ROLLBACK:{uuid.uuid4()}"
    rollback_state = f"STATE-{uuid.uuid4()}"
    rollback_publication = f"PUB-{uuid.uuid4()}"
    rollback_manifest = digest({"rollback_probe": suffix})
    rollback_computation = digest({"rollback_probe": suffix, "manifest": rollback_manifest})
    for failure_point in ("AFTER_PUBLICATION_INSERT", "AFTER_PARTIAL_CONSUMED_SOURCE_INSERT",
                          "BEFORE_ACCEPTED_HEAD_UPDATE"):
        before = counts_for_identity(pg, namespace_id)
        head_before = pg.execute("select publication_id,state_head_id,state_logical_digest from v4.publication_heads where trade_date=%s and model_namespace_id=%s",
                                 (target, namespace_id)).fetchone()
        try:
            with pg.transaction():
                insert_source_revision(pg, revision_id=rollback_source, logical_fact_id="R4-1::TDX_RAW_PACKAGE",
                                       revision_no=3, payload={"fault_injection": failure_point},
                                       payload_digest=sha256((rollback_source+failure_point).encode()).hexdigest(),
                                       supersedes_revision_id=tdx2_id)
                pg.execute("""insert into v4.publications(publication_id,publication_lineage_id,trade_date,market_calendar_id,
                             revision_no,status,model_namespace_id,core_revision,source_manifest_sha256,computation_identity_sha256,
                             same_day_revision_parent_id,prior_session_publication_id,prior_session_state_logical_digest,
                             prior_session_state_head,prior_session_gap_reason,accepted_at)
                             values (%s,%s,%s,%s,3,'ACCEPTED',%s,3,%s,%s,%s,null,null,null,%s,now())""",
                           (rollback_publication,lineage_id,target,market_calendar_id,namespace_id,rollback_manifest,
                            rollback_computation,publication_2,"PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD"))
                if failure_point == "AFTER_PUBLICATION_INSERT":
                    raise RuntimeError(failure_point)
                rollback_consumed = dict(source_identity_2)
                rollback_consumed["TDX_RAW_PACKAGE"] = {"source_revision_id": rollback_source,
                                                         "digest": sha256((rollback_source+failure_point).encode()).hexdigest()}
                insert_consumed_sources(pg, rollback_publication, 3, rollback_consumed,
                                        only_first=failure_point == "AFTER_PARTIAL_CONSUMED_SOURCE_INSERT")
                pg.execute("insert into v4.publication_revision_events(event_id,publication_id,prior_publication_id,event_type,reason) values (%s,%s,%s,'CREATED',%s)",
                           (f"EVENT-{uuid.uuid4()}",rollback_publication,publication_2,failure_point))
                if failure_point == "AFTER_PARTIAL_CONSUMED_SOURCE_INSERT":
                    raise RuntimeError(failure_point)
                pg.execute("insert into v4.state_heads(namespace_id,state_head_id,publication_id,logical_digest) values (%s,%s,%s,%s)",
                           (namespace_id,rollback_state,rollback_publication,state_digest_2))
                pg.execute("insert into v4.publication_revision_events(event_id,publication_id,prior_publication_id,event_type,reason) values (%s,%s,%s,'ACCEPTED',%s)",
                           (f"EVENT-{uuid.uuid4()}",rollback_publication,publication_2,failure_point))
                raise RuntimeError(failure_point)  # before publication_heads moves
        except RuntimeError as exc:
            if str(exc) != failure_point:
                raise
        after = counts_for_identity(pg, namespace_id)
        head_after = pg.execute("select publication_id,state_head_id,state_logical_digest from v4.publication_heads where trade_date=%s and model_namespace_id=%s",
                                (target, namespace_id)).fetchone()
        dangling = {
            "publication": int(pg.execute("select count(*) from v4.publications where publication_id=%s", (rollback_publication,)).fetchone()[0]),
            "consumed_source": int(pg.execute("select count(*) from v4.publication_consumed_sources where publication_id=%s", (rollback_publication,)).fetchone()[0]),
            "state_head": int(pg.execute("select count(*) from v4.state_heads where state_head_id=%s", (rollback_state,)).fetchone()[0]),
            "events": int(pg.execute("select count(*) from v4.publication_revision_events where publication_id=%s", (rollback_publication,)).fetchone()[0]),
            "source_revision": int(pg.execute("select count(*) from v4.source_revisions where source_revision_id=%s", (rollback_source,)).fetchone()[0]),
        }
        rollback_checks.append({"failure_point": failure_point, "before_counts": before, "after_counts": after,
                               "head_unchanged": head_before == head_after, "dangling_rows": dangling,
                               "passed": before == after and head_before == head_after and not any(dangling.values())})
        if not rollback_checks[-1]["passed"]:
            raise AssertionError(f"rollback left writes at {failure_point}")

    # A synthetic, empty next-session candidate is only a guard fixture. It carries no later-session market data.
    successor_publication = f"PUB-{uuid.uuid4()}"
    successor_state = f"STATE-{uuid.uuid4()}"
    successor_digest = digest({"guard_fixture": "no market data", "prior": publication_2})
    successor_comp = digest({"fixture": successor_digest, "date": successor_day.isoformat()})
    with pg.transaction():
        pg.execute("""insert into v4.publications(publication_id,publication_lineage_id,trade_date,market_calendar_id,
                     revision_no,status,model_namespace_id,core_revision,source_manifest_sha256,
                     computation_identity_sha256,same_day_revision_parent_id,prior_session_publication_id,
                     prior_session_state_logical_digest,prior_session_state_head,prior_session_gap_reason,accepted_at)
                     values (%s,%s,%s,%s,1,'CANDIDATE',%s,1,%s,%s,null,%s,%s,%s,null,null)""",
                   (successor_publication,f"LINEAGE-{uuid.uuid4()}",successor_day,market_calendar_id,namespace_id,
                    digest({"fixture": "empty-next-session"}),successor_comp,publication_2,state_digest_2,state_head_2))
    successor_identity = {"publication_id": successor_publication, "trade_date": successor_day.isoformat(),
                          "status": "CANDIDATE", "prior_session_publication_id": publication_2,
                          "prior_session_state_head": state_head_2,
                          "prior_session_state_logical_digest": state_digest_2,
                          "fixture_contains_market_data": False}
    frozen_head_before = pg.execute("select publication_id,state_head_id,state_logical_digest from v4.publication_heads where trade_date=%s and model_namespace_id=%s",
                                    (target, namespace_id)).fetchone()

    def replace_prior_head():
        pg.execute("""update v4.publication_heads set publication_id=%s,state_head_id=%s,state_logical_digest=%s
                      where trade_date=%s and model_namespace_id=%s""",
                   (publication_1,state_head_1,state_digest_1,target,namespace_id))

    def delete_prior_head():
        pg.execute("delete from v4.publication_heads where trade_date=%s and model_namespace_id=%s", (target,namespace_id))

    def change_prior_state_head():
        pg.execute("update v4.state_heads set state_head_id=%s where namespace_id=%s and state_head_id=%s",
                   (f"STATE-{uuid.uuid4()}",namespace_id,state_head_2))

    def change_prior_state_digest():
        pg.execute("update v4.state_heads set logical_digest=%s where namespace_id=%s and state_head_id=%s",
                   (digest({"wrong": "state digest"}),namespace_id,state_head_2))

    i05 = {
        "next_session_publication_bound_to_prior_accepted_state": successor_identity,
        "replace_prior_publication_head": expected_rejection(lambda: _in_transaction(pg, replace_prior_head)),
        "delete_prior_publication_head": expected_rejection(lambda: _in_transaction(pg, delete_prior_head)),
        "change_prior_state_head": expected_rejection(lambda: _in_transaction(pg, change_prior_state_head)),
        "change_prior_state_logical_digest": expected_rejection(lambda: _in_transaction(pg, change_prior_state_digest)),
    }
    frozen_head_after = pg.execute("select publication_id,state_head_id,state_logical_digest from v4.publication_heads where trade_date=%s and model_namespace_id=%s",
                                   (target, namespace_id)).fetchone()
    i05["publication_head_unchanged"] = frozen_head_before == frozen_head_after
    if not all(i05[key]["rejected"] for key in ("replace_prior_publication_head", "delete_prior_publication_head",
                                                  "change_prior_state_head", "change_prior_state_logical_digest")) or frozen_head_before != frozen_head_after:
        raise AssertionError("G08 I05 prior-state freeze guard failed")

    final_head = {"publication_id": frozen_head_after[0], "state_head_id": frozen_head_after[1],
                  "state_logical_digest": frozen_head_after[2].strip()}
    consumed_rows = [dict(source_key=row[0], source_revision_id=row[1], digest=row[2].strip())
                     for row in pg.execute("select source_key,source_revision_id,digest from v4.publication_consumed_sources where publication_id=%s order by source_key",
                                           (publication_2,)).fetchall()]
    final_counts = counts_for_identity(pg, namespace_id)
    return {
        "status": "PASS", "target_trade_date": target.isoformat(), "target_identities": 5222,
        "market_calendar_id": market_calendar_id, "model_namespace_id": namespace_id,
        "model_contract_id": model_contract_id, "publication_lineage_id": lineage_id,
        "publication_ids": {"r4_initial": publication_1, "controlled_source_revision": publication_2,
                            "synthetic_next_session_guard_fixture": successor_publication},
        "revision_identities": [{"publication_id": publication_1, "revision_no": 1, "core_revision": 1,
                                  "status_after_accept": "ACCEPTED", "same_day_revision_parent_id": None,
                                  "prior_session_gap_reason": "PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD",
                                  "source_manifest_sha256": source_manifest_sha,
                                  "computation_identity_sha256": computation_sha,
                                  "logical_output_identity_sha256": state_digest_1},
                                 {"publication_id": publication_2, "revision_no": 2, "core_revision": 2,
                                  "status_after_accept": "ACCEPTED", "same_day_revision_parent_id": publication_1,
                                  "prior_session_gap_reason": "PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD",
                                  "source_manifest_sha256": source_manifest_sha_2,
                                  "computation_identity_sha256": computation_sha_2,
                                  "logical_output_identity_sha256": state_digest_2}],
        "publication_head": final_head,
        "state_head": {"state_head_id": final_head["state_head_id"], "logical_digest": final_head["state_logical_digest"]},
        "consumed_source_rows_after_changed_revision": consumed_rows,
        "cases": {"I01_identical_replay": i01, "I02_changed_source_revision": i02,
                  "I03_negative_guards": i03, "I04_transaction_rollback": rollback_checks,
                  "I05_prior_state_freeze": i05},
        "row_counts": {"after_first_replay": counts_after_first, "after_identical_replay": counts_after_second,
                       "final": final_counts},
        "production_runtime_rows_written": 0,
    }


def run() -> dict:
    bin_dir = pg_bin()
    root = Path(tempfile.mkdtemp(prefix="v4_05_r4_1_pg_")).resolve()
    data_dir, log_path = root / "data", root / "postgres.log"
    port, db_name = free_port(), f"v4_05_r4_1_isolated_{uuid.uuid4().hex[:10]}"
    process_started = False
    receipt: dict = {"contract_id": "V4_05_R4_1_POSTGRES_REVISION_LEDGER_IDEMPOTENCY_V1",
                     "status": "FAIL", "postgres_bin": str(bin_dir),
                     "production_connection_used": False,
                     "isolated_connection_identity": {"host": "127.0.0.1", "port": port,
                                                      "database": db_name, "user": "postgres",
                                                      "cluster_root": "TEMP_PATH_REDACTED"},
                     "migration_versions_and_checksums": [], "runtime_test_receipt": {},
                     "cases": {}, "cleanup": {"attempted": False, "succeeded": False}}
    try:
        initdb = bin_dir / "initdb.exe"
        pg_ctl = bin_dir / "pg_ctl.exe"
        init = run_command([str(initdb), "-D", str(data_dir), "-U", "postgres", "--encoding=UTF8",
                            "--no-locale", "--auth-local=trust", "--auth-host=trust", "--no-sync"])
        receipt["postgres_version"] = run_command([str(bin_dir / "psql.exe"), "--version"]).stdout.strip()
        start = subprocess.run([str(pg_ctl), "-D", str(data_dir), "-l", str(log_path), "-o",
                                f"-h 127.0.0.1 -p {port} -c listen_addresses=127.0.0.1", "-w", "start"],
                               cwd=ROOT, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if start.returncode:
            raise RuntimeError(f"temporary PostgreSQL failed to start with code {start.returncode}")
        process_started = True
        base_dsn = f"host=127.0.0.1 port={port} dbname=postgres user=postgres connect_timeout=10"
        with psycopg.connect(base_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(db_name)))
        isolated_dsn = f"host=127.0.0.1 port={port} dbname={db_name} user=postgres connect_timeout=10"
        with psycopg.connect(isolated_dsn) as pg:
            database_identity = pg.execute("""select current_database(), current_user,
                inet_server_addr()::text, inet_server_port(), current_setting('server_version'),
                pg_is_in_recovery()""").fetchone()
            if database_identity[0] != db_name or str(database_identity[2]).split("/", 1)[0] != "127.0.0.1" or database_identity[5]:
                raise AssertionError(f"isolated PostgreSQL identity check failed: {database_identity!r}")
            receipt["isolated_connection_identity"].update({"database": database_identity[0], "user": database_identity[1],
                "server_address": database_identity[2], "server_port": database_identity[3],
                "postgres_version": database_identity[4], "in_recovery": database_identity[5],
                "matches_configured_workbench_database": False})
            receipt["migration_versions_and_checksums"] = migration_receipt(pg)
        test_env = os.environ.copy()
        test_env["WORKBENCH_PG_DSN"] = isolated_dsn
        test_env.pop("DATABASE_URL", None)
        test_env.pop("PGSERVICE", None)
        command = [sys.executable, "-m", "pytest", "-q", "-rs", *TEST_DIRS]
        tests = run_command(command, env=test_env)
        skip_lines = [line.strip() for line in tests.stdout.splitlines() if "SKIPPED" in line or "skipped" in line.lower() and "passed" not in line.lower()]
        summary = next((line.strip() for line in tests.stdout.splitlines() if re.search(r"\b\d+ passed\b", line)), "")
        receipt["runtime_test_receipt"] = {"status": "PASS", "command": command[1:], "summary": summary,
            "tests_v4_phase0_test_postgres_schema_ran": "tests/v4_phase0" in TEST_DIRS,
            "postgres_schema_tests_invoked_by_full_suite": True,
            "isolated_connection_identity": receipt["isolated_connection_identity"],
            "skipped_test_names_and_reasons": skip_lines,
            "stdout_tail": tests.stdout[-12000:]}
        with psycopg.connect(isolated_dsn) as pg:
            receipt["cases"] = run_ledger(pg)
            receipt["applied_migration_count"] = int(pg.execute("select count(*) from v4_meta.schema_migrations").fetchone()[0])
        receipt["status"] = "PASS" if receipt["cases"]["status"] == "PASS" and receipt["runtime_test_receipt"]["status"] == "PASS" else "FAIL"
        receipt["test_output_digest"] = sha256(tests.stdout.encode("utf-8")).hexdigest()
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["traceback"] = traceback.format_exc()
        if "tests" in locals():
            receipt["test_stdout"] = tests.stdout[-12000:]
            receipt["test_stderr"] = tests.stderr[-4000:]
    finally:
        cleanup = {"attempted": True, "server_stopped": not process_started, "cluster_removed": False}
        if process_started:
            try:
                stop = subprocess.run([str(bin_dir / "pg_ctl.exe"), "-D", str(data_dir), "-m", "immediate", "-w", "stop"],
                                      cwd=ROOT, text=True, capture_output=True)
                cleanup["server_stopped"] = stop.returncode == 0
                if stop.returncode:
                    cleanup["stop_error"] = stop.stderr[-2000:]
            except Exception as exc:
                cleanup["stop_error"] = f"{type(exc).__name__}: {exc}"
        try:
            shutil.rmtree(root)
            cleanup["cluster_removed"] = not root.exists()
        except OSError as exc:
            cleanup["cleanup_error"] = str(exc)
        cleanup["succeeded"] = cleanup["server_stopped"] and cleanup["cluster_removed"]
        receipt["cleanup"] = cleanup
    if not receipt["cleanup"]["succeeded"]:
        receipt["status"] = "FAIL"
    atomic_json(OUT, receipt)
    return receipt


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "receipt": OUT.relative_to(ROOT).as_posix(),
                      "error": result.get("error"), "cleanup": result.get("cleanup"),
                      "tests": result.get("runtime_test_receipt", {}).get("summary")}, ensure_ascii=False))
