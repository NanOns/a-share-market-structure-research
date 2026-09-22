"""Register external artifacts and database consumers for PGM-04."""
from __future__ import annotations

import argparse
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]


def qi(value: str) -> sql.Identifier:
    return sql.Identifier(value)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def category(path: Path) -> tuple[str, str]:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json":
        return "V3_3_BUNDLE_POINTER", "RETAIN_EXTERNAL"
    if rel.startswith("data/research_bundles_v3_3/"):
        return "V3_3_BUNDLE", "RETAIN_EXTERNAL"
    if rel.startswith("data/forward_v3_3/observations/"):
        return "V3_3_FORWARD_OBSERVATION", "RETAIN_EXTERNAL"
    if rel.startswith("data/forward_v3_3/evaluation_sources/"):
        return "V3_3_FORWARD_EVALUATION_SOURCE", "RETAIN_EXTERNAL"
    if rel.startswith("data/forward_v3_3/"):
        return "V3_3_FORWARD_ARTIFACT", "RETAIN_EXTERNAL"
    if rel.startswith("reports/p12_08/") and "outcome_plan" in path.name:
        return "V3_3_FORWARD_OUTCOME_PLAN", "RETAIN_EXTERNAL"
    if rel.startswith("reports/p12_08/") and "outcome" in path.name:
        return "V3_3_FORWARD_OUTCOME_RESULT", "RETAIN_EXTERNAL"
    if rel.startswith("data/normalized/"):
        return "NORMALIZED_PARQUET", "RETAIN_EXTERNAL"
    if rel.startswith("runtime/"):
        return "RUNTIME_POINTER_OR_RECEIPT", "RETAIN_EXTERNAL"
    return "OTHER_PROJECT_ARTIFACT", "RETAIN_EXTERNAL"


def files() -> list[Path]:
    roots = [
        ROOT / "data/current",
        ROOT / "data/research_bundles_v3_3",
        ROOT / "data/forward_v3_3",
        ROOT / "reports/p12_08",
        ROOT / "data/normalized",
    ]
    found: list[Path] = []
    for root in roots:
        if root.exists():
            found.extend(p for p in root.rglob("*") if p.is_file())
    # Only explicit runtime heads/receipts; runtime also contains large backups.
    for name in ("workbench_entry.json", "operations_config.json", "controlled_restart_status.json", "maintenance_last_receipt.json"):
        path = ROOT / "runtime" / name
        if path.is_file():
            found.append(path)
    return sorted(set(found))


def consumer_hits() -> list[tuple[str, str, str]]:
    patterns = ("duckdb.connect", "market_research.duckdb", "read_parquet(")
    hits: list[tuple[str, str, str]] = []
    for root_name in ("src", "scripts", "config"):
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".sql", ".yaml", ".yml", ".toml"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            matched = [pattern for pattern in patterns if pattern in text]
            if matched:
                status = "UNCLASSIFIED"
                rel = path.relative_to(ROOT).as_posix()
                if rel == "src/workbench_service/turnover_enrichment_service.py":
                    # The only DuckDB session here is an in-memory read_parquet
                    # used to calculate a request-time local fingerprint.  It
                    # does not open market_research.duckdb or persist rows.
                    status = "OFFLINE_DUCKDB_ALLOWED"
                elif rel == "config/workbench.yaml" or rel.startswith("src/workbench_service/") or rel.startswith("src/workbench_ops/") or rel.startswith("src/workbench_publish/") or rel in {"src/workbench_db/repository.py", "src/workbench_db/backend_provider.py"}:
                    status = "MIGRATE_TO_PG"
                elif rel.startswith("scripts/audit_") or rel.startswith("scripts/verify_"):
                    status = "RETAIN_UNTIL_AUDIT_CLOSE"
                elif rel.startswith("scripts/") or rel.startswith("src/"):
                    status = "OFFLINE_DUCKDB_ALLOWED"
                hits.append((rel, ",".join(matched), status))
    return sorted(hits)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to write catalog without --apply")
    dsn = args.dsn or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    discovered = datetime.now(timezone.utc)
    with psycopg.connect(dsn) as pg:
        with pg.cursor() as cur:
            cur.execute("create schema if not exists workbench_meta")
            cur.execute("""
                create table if not exists workbench_meta.artifact_catalog (
                    artifact_id text primary key,
                    category text not null,
                    managed_root_id text not null,
                    relative_path text not null,
                    sha256 text,
                    size_bytes bigint,
                    artifact_contract text,
                    availability text not null,
                    migration_class text not null,
                    migration_source_path text not null,
                    discovered_at timestamptz not null,
                    unique (managed_root_id, relative_path, sha256)
                )
            """)
            cur.execute("""
                create table if not exists workbench_meta.consumer_catalog (
                    consumer_id text primary key,
                    relative_path text not null,
                    matched_contract text not null,
                    disposition text not null,
                    evidence text not null,
                    reviewed_at timestamptz,
                    reviewer text
                )
            """)
            for path in files():
                rel = path.relative_to(ROOT).as_posix()
                cat, migration = category(path)
                digest = sha256(path)
                artifact_id = hashlib.sha256(f"workspace|{rel}|{digest}".encode()).hexdigest()
                cur.execute(
                    """
                    insert into workbench_meta.artifact_catalog
                    (artifact_id,category,managed_root_id,relative_path,sha256,size_bytes,artifact_contract,availability,migration_class,migration_source_path,discovered_at)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict (artifact_id) do update set sha256=excluded.sha256,size_bytes=excluded.size_bytes,availability=excluded.availability,discovered_at=excluded.discovered_at
                    """,
                    (artifact_id, cat, "PROJECT_ROOT", rel, digest, path.stat().st_size, None, "AVAILABLE", migration, str(path), discovered),
                )
            for rel, matched, disposition in consumer_hits():
                consumer_id = hashlib.sha256(rel.encode()).hexdigest()
                cur.execute(
                    """
                    insert into workbench_meta.consumer_catalog
                    (consumer_id,relative_path,matched_contract,disposition,evidence,reviewed_at,reviewer)
                    values (%s,%s,%s,%s,%s,%s,%s)
                    on conflict (consumer_id) do update set matched_contract=excluded.matched_contract,disposition=excluded.disposition,evidence=excluded.evidence
                    """,
                    (consumer_id, rel, matched, disposition, f"static scan: {matched}", None, None),
                )
            current_ids = {hashlib.sha256(rel.encode()).hexdigest() for rel, _matched, _disposition in consumer_hits()}
            cur.execute("select consumer_id from workbench_meta.consumer_catalog")
            stale_ids = [row[0] for row in cur.fetchall() if row[0] not in current_ids]
            if stale_ids:
                cur.execute("delete from workbench_meta.consumer_catalog where consumer_id = any(%s)", (stale_ids,))
        pg.commit()
        with pg.cursor() as cur:
            cur.execute("select count(*) from workbench_meta.artifact_catalog")
            artifact_count = cur.fetchone()[0]
            cur.execute("select count(*) from workbench_meta.consumer_catalog")
            consumer_count = cur.fetchone()[0]
            cur.execute("select disposition,count(*) from workbench_meta.consumer_catalog group by disposition order by disposition")
            dispositions = cur.fetchall()
        print(f"ARTIFACT_CATALOG_COMPLETE artifacts={artifact_count} consumers={consumer_count} dispositions={dispositions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
