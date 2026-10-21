"""Publish an immutable Batch07 D0 development candidate from frozen Owners."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def load_repository_dsn(repository_root):
    """Load existing secure PG settings into process memory without logging them."""
    for line in (repository_root/'config/.env').read_text(encoding='utf-8').splitlines():
        value=line.strip()
        if not value or value.startswith('#') or '=' not in value:
            continue
        key, raw=value.split('=',1)
        if key.strip() in ('WORKBENCH_PG_DSN','V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN'):
            os.environ.setdefault(key.strip(),raw.strip().strip('"').strip("'"))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-root',required=True)
    parser.add_argument('--candidate-json',required=True)
    parser.add_argument('--trade-date',required=True)
    parser.add_argument('--candidate-token',required=True)
    args=parser.parse_args()
    repository_root=Path(__file__).resolve().parents[1]
    candidate_root=Path(args.candidate_root).resolve()
    candidate_path=Path(args.candidate_json).resolve()
    allowed=Path(r'G:\codex_tmp').resolve()
    if not candidate_root.is_relative_to(allowed) or not candidate_path.is_relative_to(candidate_root):
        raise SystemExit('D0_BATCH07_CANDIDATE_MUST_BE_UNDER_G_CODEX_TMP')
    load_repository_dsn(repository_root)
    sys.path[:0]=[str(repository_root/'src'),str(repository_root)]
    import psycopg
    from workbench_db.v4_native import configured_dsn
    from workbench_analysis.d0_source_seal_r2 import publish_candidate
    migrations=[(repository_root/'src/workbench_db/migrations/v4_postgres'/name).read_text(encoding='utf-8')
        for name in ('027_d0_source_seal_batch07_r1.sql','028_d0_dev_asof_closure_r1.sql')]
    # The migration is scoped to the D0 candidate schema and exact upstream
    # reader tables. The data write is a single append-only candidate publish.
    with psycopg.connect(configured_dsn(),connect_timeout=5) as pg:
        pg.execute("SET LOCAL statement_timeout='60s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute('SET TRANSACTION READ WRITE')
        for migration in migrations:pg.execute(migration)
    candidate=json.loads(candidate_path.read_bytes())
    result=publish_candidate(repository_root=repository_root,candidate_root=candidate_root,
        candidate=candidate,trade_date=args.trade_date,candidate_token=args.candidate_token)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,default=str))


if __name__=='__main__':
    main()
