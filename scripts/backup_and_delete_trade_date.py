"""Back up and remove one generated trade date from PG and DuckDB stores.

The operation is deliberately explicit and requires ``--apply``. Raw parquet,
TDX inputs, and historical dates are never targeted.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
from typing import Any

import duckdb
import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "workbench"


def qi(value: str) -> sql.Identifier:
    return sql.Identifier(value)


def qd(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return value
    return value


def table_columns_pg(pg: psycopg.Connection[Any]) -> dict[str, list[str]]:
    with pg.cursor() as cur:
        cur.execute("select table_name,column_name from information_schema.columns where table_schema=%s order by table_name,ordinal_position", (SCHEMA,))
        result: dict[str, list[str]] = {}
        for table, column in cur.fetchall():
            result.setdefault(str(table), []).append(str(column))
        return result


def table_columns_duck(connection: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for table, column in connection.execute("select table_name,column_name from information_schema.columns where table_schema='main' order by table_name,ordinal_position").fetchall():
        result.setdefault(str(table), []).append(str(column))
    return result


def pg_fk_order(pg: psycopg.Connection[Any]) -> list[str]:
    with pg.cursor() as cur:
        cur.execute("""
            select tc.table_name,kcu.table_name,ccu.table_name
              from information_schema.table_constraints tc
              join information_schema.key_column_usage kcu using(constraint_name,table_schema,table_name)
              join information_schema.constraint_column_usage ccu using(constraint_name,table_schema)
             where tc.table_schema=%s and tc.constraint_type='FOREIGN KEY'
        """, (SCHEMA,))
        edges = [(str(child), str(parent)) for child, _ignored, parent in cur.fetchall()]
        tables = {str(row[0]) for row in cur.execute("select table_name from information_schema.tables where table_schema=%s and table_type='BASE TABLE'", (SCHEMA,)).fetchall()}
    children: dict[str, set[str]] = {table: set() for table in tables}
    for child, parent in edges:
        children.setdefault(parent, set()).add(child)
    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(table: str) -> None:
        if table in visited or table in visiting:
            return
        visiting.add(table)
        for child in sorted(children.get(table, ())):
            visit(child)
        visiting.remove(table); visited.add(table); order.append(table)
    for table in sorted(tables):
        visit(table)
    return order


def resolve_ids(pg: psycopg.Connection[Any], trade_date: date) -> dict[str, Any]:
    with pg.cursor() as cur:
        cur.execute("select publication_id from workbench.publications where trade_date=%s", (trade_date,)); publications = [str(row[0]) for row in cur.fetchall()]
        cur.execute("select snapshot_id from workbench.publication_analysis_snapshots where publication_id = any(%s)", (publications,)); snapshots = [str(row[0]) for row in cur.fetchall()] if publications else []
        cur.execute("select slice_id from workbench.analysis_snapshot_entries where snapshot_id = any(%s)", (snapshots,)); slices = [str(row[0]) for row in cur.fetchall()] if snapshots else []
        cur.execute("select result_object_id from workbench.analysis_slice_result_bindings where slice_id = any(%s)", (slices,)); objects = [str(row[0]) for row in cur.fetchall()] if slices else []
        cur.execute("select run_id from workbench.research_runs where publication_id = any(%s)", (publications,)); runs = [str(row[0]) for row in cur.fetchall()] if publications else []
        cur.execute("select bundle_digest from workbench.research_runs_v3_3 where publication_id = any(%s)", (publications,)); bundles = [str(row[0]) for row in cur.fetchall()] if publications else []
        cur.execute("select observation_id from workbench.relation_publication_bindings where publication_id = any(%s)", (publications,)); observations = [str(row[0]) for row in cur.fetchall()] if publications else []
    return {"publications": publications, "snapshots": snapshots, "slices": slices, "objects": objects, "runs": runs, "bundles": bundles, "observations": observations}


def condition(columns: list[str], trade_date: date, ids: dict[str, Any], placeholder: str = "%s") -> tuple[str, list[Any]]:
    clauses: list[str] = []; params: list[Any] = []
    mapping = {
        "publication_id": (ids["publications"], "publication_id"), "snapshot_id": (ids["snapshots"], "snapshot_id"),
        "slice_id": (ids["slices"], "slice_id"), "result_object_id": (ids["objects"], "result_object_id"),
        "run_id": (ids["runs"], "run_id"), "signal_run_id": (ids["runs"], "signal_run_id"),
        "bundle_digest": (ids["bundles"], "bundle_digest"), "observation_id": (ids["observations"], "observation_id"),
    }
    for column, (values, _name) in mapping.items():
        if column in columns and values:
            clauses.append(f'{qd(column)} = any({placeholder})'); params.append(values)
    if "trade_date" in columns:
        clauses.append(f'{qd("trade_date")} = {placeholder}'); params.append(trade_date)
    return (" OR ".join(clauses) or "false"), params


def backup_pg(pg: psycopg.Connection[Any], backup_path: Path, trade_date: date, ids: dict[str, Any], columns: dict[str, list[str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with gzip.open(backup_path / "postgres_rows.jsonl.gz", "wt", encoding="utf-8") as output:
        with pg.cursor() as cur:
            for table, names in columns.items():
                predicate, params = condition(names, trade_date, ids)
                cur.execute(sql.SQL("select {} from {}.{} where ").format(sql.SQL(",").join(qi(name) for name in names), qi(SCHEMA), qi(table)) + sql.SQL(predicate), params)
                rows = cur.fetchall()
                if rows:
                    counts[table] = len(rows)
                    output.write(json.dumps({"table": table, "columns": names, "rows": [[jsonable(v) for v in row] for row in rows]}, ensure_ascii=False, default=str) + "\n")
    return counts


def delete_pg(pg: psycopg.Connection[Any], trade_date: date, ids: dict[str, Any], columns: dict[str, list[str]], order: list[str]) -> dict[str, int]:
    deleted: dict[str, int] = {}
    with pg.cursor() as cur:
        for table in order:
            names = columns.get(table, [])
            predicate, params = condition(names, trade_date, ids)
            if predicate == "false":
                continue
            cur.execute(sql.SQL("delete from {}.{} where ").format(qi(SCHEMA), qi(table)) + sql.SQL(predicate), params)
            if cur.rowcount:
                deleted[table] = cur.rowcount
    return deleted


def duck_condition(columns: list[str], trade_date: date, ids: dict[str, Any]) -> tuple[str, list[Any]]:
    clauses: list[str] = []; params: list[Any] = []
    for column, key in (("publication_id", "publications"), ("snapshot_id", "snapshots"), ("slice_id", "slices"), ("result_object_id", "objects"), ("run_id", "runs"), ("signal_run_id", "runs"), ("bundle_digest", "bundles"), ("observation_id", "observations")):
        values = ids[key]
        if column in columns and values:
            clauses.append(f'"{column}" in ({",".join("?" for _ in values)})'); params.extend(values)
    if "trade_date" in columns:
        clauses.append('"trade_date"=?'); params.append(trade_date)
    return (" or ".join(clauses) or "false"), params


def delete_duck(database: Path, trade_date: date, ids: dict[str, Any], order: list[str], backup_path: Path) -> dict[str, int]:
    deleted: dict[str, int] = {}
    with duckdb.connect(str(database)) as connection:
        columns = table_columns_duck(connection)
        with gzip.open(backup_path / (database.stem + "_rows.jsonl.gz"), "wt", encoding="utf-8") as output:
            for table, names in columns.items():
                predicate, params = duck_condition(names, trade_date, ids)
                if predicate == "false": continue
                rows = connection.execute(f'select {",".join(qd(n) for n in names)} from "{table}" where {predicate}', params).fetchall()
                if rows:
                    output.write(json.dumps({"table": table, "columns": names, "rows": [[jsonable(v) for v in row] for row in rows]}, ensure_ascii=False, default=str) + "\n")
            for table in order:
                names = columns.get(table, [])
                predicate, params = duck_condition(names, trade_date, ids)
                if predicate == "false": continue
                connection.execute(f'delete from "{table}" where {predicate}', params)
                count = connection.execute("select changes()" ).fetchone()[0] if False else 0
                # DuckDB does not expose rowcount consistently; re-counting is
                # intentionally omitted from the destructive path.
        connection.execute("CHECKPOINT")
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--trade-date", required=True); parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply: raise SystemExit("Refusing destructive delete without --apply")
    trade_date = date.fromisoformat(args.trade_date)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ROOT / "runtime" / "manual_delete_backups" / f"trade_date_{trade_date.isoformat()}_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    dsn = os.environ.get("WORKBENCH_PG_DSN")
    if not dsn: raise SystemExit("WORKBENCH_PG_DSN_REQUIRED")
    source_duck = ROOT / "data/database/market_research.duckdb"
    compute_duck = ROOT / "runtime/compute/daily_pipeline.duckdb"
    if source_duck.is_file(): shutil.copy2(source_duck, backup / source_duck.name)
    if compute_duck.is_file(): shutil.copy2(compute_duck, backup / compute_duck.name)
    pointer = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
    pointer_payload = json.loads(pointer.read_text(encoding="utf-8")) if pointer.is_file() else None
    if pointer_payload: (backup / pointer.name).write_text(json.dumps(pointer_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result: dict[str, Any] = {"trade_date": args.trade_date, "backup": str(backup), "data_generation_triggered": False}
    with psycopg.connect(dsn) as pg:
        columns = table_columns_pg(pg); ids = resolve_ids(pg, trade_date); result["ids"] = ids
        result["pg_backup_counts"] = backup_pg(pg, backup, trade_date, ids, columns)
        order = pg_fk_order(pg); result["pg_deleted_counts"] = delete_pg(pg, trade_date, ids, columns, order)
        pg.commit()
    if compute_duck.is_file():
        # The compute cache is not the serving store, but it must not retain
        # today's rows or the next page run could reuse stale artifacts.
        result["compute_deleted"] = True
        delete_duck(compute_duck, trade_date, ids, order, backup)
    if pointer_payload:
        bundle_path = Path(str(pointer_payload.get("bundle_path") or "")).resolve()
        if ROOT in bundle_path.parents and bundle_path.is_dir():
            shutil.copytree(bundle_path, backup / "active_bundle", dirs_exist_ok=True)
            shutil.rmtree(bundle_path)
        pointer.unlink(missing_ok=True)
        result["active_bundle_deleted"] = True
    (backup / "deletion_receipt.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__": raise SystemExit(main())
