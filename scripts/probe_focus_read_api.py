"""Rollback-only FOCUS-05 API mapping probe using PostgreSQL temp tables."""
from __future__ import annotations

from datetime import date

from apply_focus_pg_schema_v1 import _dsn
from psycopg.types.json import Jsonb

from focus_tracker.contracts import SOURCE_AUTHORITY_CONTRACT, digest
from focus_tracker.member_strength import CONTRACT_ID as MEMBER_STRENGTH_CONTRACT, SOURCE_MEMBER_CONTRACT
from focus_tracker.read_api import FocusTrackerReadAPI
from focus_tracker.previous_reader import read_predecessor
from workbench_db.postgres_repository import PostgresRepository


RUN_ID = "focus-read-api-probe-run"
CURRENT_EPISODE = "focus-read-api-current-episode"
EXITED_EPISODE = "focus-read-api-exited-episode"
SECURITY_ID = "SH.600000"
TRADE_DATE = date(2026, 9, 22)

DDL = (
    "create temp table focus_runs (focus_run_id text,trade_date date,revision int,publication_id text,"
    "source_authority_contract_id text,source_family_set jsonb,family_capabilities jsonb,"
    "state_contract_id text,parameter_set_id text,evaluation_basis text,core_publication_status text,"
    "outcome_settlement_status text,activated_at_utc timestamptz)",
    "create temp table focus_trade_date_heads (trade_date date,source_authority_contract_id text,"
    "accepted_focus_run_id text,lineage_state text)",
    "create temp table focus_daily_items (focus_run_id text,source_family text,entity_type text,"
    "entity_id text,selection_contract_family text,source_item_key text,source_item_digest text,"
    "source_contract_id text,source_membership_state text,source_focus_class text,source_rank int,"
    "source_quality text,source_facts jsonb)",
    "create temp table stock_daily (publication_id text,security_id text,security_name text)",
    "create temp table focus_episodes (episode_id text,source_family text,entity_type text,entity_id text,"
    "selection_contract_family text,first_trade_date date,first_focus_run_id text,parent_episode_id text)",
    "create temp table focus_episode_observations (episode_id text,focus_run_id text,trade_date date,"
    "source_revision int,evaluation_mode text,state_contract_id text,source_membership_state text,"
    "membership_phase text,validity_state text,followup_state text,current_path_state text,"
    "lifetime_path_tags jsonb,continuity_quality text,comparison_gap_sessions int,"
    "entry_primary_sector_id text,current_primary_sector_id text,first_supported_anchor_id text,"
    "close_price numeric,return_since_first numeric,drawdown_from_peak numeric,"
    "adjustment_source_hash text,quality_status text,fact_digest text,facts jsonb)",
    "create temp table focus_episode_transitions (episode_id text,focus_run_id text,source_revision int,"
    "transition_trade_date date,effective_trade_date date,confirmation_trade_date date,"
    "transition_type text,from_membership text,to_membership text,reason_codes jsonb)",
    "create temp table focus_episode_anchors (anchor_id text,episode_id text,anchor_type text,trade_date date,"
    "focus_run_id text,source_revision int,reference_price numeric,price_basis text,quality_status text)",
    "create temp table focus_episode_outcomes (anchor_id text,horizon int,target_revision int,"
    "target_trade_date date,status text,evaluation_basis text,forward_return numeric,mfe numeric,mae numeric,"
    "mdd numeric,input_digest text,reason_codes jsonb,evidence jsonb,observed_at_utc timestamptz)",
    "create temp table focus_outcome_heads (anchor_id text,horizon int,accepted_target_revision int,"
    "activated_at_utc timestamptz)",
    "create temp table focus_stock_sector_links (focus_run_id text,security_id text,sector_id text,"
    "relation_type text,support_status text,loo_status text,is_primary boolean,source_fact_digest text,evidence jsonb)",
    "create temp table focus_episode_baskets (episode_id text,focus_run_id text,publication_id text,member_ids jsonb,basket_digest text)",
    "create temp table analysis_snapshot_heads (snapshot_id text,trade_date date,publication_id text,domain text)",
    "create temp table analysis_snapshots (snapshot_id text,status text,cutoff_date date)",
    "create temp table analysis_snapshot_entries (snapshot_id text,domain text,trade_date date,slice_id text)",
    "create temp table analysis_slice_result_bindings (slice_id text,result_object_id text)",
    "create temp table analysis_result_objects (result_object_id text,domain text,semantic_contract text,value_hash text)",
    "create temp table member_state_result_rows (result_object_id text,trade_date date,sector_id text,security_id text,member_present bool,strong_state bool,contract_id text)",
    "create temp table relation_publication_bindings (publication_id text,source_scope text,attribute_version_id text)",
    "create temp table sector_attribute_revisions (source_scope text,attribute_revision int,attribute_set_hash text)",
    "create temp table sector_attribute_revision_bindings (source_scope text,sector_id text,from_attribute_revision int,to_attribute_revision int,attribute_version_id text)",
    "create temp table sector_attribute_versions (source_scope text,sector_id text,attribute_version_id text,name text,type text)",
    "create temp table focus_statistics_batches (statistics_batch_id text primary key,focus_run_id text,"
    "statistics_contract_id text,as_of_trade_date date,input_digest char(64),group_count int,"
    "outcome_count int,created_at_utc timestamptz)",
    "create temp table focus_statistics_heads (focus_run_id text primary key,statistics_batch_id text)",
    "create temp table focus_statistics_rows (statistics_batch_id text primary key,source_family text,"
    "entity_type text,selection_contract_family text,source_model_contract_id text,state_contract_id text,"
    "anchor_type text,horizon int,evaluation_basis text,price_basis text,sample_count int,"
    "signal_date_count int,incomplete_count int,gate_status text,p25_return numeric,median_return numeric,"
    "p75_return numeric,max_mfe numeric,worst_mdd numeric)",
)


class _BorrowedRepository:
    def __init__(self, connection, **_kwargs):
        self.connection = _ProbeConnection(connection)
        self.schema = "pg_temp"

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None


class _ProbeConnection:
    def __init__(self, connection):
        self._connection = connection
        self.query_count = 0

    def cursor(self):
        return _ProbeCursor(self._connection.cursor(), self)

    def rollback(self):
        return self._connection.rollback()


class _ProbeCursor:
    def __init__(self, cursor, owner):
        self._cursor = cursor
        self._owner = owner

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self._cursor.close()

    def execute(self, statement, params=None):
        if str(statement).strip().upper() == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY":
            # The probe transaction contains temp fixture inserts. All API
            # statements remain reads; the endpoint rollback removes fixtures.
            return None
        self._owner.query_count += 1
        return self._cursor.execute(statement, params)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


def _seed(connection, *, add_head: bool = True, replay_required: bool = False,
          exited_followup_state: str = "POST_EXIT") -> None:
    with connection.cursor() as cur:
        cur.execute(
            "insert into pg_temp.focus_runs values (%s,%s,1,%s,%s,%s,%s,%s,%s,%s,'ACTIVATED','PENDING',now())",
            (RUN_ID, TRADE_DATE, "probe-publication", SOURCE_AUTHORITY_CONTRACT,
             Jsonb(["V3_SHORTLIST_STOCK"]), Jsonb({"V3_SHORTLIST_STOCK": {"status": "COMPLETE"}}),
             "FOCUS_STATE_CONTRACT_V1", "probe-parameters", "HISTORICAL_RECONSTRUCTED"))
        if add_head:
            cur.execute("insert into pg_temp.focus_trade_date_heads values (%s,%s,%s,'VALID')",
                        (TRADE_DATE, SOURCE_AUTHORITY_CONTRACT, RUN_ID))
        if replay_required:
            cur.execute("insert into pg_temp.focus_trade_date_heads values (%s,%s,%s,'REPLAY_REQUIRED')",
                        (date(2026, 9, 23), SOURCE_AUTHORITY_CONTRACT, "probe-replay-run"))
        cur.execute(
            "insert into pg_temp.focus_daily_items values (%s,'V3_SHORTLIST_STOCK','STOCK',%s,"
            "'V3_SHORTLIST_FAMILY','source-key','a' || repeat('b',63),'V3_SOURCE_CONTRACT_V1',"
            "'CURRENT','FOCUS',1,'COMPLETE',%s)",
            (RUN_ID, SECURITY_ID, Jsonb({"scenario": "RECOVERY_TURN", "explain": ["probe"],
                                        "waiting_for": ["MA5 reclaim"], "invalid_if": "close < signal low"})))
        cur.execute("insert into pg_temp.stock_daily values ('probe-publication',%s,'测试个股')", (SECURITY_ID,))
        cur.execute(
            "insert into pg_temp.focus_episodes values "
            "(%s,'V3_SHORTLIST_STOCK','STOCK',%s,'V3_SHORTLIST_FAMILY',%s,%s,null),"
            "(%s,'V3_SHORTLIST_STOCK','STOCK',%s,'V3_SHORTLIST_FAMILY',%s,%s,null),"
            "('focus-read-api-sector-episode','V3_SECTOR_TRACK','SECTOR','IND:801010',"
            "'V3_SECTOR_FAMILY',%s,%s,null)",
            (CURRENT_EPISODE, SECURITY_ID, TRADE_DATE, RUN_ID,
             EXITED_EPISODE, SECURITY_ID, date(2026, 9, 18), RUN_ID, TRADE_DATE, RUN_ID))
        common = (RUN_ID, 1, "AS_RECORDED", "FOCUS_STATE_CONTRACT_V1", "VALID",
                  "DATA_AVAILABLE", "a" * 64)
        cur.execute(
            "insert into pg_temp.focus_episode_observations values "
            "(%s,%s,%s,1,%s,%s,'CURRENT','CURRENT','VALID','ACTIVE_FOCUS','TREND_ACCELERATING',"
            "'[]'::jsonb,'COMPLETE',0,'IND:801010','IND:801010',null,12.5,0.04,-0.01,'" + "b" * 64 + "',%s,'" + "c" * 64 + "',%s),"
            "(%s,%s,%s,1,%s,%s,'NONE','EXITED','VALID',%s,'EXITED_FOLLOW_UP',"
            "'[]'::jsonb,'COMPLETE',0,null,'IND:801010',null,11.0,0.02,-0.03,'" + "b" * 64 + "',%s,'" + "d" * 64 + "',%s)",
            (CURRENT_EPISODE, RUN_ID, TRADE_DATE, common[2], common[3], "READY",
             Jsonb({"state": "current", "validity_capability": {"status": "APPLICABLE"}}), EXITED_EPISODE, RUN_ID, TRADE_DATE,
             common[2], common[3], exited_followup_state, "COMPLETE", Jsonb({"state": "exited"})))
        cur.execute(
            "insert into pg_temp.focus_episode_transitions values "
            "(%s,%s,1,%s,%s,%s,'FIRST_FOCUS','NONE','CURRENT','[]'::jsonb),"
            "(%s,%s,1,%s,%s,%s,'EXIT_EFFECTIVE','CURRENT','NONE','[\"SOURCE_DROPPED\"]'::jsonb)",
            (CURRENT_EPISODE, RUN_ID, TRADE_DATE, TRADE_DATE, TRADE_DATE,
             EXITED_EPISODE, RUN_ID, TRADE_DATE, TRADE_DATE, TRADE_DATE))
        cur.execute(
            "insert into pg_temp.focus_episode_anchors values "
            "('probe-first-anchor',%s,'FIRST_FOCUS',%s,%s,1,10,'LOCAL_ADJUSTED','COMPLETE')",
            (CURRENT_EPISODE, date(2026, 9, 18), RUN_ID))
        cur.execute(
            "insert into pg_temp.focus_episode_outcomes values "
            "('probe-first-anchor',1,1,%s,'OBSERVED','HISTORICAL_RECONSTRUCTED',0.05,0.07,-0.02,-0.03,"
            "'" + "e" * 64 + "','[]'::jsonb,%s,now())",
            (TRADE_DATE, Jsonb({"path": "verified"})))
        cur.execute("insert into pg_temp.focus_outcome_heads values ('probe-first-anchor',1,1,now())")
        cur.execute("insert into pg_temp.focus_episode_outcomes values "
                    "('probe-first-anchor',3,1,%s,'OBSERVED','HISTORICAL_RECONSTRUCTED',0.09,0.12,-0.03,-0.05,"
                    "'" + "9" * 64 + "','[]'::jsonb,%s,now())", (date(2026, 9, 24), Jsonb({"path": "future"})))
        cur.execute("insert into pg_temp.focus_outcome_heads values ('probe-first-anchor',3,1,now())")
        cur.execute(
            "insert into pg_temp.focus_stock_sector_links values (%s,%s,'IND:801010','PRIMARY','SUPPORTED',"
            "'COMPLETE',true,'" + "f" * 64 + "',%s)",
            (RUN_ID, SECURITY_ID, Jsonb({"source": "probe"})))
        cur.execute("insert into pg_temp.relation_publication_bindings values "
                    "('probe-publication','probe-scope','attrset-111111111111111111111111')")
        cur.execute("insert into pg_temp.sector_attribute_revisions values "
                    "('probe-scope',1,'111111111111111111111111" + "1" * 40 + "')")
        cur.execute("insert into pg_temp.sector_attribute_revision_bindings values "
                    "('probe-scope','IND:801010',1,null,'probe-sector-attribute')")
        cur.execute("insert into pg_temp.sector_attribute_versions values "
                    "('probe-scope','IND:801010','probe-sector-attribute','测试行业板块','INDUSTRY')")
        member_ids = [SECURITY_ID, "SZ.000001"]
        basket_digest = "b" * 64
        cur.execute("insert into pg_temp.focus_episode_baskets values "
                    "('focus-read-api-sector-episode',%s,'probe-publication',%s,%s)",
                    (RUN_ID, Jsonb(member_ids), basket_digest))
        cur.execute("insert into pg_temp.analysis_snapshot_heads values ('probe-strength-snapshot',%s,'probe-publication','LOCAL_RECONSTRUCTED')", (TRADE_DATE,))
        cur.execute("insert into pg_temp.analysis_snapshots values ('probe-strength-snapshot','SUCCESS',%s)", (TRADE_DATE,))
        cur.execute("insert into pg_temp.analysis_snapshot_entries values ('probe-strength-snapshot','member_state',%s,'probe-strength-slice')", (TRADE_DATE,))
        cur.execute("insert into pg_temp.analysis_slice_result_bindings values ('probe-strength-slice','probe-strength-result')")
        cur.execute("insert into pg_temp.analysis_result_objects values ('probe-strength-result','member_state','MEMBER_STATE_RESULT_V3','c' || repeat('d',63))")
        cur.execute("insert into pg_temp.member_state_result_rows values ('probe-strength-result',%s,'IND:801010',%s,true,true,'SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC')", (TRADE_DATE, SECURITY_ID))
        cur.execute("insert into pg_temp.stock_daily values ('probe-publication','SZ.000001','第二只个股')")
        cur.execute("insert into pg_temp.member_state_result_rows values ('probe-strength-result',%s,'IND:801010','SZ.000001',true,false,'SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC')", (TRADE_DATE,))
        strength_evidence = {"contract": MEMBER_STRENGTH_CONTRACT, "trade_date": TRADE_DATE,
                             "publication_id": "probe-publication", "snapshot_id": "probe-strength-snapshot",
                             "slice_id": "probe-strength-slice", "result_object_id": "probe-strength-result",
                             "result_value_hash": "c" + "d" * 63,
                             "result_semantic_contract": "MEMBER_STATE_RESULT_V3",
                             "member_contract": SOURCE_MEMBER_CONTRACT, "sector_id": "IND:801010",
                             "basket_digest": basket_digest,
                             "member_states": [(SECURITY_ID, True), ("SZ.000001", False)]}
        cur.execute("insert into pg_temp.focus_episode_observations values "
                    "('focus-read-api-sector-episode',%s,%s,1,'AS_RECORDED','FOCUS_STATE_CONTRACT_V1',"
                    "'CURRENT','RETAINED','VALID','FOLLOW_UP_COMPLETED','TREND_CONTINUE','[]'::jsonb,'COMPLETE',0,"
                    "null,null,null,0,0,0,'" + "a" * 64 + "','COMPLETE','" + "e" * 64 + "',%s)",
                    (RUN_ID, TRADE_DATE, Jsonb({"predicate_facts": {"strength_fact_digest": digest(strength_evidence)}})))
        cur.execute("insert into pg_temp.focus_statistics_batches values "
                    "('probe-statistics-batch',%s,'FOCUS_STATISTICS_MATERIALIZATION_V1',%s,%s,1,30,now()) "
                    "on conflict do nothing", (RUN_ID, TRADE_DATE, "1" * 64))
        cur.execute("insert into pg_temp.focus_statistics_heads values (%s,'probe-statistics-batch') "
                    "on conflict do nothing", (RUN_ID,))
        cur.execute("insert into pg_temp.focus_statistics_rows values "
                    "('probe-statistics-batch','V3_SHORTLIST_STOCK','STOCK','V3_SHORTLIST_FAMILY',"
                    "'V3_SOURCE_CONTRACT_V1','FOCUS_STATE_CONTRACT_V1','FIRST_FOCUS',5,"
                    "'HISTORICAL_RECONSTRUCTED','LOCAL_ADJUSTED',30,5,0,'READY',0.01,0.04,0.08,0.2,-0.1) "
                    "on conflict do nothing")


def run_probe() -> dict[str, object]:
    with PostgresRepository(dsn=_dsn()) as repository:
        connection = repository.connection
        assert connection is not None
        with connection.cursor() as cur:
            for statement in DDL:
                cur.execute(statement)
        connection.commit()  # only temporary objects; removed when this session closes
        borrowed_repository = _BorrowedRepository(connection)
        api = FocusTrackerReadAPI(dsn=_dsn(), schema="pg_temp", repository_factory=
                                  lambda **kwargs: borrowed_repository)

        def request(path: str, params: dict[str, str] | None = None,
                    *, exited_followup_state: str = "POST_EXIT"):
            _seed(connection, exited_followup_state=exited_followup_state)
            status, body = api.handle(path, params or {})
            assert status == 200, (status, body)
            return body

        summary = request("/api/v3/focus-tracker/summary")
        assert summary["focus_run_id"] == RUN_ID and summary["total_items"] == 1
        items = request("/api/v3/focus-tracker/items")
        assert items["total"] == 2
        first_item_page = request("/api/v3/focus-tracker/items", {"page": "1", "page_size": "1"})
        assert first_item_page["returned_count"] == 1 and first_item_page["has_more"] is True
        facets = request("/api/v3/focus-tracker/facets")
        assert facets["facets_contract"] == "FOCUS_ITEMS_FACETS_V1"
        assert set(facets["paths"]) == {"TREND_ACCELERATING", "EXITED_FOLLOW_UP"}
        assert set(facets["memberships"]) == {"CURRENT", "NONE"}
        assert facets["source_qualities"] == ["COMPLETE"]
        assert set(facets["observation_qualities"]) == {"COMPLETE", "READY"}
        assert "IND:801010" in facets["sector_ids"]
        assert next(item for item in items["items"] if not item["is_followup"])["security_name"] == "测试个股"
        assert {item["is_followup"] for item in items["items"]} == {False, True}
        assert len({item["episode_id"] for item in items["items"]}) == 2
        current_item = next(item for item in items["items"] if not item["is_followup"])
        exited_item = next(item for item in items["items"] if item["is_followup"])
        assert current_item["source_quality"] == "COMPLETE"
        assert current_item["observation_quality"] == "READY"
        assert current_item["validity_capability"] == "APPLICABLE"
        assert exited_item["source_quality"] == "COMPLETE"
        assert exited_item["observation_quality"] == "COMPLETE"
        source_filtered = request("/api/v3/focus-tracker/items", {"source_quality": "COMPLETE"})
        observation_filtered = request("/api/v3/focus-tracker/items", {"observation_quality": "COMPLETE"})
        assert source_filtered["total"] == 2
        assert observation_filtered["total"] == 1 and observation_filtered["items"][0]["is_followup"]
        assert current_item["first_trade_date"] == TRADE_DATE.isoformat()
        assert current_item["observed_session_count"] == 1
        assert current_item["return_since_first"] == 0.04
        assert current_item["drawdown_from_peak"] == -0.01
        assert current_item["entry_primary_sector_id"] == "IND:801010"
        assert current_item["source_facts"]["waiting_for"] == ["MA5 reclaim"]
        assert current_item["source_facts"]["invalid_if"] == "close < signal low"
        assert exited_item["first_trade_date"] == date(2026, 9, 18).isoformat()
        assert exited_item["followup_state"] == "POST_EXIT"
        pending = request("/api/v3/focus-tracker/items", exited_followup_state="PENDING_SETTLEMENT")
        assert pending["total"] == 2
        assert next(item for item in pending["items"] if item["is_followup"])["followup_state"] == "PENDING_SETTLEMENT"
        completed = request("/api/v3/focus-tracker/items", exited_followup_state="FOLLOW_UP_COMPLETED")
        assert completed["total"] == 1
        exited = request("/api/v3/focus-tracker/items", {"membership": "NONE"})
        assert exited["total"] == 1 and exited["items"][0]["is_followup"] is True
        sector = request("/api/v3/focus-tracker/items", {"sector_id": "IND:801010"})
        assert sector["total"] == 2
        catalog = request("/api/v3/focus-tracker/sectors/catalog")
        assert catalog["items"][0]["name"] == "测试行业板块"
        members = request("/api/v3/focus-tracker/sectors/IND%3A801010/members")
        assert members["total"] == 2 and members["items"][0]["security_name"] == "测试个股"
        assert members["items"][0]["strong_state"] is True
        assert members["items"][0]["episode_id"] == CURRENT_EPISODE
        assert members["has_more"] is False
        member_page = request("/api/v3/focus-tracker/sectors/IND%3A801010/members",
                              {"page": "1", "page_size": "1"})
        assert member_page["total"] == 2 and member_page["has_more"] is True
        assert member_page["items"][0]["strong_state"] is True
        member_page_2 = request("/api/v3/focus-tracker/sectors/IND%3A801010/members",
                                {"page": "2", "page_size": "1"})
        assert member_page_2["items"][0]["security_name"] == "第二只个股"
        episode = request("/api/v3/focus-tracker/episodes/" + CURRENT_EPISODE)
        assert episode["episode"]["episode_id"] == CURRENT_EPISODE
        assert episode["observations"][0]["validity_capability"] == "APPLICABLE"
        assert len(episode["outcomes"]) == 1
        assert episode["outcomes"][0]["status"] == "OBSERVED"
        assert episode["outcomes"][0]["target_trade_date"] == TRADE_DATE.isoformat()
        before_entity_queries = borrowed_repository.connection.query_count
        stock = request("/api/v3/focus-tracker/stocks/" + SECURITY_ID)
        entity_query_count = borrowed_repository.connection.query_count - before_entity_queries
        assert len(stock["episodes"]) == 2
        # One fixed-run resolution plus five bounded entity-detail queries.
        # This remains constant as the number of episodes grows to the cap.
        assert entity_query_count == 6, entity_query_count
        _seed(connection)
        prior_run = "focus-read-api-prior-accepted"
        stale_run = "focus-read-api-stale-revision"
        with connection.cursor() as cur:
            for run_id, run_date, revision in ((prior_run, date(2026, 9, 18), 1),
                                               (stale_run, TRADE_DATE, 2)):
                cur.execute(
                    "insert into pg_temp.focus_runs values "
                    "(%s,%s,%s,'probe-publication',%s,'[]'::jsonb,'{}'::jsonb,"
                    "'FOCUS_STATE_CONTRACT_V1','probe-parameters','HISTORICAL_RECONSTRUCTED',"
                    "'ACTIVATED','PENDING',now())",
                    (run_id, run_date, revision, SOURCE_AUTHORITY_CONTRACT))
            cur.execute("insert into pg_temp.focus_trade_date_heads values (%s,%s,%s,'VALID')",
                        (date(2026, 9, 18), SOURCE_AUTHORITY_CONTRACT, prior_run))
            for run_id, day, phase in ((prior_run, date(2026, 9, 18), "NEW"),
                                       (stale_run, TRADE_DATE, "STALE_REVISION")):
                cur.execute(
                    "insert into pg_temp.focus_episode_observations "
                    "select episode_id,%s,%s,1,evaluation_mode,state_contract_id,"
                    "source_membership_state,%s,validity_state,followup_state,current_path_state,"
                    "lifetime_path_tags,continuity_quality,comparison_gap_sessions,"
                    "entry_primary_sector_id,current_primary_sector_id,first_supported_anchor_id,"
                    "close_price,return_since_first,drawdown_from_peak,adjustment_source_hash,"
                    "quality_status,fact_digest,facts from pg_temp.focus_episode_observations "
                    "where episode_id=%s and focus_run_id=%s",
                    (run_id, day, phase, EXITED_EPISODE, RUN_ID))
                cur.execute(
                    "insert into pg_temp.focus_episode_transitions values "
                    "(%s,%s,1,%s,%s,%s,%s,'NONE','CURRENT','[]'::jsonb)",
                    (EXITED_EPISODE, run_id, day, day, day, phase))
                cur.execute(
                    "insert into pg_temp.focus_episode_anchors values "
                    "(%s,%s,'MILESTONE',%s,%s,1,10,'LOCAL_ADJUSTED','COMPLETE')",
                    (run_id + "-anchor", EXITED_EPISODE, day, run_id))
            cur.execute(
                "insert into pg_temp.focus_episodes values "
                "('focus-read-api-unaccepted-parent','V3_SHORTLIST_STOCK','STOCK',%s,"
                "'V3_SHORTLIST_FAMILY',%s,%s,null)",
                (SECURITY_ID, TRADE_DATE, stale_run))
        with connection.cursor() as cur:
            historical_run = api._resolve_run(cur, stale_run)
            assert historical_run is not None
            historical_revision = api._episode(cur, EXITED_EPISODE, historical_run)
            accepted_run = api._resolve_run(cur, RUN_ID)
            assert accepted_run is not None
            entity_history = api._entity(cur, "STOCK", SECURITY_ID, accepted_run)
        exited_history = next(item for item in entity_history["episodes"]
                              if item["episode_id"] == EXITED_EPISODE)
        assert [row["trade_date"] for row in exited_history["observations"]] == [
            "2026-09-18", TRADE_DATE.isoformat()]
        assert "STALE_REVISION" not in {row["transition_type"]
                                        for row in exited_history["transitions"]}
        assert "EXIT_EFFECTIVE" not in {row["transition_type"] for row in historical_revision["transitions"]}
        assert "STALE_REVISION" in {row["transition_type"] for row in historical_revision["transitions"]}
        with connection.cursor() as cur:
            cur.execute("delete from pg_temp.focus_episode_observations "
                        "where episode_id=%s and focus_run_id=%s", (CURRENT_EPISODE, RUN_ID))
        predecessor = read_predecessor(_BorrowedRepository(connection), date(2026, 9, 23))
        assert predecessor.focus_run_id == RUN_ID
        assert "focus-read-api-unaccepted-parent" not in {
            prior.episode_id for prior in predecessor.previous.values()}
        status, accepted_history = api.handle("/api/v3/focus-tracker/episodes/" + EXITED_EPISODE, {})
        assert status == 200, (status, accepted_history)
        assert [row["trade_date"] for row in accepted_history["observations"]] == [
            "2026-09-18", TRADE_DATE.isoformat()]
        assert "STALE_REVISION" not in {row["membership_phase"] for row in accepted_history["observations"]}
        assert "STALE_REVISION" not in {row["transition_type"] for row in accepted_history["transitions"]}
        assert stale_run + "-anchor" not in {row["anchor_id"] for row in accepted_history["anchors"]}
        connection.rollback()
        _seed(connection)
        with connection.cursor() as cur:
            cur.executemany(
                "insert into pg_temp.focus_episodes values "
                "(%s,'V3_SHORTLIST_STOCK','STOCK',%s,'V3_SHORTLIST_FAMILY',%s,%s,null)",
                [(f"focus-read-api-extra-{index:02d}", SECURITY_ID, TRADE_DATE, RUN_ID)
                 for index in range(50)])
        before_capped_queries = borrowed_repository.connection.query_count
        status, capped_stock = api.handle("/api/v3/focus-tracker/stocks/" + SECURITY_ID, {})
        capped_query_count = borrowed_repository.connection.query_count - before_capped_queries
        assert status == 200 and len(capped_stock["episodes"]) == 50
        assert capped_stock["episodes_truncated"] is True
        assert capped_query_count == entity_query_count == 6, capped_query_count
        transitions = request("/api/v3/focus-tracker/transitions")
        assert transitions["total"] == 2
        transition_page_1 = request("/api/v3/focus-tracker/transitions", {"page": "1", "page_size": "1"})
        transition_page_2 = request("/api/v3/focus-tracker/transitions", {"page": "2", "page_size": "1"})
        assert transition_page_1["page_size"] == 1 and transition_page_1["has_more"] is True
        assert transition_page_2["page"] == 2 and transition_page_2["has_more"] is False
        assert transition_page_1["items"][0]["episode_id"] != transition_page_2["items"][0]["episode_id"]
        runs = request("/api/v3/focus-tracker/runs")
        assert runs["total"] == 1 and runs["items"][0]["focus_run_id"] == RUN_ID
        stats = request("/api/v3/focus-tracker/statistics")
        assert stats["status"] == "AVAILABLE"
        assert stats["statistics_batch"]["statistics_batch_id"] == "probe-statistics-batch"
        assert stats["groups"][0]["gate_status"] == "READY"
        assert stats["groups"][0]["signal_date_count"] == 5
        _seed(connection)
        with connection.cursor() as cur:
            cur.execute("delete from pg_temp.focus_statistics_heads where focus_run_id=%s", (RUN_ID,))
        status, not_materialized = api.handle("/api/v3/focus-tracker/statistics", {})
        assert status == 200 and not_materialized["status"] == "STATISTICS_NOT_MATERIALIZED", (status, not_materialized)

        _seed(connection, replay_required=True)
        status, replay = api.handle("/api/v3/focus-tracker/summary", {})
        assert status == 200 and replay["status"] == "REPLAY_REQUIRED"
        _seed(connection, add_head=False)
        status, historical = api.handle("/api/v3/focus-tracker/summary", {"focus_run_id": RUN_ID})
        assert status == 200
        assert historical["lineage_state"] == "HISTORICAL", historical
        _seed(connection, add_head=False)
        status, no_run_statistics = api.handle("/api/v3/focus-tracker/statistics", {})
        assert status == 200 and no_run_statistics["status"] == "NO_ACCEPTED_RUN"
        assert no_run_statistics["groups"] == []
        connection.rollback()
        return {"mode": "ROLLBACK_ONLY_TEMP_SCHEMA", "run": RUN_ID,
                "current_and_exited_items": items["total"],
                "item_context_fields": True,
                "followup_rows": exited["total"], "reentry_episodes_distinct": True,
                "episode_outcome_mapped": True, "stock_episodes": len(stock["episodes"]),
                "entity_detail_queries": entity_query_count,
                "entity_detail_queries_at_episode_cap": capped_query_count,
                "entity_episode_cap": len(capped_stock["episodes"]),
                "entity_episode_list_truncated": capped_stock["episodes_truncated"],
                "transitions": transitions["total"], "replay_fail_closed": True,
                "historical_run_labeled": True,
                "statistics_materialized_read": stats["status"],
                "statistics_gate": stats["groups"][0]["gate_status"],
                "future_outcome_hidden": True, "missing_statistics_head_fails_closed": True,
                "no_run_statistics_safe_shape": True,
                "persisted_changes": 0}


if __name__ == "__main__":
    print(run_probe())
