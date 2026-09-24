"""Atomically publish one contiguous next-day Focus core run."""
from __future__ import annotations

import json
from datetime import date

from psycopg.types.json import Jsonb

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.run_focus_initial_core_transaction import _source_quality
from src.focus_tracker.basket_store import insert_entry_basket
from src.focus_tracker.contracts import (SOURCE_AUTHORITY_CONTRACT, canonical_bytes,
                                          digest, revisioned_anchor_id)
from src.focus_tracker.core_activation import activate_core_head
from src.focus_tracker.core_run_identity import inspect_run_slot
from src.focus_tracker.daily_builder import build_focus_daily_batch
from src.focus_tracker.daily_head_plan import read_daily_head_plan
from src.focus_tracker.lifecycle import segment_id
from src.focus_tracker.frozen_invalidation_facts import (insert_episode_facts,
                                                         verify_episode_facts)
from src.focus_tracker.path_fact_index import index_stock_path_facts
from src.focus_tracker.previous_reader import read_predecessor
from src.focus_tracker.projection import rebuild_current_projection, verify_current_projection
from src.focus_tracker.release_gate import require_core_publication_ready
from src.focus_tracker.source_reader import read_accepted_sources
from src.focus_tracker.states import CONTRACT_ID as STATE_CONTRACT
from src.focus_tracker.tracking_context import read_first_source_rows, resolve_tracking_contexts
from src.workbench_db.postgres_repository import PostgresRepository


NEW_EPISODE_PHASES = frozenset({"NEW", "REENTERED", "MODEL_BASELINE"})


def publish_next_day(*, trade_date: date, expected_manifest_digest: str,
                     commit: bool = False) -> dict[str, object]:
    manifest, sources, plan, stock_facts, observations, baskets, closure = build_focus_daily_batch(
        evaluation_basis="REAL_FORWARD", expected_trade_date=trade_date)
    if manifest.sha256 != expected_manifest_digest:
        raise RuntimeError("FOCUS_PREFLIGHT_MANIFEST_CHANGED_BEFORE_APPLY")
    observed_episodes = {(item.key, item.observation.episode_id)
                         for item in observations}
    plan_decisions = getattr(plan, "episode_tracking", ()) or plan.decisions
    planned_episodes = {(item.key, item.episode_id) for item in plan_decisions}
    if observed_episodes != planned_episodes:
        raise ValueError("FOCUS_CONTINUATION_EPISODE_OBSERVATION_SET_INCOMPLETE")
    with PostgresRepository(dsn=_dsn()) as repo:
        head = read_daily_head_plan(repo, trade_date=trade_date)
        repo.connection.rollback()
    if head.status not in {"NEXT_DAY", "REVISION_REQUIRED"}:
        raise RuntimeError("FOCUS_CONTINUATION_REQUIRES_NEXT_DAY_OR_REVISION_HEAD")
    revision = head.revision
    run_id = "focus-run-" + digest({"manifest": manifest.sha256,
                                    "closure": closure.input_digest,
                                    "revision": revision})[:32]
    rows = {row.key: row for row in sources.rows}
    decisions = {(item.key, item.episode_id): item for item in plan_decisions}
    by_stock = index_stock_path_facts(requests=plan.stock_path_requests,
                                      facts=stock_facts)
    by_sector = {(basket.sector_id, basket.basket_digest): basket for basket in baskets}
    payload = manifest.payload
    identity = dict(trade_date=trade_date, revision=revision, run_id=run_id,
                    source_identity_digest=sources.source_identity_digest,
                    observation_input_digest=closure.input_digest,
                    state_contract_id=payload["state_contract_id"],
                    parameter_set_id=payload["parameter_set_id"],
                    dependency_lock_hash=payload["dependency_lock_hash"])
    with PostgresRepository(dsn=_dsn()) as repo:
        con = repo.connection
        assert con is not None
        committed = False
        try:
            with con.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))",
                            ("FOCUS_DAILY_CORE_" + trade_date.isoformat(),))
            head = read_daily_head_plan(repo, trade_date=trade_date)
            if (head.status not in {"NEXT_DAY", "REVISION_REQUIRED"} or
                    head.revision != revision):
                raise RuntimeError("FOCUS_CONTINUATION_HEAD_CHANGED_BEFORE_APPLY")
            previous = read_predecessor(repo, trade_date)
            if previous.focus_run_id != head.predecessor_focus_run_id:
                raise RuntimeError("FOCUS_PREDECESSOR_CHANGED_BEFORE_APPLY")
            live = read_accepted_sources(repo, trade_date)
            if live.source_identity_digest != sources.source_identity_digest:
                raise RuntimeError("FOCUS_ACCEPTED_SOURCE_CHANGED_BEFORE_APPLY")
            require_core_publication_ready(
                manifest=manifest, sources=live, plan=plan,
                expected_trade_date=trade_date, repository=repo)
            slot = inspect_run_slot(repo, **identity)
            if slot == "ALREADY_ACTIVATED":
                if not verify_current_projection(repo, focus_run_id=run_id):
                    raise RuntimeError("idempotent projection mismatch")
                con.rollback()
                return {"status": "ALREADY_ACTIVATED", "focus_run_id": run_id,
                        "trade_date": trade_date.isoformat(), "writes": 0}
            historical_ids = {episode for (_, episode), decision in decisions.items()
                              if decision.phase not in NEW_EPISODE_PHASES}
            first_rows = read_first_source_rows(repo, episode_ids=historical_ids)
            contexts = resolve_tracking_contexts(plan=plan, sources=sources,
                                                 first_source_rows=first_rows)
            with con.cursor() as cur:
                cur.execute("""insert into workbench.focus_runs
                    (focus_run_id,trade_date,revision,publication_id,
                     source_authority_contract_id,source_family_set,family_capabilities,
                     source_identity_digest,calendar_digest,observation_input_digest,
                     state_contract_id,parameter_set_id,price_basis,dependency_lock_hash,
                     evaluation_basis,core_publication_status)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            'REAL_FORWARD','BUILDING')""",
                    (run_id, trade_date, revision, sources.publication_id,
                     SOURCE_AUTHORITY_CONTRACT, Jsonb(sorted(sources.capabilities)),
                     Jsonb(sources.capabilities), sources.source_identity_digest,
                     payload["calendar_digest"], closure.input_digest,
                     payload["state_contract_id"], payload["parameter_set_id"],
                     "TDX_NATIVE_AFFINE_QFQ", payload["dependency_lock_hash"]))
                for row in sources.rows:
                    cur.execute("""insert into workbench.focus_daily_items
                        (focus_run_id,source_family,entity_type,entity_id,
                         selection_contract_family,source_item_key,source_item_digest,
                         source_contract_id,source_membership_state,source_focus_class,
                         source_rank,source_quality,source_facts)
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (run_id, row.key.source_family, row.key.entity_type,
                         row.key.entity_id, row.key.selection_contract_family,
                         row.source_item_key, row.source_item_digest,
                         row.source_contract_id, row.membership,
                         row.source_focus_class, row.source_rank, _source_quality(row),
                         Jsonb(json.loads(canonical_bytes(row.source_facts)))))
                for item in observations:
                    key, observation = item.key, item.observation
                    episode_identity = (key, observation.episode_id)
                    decision, context = decisions[episode_identity], contexts[episode_identity]
                    episode = decision.episode_id
                    if episode is None or episode != observation.episode_id:
                        raise ValueError("continuation episode identity mismatch")
                    is_new = decision.phase in NEW_EPISODE_PHASES
                    if is_new:
                        cur.execute("""insert into workbench.focus_episodes
                            (episode_id,source_family,entity_type,entity_id,
                             selection_contract_family,first_trade_date,
                             first_focus_run_id,parent_episode_id)
                            values (%s,%s,%s,%s,%s,%s,%s,%s)
                            on conflict (episode_id) do nothing""",
                            (episode, key.source_family, key.entity_type,
                             key.entity_id, key.selection_contract_family,
                             trade_date, run_id, decision.parent_episode_id))
                        episode_inserted = cur.rowcount == 1
                        cur.execute("select first_trade_date,selection_contract_family "
                                    "from workbench.focus_episodes where episode_id=%s", (episode,))
                        stored_episode = cur.fetchone()
                        if stored_episode is None or stored_episode[0] != trade_date:
                            raise ValueError("revision episode identity collision")
                        if len(stored_episode) > 1 and stored_episode[1] != key.selection_contract_family:
                            raise ValueError("revision episode selection contract mismatch")
                        # A same-day revision keeps the logical episode and segment,
                        # while its run-scoped observation and anchors remain immutable.
                        if (episode_inserted or
                                context.first_trade_date == trade_date):
                            insert_episode_facts(
                                cur, episode_id=episode, row=rows[key],
                                source_revision=revision,
                                insert_legacy=episode_inserted)
                        is_new = episode_inserted
                    else:
                        cur.execute("""select first_trade_date,selection_contract_family
                                       from workbench.focus_episodes
                                       where episode_id=%s and source_family=%s
                                       and entity_type=%s and entity_id=%s""",
                                    (episode, key.source_family, key.entity_type,
                                     key.entity_id))
                        stored_episode = cur.fetchone()
                        active_selection = None
                        if stored_episode is not None:
                            cur.execute("""select s.selection_contract_family
                                from workbench.focus_episode_segments s
                                join workbench.focus_trade_date_heads h
                                  on h.accepted_focus_run_id=s.focus_run_id
                                 and h.lineage_state='VALID'
                                where s.episode_id=%s and s.segment_type='SOURCE_MODEL'
                                  and s.start_trade_date<=%s
                                order by s.start_trade_date desc limit 1""",
                                (episode, trade_date))
                            active_segment = cur.fetchone()
                            active_selection = active_segment[0] if active_segment else None
                        if (stored_episode is None or
                                stored_episode[0] != context.first_trade_date or
                                (len(stored_episode) > 1 and
                                 stored_episode[1] != key.selection_contract_family and
                                 active_selection != key.selection_contract_family and
                                 decision.phase != "SOURCE_MODEL_BOUNDARY")):
                            raise ValueError("continuation episode does not match stored identity")
                        if key.source_family == "V3_3_TODAY_CANDIDATE":
                            verify_episode_facts(cur, episode_id=episode,
                                                 first_row=first_rows[episode])
                    if is_new or decision.phase == "SOURCE_MODEL_BOUNDARY":
                        reason = "FIRST_FOCUS" if is_new else "SELECTION_CONTRACT_BOUNDARY"
                        cur.execute("""insert into workbench.focus_episode_segments
                            (segment_id,episode_id,segment_type,start_trade_date,
                             source_model_contract_id,selection_contract_family,
                             state_contract_id,parameter_set_id,
                             boundary_reason,focus_run_id)
                            values (%s,%s,'SOURCE_MODEL',%s,%s,%s,%s,%s,%s,%s)
                            on conflict do nothing""",
                            (segment_id(episode, "SOURCE_MODEL", trade_date,
                                        context.source_contract_id, STATE_CONTRACT, revision),
                             episode, trade_date, context.source_contract_id,
                             key.selection_contract_family, STATE_CONTRACT,
                             payload["parameter_set_id"], reason, run_id))
                    old = previous.previous.get(key)
                    if old is None:
                        old = next((value for prior_key, value in previous.previous.items()
                                    if (prior_key.source_family, prior_key.entity_type,
                                        prior_key.entity_id) ==
                                    (key.source_family, key.entity_type,
                                     key.entity_id)), None)
                    prior_membership = old.membership if old else "NONE"
                    if decision.reason != "PENDING_EPISODE_FOLLOW_UP":
                        cur.execute("""insert into workbench.focus_episode_transitions
                        (episode_id,focus_run_id,source_revision,transition_trade_date,
                         effective_trade_date,confirmation_trade_date,transition_type,
                         from_membership,to_membership,reason_codes)
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (episode, run_id, revision, trade_date, trade_date, trade_date,
                             decision.phase, prior_membership, decision.membership,
                             Jsonb([decision.reason])))
                    stock_fact = (by_stock[(key.entity_id, context.first_trade_date)]
                                  if key.entity_type == "STOCK" else None)
                    sector_basket = (by_sector[(key.entity_id,
                                                observation.evidence["predicate_facts"]["basket_digest"])]
                                     if key.entity_type == "SECTOR" else None)
                    source_digest = (stock_fact.input_digest if stock_fact else
                                     sector_basket.basket_digest)
                    for anchor_type, anchor in decision.anchors:
                        if revision > 1:
                            anchor = revisioned_anchor_id(anchor, revision)
                        cur.execute("""insert into workbench.focus_episode_anchors
                            (anchor_id,episode_id,anchor_type,trade_date,focus_run_id,
                             source_revision,reference_price,price_basis,quality_status,
                             source_fact_digest)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (anchor, episode, anchor_type, trade_date, run_id, revision,
                             stock_fact.close_price if stock_fact else None,
                             "TDX_NATIVE_AFFINE_QFQ" if stock_fact else "FROZEN_BASKET_NAV",
                             stock_fact.quality_status if stock_fact else "NO_BASE_PRICE",
                             source_digest))
                    cur.execute("""insert into workbench.focus_episode_observations
                        (episode_id,focus_run_id,trade_date,source_revision,
                         evaluation_mode,state_contract_id,source_membership_state,
                         membership_phase,validity_state,followup_state,
                         current_path_state,lifetime_path_tags,continuity_quality,
                         close_price,return_since_first,drawdown_from_peak,
                         adjustment_source_hash,quality_status,fact_digest,facts)
                        values (%s,%s,%s,%s,'AS_RECORDED',%s,%s,%s,%s,%s,%s,%s,
                                'CONTINUOUS',%s,%s,%s,%s,%s,%s,%s)""",
                        (episode, run_id, trade_date, revision, STATE_CONTRACT,
                         observation.source_membership_state,
                         observation.membership_phase, observation.validity_state,
                         observation.followup_state, observation.current_path_state,
                         Jsonb(list(observation.lifetime_path_tags)),
                         stock_fact.close_price if stock_fact else None,
                         stock_fact.return_since_start if stock_fact else None,
                         stock_fact.drawdown_current if stock_fact else None,
                         payload["normalized_artifact_sha256"] if stock_fact else None,
                         observation.quality_status, observation.fact_digest,
                         Jsonb(observation.evidence)))
                    evaluation_id = "focus-eval-" + digest({
                        "episode": episode, "day": trade_date, "revision": revision,
                        "state": STATE_CONTRACT})[:32]
                    cur.execute("""insert into workbench.focus_state_evaluations
                        (state_evaluation_id,episode_id,trade_date,source_revision,
                         state_contract_id,parameter_set_id,evaluation_mode,
                         validity_state,current_path_state,quality_status,evidence_digest)
                        values (%s,%s,%s,%s,%s,%s,'AS_RECORDED',%s,%s,%s,%s)""",
                        (evaluation_id, episode, trade_date, revision, STATE_CONTRACT,
                         payload["parameter_set_id"], observation.validity_state,
                         observation.current_path_state, observation.quality_status,
                         observation.fact_digest))
                    for predicate, result in observation.evidence["path_predicates"].items():
                        cur.execute("""insert into workbench.focus_state_evaluation_facts
                            (state_evaluation_id,predicate_id,operand_mode,result,
                             reason_code,evidence)
                            values (%s,%s,'COMPOSITE',%s,%s,%s)""",
                            (evaluation_id, predicate, result,
                             "UNAVAILABLE_INPUT" if result == "UNKNOWN" else None,
                             Jsonb({"result": result, "observation": observation.fact_digest})))
                    if is_new and key.entity_type == "SECTOR":
                        insert_entry_basket(repo, episode_id=episode,
                                            focus_run_id=run_id,
                                            publication_id=sources.publication_id,
                                                basket=sector_basket)
                cur.execute("update workbench.focus_runs set core_publication_status='READY' "
                            "where focus_run_id=%s", (run_id,))
            activate_core_head(repo, focus_run_id=run_id,
                               trade_date=trade_date, revision=revision)
            rebuild_current_projection(repo, focus_run_id=run_id)
            if not verify_current_projection(repo, focus_run_id=run_id):
                raise RuntimeError("continuation projection verification failed")
            if inspect_run_slot(repo, **identity) != "ALREADY_ACTIVATED":
                raise RuntimeError("continuation run identity verification failed")
            result = {"status": "ACTIVATED" if commit else "ROLLBACK_READY",
                      "focus_run_id": run_id, "trade_date": trade_date.isoformat(),
                      "source_rows": len(sources.rows),
                      "observation_count": len(observations),
                      "tracking_keys": len(plan.tracking_keys),
                      "tracking_episodes": len(planned_episodes),
                      "predecessor_focus_run_id": head.predecessor_focus_run_id,
                      "revision": revision, "head_plan_status": head.status}
            if commit:
                con.commit()
                committed = True
            else:
                con.rollback()
            return result
        finally:
            if not committed:
                con.rollback()
