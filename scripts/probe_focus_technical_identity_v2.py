"""Read-only reconciliation of one accepted technical object across DuckDB and PG."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import psycopg
from psycopg import sql

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.technical_identity import CONTRACT_ID, canonical_technical_identity
from workbench_analysis.technical import TECHNICAL_RESULT_COLUMNS, _technical_hash


DEFAULT_BACKUP = Path("runtime/manual_delete_backups/trade_date_2026-09-22_20260922T144602Z/market_research.duckdb")
DEFAULT_OBJECT = "result-obj-96a6dbe035d14025db62b71ec11ec90b"


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(8 * 1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def run(*, backup: Path = DEFAULT_BACKUP, object_id: str = DEFAULT_OBJECT) -> dict[str, object]:
    backup = backup.resolve(strict=True)
    columns = ",".join(TECHNICAL_RESULT_COLUMNS)
    with duckdb.connect(str(backup), read_only=True) as source:
        original = [dict(zip(TECHNICAL_RESULT_COLUMNS, row)) for row in source.execute(
            f"select {columns} from technical_result_rows where result_object_id=? "
            "order by security_id,trade_date", [object_id]).fetchall()]
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select value_hash,row_count,semantic_contract from "
                        "workbench.analysis_result_objects where result_object_id=%s", (object_id,))
            registered = cur.fetchone()
            if registered is None:
                raise ValueError("accepted technical object not registered")
            cur.execute(sql.SQL("select {} from workbench.technical_result_rows "
                                "where result_object_id=%s order by security_id,trade_date")
                        .format(sql.SQL(",").join(map(sql.Identifier, TECHNICAL_RESULT_COLUMNS))),
                        (object_id,))
            migrated = [dict(zip(TECHNICAL_RESULT_COLUMNS, row)) for row in cur.fetchall()]
        connection.rollback()
    legacy_hash, legacy_count, _ = _technical_hash(original)
    source_hash, source_logical, source_count = canonical_technical_identity(original)
    target_hash, target_logical, target_count = canonical_technical_identity(migrated)
    backup_sha = file_sha256(backup)
    if not (legacy_hash == registered[0] and legacy_count == registered[1] ==
            source_count == target_count and source_hash == target_hash and
            source_logical == target_logical and registered[2] == "TECHNICAL_RESULT_V3"):
        raise ValueError("technical identity reconciliation failed closed")
    return {"contract_id": CONTRACT_ID, "status": "READ_ONLY_RECONCILED",
            "source_object_id": object_id, "legacy_hash": legacy_hash,
            "canonical_hash": source_hash, "canonical_logical_hash": source_logical,
            "row_count": source_count, "backup_sha256": backup_sha,
            "migration_reason": "DUCKDB_JSON_TEXT_TO_POSTGRES_JSONB_SEMANTIC_EQUIVALENCE"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--result-object-id", default=DEFAULT_OBJECT)
    arguments = parser.parse_args()
    print(json.dumps(run(backup=arguments.backup, object_id=arguments.result_object_id),
                     ensure_ascii=False, sort_keys=True))
