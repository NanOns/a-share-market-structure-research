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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    command: Sequence[str], *, check: bool = True, capture_output: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        capture_output=capture_output,
        stdout=None if capture_output else subprocess.DEVNULL,
        stderr=None if capture_output else subprocess.DEVNULL,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {command[0]}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def write_sql(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply and roll back V4-07 migration 015 in a disposable local PostgreSQL cluster."
    )
    parser.add_argument(
        "--postgres-bin",
        type=Path,
        default=Path(os.environ.get("V4_07_POSTGRES_BIN", r"E:\Postgres\bin")),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "reports/v4_07/V4_07_MIGRATION_ROLLBACK_TEST.json",
    )
    args = parser.parse_args()
    pg_bin = args.postgres_bin.resolve()
    initdb = pg_bin / "initdb.exe"
    pg_ctl = pg_bin / "pg_ctl.exe"
    psql = pg_bin / "psql.exe"
    postgres = pg_bin / "postgres.exe"
    for executable in (initdb, pg_ctl, psql, postgres):
        if not executable.is_file():
            raise FileNotFoundError(f"PostgreSQL executable is missing: {executable}")

    migration = ROOT / "src/workbench_db/migrations/v4_postgres/015_v4_07_base_seed_results.sql"
    rollback = ROOT / "src/workbench_db/migrations/v4_postgres/rollback/015_v4_07_base_seed_results.sql"
    version = run([str(postgres), "--version"]).stdout.strip()
    migration_applied = False
    append_only_update_rejected = False
    append_only_delete_rejected = False
    rollback_scoped = False

    with tempfile.TemporaryDirectory(prefix="v4_07_postgres_") as temporary:
        temp_root = Path(temporary)
        data = temp_root / "data"
        log = temp_root / "postgres.log"
        run([str(initdb), "-D", str(data), "-U", "postgres", "--auth=trust", "--encoding=UTF8"])
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]

        started = False
        try:
            run(
                [
                    str(pg_ctl),
                    "-D",
                    str(data),
                    "-o",
                    f"-h 127.0.0.1 -p {port}",
                    "-l",
                    str(log),
                    "-w",
                    "-t",
                    "60",
                    "start",
                ],
                capture_output=False,
            )
            started = True

            def psql_file(sql: str, name: str) -> subprocess.CompletedProcess[str]:
                sql_path = write_sql(temp_root / name, sql)
                return run(
                    [
                        str(psql),
                        "-X",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-h",
                        "127.0.0.1",
                        "-p",
                        str(port),
                        "-U",
                        "postgres",
                        "-d",
                        "postgres",
                        "-f",
                        str(sql_path),
                    ]
                )

            psql_file(
                """CREATE SCHEMA v4;
CREATE TABLE v4.publications (publication_id text PRIMARY KEY);
CREATE OR REPLACE FUNCTION v4.reject_append_only_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'append-only guard rejected %', TG_OP;
END;
$$;
INSERT INTO v4.publications VALUES ('PUB-3c03e227-c60a-4d8c-86ae-2861507c257b');
""",
                "prerequisites.sql",
            )
            run(
                [
                    str(psql),
                    "-X",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-h",
                    "127.0.0.1",
                    "-p",
                    str(port),
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                    "-f",
                    str(migration),
                ]
            )
            migration_applied = True

            mutation_result = psql_file(
                """INSERT INTO v4.base_seed_results (
  publication_id, trade_date, security_id, model_contract_id, parameter_set_id,
  source_publication_id, source_core_logical_digest, input_digest, fact_digest,
  base_seed_state, matched_seed_paths, domain_states, waiting_for, invalid_if,
  quality, quality_codes, seed_participation_annotation
) VALUES (
  'PUB-3c03e227-c60a-4d8c-86ae-2861507c257b', '2026-09-28', 'SEC-00000000000000000000000000000000',
  'BASE_SEED_V1', 'V4_07_BASE_SEED_PARAMETER_SET_V1', 'V4_05_R4_T0_CURRENT_COORDINATE',
  repeat('a',64), repeat('b',64), repeat('c',64), 'UNKNOWN', '[]', '{}', '[]', '[]',
  'PARTIAL_UNKNOWN', '[]', 'UNKNOWN'
);
DO $$
DECLARE msg text;
BEGIN
  BEGIN
    UPDATE v4.base_seed_results SET quality='COMPLETE';
    RAISE EXCEPTION 'UPDATE_SHOULD_FAIL';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS msg = MESSAGE_TEXT;
    IF msg NOT LIKE 'append-only guard rejected UPDATE%' THEN RAISE; END IF;
  END;
  BEGIN
    DELETE FROM v4.base_seed_results;
    RAISE EXCEPTION 'DELETE_SHOULD_FAIL';
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS msg = MESSAGE_TEXT;
    IF msg NOT LIKE 'append-only guard rejected DELETE%' THEN RAISE; END IF;
  END;
END;
$$;
SELECT 'INSERT_AND_APPEND_ONLY_GUARD_PASS' AS result;
""",
                "mutation_checks.sql",
            )
            append_only_update_rejected = "UPDATE_SHOULD_FAIL" not in mutation_result.stdout
            append_only_delete_rejected = "DELETE_SHOULD_FAIL" not in mutation_result.stdout

            run(
                [
                    str(psql),
                    "-X",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-h",
                    "127.0.0.1",
                    "-p",
                    str(port),
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                    "-f",
                    str(rollback),
                ]
            )
            scope_result = psql_file(
                """DO $$ BEGIN
  IF to_regclass('v4.base_seed_results') IS NOT NULL THEN RAISE EXCEPTION 'stage table remains'; END IF;
  IF to_regclass('v4.publications') IS NULL THEN RAISE EXCEPTION 'pre-existing publications table lost'; END IF;
END $$;
SELECT 'ROLLBACK_SCOPE_PASS' AS result;
""",
                "rollback_scope.sql",
            )
            rollback_scoped = "ROLLBACK_SCOPE_PASS" in scope_result.stdout
        finally:
            if started:
                status = run([str(pg_ctl), "-D", str(data), "status"], check=False)
                if status.returncode == 0:
                    run([str(pg_ctl), "-D", str(data), "-m", "fast", "-w", "-t", "30", "stop"])

    checks = {
        "migration_015_applied": migration_applied,
        "insert_allowed": migration_applied,
        "update_rejected": append_only_update_rejected,
        "delete_rejected": append_only_delete_rejected,
        "rollback_removed_only_stage_table": rollback_scoped,
    }
    passed = all(checks.values())
    evidence = {
        "contract_id": "V4_07_MIGRATION_ROLLBACK_TEST_V1",
        "status": "PASS_ISOLATED_MIGRATION_AND_ROLLBACK" if passed else "FAIL",
        "postgres_version": version,
        "database_scope": "disposable localhost PostgreSQL cluster initialized by this script; no configured database or config/.env used",
        "checks": checks,
        "migration_015_sha256": sha256(migration),
        "rollback_015_sha256": sha256(rollback),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
