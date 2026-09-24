"""Rollback-only Focus core FK/head atomicity rehearsal with one real source row."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from psycopg.types.json import Jsonb

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.contracts import (SOURCE_AUTHORITY_CONTRACT, anchor_id,
                                         digest, episode_id)
from src.focus_tracker.lifecycle import Decision, segment_id
from src.focus_tracker.materialize import PathRequest, materialize_stock_paths
from src.focus_tracker.observation import CONTRACT_ID as OBS_CONTRACT, assemble_observation
from src.focus_tracker.predicates import Tri
from src.focus_tracker.source_reader import read_accepted_sources
from src.focus_tracker.states import CONTRACT_ID as STATE_CONTRACT
from src.workbench_db.postgres_repository import PostgresRepository


def _counts(cur) -> tuple[int, int, int]:
    cur.execute("""select (select count(*) from workbench.focus_runs),
                          (select count(*) from workbench.focus_trade_date_heads),
                          (select count(*) from workbench.focus_episode_observations)""")
    return tuple(int(value) for value in cur.fetchone())


def main() -> int:
    with PostgresRepository(dsn=_dsn()) as repo:
        con = repo.connection
        assert con is not None
        before = None
        try:
            with con.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))",
                            ("FOCUS_CORE_ROLLBACK_PROBE",))
                before = _counts(cur)
                cur.execute("select max(trade_date) from workbench.publication_heads")
                day: date = cur.fetchone()[0]
                cur.execute("""select sha256 from workbench_meta.artifact_catalog
                               where relative_path=%s and availability='AVAILABLE'
                               order by discovered_at desc limit 1""",
                            ("data/normalized/adjusted_daily.parquet",))
                artifact_sha = cur.fetchone()[0]
                cur.execute("""select 1 from workbench.focus_trade_date_heads
                               where trade_date=%s and source_authority_contract_id=%s""",
                            (day, SOURCE_AUTHORITY_CONTRACT))
                if cur.fetchone():
                    raise RuntimeError("probe requires empty Focus day head")
            sources = read_accepted_sources(repo, day)
            row = next(item for item in sources.rows
                       if item.key.source_family == "V3_3_TODAY_CANDIDATE")
            stock_fact = materialize_stock_paths(
                normalized_path=Path("data/normalized/adjusted_daily.parquet"),
                expected_sha256=str(artifact_sha), trade_date=day,
                requests=[PathRequest(row.key.entity_id, day)])[0]
            eid = episode_id(row.key, day)
            decision = Decision(row.key, row.membership, "NEW", eid, None,
                                (("FIRST_FOCUS", anchor_id(eid, "FIRST_FOCUS", day)),),
                                "SOURCE_MEMBERSHIP")
            observation = assemble_observation(
                decision=decision, source_contract_id=row.source_contract_id,
                stock_fact=stock_fact, predicate_facts={}, invalidation=Tri.UNKNOWN)
            run_id = "focus-core-probe-" + uuid4().hex
            first_anchor = decision.anchors[0][1]
            seg = segment_id(eid, "SOURCE_MODEL", day, row.source_contract_id,
                             STATE_CONTRACT)
            evaluation_id = "focus-eval-probe-" + uuid4().hex
            parameter_set = "FOCUS_STOCK_PATH_PARAMS_V1_CANDIDATE"
            with con.cursor() as cur:
                cur.execute("""insert into workbench.focus_runs
                    (focus_run_id,trade_date,revision,publication_id,
                     source_authority_contract_id,source_family_set,family_capabilities,
                     source_identity_digest,calendar_digest,observation_input_digest,
                     state_contract_id,parameter_set_id,price_basis,dependency_lock_hash,
                     evaluation_basis,core_publication_status,activated_at_utc)
                    values (%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            'HISTORICAL_RECONSTRUCTED','ACTIVATED',now())""",
                    (run_id, day, sources.publication_id, SOURCE_AUTHORITY_CONTRACT,
                     Jsonb([row.key.source_family]), Jsonb(sources.capabilities),
                     sources.source_identity_digest, digest([day]),
                     stock_fact.input_digest, STATE_CONTRACT, parameter_set,
                     "TDX_NATIVE_AFFINE_QFQ", "0" * 64))
                cur.execute("""insert into workbench.focus_daily_items
                    (focus_run_id,source_family,entity_type,entity_id,
                     selection_contract_family,source_item_key,source_item_digest,
                     source_contract_id,source_membership_state,source_focus_class,
                     source_rank,source_quality,source_facts)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (run_id, row.key.source_family, row.key.entity_type,
                     row.key.entity_id, row.key.selection_contract_family,
                     row.source_item_key, row.source_item_digest,
                     row.source_contract_id, row.membership, row.source_focus_class,
                     row.source_rank, "READY", Jsonb(row.source_facts)))
                cur.execute("""insert into workbench.focus_episodes
                    (episode_id,source_family,entity_type,entity_id,
                     selection_contract_family,first_trade_date,first_focus_run_id)
                    values (%s,%s,%s,%s,%s,%s,%s)""",
                    (eid, row.key.source_family, row.key.entity_type,
                     row.key.entity_id, row.key.selection_contract_family,
                     day, run_id))
                cur.execute("""insert into workbench.focus_episode_segments
                    (segment_id,episode_id,segment_type,start_trade_date,
                     source_model_contract_id,selection_contract_family,
                     state_contract_id,parameter_set_id,
                     boundary_reason,focus_run_id)
                    values (%s,%s,'SOURCE_MODEL',%s,%s,%s,%s,%s,'FIRST_FOCUS',%s)""",
                    (seg, eid, day, row.source_contract_id,
                     row.key.selection_contract_family, STATE_CONTRACT,
                     parameter_set, run_id))
                cur.execute("""insert into workbench.focus_episode_transitions
                    (episode_id,focus_run_id,source_revision,transition_trade_date,
                     effective_trade_date,confirmation_trade_date,transition_type,
                     from_membership,to_membership,reason_codes)
                    values (%s,%s,1,%s,%s,%s,'NEW','NONE',%s,%s)""",
                    (eid, run_id, day, day, day, row.membership,
                     Jsonb([decision.reason])))
                cur.execute("""insert into workbench.focus_episode_anchors
                    (anchor_id,episode_id,anchor_type,trade_date,focus_run_id,
                     source_revision,reference_price,price_basis,quality_status,
                     source_fact_digest)
                    values (%s,%s,'FIRST_FOCUS',%s,%s,1,%s,%s,%s,%s)""",
                    (first_anchor, eid, day, run_id, stock_fact.close_price,
                     "TDX_NATIVE_AFFINE_QFQ", stock_fact.quality_status,
                     stock_fact.input_digest))
                cur.execute("""insert into workbench.focus_episode_observations
                    (episode_id,focus_run_id,trade_date,source_revision,
                     evaluation_mode,state_contract_id,source_membership_state,
                     membership_phase,validity_state,followup_state,
                     current_path_state,lifetime_path_tags,continuity_quality,
                     close_price,drawdown_from_peak,adjustment_source_hash,
                     quality_status,fact_digest,facts)
                    values (%s,%s,%s,1,'AS_RECORDED',%s,%s,%s,%s,%s,%s,%s,
                            'FIRST_DAY',%s,%s,%s,%s,%s,%s)""",
                    (eid, run_id, day, STATE_CONTRACT,
                     observation.source_membership_state,
                     observation.membership_phase, observation.validity_state,
                     observation.followup_state, observation.current_path_state,
                     Jsonb(list(observation.lifetime_path_tags)),
                     stock_fact.close_price, stock_fact.drawdown_current,
                     artifact_sha, observation.quality_status,
                     observation.fact_digest, Jsonb(observation.evidence)))
                cur.execute("""insert into workbench.focus_state_evaluations
                    (state_evaluation_id,episode_id,trade_date,source_revision,
                     state_contract_id,parameter_set_id,evaluation_mode,
                     validity_state,current_path_state,quality_status,evidence_digest)
                    values (%s,%s,%s,1,%s,%s,'AS_RECORDED',%s,%s,%s,%s)""",
                    (evaluation_id, eid, day, STATE_CONTRACT, parameter_set,
                     observation.validity_state, observation.current_path_state,
                     observation.quality_status, observation.fact_digest))
                for predicate, result in observation.evidence["path_predicates"].items():
                    cur.execute("""insert into workbench.focus_state_evaluation_facts
                        (state_evaluation_id,predicate_id,operand_mode,result,
                         reason_code,evidence)
                        values (%s,%s,'COMPOSITE',%s,%s,%s)""",
                        (evaluation_id, predicate, result,
                         "UNAVAILABLE_INPUT" if result == "UNKNOWN" else None,
                         Jsonb({"result": result, "assembly_contract": OBS_CONTRACT})))
                projection_digest = digest({"episode": eid,
                                            "observation": observation.fact_digest})
                cur.execute("""insert into workbench.focus_current_projection
                    (source_family,entity_type,entity_id,active_episode_id,
                     last_episode_id,latest_trade_date,latest_focus_run_id,
                     source_membership_state,membership_phase,validity_state,
                     followup_state,current_path_state,projection_digest)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (row.key.source_family, row.key.entity_type,
                     row.key.entity_id, eid, eid, day, run_id,
                     observation.source_membership_state,
                     observation.membership_phase, observation.validity_state,
                     observation.followup_state,
                     observation.current_path_state, projection_digest))
                cur.execute("""insert into workbench.focus_trade_date_heads
                    (trade_date,source_authority_contract_id,accepted_focus_run_id,
                     accepted_revision,lineage_state,activated_at_utc)
                    values (%s,%s,%s,1,'VALID',now())""",
                    (day, SOURCE_AUTHORITY_CONTRACT, run_id))
                cur.execute("""select count(*) from workbench.focus_episode_observations
                               where episode_id=%s and focus_run_id=%s""", (eid, run_id))
                if cur.fetchone()[0] != 1:
                    raise RuntimeError("probe observation missing before rollback")
                cur.execute("""select accepted_focus_run_id from workbench.focus_trade_date_heads
                               where trade_date=%s and source_authority_contract_id=%s""",
                            (day, SOURCE_AUTHORITY_CONTRACT))
                if cur.fetchone()[0] != run_id:
                    raise RuntimeError("probe head not visible inside transaction")
        finally:
            con.rollback()
        with con.cursor() as cur:
            after = _counts(cur)
        con.rollback()
        if after != before:
            raise RuntimeError("rollback left Focus business rows")
        print({"mode": "ROLLBACK_ONLY", "source_date": str(day),
               "inside_transaction": "PASS", "post_rollback_counts": after,
               "unchanged": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
