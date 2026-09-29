from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
TASK_NAMES = (
    "001_v4_phase0_foundation.sql",
    "002_namespace_integrity.sql",
    "003_phase0_contract_alignment.sql",
    "004_publication_head_revision_identity.sql",
    "005_market_session_publication_chain.sql",
    "006_fact_source_guard_table_specific_fields.sql",
    "007_state_and_namespace_publication_identity.sql",
    "008_prior_session_state_freeze_integrity.sql",
    "009_publication_head_guard_sql_alias_fix.sql",
    "010_security_lifecycle_history_r5.sql",
    "011_security_membership_interval_r6_2.sql",
    "012_provider_lifecycle_fact_r6_2.sql",
    "013_v4_06_stock_profile_enrichments.sql",
    "014_v4_06_turnover_contract_semantics_r2.sql",
    "015_v4_07_base_seed_results.sql",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: Sequence[str], *, check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay required V4 Phase 0 schema tests against a disposable local PostgreSQL cluster."
    )
    parser.add_argument(
        "--postgres-bin",
        type=Path,
        default=Path(os.environ.get("V4_07_POSTGRES_BIN", r"E:\Postgres\bin")),
    )
    parser.add_argument(
        "--accepted-inputs-root",
        type=Path,
        default=Path(os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT", r"E:\codex work\大A交易")),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "reports/v4_07/V4_07_ISOLATED_FULL_REGRESSION.json",
    )
    args = parser.parse_args()
    pg_bin = args.postgres_bin.resolve()
    source_root = args.accepted_inputs_root.resolve()
    migration_sources = []
    for name in TASK_NAMES:
        if name.startswith("014_"):
            path = source_root / "src/workbench_db/migrations/v4_postgres" / name
        else:
            path = ROOT / "src/workbench_db/migrations/v4_postgres" / name
        if not path.is_file():
            raise FileNotFoundError(f"required isolated regression migration is missing: {path}")
        migration_sources.append(path)

    version_names = {
        "014_v4_06_turnover_contract_semantics_r2.sql": "V4_06_TURNOVER_CONTRACT_SEMANTICS_R2",
        "015_v4_07_base_seed_results.sql": "V4_07_BASE_SEED_RESULTS_V1",
    }
    pg_ctl = pg_bin / "pg_ctl.exe"
    initdb = pg_bin / "initdb.exe"
    createdb = pg_bin / "createdb.exe"
    postgres = pg_bin / "postgres.exe"
    for executable in (pg_ctl, initdb, createdb, postgres):
        if not executable.is_file():
            raise FileNotFoundError(f"PostgreSQL executable is missing: {executable}")
    version_text = run([str(postgres), "--version"]).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="v4_07_phase0_pg_") as temporary:
        temp_root = Path(temporary)
        data = temp_root / "data"
        log = temp_root / "postgres.log"
        migrations = temp_root / "migrations"
        migrations.mkdir()
        for source in migration_sources:
            (migrations / source.name).write_bytes(source.read_bytes())

        run(
            [
                str(initdb),
                "-D",
                str(data),
                "-U",
                "postgres",
                "--auth=trust",
                "--encoding=UTF8",
                "--locale=Chinese (Simplified)_China.936",
            ]
        )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        started = False
        dsn = f"host=127.0.0.1 port={port} dbname=market_research user=postgres sslmode=disable"
        prior_dsn = os.environ.get("WORKBENCH_PG_DSN")
        prior_v406_root = os.environ.get("V4_06_ACCEPTED_INPUTS_ROOT")
        prior_v407_root = os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT")
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
            run(
                [
                    str(createdb),
                    "-h",
                    "127.0.0.1",
                    "-p",
                    str(port),
                    "-U",
                    "postgres",
                    "-O",
                    "postgres",
                    "market_research",
                ]
            )

            sys.path.insert(0, str(ROOT))
            import scripts.apply_v4_phase0_schema as schema_runner

            schema_runner.MIGRATIONS = migrations
            schema_runner.VERSIONS = {
                **schema_runner.VERSIONS,
                **version_names,
            }
            os.environ["WORKBENCH_PG_DSN"] = dsn
            os.environ["V4_06_ACCEPTED_INPUTS_ROOT"] = str(source_root)
            os.environ["V4_07_ACCEPTED_INPUTS_ROOT"] = str(source_root)
            migration_receipt = schema_runner.apply()

            pytest = run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/v4_01",
                    "tests/v4_02",
                    "tests/v4_03",
                    "tests/v4_04",
                    "tests/v4_05",
                    "tests/v4_06",
                    "tests/v4_07",
                    "tests/v4_joint",
                    "tests/v4_phase0",
                    "-q",
                ],
                check=False,
            )
            if pytest.returncode:
                raise RuntimeError(
                    f"isolated combined regression suite failed ({pytest.returncode})\n"
                    f"stdout:\n{pytest.stdout}\nstderr:\n{pytest.stderr}"
                )
            test_output = (pytest.stdout + pytest.stderr).strip()
        finally:
            if prior_dsn is None:
                os.environ.pop("WORKBENCH_PG_DSN", None)
            else:
                os.environ["WORKBENCH_PG_DSN"] = prior_dsn
            for key, prior in (
                ("V4_06_ACCEPTED_INPUTS_ROOT", prior_v406_root),
                ("V4_07_ACCEPTED_INPUTS_ROOT", prior_v407_root),
            ):
                if prior is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prior
            if started:
                status = run([str(pg_ctl), "-D", str(data), "status"], check=False)
                if status.returncode == 0:
                    run([str(pg_ctl), "-D", str(data), "-m", "fast", "-w", "-t", "30", "stop"])

    evidence = {
        "contract_id": "V4_07_ISOLATED_FULL_REGRESSION_V1",
        "status": "PASS_ISOLATED_FULL_REGRESSION",
        "test_command": "python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_05 tests/v4_06 tests/v4_07 tests/v4_joint tests/v4_phase0 -q",
        "test_output": test_output,
        "test_summary": test_output.splitlines()[-1] if test_output.splitlines() else "MISSING_SUMMARY",
        "postgres_version": version_text,
        "database_identity": {
            "database": "market_research",
            "user": "postgres",
            "host": "127.0.0.1",
            "port": port,
            "database_is_disposable": True,
            "dsn_source": "process environment WORKBENCH_PG_DSN; config/.env not read or created",
        },
        "migration_run": migration_receipt,
        "migration_014_read_only_source": str(migration_sources[-2]),
        "migration_014_sha256": sha256(migration_sources[-2]),
        "migration_015_sha256": sha256(migration_sources[-1]),
        "temporary_cluster_cleaned_up": True,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
