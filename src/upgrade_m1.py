"""Execute M1: schema, repository, logical digest, history import and ownership."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq

from workbench_db.digest import logical_digest, normalize_csv_row
from workbench_db.repository import SCHEMA_VERSION, WorkbenchRepository


VERSION = "unified-workbench-m1-data-foundation-v1.1"
FIXED_DATE = "20260904"
HEADS = {
    "20260904": "695c7ae5affd4abbb3d86eddb4b154e0",
    "20260907": "452811b8e0c54c029560aae46c6d3081",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _atomic(path: Path, text: str, tdx: Path) -> None:
    path = path.resolve(); tdx = tdx.resolve()
    if path == tdx or tdx in path.parents:
        raise ValueError("OUTPUT_UNDER_TDX_ROOT")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _csv_digest(path: Path, primary_key: list[str]) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = [normalize_csv_row(row) for row in reader]
    return logical_digest(rows, columns, primary_key)


def _table_digest(repository: WorkbenchRepository, table: str, publication_id: str, columns: list[str], primary_key: list[str]) -> dict[str, Any]:
    return logical_digest(repository.payload_rows(table, publication_id), columns, primary_key)


def _source_rows(path: Path, artifact_name: str, trade_date: str) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [normalize_csv_row(row) for row in csv.DictReader(handle)]
    rows = pq.read_table(path).to_pylist()
    if artifact_name in {"market_daily", "membership_entries"}:
        rows = [row for row in rows if str(row.get("date")) == trade_date]
    return rows


def _database_rows(repository: WorkbenchRepository, publication_id: str, artifact_name: str) -> list[dict[str, Any]]:
    assert repository.connection is not None
    if artifact_name == "membership_entries":
        snapshot = repository.connection.execute(
            "SELECT membership_snapshot_id FROM publication_memberships WHERE publication_id=?", [publication_id]
        ).fetchone()[0]
        values = repository.connection.execute(
            "SELECT payload_json FROM membership_entries WHERE membership_snapshot_id=?", [snapshot]
        ).fetchall()
        return [json.loads(value) for (value,) in values]
    if artifact_name.startswith("structure_details/"):
        queue = artifact_name.split("/", 1)[1]
        values = repository.connection.execute(
            "SELECT payload_json FROM structure_details WHERE publication_id=? AND queue_name=?", [publication_id, queue]
        ).fetchall()
        return [json.loads(value) for (value,) in values]
    table = {
        "stocks.csv": "stock_daily",
        "sectors.csv": "sector_daily",
        "candidates.csv": "candidate_daily",
        "market_daily": "market_daily",
        "queue_memberships": "queue_memberships",
        "unified_board": "unified_board",
        "queue_rankings": "queue_rankings",
    }[artifact_name]
    return repository.payload_rows(table, publication_id)


def _all_artifact_comparisons(repository: WorkbenchRepository) -> dict[str, dict[str, Any]]:
    assert repository.connection is not None
    rows = repository.connection.execute(
        "SELECT a.publication_id, CAST(p.trade_date AS VARCHAR), a.artifact_name, a.source_path, "
        "a.file_sha256, a.logical_sha256, a.row_count, a.columns_json, a.primary_key_json "
        "FROM publication_artifacts a JOIN publications p USING(publication_id) ORDER BY 1, 3"
    ).fetchall()
    comparisons: dict[str, dict[str, Any]] = {}
    for publication_id, trade_date, name, source_path, file_sha, registered_sha, registered_count, columns_json, key_json in rows:
        path = Path(source_path)
        columns, primary_key = json.loads(columns_json), json.loads(key_json)
        source = logical_digest(_source_rows(path, name, trade_date), columns, primary_key)
        database = logical_digest(_database_rows(repository, publication_id, name), columns, primary_key)
        file_matches = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == file_sha
        passed = (
            file_matches
            and source["sha256"] == database["sha256"] == registered_sha
            and source["row_count"] == database["row_count"] == registered_count
        )
        comparisons[f"{publication_id}:{name}"] = {
            "source_rows": source["row_count"], "database_rows": database["row_count"],
            "source_logical_sha256": source["sha256"], "database_logical_sha256": database["sha256"],
            "registered_logical_sha256": registered_sha, "file_sha256_matches": file_matches, "pass": passed,
        }
    return comparisons


def _markdown(receipt: dict[str, Any]) -> str:
    return "\n".join([
        "# M1 数据底座验收",
        "",
        f"- 状态：`{receipt['final_status']}`",
        f"- Schema：`{receipt['schema_version']}`",
        f"- 数据库：`{receipt['database_path']}`",
        f"- 历史发布：{receipt['publication_count']} 个；日期 {', '.join(receipt['publication_dates'])}",
        f"- 固定日期逐字段一致：`{receipt['acceptance']['fixed_date_field_equality']}`",
        f"- 重复导入无重复：`{receipt['acceptance']['repeat_import_idempotent']}`",
        f"- 单所有者互斥：`{receipt['acceptance']['single_owner_exclusive']}`",
        "",
        "逻辑摘要与文件 SHA256 分开保存；CSV 空值规范化为 NULL，非空数值文本保留原精度。旧发布文件未修改。",
        "",
        f"下一阶段：`{receipt['next_stage']}`，必须由用户手动开启。",
        "",
    ])


def run(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    tdx = Path(r"D:\new_tdx").resolve()
    m0 = json.loads((root / "reports/upgrade_m0/M0_RISK_CONVERGENCE_RECEIPT.json").read_text(encoding="utf-8"))
    if m0.get("final_status") != "FULL_PASS" or not m0.get("phase_accepted"):
        raise RuntimeError("M0_FULL_PASS_REQUIRED")
    database = root / "data/database/market_research.duckdb"
    candidate_database = database.with_name("market_research.m1_candidate.duckdb")
    candidate_database.unlink(missing_ok=True)
    candidate_database.with_suffix(candidate_database.suffix + ".owner.lock").unlink(missing_ok=True)
    imports = []
    checks: dict[str, Any] = {}
    with WorkbenchRepository(root, candidate_database) as repository:
        for revision, (date, run_id) in enumerate(sorted(HEADS.items()), start=1):
            release = root / "reports/releases" / date / run_id
            imports.append(repository.import_publication(release, revision=revision, make_head=True))
        count_tables = ["publications", "publication_heads", "stock_daily", "sector_daily", "candidate_daily", "market_daily", "structure_details", "queue_memberships", "unified_board", "queue_rankings", "membership_entries", "publication_artifacts"]
        before = {table: repository.table_count(table) for table in count_tables}
        repeat_imports = []
        for revision, (date, run_id) in enumerate(sorted(HEADS.items()), start=1):
            repeat_imports.append(repository.import_publication(root / "reports/releases" / date / run_id, revision=revision, make_head=True))
        after = {table: repository.table_count(table) for table in count_tables}
        checks["repeat_import_idempotent"] = before == after and all(item.get("reused") for item in repeat_imports)
        checks["repeat_import_results"] = repeat_imports
        fixed_id = HEADS[FIXED_DATE]
        comparisons = {}
        for filename, table, key in (("stocks.csv", "stock_daily", ["security_id"]), ("sectors.csv", "sector_daily", ["sector_id"]), ("candidates.csv", "candidate_daily", ["security_id"])):
            path = root / "reports/releases" / FIXED_DATE / fixed_id / filename
            source = _csv_digest(path, key)
            artifact = repository.connection.execute("SELECT columns_json, logical_sha256, row_count FROM publication_artifacts WHERE publication_id=? AND artifact_name=?", [fixed_id, filename]).fetchone()
            columns = json.loads(artifact[0])
            database_digest = _table_digest(repository, table, fixed_id, columns, key)
            comparisons[filename] = {"source_logical_sha256": source["sha256"], "database_logical_sha256": database_digest["sha256"], "artifact_logical_sha256": artifact[1], "source_rows": source["row_count"], "database_rows": database_digest["row_count"], "columns_equal": source["columns"] == columns, "pass": source["sha256"] == database_digest["sha256"] == artifact[1] and source["row_count"] == database_digest["row_count"] == artifact[2]}
        checks["fixed_date_field_equality"] = all(value["pass"] for value in comparisons.values())
        checks["fixed_date_comparisons"] = comparisons
        artifact_comparisons = _all_artifact_comparisons(repository)
        checks["all_artifact_field_equality"] = len(artifact_comparisons) == 26 and all(
            value["pass"] for value in artifact_comparisons.values()
        )
        checks["artifact_comparisons"] = artifact_comparisons
        checks["primary_key_uniqueness"] = all(repository.connection.execute(f"SELECT count(*)=count(DISTINCT {key}) FROM {table} WHERE publication_id=?", [fixed_id]).fetchone()[0] for table, key in (("stock_daily", "security_id"), ("sector_daily", "sector_id"), ("candidate_daily", "security_id"), ("unified_board", "security_id")))
        checks["head_only_success"] = repository.connection.execute(
            "SELECT count(*)=2 AND bool_and(p.status='SUCCESS') AND bool_and(h.trade_date=p.trade_date) "
            "FROM publication_heads h JOIN publications p USING(publication_id)"
        ).fetchone()[0]
        checks["single_owner_exclusive"] = False
        probe = "from pathlib import Path; import sys; sys.path.insert(0,str(Path.cwd()/'src')); from workbench_db.owner import DatabaseOwner,DatabaseOwnerBusy;\ntry: DatabaseOwner(Path(r'%s')).acquire(); raise SystemExit(1)\nexcept DatabaseOwnerBusy: raise SystemExit(0)" % str(candidate_database).replace("\\", "\\\\")
        busy = subprocess.run([sys.executable, "-c", probe], cwd=root, capture_output=True, text=True, timeout=30)
        checks["single_owner_exclusive"] = busy.returncode == 0
        table_counts = after
        publication_dates = [str(row[0]) for row in repository.connection.execute("SELECT trade_date FROM publication_heads ORDER BY trade_date").fetchall()]
        migration_versions = [row[0] for row in repository.connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
    test_run = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/upgrade_m1"], cwd=root, capture_output=True, text=True, timeout=120)
    checks["m1_tests"] = test_run.returncode == 0
    all_pass = all(bool(checks[name]) for name in ("repeat_import_idempotent", "fixed_date_field_equality", "all_artifact_field_equality", "primary_key_uniqueness", "head_only_success", "single_owner_exclusive", "m1_tests"))
    if all_pass:
        database.parent.mkdir(parents=True, exist_ok=True)
        os.replace(candidate_database, database)
    receipt = {
        "version": VERSION,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_status": "FULL_PASS" if all_pass else "BLOCKED",
        "phase_accepted": all_pass,
        "phase_closed": all_pass,
        "next_stage": "M2_SERVICE_AND_READ_ONLY_UI" if all_pass else "NONE",
        "manual_gate": "REQUIRE_EXPLICIT_USER_START_FOR_NEXT_STAGE",
        "m0_receipt_sha256": m0.get("receipt_sha256"),
        "schema_version": SCHEMA_VERSION,
        "migration_versions": migration_versions,
        "database_path": str(database),
        "database_bytes": database.stat().st_size if all_pass else candidate_database.stat().st_size,
        "database_engine": "DuckDB",
        "publication_count": table_counts["publications"],
        "publication_dates": publication_dates,
        "head_run_ids": HEADS,
        "table_counts": table_counts,
        "imports": imports,
        "acceptance": checks,
        "test_output": (test_run.stdout + test_run.stderr)[-4000:],
        "tdx_write_attempted": False,
        "network_data_used": False,
        "scanner_started": False,
        "service_started": False,
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    output = root / "reports/upgrade_m1"
    _atomic(output / "M1_DATA_FOUNDATION_RECEIPT.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", tdx)
    _atomic(output / "M1_DATA_FOUNDATION.md", _markdown(receipt), tdx)
    return receipt
