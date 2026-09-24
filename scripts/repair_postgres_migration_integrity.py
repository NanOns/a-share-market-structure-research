"""Restore verified legacy keys and refresh current immutable artifact records.

Contract: PGM_REPAIR_INTEGRITY_V1. Reads only the frozen DuckDB snapshot and
performs narrowly scoped, conflict-safe PostgreSQL inserts/metadata updates.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime/postgres_migration/20260922/market_research.source.duckdb"
REPORT = ROOT / "runtime/postgres_migration/20260923/pg_integrity_repair_receipt.json"
REPAIR_TABLES = {
    "analysis_slice_result_bindings": ("slice_id",),
    "analysis_snapshot_entries": ("snapshot_id", "domain", "trade_date"),
}


def read_dsn() -> str:
    value = os.environ.get("WORKBENCH_PG_DSN")
    env_file = ROOT / "config/.env"
    if not value and env_file.is_file():
        for line in env_file.read_text("utf-8").splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip() == "WORKBENCH_PG_DSN":
                value = val.strip().strip("\"").strip("'")
                break
    if not value:
        raise RuntimeError("WORKBENCH_PG_DSN_REQUIRED")
    return value


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def missing_count(pg: psycopg.Connection, table: str, keys: tuple[str, ...]) -> int:
    projection = sql.SQL(",").join(map(sql.Identifier, keys))
    q = sql.SQL("select count(*) from (select {k} from legacy.{t} except select {k} from workbench.{t}) m").format(k=projection, t=sql.Identifier(table))
    return int(pg.execute(q).fetchone()[0])


def reconcile_catalog(pg: psycopg.Connection) -> dict[str, object]:
    rows = pg.execute(
        "select artifact_id,category,managed_root_id,relative_path,sha256,size_bytes,artifact_contract,migration_class "
        "from workbench_meta.artifact_catalog where availability='AVAILABLE' order by relative_path,artifact_id"
    ).fetchall()
    changed: list[dict[str, object]] = []
    for old_id, category, root_id, rel, old_hash, old_size, contract, migration_class in rows:
        path = (ROOT / Path(*str(rel).replace("\\", "/").split("/"))).resolve()
        if root_id != "PROJECT_ROOT" or (path != ROOT and ROOT not in path.parents):
            continue
        if not path.is_file():
            continue
        actual_hash, actual_size = digest(path), path.stat().st_size
        if actual_hash == old_hash and actual_size == old_size:
            continue
        changed.append({"relative_path": rel, "old_sha256": old_hash, "new_sha256": actual_hash, "old_size": old_size, "new_size": actual_size})
        new_id = hashlib.sha256(f"workspace|{rel}|{actual_hash}".encode("utf-8")).hexdigest()
        pg.execute("update workbench_meta.artifact_catalog set availability='STALE_REFERENCE' where artifact_id=%s", (old_id,))
        pg.execute(
            "insert into workbench_meta.artifact_catalog "
            "(artifact_id,category,managed_root_id,relative_path,sha256,size_bytes,artifact_contract,availability,migration_class,migration_source_path,discovered_at) "
            "values (%s,%s,%s,%s,%s,%s,%s,'AVAILABLE',%s,%s,%s) on conflict (artifact_id) do update set "
            "category=excluded.category,sha256=excluded.sha256,size_bytes=excluded.size_bytes,artifact_contract=excluded.artifact_contract,"
            "availability='AVAILABLE',migration_class=excluded.migration_class,migration_source_path=excluded.migration_source_path,discovered_at=excluded.discovered_at",
            (new_id, category, root_id, rel, actual_hash, actual_size, contract, migration_class, str(path), datetime.now(timezone.utc)),
        )

    bundle_files = sorted((ROOT / "data/research_bundles_v3_3").glob("*/bundle.json"))
    registered_bundle_files = 0
    for manifest in bundle_files:
        bundle_dir = manifest.parent
        for path in sorted(p for p in bundle_dir.iterdir() if p.is_file()):
            rel = path.relative_to(ROOT).as_posix()
            file_hash = digest(path)
            artifact_id = hashlib.sha256(f"workspace|{rel}|{file_hash}".encode("utf-8")).hexdigest()
            pg.execute("update workbench_meta.artifact_catalog set availability='STALE_REFERENCE' where managed_root_id='PROJECT_ROOT' and relative_path=%s and availability='AVAILABLE' and sha256<>%s", (rel, file_hash))
            pg.execute(
                "insert into workbench_meta.artifact_catalog "
                "(artifact_id,category,managed_root_id,relative_path,sha256,size_bytes,artifact_contract,availability,migration_class,migration_source_path,discovered_at) "
                "values (%s,'V3_3_BUNDLE','PROJECT_ROOT',%s,%s,%s,'V3_3_IMMUTABLE_BUNDLE_FILE_V1','AVAILABLE','RETAIN_EXTERNAL',%s,%s) "
                "on conflict (artifact_id) do update set availability='AVAILABLE',sha256=excluded.sha256,size_bytes=excluded.size_bytes,discovered_at=excluded.discovered_at",
                (artifact_id, rel, file_hash, path.stat().st_size, str(path), datetime.now(timezone.utc)),
            )
            registered_bundle_files += 1
    return {"stale_records": len(changed), "changed_files": changed, "bundle_files_registered": registered_bundle_files}


def main() -> int:
    source_hash = digest(SOURCE)
    duck = duckdb.connect(str(SOURCE), read_only=True)
    source_counts = {t: int(duck.execute(f'select count(*) from "{t}"').fetchone()[0]) for t in REPAIR_TABLES}
    dsn = read_dsn()
    receipt: dict[str, object] = {"contract": "PGM_REPAIR_INTEGRITY_V1", "source_sha256": source_hash, "source_rows": source_counts, "started_at_utc": datetime.now(timezone.utc).isoformat(), "status": "BLOCKED"}
    try:
        with psycopg.connect(dsn) as pg:
            with pg.transaction():
                pg.execute("set transaction isolation level serializable")
                pg.execute("lock table workbench.analysis_slice_result_bindings, workbench.analysis_snapshot_entries in share row exclusive mode")
                before = {t: missing_count(pg, t, keys) for t, keys in REPAIR_TABLES.items()}
                expected = {"analysis_slice_result_bindings": 18, "analysis_snapshot_entries": 818}
                if before != expected:
                    raise RuntimeError(f"UNEXPECTED_MISSING_KEY_SET:{before}")
                refs = {
                    "slice_result_bindings": int(pg.execute("select count(*) from (select l.slice_id from legacy.analysis_slice_result_bindings l left join workbench.analysis_slices s using(slice_id) left join workbench.analysis_result_objects o using(result_object_id) where s.slice_id is null or o.result_object_id is null) x").fetchone()[0]),
                    "snapshot_entries": int(pg.execute("select count(*) from (select l.snapshot_id,l.slice_id from legacy.analysis_snapshot_entries l left join workbench.analysis_snapshots s using(snapshot_id) left join workbench.analysis_slices a using(slice_id) where s.snapshot_id is null or a.slice_id is null) x").fetchone()[0]),
                }
                if any(refs.values()):
                    raise RuntimeError(f"MISSING_REPAIR_REFERENCES:{refs}")
                for table in ("analysis_slice_result_bindings", "analysis_snapshot_entries"):
                    pg.execute(sql.SQL("insert into workbench.{t} select * from legacy.{t} on conflict do nothing").format(t=sql.Identifier(table)))
                after = {t: missing_count(pg, t, keys) for t, keys in REPAIR_TABLES.items()}
                if any(after.values()):
                    raise RuntimeError(f"RESTORE_DID_NOT_CLOSE_KEY_GAPS:{after}")
                artifact_result = reconcile_catalog(pg)
                receipt.update({"before_missing_keys": before, "after_missing_keys": after, "references": refs, "artifact_catalog": artifact_result, "status": "FULL_PASS", "finished_at_utc": datetime.now(timezone.utc).isoformat()})
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        tmp = REPORT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, REPORT)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    finally:
        duck.close()


if __name__ == "__main__":
    raise SystemExit(main())
