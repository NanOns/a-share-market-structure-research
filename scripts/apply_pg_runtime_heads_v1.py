"""Install versioned PostgreSQL runtime heads for publication projections."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def dsn() -> str:
    value = os.environ.get("WORKBENCH_PG_DSN")
    local = ROOT / "config/.env"
    if not value and local.is_file():
        for line in local.read_text("utf-8").splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip() == "WORKBENCH_PG_DSN":
                value = val.strip().strip("\"").strip("'")
                break
    if not value:
        raise RuntimeError("WORKBENCH_PG_DSN_REQUIRED")
    return value


DDL = """
create table if not exists workbench.research_bundle_heads (
    trade_date date primary key,
    publication_id text not null references workbench.publications(publication_id),
    bundle_digest text not null unique references workbench.research_runs_v3_3(bundle_digest),
    research_run_id text not null,
    snapshot_id text not null,
    activated_at timestamptz not null default now()
);
create table if not exists workbench.analysis_snapshot_heads (
    trade_date date not null,
    domain text not null,
    publication_id text not null references workbench.publications(publication_id),
    snapshot_id text not null references workbench.analysis_snapshots(snapshot_id),
    activated_at timestamptz not null default now(),
    primary key (trade_date, domain),
    foreign key (publication_id, domain)
      references workbench.publication_analysis_snapshots(publication_id, domain)
);
""".strip()


def main() -> int:
    checksum = hashlib.sha256(DDL.encode("utf-8")).hexdigest()
    with psycopg.connect(dsn()) as pg:
        with pg.transaction():
            pg.execute("lock table workbench.publication_heads, workbench.publication_analysis_snapshots in share row exclusive mode")
            pg.execute(DDL.split(";", 1)[0])
            pg.execute(DDL.split(";", 1)[1])
            pg.execute(
                """insert into workbench.research_bundle_heads
                   (trade_date,publication_id,bundle_digest,research_run_id,snapshot_id,activated_at)
                   select distinct on (h.trade_date) h.trade_date,h.publication_id,r.bundle_digest,
                          r.research_run_id,r.snapshot_id,now()
                     from workbench.publication_heads h
                     join workbench.research_runs_v3_3 r
                       on r.trade_date=h.trade_date and r.publication_id=h.publication_id and r.status='COMPLETE'
                    order by h.trade_date,r.registered_at desc
                   on conflict (trade_date) do update set publication_id=excluded.publication_id,
                     bundle_digest=excluded.bundle_digest,research_run_id=excluded.research_run_id,
                     snapshot_id=excluded.snapshot_id,activated_at=excluded.activated_at"""
            )
            pg.execute(
                """insert into workbench.analysis_snapshot_heads
                   (trade_date,domain,publication_id,snapshot_id,activated_at)
                   select distinct on (p.trade_date,a.domain) p.trade_date,a.domain,a.publication_id,a.snapshot_id,now()
                     from workbench.publication_analysis_snapshots a
                     join workbench.publication_heads h using(publication_id)
                     join workbench.publications p using(publication_id)
                    order by p.trade_date,a.domain,a.bound_at desc
                   on conflict (trade_date,domain) do update set publication_id=excluded.publication_id,
                     snapshot_id=excluded.snapshot_id,activated_at=excluded.activated_at"""
            )
            pg.execute(
                "insert into workbench_meta.schema_migrations(version,checksum,applied_at,status) values (%s,%s,now(),'COMPLETE') "
                "on conflict(version) do update set checksum=excluded.checksum,applied_at=excluded.applied_at,status='COMPLETE'",
                ("PG_RUNTIME_HEADS_V1", checksum),
            )
            research = int(pg.execute("select count(*) from workbench.research_bundle_heads").fetchone()[0])
            snapshots = int(pg.execute("select count(*) from workbench.analysis_snapshot_heads").fetchone()[0])
            latest = pg.execute("select trade_date,publication_id,bundle_digest from workbench.research_bundle_heads order by trade_date desc limit 1").fetchone()
            if not latest or research < 1 or snapshots < 1:
                raise RuntimeError("PG_RUNTIME_HEADS_BACKFILL_FAILED")
    print({"migration": "PG_RUNTIME_HEADS_V1", "checksum": checksum, "research_bundle_heads": research, "analysis_snapshot_heads": snapshots, "latest": tuple(str(v) for v in latest)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
