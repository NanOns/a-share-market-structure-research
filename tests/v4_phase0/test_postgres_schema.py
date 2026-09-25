from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
import uuid

import pytest

psycopg=pytest.importorskip("psycopg")
from psycopg import sql
from scripts.apply_v4_phase0_schema import dsn


def connect():
    return psycopg.connect(dsn())


@contextmanager
def rollback_only(pg):
    pg.execute("BEGIN")
    try:
        yield
    finally:
        pg.rollback()


def test_fresh_v4_schema_has_required_relations_indexes_and_migrations():
    with connect() as pg:
        tables={r[0] for r in pg.execute("select table_name from information_schema.tables where table_schema='v4'").fetchall()}
        assert {"source_packages","source_revisions","security_lifecycle_facts","universe_snapshots","universe_members","model_namespaces","publications","publication_heads","publication_consumed_sources","publication_revision_events","namespace_migrations","event_observations","state_heads"} <= tables
        assert pg.execute("select count(*) from v4_meta.schema_migrations where version in ('V4_PHASE0_FOUNDATION_V1','V4_PHASE0_NAMESPACE_INTEGRITY_V1')").fetchone()[0]==2
        assert pg.execute("select count(*) from pg_indexes where schemaname='v4' and indexname in ('uq_source_revision_single_successor','ix_source_revisions_cutoff','ix_publication_consumed_source_revision')").fetchone()[0]==3


def test_reset_leaves_no_legacy_heads_or_v4_runtime_rows():
    with connect() as pg:
        assert pg.execute("select count(*) from information_schema.schemata where schema_name in ('legacy','workbench','workbench_meta')").fetchone()[0]==0
        tables=pg.execute("select tablename from pg_tables where schemaname='v4'").fetchall()
        assert all(pg.execute(f'select count(*) from v4."{name}"').fetchone()[0]==0 for (name,) in tables)
        assert pg.execute("select count(*) from v4.publication_heads").fetchone()[0]==0


def test_same_day_revision_namespace_and_late_correction_are_append_only():
    suffix=uuid.uuid4().hex
    d1=date(2026,9,24)
    with connect() as pg:
        with rollback_only(pg):
            prod=f"PROD-{suffix}"; shadow=f"SHADOW-{suffix}"
            pg.execute("insert into v4.model_namespaces(namespace_id,model_contract_id,execution_mode,namespace) values (%s,'M-V1','PRODUCTION','PRODUCTION_V4'),(%s,'M-V1','SHADOW','SHADOW_V4')",(prod,shadow))
            pg.execute("insert into v4.state_heads(namespace_id,state_head_id,logical_digest) values (%s,'prior-prod',%s)",(prod,"a"*64))
            pg.execute("insert into v4.publications(publication_id,trade_date,revision,status,model_namespace_id,core_revision,source_manifest_sha256,computation_identity_sha256,prior_session_state_head,accepted_at) values ('PUB-{0}',%s,1,'ACCEPTED',%s,1,%s,%s,'prior-prod',now())".format(suffix),(d1,prod,"b"*64,"c"*64))
            pub=f"PUB-{suffix}"
            pg.execute("insert into v4.publication_heads values (%s,%s,%s,1)",(d1,prod,pub))
            pg.execute("insert into v4.publications(publication_id,trade_date,revision,status,model_namespace_id,core_revision,source_manifest_sha256,computation_identity_sha256,prior_session_state_head,same_day_revision_parent,accepted_at) values (%s,%s,2,'ACCEPTED',%s,1,%s,%s,'prior-prod',%s,now())",(pub,d1,prod,"d"*64,"e"*64,pub))
            assert pg.execute("select revision from v4.publications where publication_id=%s order by revision",(pub,)).fetchall()==[(1,),(2,)]
            pg.execute("update v4.publication_heads set revision=2 where trade_date=%s and model_namespace_id=%s",(d1,prod))
            assert pg.execute("select revision from v4.publication_heads where trade_date=%s and model_namespace_id=%s",(d1,prod)).fetchone()==(2,)
            pg.execute("savepoint mutation_guard")
            with pytest.raises(psycopg.Error,match="V4_APPEND_ONLY_TABLE"):
                pg.execute("update v4.publications set status='RETRACTED' where publication_id=%s and revision=1",(pub,))
            pg.execute("rollback to savepoint mutation_guard")
            pg.execute("savepoint namespace_guard")
            with pytest.raises(psycopg.Error,match="V4_PRIOR_STATE_HEAD_NAMESPACE_MISMATCH"):
                pg.execute("insert into v4.publications(publication_id,trade_date,revision,status,model_namespace_id,core_revision,source_manifest_sha256,computation_identity_sha256,prior_session_state_head,accepted_at) values (%s,%s,1,'ACCEPTED',%s,1,%s,%s,'prior-prod',now())",(f"SH-{suffix}",d1,shadow,"f"*64,"1"*64))
            pg.execute("rollback to savepoint namespace_guard")
            pg.execute("savepoint head_guard")
            with pytest.raises(psycopg.Error,match="V4_PUBLICATION_HEAD_TARGET_INVALID"):
                pg.execute("insert into v4.publication_heads values (%s,%s,%s,99)",(d1,prod,pub))
            pg.execute("rollback to savepoint head_guard")


def test_source_revision_fork_is_rejected():
    suffix=uuid.uuid4().hex
    with connect() as pg:
        with rollback_only(pg):
            now=pg.execute("select now()").fetchone()[0]
            logical=f"fact-{suffix}"
            pg.execute("insert into v4.source_revisions(source_revision_id,logical_fact_id,revision_no,payload,digest,observed_at,ingested_at,system_available_at) values (%s,%s,1,'{}',%s,%s,%s,%s)",(f"root-{suffix}",logical,"a"*64,now,now,now))
            for n in (2,3):
                if n==3: pg.execute("savepoint fork_guard")
                if n==3:
                    with pytest.raises(psycopg.Error):
                        pg.execute("insert into v4.source_revisions(source_revision_id,logical_fact_id,revision_no,payload,digest,observed_at,ingested_at,system_available_at,supersedes_revision_id) values (%s,%s,%s,'{}',%s,%s,%s,%s,%s)",(f"child-{suffix}-{n}",logical,n,"b"*64,now,now,now,f"root-{suffix}"))
                    pg.execute("rollback to savepoint fork_guard")
                else:
                    pg.execute("insert into v4.source_revisions(source_revision_id,logical_fact_id,revision_no,payload,digest,observed_at,ingested_at,system_available_at,supersedes_revision_id) values (%s,%s,%s,'{}',%s,%s,%s,%s,%s)",(f"child-{suffix}-{n}",logical,n,"b"*64,now,now,now,f"root-{suffix}"))
            assert pg.execute("select count(*) from v4.source_revisions where logical_fact_id=%s",(logical,)).fetchone()[0]==2


def test_failed_schema_migration_rolls_back_all_ddl():
    probe=f"rollback_probe_{uuid.uuid4().hex}"
    with connect() as pg:
        with pytest.raises(psycopg.Error):
            with pg.transaction():
                pg.execute(sql.SQL("create table v4_meta.{} (id integer primary key)").format(sql.Identifier(probe)))
                pg.execute("CREATE TABLE v4_meta.__intentionally_invalid_ddl ( id this_is_not_a_type )")
        assert pg.execute("select to_regclass(%s)",(f"v4_meta.{probe}",)).fetchone()[0] is None
