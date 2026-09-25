from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
from scripts.apply_v4_phase0_schema import dsn

ROOT = Path(__file__).resolve().parents[2]


def connect():
    return psycopg.connect(dsn())


@contextmanager
def rollback_only(pg):
    pg.execute("BEGIN")
    try:
        yield
    finally:
        pg.rollback()


def add_namespace(pg, namespace_id, model_contract_id=None):
    pg.execute(
        "insert into v4.model_namespaces(namespace_id,model_contract_id,execution_mode,namespace) values (%s,%s,'SHADOW',%s)",
        (namespace_id, model_contract_id or f"MC-{namespace_id}", namespace_id),
    )


def add_calendar_session(pg, calendar_id, trade_date, session_no=None):
    pg.execute(
        "insert into v4.market_calendar_sessions(market_calendar_id,session_no,trade_date,calendar_digest) values (%s,%s,%s,%s) on conflict do nothing",
        (calendar_id, session_no or trade_date.toordinal(), trade_date, "e" * 64),
    )


def add_publication(pg, *, publication_id, namespace_id, trade_date, lineage_id, calendar_id=None, revision_no=1, core_revision=1, parent_id=None, prior_id=None, prior_digest=None, gap="INITIAL"):
    calendar_id = calendar_id or f"CAL-{namespace_id}"
    add_calendar_session(pg, calendar_id, trade_date)
    pg.execute(
        """insert into v4.publications(
             publication_id,publication_lineage_id,trade_date,market_calendar_id,revision_no,status,model_namespace_id,
             core_revision,source_manifest_sha256,computation_identity_sha256,same_day_revision_parent_id,
             prior_session_publication_id,prior_session_revision_digest,prior_session_gap_reason,accepted_at)
           values (%s,%s,%s,%s,%s,'ACCEPTED',%s,%s,%s,%s,%s,%s,%s,%s,now())""",
        (publication_id, lineage_id, trade_date, calendar_id, revision_no, namespace_id, core_revision,
         "a" * 64, (publication_id.encode().hex() * 64)[:64], parent_id, prior_id, prior_digest,
         None if prior_id else gap),
    )


def add_source_revision(pg, *, revision_id, logical_id, revision_no, now, parent_id=None, provider_available_at=None):
    pg.execute(
        """insert into v4.source_revisions(source_revision_id,logical_fact_id,revision_no,payload,digest,
             provider_available_at,observed_at,ingested_at,system_available_at,supersedes_revision_id)
           values (%s,%s,%s,'{}',%s,%s,%s,%s,%s,%s)""",
        (revision_id, logical_id, revision_no, "b" * 64, provider_available_at, now, now, now, parent_id),
    )


def assert_rejected(pg, operation, *, match=None):
    with pytest.raises(psycopg.Error, match=match):
        with pg.transaction():
            operation()


def test_fresh_v4_schema_has_revisionable_pit_and_publication_relations():
    with connect() as pg:
        tables = {r[0] for r in pg.execute("select table_name from information_schema.tables where table_schema='v4'").fetchall()}
        assert {"source_packages", "source_revisions", "security_lifecycle_facts", "security_membership_facts", "market_calendar_sessions", "universe_snapshots", "universe_members", "model_namespaces", "publications", "publication_heads", "publication_consumed_sources", "publication_revision_events", "namespace_migrations", "event_observations", "state_heads"} <= tables
        versions = pg.execute("select version from v4_meta.schema_migrations order by version").fetchall()
        assert {"V4_PHASE0_FOUNDATION_V1", "V4_PHASE0_NAMESPACE_INTEGRITY_V1", "V4_PHASE0_CONTRACT_ALIGNMENT_R2", "V4_PUBLICATION_HEAD_REVISION_IDENTITY_R2", "V4_MARKET_SESSION_PUBLICATION_CHAIN_R2", "V4_FACT_SOURCE_GUARD_TABLE_SPECIFIC_FIELDS_R2", "V4_STATE_AND_NAMESPACE_PUBLICATION_IDENTITY_R2"} <= {x[0] for x in versions}
        indexes = {r[0] for r in pg.execute("select indexname from pg_indexes where schemaname='v4'").fetchall()}
        assert {"uq_source_revision_single_successor", "ix_source_revisions_cutoff", "ix_publication_consumed_source_revision", "uq_publication_same_day_parent_single_successor", "ix_membership_effective"} <= indexes
        columns = {r[0] for r in pg.execute("select column_name from information_schema.columns where table_schema='v4' and table_name='publications'").fetchall()}
        assert {"publication_id", "publication_lineage_id", "revision_no", "core_revision", "same_day_revision_parent_id", "prior_session_publication_id", "prior_session_revision_digest", "prior_session_gap_reason", "market_calendar_id"} <= columns
        assert "revision" not in columns
        state_head_columns = {r[0] for r in pg.execute("select column_name from information_schema.columns where table_schema='v4' and table_name='state_heads'").fetchall()}
        assert "publication_revision" not in state_head_columns
        constraints = {r[0] for r in pg.execute("select conname from pg_constraint where connamespace='v4'::regnamespace").fetchall()}
        assert {"fk_state_head_publication_identity", "fk_namespace_migration_frozen_source_head"} <= constraints


def test_reset_leaves_no_legacy_heads_or_v4_runtime_rows():
    with connect() as pg:
        assert pg.execute("select count(*) from information_schema.schemata where schema_name in ('legacy','workbench','workbench_meta')").fetchone()[0] == 0
        tables = pg.execute("select tablename from pg_tables where schemaname='v4'").fetchall()
        assert all(pg.execute(f'select count(*) from v4."{name}"').fetchone()[0] == 0 for (name,) in tables)
        assert pg.execute("select count(*) from v4.publication_heads").fetchone()[0] == 0


def test_each_revision_has_unique_publication_id_and_same_day_parent_identity():
    suffix = uuid.uuid4().hex
    ns = f"NS-{suffix}"
    d = date(2026, 9, 24)
    with connect() as pg, rollback_only(pg):
        add_namespace(pg, ns)
        root = f"PUB-ROOT-{suffix}"
        child = f"PUB-CHILD-{suffix}"
        add_publication(pg, publication_id=root, namespace_id=ns, trade_date=d, lineage_id=f"LINE-{suffix}")
        add_publication(pg, publication_id=child, namespace_id=ns, trade_date=d, lineage_id=f"LINE-{suffix}", revision_no=2, core_revision=2, parent_id=root)
        rows = pg.execute("select publication_id,revision_no from v4.publications where publication_lineage_id=%s order by revision_no", (f"LINE-{suffix}",)).fetchall()
        assert rows == [(root, 1), (child, 2)]
        assert_rejected(pg, lambda: add_publication(pg, publication_id=root, namespace_id=ns, trade_date=d, lineage_id=f"LINE-{suffix}-OTHER"))


def test_same_day_parent_must_match_namespace_and_trade_date():
    suffix = uuid.uuid4().hex
    ns_a, ns_b = f"NSA-{suffix}", f"NSB-{suffix}"
    d = date(2026, 9, 24)
    with connect() as pg, rollback_only(pg):
        add_namespace(pg, ns_a)
        add_namespace(pg, ns_b)
        parent = f"P-{suffix}"
        add_publication(pg, publication_id=parent, namespace_id=ns_a, trade_date=d, lineage_id=f"L-{suffix}")
        assert_rejected(pg, lambda: add_publication(pg, publication_id=f"BAD-NS-{suffix}", namespace_id=ns_b, trade_date=d, lineage_id=f"L-{suffix}", revision_no=2, core_revision=2, parent_id=parent))
        assert_rejected(pg, lambda: add_publication(pg, publication_id=f"BAD-DATE-{suffix}", namespace_id=ns_a, trade_date=date(2026, 9, 25), lineage_id=f"L-{suffix}", revision_no=2, core_revision=2, parent_id=parent))
        assert_rejected(pg, lambda: add_publication(pg, publication_id=f"SELF-{suffix}", namespace_id=ns_a, trade_date=d, lineage_id=f"L-{suffix}", revision_no=2, core_revision=2, parent_id=f"SELF-{suffix}"))


def test_revision_lineage_no_fork_and_core_revision_unique_per_date_namespace():
    suffix = uuid.uuid4().hex
    ns = f"NS-{suffix}"
    d = date(2026, 9, 24)
    with connect() as pg, rollback_only(pg):
        add_namespace(pg, ns)
        parent = f"P-{suffix}"
        add_publication(pg, publication_id=parent, namespace_id=ns, trade_date=d, lineage_id=f"L-{suffix}")
        add_publication(pg, publication_id=f"C1-{suffix}", namespace_id=ns, trade_date=d, lineage_id=f"L-{suffix}", revision_no=2, core_revision=2, parent_id=parent)
        assert_rejected(pg, lambda: add_publication(pg, publication_id=f"C2-{suffix}", namespace_id=ns, trade_date=d, lineage_id=f"L-{suffix}", revision_no=2, core_revision=3, parent_id=parent))
        assert_rejected(pg, lambda: add_publication(pg, publication_id=f"CORE-DUP-{suffix}", namespace_id=ns, trade_date=d, lineage_id=f"OTHER-{suffix}", core_revision=1))


def test_prior_session_publication_namespace_and_digest_are_validated():
    suffix = uuid.uuid4().hex
    ns_a, ns_b = f"NSA-{suffix}", f"NSB-{suffix}"
    with connect() as pg, rollback_only(pg):
        add_namespace(pg, ns_a, "SHARED-MODEL")
        add_namespace(pg, ns_b, "SHARED-MODEL")
        prior = f"PRIOR-{suffix}"
        add_publication(pg, publication_id=prior, namespace_id=ns_a, trade_date=date(2026, 9, 23), lineage_id=f"LP-{suffix}")
        digest = (prior.encode().hex() * 64)[:64]
        assert_rejected(pg, lambda: add_publication(pg, publication_id=f"CROSS-NS-{suffix}", namespace_id=ns_b, calendar_id=f"CAL-{ns_a}", trade_date=date(2026, 9, 24), lineage_id=f"LC-{suffix}", prior_id=prior, prior_digest=digest), match="V4_PRIOR_SESSION_PUBLICATION_INVALID")
        assert_rejected(pg, lambda: add_publication(pg, publication_id=f"BAD-DIGEST-{suffix}", namespace_id=ns_a, trade_date=date(2026, 9, 24), lineage_id=f"LD-{suffix}", prior_id=prior, prior_digest="f" * 64), match="V4_PRIOR_SESSION_PUBLICATION_INVALID")
        current = f"CURRENT-{suffix}"
        add_publication(pg, publication_id=current, namespace_id=ns_a, trade_date=date(2026, 9, 24), lineage_id=f"LE-{suffix}", prior_id=prior, prior_digest=digest)
        pg.execute("insert into v4.publication_heads(trade_date,model_namespace_id,publication_id) values (%s,%s,%s)", (date(2026, 9, 24), ns_a, current))


def test_lifecycle_machine_contract_matches_schema():
    contract = json.loads((ROOT / "config/v4_security_lifecycle_fact_v1.json").read_text("utf-8"))
    with connect() as pg:
        columns = {r[0] for r in pg.execute("select column_name from information_schema.columns where table_schema='v4' and table_name='security_lifecycle_facts'").fetchall()}
    assert set(contract["required_fields"]) <= columns
    assert contract["status"] == "CONTRACT_FROZEN_IMPLEMENTED_IN_V4_SCHEMA"


def test_membership_machine_contract_matches_schema():
    contract = json.loads((ROOT / "config/v4_pit_membership_fact_v1.json").read_text("utf-8"))
    with connect() as pg:
        columns = {r[0] for r in pg.execute("select column_name from information_schema.columns where table_schema='v4' and table_name='security_membership_facts'").fetchall()}
    assert set(contract["required_fields"]) <= columns
    assert contract["status"] == "CONTRACT_FROZEN_IMPLEMENTED_IN_V4_SCHEMA"


def test_lifecycle_fact_revision_and_knowledge_timestamps_match_source_revision():
    suffix = uuid.uuid4().hex
    security_id = f"SH.6{suffix[:5]}"
    with connect() as pg, rollback_only(pg):
        now = pg.execute("select now()::timestamptz").fetchone()[0]
        provider_at = pg.execute("select now() - interval '1 second'").fetchone()[0]
        source_id = f"LIFE-SRC-{suffix}"
        add_source_revision(pg, revision_id=source_id, logical_id=f"LIFECYCLE-{security_id}", revision_no=1, now=now, provider_available_at=provider_at)
        pg.execute("""insert into v4.security_lifecycle_facts(security_id,security_type,board,listed_from,listed_to,
                    st_state,trade_status,effective_from,effective_to,provider_available_at,observed_at,ingested_at,
                    system_available_at,source_revision_id,supersedes_revision_id,source_identity,quality)
                    values (%s,'A_STOCK','MAIN',%s,null,'NORMAL','TRADING',%s,null,%s,%s,%s,%s,%s,null,'master-v1','OBSERVED')""",
                   (security_id, date(2020, 1, 1), date(2020, 1, 1), provider_at, now, now, now, source_id))
        with pytest.raises(psycopg.Error):
            with pg.transaction():
                pg.execute("""insert into v4.security_lifecycle_facts(security_id,security_type,effective_from,observed_at,
                            ingested_at,system_available_at,source_revision_id,provider_available_at,supersedes_revision_id,
                            source_identity,quality) values (%s,'A_STOCK',%s,%s,%s,%s,%s,%s,null,'bad','OBSERVED')""",
                           (security_id, date(2020, 1, 1), now, now, now, source_id, now))


def test_pit_fact_revision_chain_and_late_correction_are_append_only():
    suffix = uuid.uuid4().hex
    membership_id = f"MEM-{suffix}"
    security_id = f"SH.600000"
    effective = date(2026, 1, 1)
    with connect() as pg, rollback_only(pg):
        now = pg.execute("select now()::timestamptz").fetchone()[0]
        add_source_revision(pg, revision_id=f"SRC1-{suffix}", logical_id=membership_id, revision_no=1, now=now)
        pg.execute("""insert into v4.security_membership_facts(membership_id,security_id,effective_from,effective_to,
                    provider_available_at,observed_at,ingested_at,system_available_at,source_revision_id,
                    supersedes_revision_id,source_identity,quality)
                    values (%s,%s,%s,null,null,%s,%s,%s,%s,null,'test-source','OBSERVED')""",
                   (membership_id, security_id, effective, now, now, now, f"SRC1-{suffix}"))
        later = pg.execute("select now() + interval '1 second'").fetchone()[0]
        add_source_revision(pg, revision_id=f"SRC2-{suffix}", logical_id=membership_id, revision_no=2, now=later, parent_id=f"SRC1-{suffix}")
        pg.execute("""insert into v4.security_membership_facts(membership_id,security_id,effective_from,effective_to,
                    provider_available_at,observed_at,ingested_at,system_available_at,source_revision_id,
                    supersedes_revision_id,source_identity,quality)
                    values (%s,%s,%s,null,null,%s,%s,%s,%s,%s,'test-source','CORRECTED')""",
                   (membership_id, security_id, effective, later, later, later, f"SRC2-{suffix}", f"SRC1-{suffix}"))
        assert pg.execute("select count(*) from v4.security_membership_facts where membership_id=%s", (membership_id,)).fetchone()[0] == 2
        pg.execute("savepoint append_only_guard")
        with pytest.raises(psycopg.Error, match="V4_APPEND_ONLY_TABLE"):
            pg.execute("delete from v4.security_membership_facts where membership_id=%s", (membership_id,))
        pg.execute("rollback to savepoint append_only_guard")


def test_current_universe_member_is_not_historical_membership_proof():
    contract = json.loads((ROOT / "config/v4_pit_membership_fact_v1.json").read_text("utf-8"))
    assert contract["current_membership_replay"] == "DIAGNOSTIC_ONLY"
    assert contract["selection_rule"].find("system_available_at") >= 0
    with connect() as pg, rollback_only(pg):
        suffix = uuid.uuid4().hex
        now = pg.execute("select now()").fetchone()[0]
        snapshot = f"S-{suffix}"
        pg.execute("insert into v4.universe_snapshots(universe_snapshot_id,contract_id,contract_version,trade_date,observed_at,ingested_at,system_available_at,universe_basis,logical_digest,member_count) values (%s,'U','1.0.0',%s,%s,%s,%s,'DIAGNOSTIC_NON_PIT',%s,1)", (snapshot, date(2026, 9, 24), now, now, now, "d" * 64))
        pg.execute("insert into v4.universe_members(universe_snapshot_id,security_id,security_type,quality) values (%s,'SH.600000','A_STOCK','CURRENT_ONLY')", (snapshot,))
        assert pg.execute("select count(*) from v4.security_membership_facts where security_id='SH.600000'").fetchone()[0] == 0


def test_source_revision_fork_is_rejected():
    suffix = uuid.uuid4().hex
    with connect() as pg, rollback_only(pg):
        now = pg.execute("select now()").fetchone()[0]
        logical = f"fact-{suffix}"
        add_source_revision(pg, revision_id=f"root-{suffix}", logical_id=logical, revision_no=1, now=now)
        add_source_revision(pg, revision_id=f"child-{suffix}-2", logical_id=logical, revision_no=2, now=now, parent_id=f"root-{suffix}")
        assert_rejected(pg, lambda: add_source_revision(pg, revision_id=f"child-{suffix}-other", logical_id=logical, revision_no=2, now=now, parent_id=f"root-{suffix}"))


def test_failed_schema_migration_rolls_back_all_ddl():
    probe = f"rollback_probe_{uuid.uuid4().hex}"
    with connect() as pg:
        with pytest.raises(psycopg.Error):
            with pg.transaction():
                pg.execute("create table v4_meta.\"" + probe + "\" (id integer primary key)")
                pg.execute("CREATE TABLE v4_meta.__intentionally_invalid_ddl ( id this_is_not_a_type )")
        assert pg.execute("select to_regclass(%s)", (f"v4_meta.{probe}",)).fetchone()[0] is None
