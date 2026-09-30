from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIGEST = "4a8d1c8e6574bfa9985e7980ca83337b7a14bed54bfbbace9e817d44b2076743"


def run(command: Sequence[str], *, check: bool = True, capture_output: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        capture_output=capture_output,
        stdout=None if capture_output else subprocess.DEVNULL,
        stderr=None if capture_output else subprocess.DEVNULL,
        check=False,
        timeout=75,
        env=env,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {command[0]}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checkpoint(value: str) -> None:
    print(f"[v4-08 migration] {value}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply and verify V4-08 membership migration in a disposable PostgreSQL cluster.")
    parser.add_argument("--postgres-bin", type=Path, default=Path(os.environ.get("V4_08_POSTGRES_BIN", r"E:\Postgres\bin")))
    parser.add_argument("--evidence", type=Path, default=ROOT / "reports/v4_08/V4_08_MEMBERSHIP_SCHEMA_MIGRATION_RECEIPT.json")
    args = parser.parse_args()
    pg_bin = args.postgres_bin.resolve()
    initdb, pg_ctl, psql, postgres = (pg_bin / f"{name}.exe" for name in ("initdb", "pg_ctl", "psql", "postgres"))
    for executable in (initdb, pg_ctl, psql, postgres):
        if not executable.is_file():
            raise FileNotFoundError(f"PostgreSQL executable is missing: {executable}")
    migrations = [
        ROOT / "src/workbench_db/migrations/v4_postgres/016_v4_08_sector_membership.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/017_v4_08_membership_fact_evidence_view.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/018_v4_08_membership_contract_repair_r2.sql",
    ]
    rollbacks = [
        ROOT / "src/workbench_db/migrations/v4_postgres/rollback/018_v4_08_membership_contract_repair_r2.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/rollback/017_v4_08_membership_fact_evidence_view.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/rollback/016_v4_08_sector_membership.sql",
    ]
    version = run([str(postgres), "--version"]).stdout.strip()
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="v4_08_membership_pg_") as temp:
        checkpoint("initializing disposable PostgreSQL cluster")
        temp_root = Path(temp)
        data = temp_root / "pgdata"
        log = temp_root / "postgres.log"
        run([str(initdb), "-D", str(data), "-U", "postgres", "--auth=trust", "--encoding=UTF8"])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        started = False
        try:
            run([str(pg_ctl), "-D", str(data), "-o", f"-h 127.0.0.1 -p {port}", "-l", str(log), "-w", "-t", "60", "start"], capture_output=False)
            started = True
            checkpoint("cluster ready")

            def sql(text: str, name: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
                file = temp_root / name
                file.write_text(text, encoding="utf-8", newline="\n")
                env = os.environ.copy()
                env["PGOPTIONS"] = "-c lc_messages=C"
                return run([str(psql), "-X", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(port), "-U", "postgres", "-d", "postgres", "-f", str(file)], check=check, env=env)

            sql("""CREATE SCHEMA v4;
CREATE TABLE v4.preserved_sentinel(id integer PRIMARY KEY);
INSERT INTO v4.preserved_sentinel VALUES (1);
CREATE OR REPLACE FUNCTION v4.reject_append_only_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'append-only guard rejected %', TG_OP; END;
$$;
""", "prerequisites.sql")
            for index, migration in enumerate(migrations, 1):
                run([str(psql), "-X", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(port), "-U", "postgres", "-d", "postgres", "-f", str(migration)])
                checkpoint(f"migration {index}/{len(migrations)} applied")
            checks["migration_applied"] = True
            columns = sql("""SELECT column_name FROM information_schema.columns
WHERE table_schema='v4' AND table_name='sector_membership_fact_evidence';
""", "fact_evidence_columns.sql")
            evidence_columns = {line.strip() for line in columns.stdout.splitlines() if line.strip()}
            required_evidence_columns = {"observed_at", "ingested_at", "system_available_at", "provider_available_at", "source_digest", "source_file_digests", "target_trade_date", "membership_asof_date", "source_bytes_digest", "temporal_evidence_digest", "provider_available_at_basis", "membership_asof_basis", "revision_quality", "parent_snapshot_id", "snapshot_lineage_role"}
            checks["fact_evidence_view_exposes_contract_timestamps_and_digests"] = required_evidence_columns <= evidence_columns
            policy = sql("""SELECT sector_type || ':' || formal_radar_allowed::text || ':' || formal_sector_qualification_allowed::text || ':' || formal_rotation_qualification_allowed::text
FROM v4.sector_membership_type_policy WHERE registry_digest = '__REGISTRY_DIGEST__' ORDER BY sector_type;
""".replace("__REGISTRY_DIGEST__", REGISTRY_DIGEST), "policy.sql")
            policy_lines = [line.strip() for line in policy.stdout.splitlines() if line.strip().startswith(("INDUSTRY:", "THEME:", "STYLE:", "UNKNOWN:"))]
            checks["versioned_type_registry_seeded"] = len(policy_lines) == 4
            checks["style_and_unknown_excluded_by_policy"] = "STYLE:false:false:false" in policy_lines and "UNKNOWN:false:false:false" in policy_lines

            seed_rows_sql = """INSERT INTO v4.sector_membership_source_revisions
(source_revision_id,source_contract_id,source_digest,source_file_digests,observed_at,ingested_at,system_available_at,provider_available_at,membership_asof_date,membership_basis,supersedes_revision_id,created_at,source_bytes_digest,temporal_evidence_digest,temporal_evidence,provider_available_at_basis,membership_asof_basis,revision_quality) VALUES
('rev-1','V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',repeat('a',64),'{}','2026-09-30T08:00:00Z','2026-09-30T08:01:00Z','2026-09-30T08:01:00Z','2026-09-30T07:59:00Z','2026-09-30','PIT_OBSERVED',NULL,'2026-09-30T08:01:00Z',repeat('1',64),repeat('2',64),'{"revision_chain_valid":true}','PROVIDER_NATIVE','SOURCE_OBSERVED_DATE','PIT_OBSERVED_ACCEPTED'),
('rev-degraded','V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',repeat('d',64),'{}','2026-09-30T08:00:00Z','2026-09-30T08:01:00Z','2026-09-30T08:01:00Z','2026-09-30T07:59:00Z','2026-09-30','PIT_OBSERVED',NULL,'2026-09-30T08:01:00Z',repeat('1',64),repeat('3',64),'{"revision_chain_valid":true}','PROJECT_FIRST_OBSERVED_PROVIDER_BYTES','PROJECT_FIRST_OBSERVED_PROVIDER_BYTES','SOURCE_TIME_UNVERIFIED'),
('rev-2','V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',repeat('b',64),'{}','2026-09-30T10:00:00Z','2026-09-30T10:01:00Z','2026-09-30T10:01:00Z','2026-09-30T10:00:00Z','2026-09-30','PIT_OBSERVED','rev-1','2026-09-30T10:01:00Z',repeat('4',64),repeat('5',64),'{"revision_chain_valid":true}','PROVIDER_NATIVE','SOURCE_OBSERVED_DATE','PIT_OBSERVED_ACCEPTED'),
('rev-current','V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',repeat('c',64),'{}','2026-09-30T08:00:00Z','2026-09-30T08:01:00Z','2026-09-30T08:01:00Z',NULL,NULL,'CURRENT_TDX_MEMBERSHIP',NULL,'2026-09-30T08:01:00Z',repeat('6',64),repeat('7',64),'{"revision_chain_valid":true}','NOT_APPLICABLE','NOT_APPLICABLE','CURRENT_TDX_DIAGNOSTIC'),
('rev-parent','V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',repeat('c',64),'{}','2026-09-30T08:00:00Z','2026-09-30T08:01:00Z','2026-09-30T08:01:00Z',NULL,NULL,'DERIVED_PARENT_MEMBERSHIP',NULL,'2026-09-30T08:01:00Z',repeat('6',64),repeat('8',64),'{"revision_chain_valid":true}','NOT_APPLICABLE','NOT_APPLICABLE','DERIVED_PARENT_DIAGNOSTIC');
INSERT INTO v4.sector_membership_snapshots
(snapshot_id,target_trade_date,cutoff,sector_type_registry_digest,source_revision_id,source_digest,source_file_digests,membership_basis,membership_quality,pit_observed,historical_backtest_safe,row_count,supersedes_snapshot_id,created_at,parent_snapshot_id,snapshot_lineage_role) VALUES
(repeat('1',64),'2026-09-30','2026-09-30T09:00:00Z','__REGISTRY_DIGEST__','rev-1',repeat('a',64),'{}','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,2,NULL,'2026-09-30T09:00:00Z',NULL,'FORWARD_PIT_CANDIDATE'),
(repeat('2',64),'2026-09-30','2026-09-30T09:00:00Z','__REGISTRY_DIGEST__','rev-degraded',repeat('d',64),'{}','PIT_OBSERVED','SOURCE_TIME_UNVERIFIED',true,false,1,NULL,'2026-09-30T09:00:00Z',NULL,'FORWARD_PIT_CANDIDATE'),
(repeat('3',64),'2026-09-30','2026-09-30T09:00:00Z','__REGISTRY_DIGEST__','rev-2',repeat('b',64),'{}','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,1,NULL,'2026-09-30T09:00:00Z',NULL,'FORWARD_PIT_CANDIDATE'),
(repeat('4',64),'2026-09-30','2026-09-30T09:00:00Z','__REGISTRY_DIGEST__','rev-current',repeat('c',64),'{}','CURRENT_TDX_MEMBERSHIP','CURRENT_TDX_DIAGNOSTIC',false,false,1,NULL,'2026-09-30T09:00:00Z',NULL,'RAW_CURRENT'),
(repeat('5',64),'2026-09-30','2026-09-30T09:00:00Z','__REGISTRY_DIGEST__','rev-parent',repeat('c',64),'{}','DERIVED_PARENT_MEMBERSHIP','DERIVED_PARENT_DIAGNOSTIC',false,false,1,NULL,'2026-09-30T09:00:00Z',repeat('4',64),'DERIVED_PARENT');
INSERT INTO v4.sector_membership_facts
(membership_fact_id,snapshot_id,source_revision_id,sector_id,sector_code,sector_name,sector_type,source_sector_type,source_security_key,security_id,identity_status,target_trade_date,membership_asof_date,cutoff,membership_basis,membership_quality,pit_observed,historical_backtest_safe,supersedes_revision_id,created_at) VALUES
(repeat('a',64),repeat('1',64),'rev-1','INDUSTRY:801010','801010','Industry','INDUSTRY','industry','SH.600001','SEC-1','MAPPED','2026-09-30','2026-09-30','2026-09-30T09:00:00Z','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,NULL,'2026-09-30T09:00:00Z'),
(repeat('b',64),repeat('1',64),'rev-1','THEME:880001','880001','Theme','THEME','concept','SH.600001','SEC-1','MAPPED','2026-09-30','2026-09-30','2026-09-30T09:00:00Z','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,NULL,'2026-09-30T09:00:00Z'),
(repeat('c',64),repeat('1',64),'rev-1','STYLE:1','1','Style','STYLE','style','SH.600001','SEC-1','MAPPED','2026-09-30','2026-09-30','2026-09-30T09:00:00Z','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,NULL,'2026-09-30T09:00:00Z'),
(repeat('d',64),repeat('2',64),'rev-degraded','INDUSTRY:801011','801011','Degraded PIT','INDUSTRY','industry','SH.600002','SEC-2','MAPPED','2026-09-30','2026-09-30','2026-09-30T09:00:00Z','PIT_OBSERVED','SOURCE_TIME_UNVERIFIED',true,false,NULL,'2026-09-30T09:00:00Z'),
(repeat('e',64),repeat('2',64),'rev-degraded','UNKNOWN:index_group:1','1','Raw Index','UNKNOWN','index_group','SH.999999',NULL,'UNKNOWN','2026-09-30','2026-09-30','2026-09-30T09:00:00Z','PIT_OBSERVED','UNKNOWN_IDENTITY',true,false,NULL,'2026-09-30T09:00:00Z'),
(repeat('f',64),repeat('4',64),'rev-current','INDUSTRY:801010','801010','Raw child','INDUSTRY','industry','SH.600001','SEC-1','MAPPED','2026-09-30',NULL,'2026-09-30T09:00:00Z','CURRENT_TDX_MEMBERSHIP','CURRENT_TDX_DIAGNOSTIC',false,false,NULL,'2026-09-30T09:00:00Z'),
(repeat('0',64),repeat('5',64),'rev-parent','INDUSTRY:80101','80101','Derived parent','INDUSTRY','industry','SH.600001','SEC-1','MAPPED','2026-09-30',NULL,'2026-09-30T09:00:00Z','DERIVED_PARENT_MEMBERSHIP','DERIVED_PARENT_DIAGNOSTIC',false,false,NULL,'2026-09-30T09:00:00Z');
"""
            sql(seed_rows_sql.replace("__REGISTRY_DIGEST__", REGISTRY_DIGEST), "seed_rows.sql")
            checkpoint("fixture rows inserted")
            formal = sql("SELECT count(*) FROM v4.formal_sector_membership;", "formal_view.sql")
            checks["formal_view_contains_industry_and_theme_only"] = "2" in [x.strip() for x in formal.stdout.splitlines()]
            degraded_formal = sql("SELECT count(*) FROM v4.formal_sector_membership WHERE membership_quality='SOURCE_TIME_UNVERIFIED';", "formal_quality_gate.sql")
            checks["formal_view_rejects_pit_with_unaccepted_quality"] = "0" in [x.strip() for x in degraded_formal.stdout.splitlines()]
            degraded_pit = sql("SELECT count(*) FROM v4.sector_membership_facts WHERE membership_basis='PIT_OBSERVED' AND membership_quality='SOURCE_TIME_UNVERIFIED' AND pit_observed AND NOT historical_backtest_safe;", "degraded_pit_allowed.sql")
            checks["pit_observed_degraded_history_unsafe_is_allowed"] = "1" in [x.strip() for x in degraded_pit.stdout.splitlines()]
            unknown = sql("SELECT count(*) FROM v4.sector_membership_facts WHERE identity_status='UNKNOWN';", "unknown_retained.sql")
            checks["unknown_identity_row_retained"] = "1" in [x.strip() for x in unknown.stdout.splitlines()]
            parent_lineage = sql("SELECT parent_snapshot_id=repeat('4',64) AND snapshot_lineage_role='DERIVED_PARENT' FROM v4.sector_membership_snapshots WHERE snapshot_id=repeat('5',64);", "parent_lineage.sql")
            checks["derived_parent_snapshot_references_raw_source_snapshot"] = "t" in [x.strip() for x in parent_lineage.stdout.splitlines()]
            available = sql("SELECT count(*) FROM v4.sector_membership_source_revisions WHERE revision_quality='PIT_OBSERVED_ACCEPTED' AND system_available_at <= '2026-09-30T09:00:00Z';", "cutoff_select.sql")
            checks["cutoff_excludes_later_revision"] = "1" in [x.strip() for x in available.stdout.splitlines()]
            checkpoint("temporal and type checks complete")

            fork = sql("""INSERT INTO v4.sector_membership_source_revisions
(source_revision_id,source_contract_id,source_digest,source_file_digests,observed_at,ingested_at,system_available_at,provider_available_at,membership_asof_date,membership_basis,supersedes_revision_id,created_at,source_bytes_digest,temporal_evidence_digest,temporal_evidence,provider_available_at_basis,membership_asof_basis,revision_quality) VALUES
('rev-3','V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',repeat('c',64),'{}','2026-09-30T11:00:00Z','2026-09-30T11:01:00Z','2026-09-30T11:01:00Z','2026-09-30T11:00:00Z','2026-09-30','PIT_OBSERVED','rev-1','2026-09-30T11:01:00Z',repeat('9',64),repeat('8',64),'{"revision_chain_valid":true}','PROVIDER_NATIVE','SOURCE_OBSERVED_DATE','PIT_OBSERVED_ACCEPTED');
""", "fork.sql", check=False)
            checks["revision_fork_rejected"] = fork.returncode != 0 and "ux_v4_sector_membership_revision_no_fork" in fork.stderr

            duplicate = sql("""INSERT INTO v4.sector_membership_facts VALUES
(repeat('7',64),repeat('1',64),'rev-1','INDUSTRY:801010','801010','Industry','INDUSTRY','industry','SH.600001.ALIAS','SEC-1','MAPPED','2026-09-30','2026-09-30','2026-09-30T09:00:00Z','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,NULL,'2026-09-30T09:00:00Z');
""", "duplicate_fact.sql", check=False)
            checks["duplicate_canonical_fact_rejected"] = duplicate.returncode != 0 and "ux_v4_sector_membership_fact_identity" in duplicate.stderr

            late = sql("""INSERT INTO v4.sector_membership_facts VALUES
(repeat('6',64),repeat('3',64),'rev-2','INDUSTRY:801011','801011','Late','INDUSTRY','industry','SH.600002','SEC-2','MAPPED','2026-09-30','2026-09-30','2026-09-30T09:00:00Z','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,NULL,'2026-09-30T09:00:00Z');
""", "late_fact.sql", check=False)
            checks["temporal_leakage_rejected"] = late.returncode != 0 and "unavailable at snapshot cutoff" in late.stderr

            stale = sql("""INSERT INTO v4.sector_membership_facts
(membership_fact_id,snapshot_id,source_revision_id,sector_id,sector_code,sector_name,sector_type,source_sector_type,source_security_key,security_id,identity_status,target_trade_date,membership_asof_date,cutoff,membership_basis,membership_quality,pit_observed,historical_backtest_safe,supersedes_revision_id,created_at)
VALUES (repeat('9',64),repeat('1',64),'rev-1','INDUSTRY:801012','801012','Stale','INDUSTRY','industry','SH.600003','SEC-3','MAPPED','2026-09-30','2026-09-29','2026-09-30T09:00:00Z','PIT_OBSERVED','PIT_OBSERVED_ACCEPTED',true,true,NULL,'2026-09-30T09:00:00Z');
""", "stale_asof.sql", check=False)
            checks["stale_membership_asof_rejected"] = stale.returncode != 0 and "exact effective date" in stale.stderr

            mixed_basis = sql("""INSERT INTO v4.sector_membership_facts
(membership_fact_id,snapshot_id,source_revision_id,sector_id,sector_code,sector_name,sector_type,source_sector_type,source_security_key,security_id,identity_status,target_trade_date,membership_asof_date,cutoff,membership_basis,membership_quality,pit_observed,historical_backtest_safe,supersedes_revision_id,created_at)
VALUES (repeat('8',64),repeat('4',64),'rev-parent','INDUSTRY:801019','801019','Mixed','INDUSTRY','industry','SH.600019','SEC-19','MAPPED','2026-09-30',NULL,'2026-09-30T09:00:00Z','DERIVED_PARENT_MEMBERSHIP','DERIVED_PARENT_DIAGNOSTIC',false,false,NULL,'2026-09-30T09:00:00Z');
""", "mixed_basis.sql", check=False)
            checks["raw_snapshot_rejects_parent_basis_fact"] = mixed_basis.returncode != 0 and "does not match snapshot header" in mixed_basis.stderr

            same_bytes = sql("""SELECT count(DISTINCT source_revision_id) = 2 AND count(DISTINCT temporal_evidence_digest) = 2
FROM v4.sector_membership_source_revisions WHERE source_bytes_digest=repeat('1',64);
""", "same_bytes_temporal_revisions.sql")
            checks["same_bytes_new_temporal_evidence_is_a_new_revision"] = "t" in [x.strip() for x in same_bytes.stdout.splitlines()]

            mutation = sql("""UPDATE v4.sector_membership_facts SET sector_name='changed' WHERE membership_fact_id=repeat('a',64);
""", "update_rejected.sql", check=False)
            checks["update_rejected"] = mutation.returncode != 0 and "append-only guard rejected UPDATE" in mutation.stderr
            mutation = sql("DELETE FROM v4.sector_membership_source_revisions WHERE source_revision_id='rev-1';", "delete_rejected.sql", check=False)
            checks["delete_rejected"] = mutation.returncode != 0 and "append-only guard rejected DELETE" in mutation.stderr
            mutation = sql("UPDATE v4.sector_membership_source_revisions SET temporal_evidence_digest=repeat('f',64) WHERE source_revision_id='rev-1';", "revision_metadata_update_rejected.sql", check=False)
            checks["temporal_evidence_revision_is_append_only"] = mutation.returncode != 0 and "append-only guard rejected UPDATE" in mutation.stderr
            checkpoint("append-only checks complete")
            for index, rollback in enumerate(rollbacks, 1):
                run([str(psql), "-X", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(port), "-U", "postgres", "-d", "postgres", "-f", str(rollback)])
                checkpoint(f"rollback {index}/{len(rollbacks)} applied")
            sentinel = sql("SELECT count(*) FROM v4.preserved_sentinel;", "rollback_scope.sql")
            checks["rollback_removed_only_stage_schema"] = "1" in [x.strip() for x in sentinel.stdout.splitlines()] and "v4.sector_membership_facts" not in sql("SELECT coalesce(to_regclass('v4.sector_membership_facts')::text,'NULL');", "rollback_check.sql").stdout
        finally:
            if started:
                status = run([str(pg_ctl), "-D", str(data), "status"], check=False)
                if status.returncode == 0:
                    checkpoint("stopping disposable PostgreSQL cluster")
                    run([str(pg_ctl), "-D", str(data), "-m", "fast", "-w", "-t", "30", "stop"])
        checkpoint("cluster removed")

    passed = bool(checks) and all(checks.values())
    evidence = {
        "contract_id": "V4_08_R2_SCHEMA_MIGRATION_RECEIPT_V1",
        "status": "PASS_ISOLATED_MIGRATION_AND_ROLLBACK" if passed else "FAIL",
        "database_scope": "disposable localhost PostgreSQL cluster initialized by this verifier; config/.env and configured databases were not read",
        "postgres_version": version,
        "migrations": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)} for path in migrations],
        "rollbacks": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)} for path in rollbacks],
        "migration_sha256": sha(migrations[-1]),
        "rollback_sha256": sha(rollbacks[0]),
        "sector_type_registry_digest": REGISTRY_DIGEST,
        "checks": checks,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    dest = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{dest.name}.", suffix=".tmp", dir=dest.parent, delete=False, mode="w", encoding="utf-8", newline="\n") as stream:
        temp_path = Path(stream.name)
        stream.write(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, dest)
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
