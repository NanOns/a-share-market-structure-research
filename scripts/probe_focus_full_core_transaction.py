"""All-row initial Focus core transaction rehearsal; always rolls back."""
from __future__ import annotations

import argparse
import json
from datetime import date

from psycopg.types.json import Jsonb

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.probe_focus_observations import build_observation_batch
from src.focus_tracker.basket_store import insert_entry_basket
from src.focus_tracker.contracts import (SOURCE_AUTHORITY_CONTRACT,
                                         canonical_bytes, digest)
from src.focus_tracker.core_activation import activate_core_head
from src.focus_tracker.core_run_identity import inspect_run_slot
from src.focus_tracker.lifecycle import segment_id
from src.focus_tracker.projection import (rebuild_current_projection,
                                          verify_current_projection)
from src.focus_tracker.release_gate import require_core_publication_ready
from src.focus_tracker.source_reader import read_accepted_sources
from src.focus_tracker.states import CONTRACT_ID as STATE_CONTRACT
from src.workbench_db.postgres_repository import PostgresRepository


class InjectedCoreFailure(RuntimeError):
    pass


def _source_quality(row) -> str:
    facts = row.source_facts
    if row.key.source_family == "V3_SECTOR_TRACK":
        return str(facts.get("quality") or "UNKNOWN")
    factor = facts.get("factor_evidence")
    if isinstance(factor, dict) and factor.get("quality"):
        return str(factor["quality"])
    scanner = facts.get("scanner_evidence")
    category_to_branch = {"LAUNCH_CONFIRM": "launch",
                          "STRONG_PULLBACK": "pullback",
                          "SETUP_WATCH": "setup_watch",
                          "RECOVERY_TURN": "recovery_turn",
                          "TREND_CONTINUE": "trend_continue"}
    if isinstance(scanner, dict):
        branch = scanner.get(category_to_branch.get(facts.get("primary_category"), ""))
        return str(branch.get("quality") or "UNKNOWN") if isinstance(branch, dict) else "UNKNOWN"
    return "READY"


def _counts(cur) -> tuple[int, ...]:
    names = ("focus_runs", "focus_daily_items", "focus_episodes",
             "focus_episode_segments", "focus_episode_transitions",
             "focus_episode_anchors", "focus_episode_observations",
             "focus_state_evaluations", "focus_state_evaluation_facts",
             "focus_current_projection", "focus_trade_date_heads",
             "focus_episode_baskets")
    result = []
    for name in names:
        cur.execute("select count(*) from workbench." + name)
        result.append(int(cur.fetchone()[0]))
    return tuple(result)


def main(*, inject_after_observations: int | None = None,
         commit: bool = False,
         expected_trade_date: date | None = None,
         expected_manifest_digest: str | None = None) -> int:
    if inject_after_observations is not None and inject_after_observations < 1:
        raise ValueError("failure injection count must be positive")
    if commit and inject_after_observations is not None:
        raise ValueError("failure injection cannot be combined with commit")
    basis = "REAL_FORWARD" if commit else "HISTORICAL_RECONSTRUCTED"
    manifest, sources, plan, stock_facts, observations, baskets, closure = build_observation_batch(
        evaluation_basis=basis, expected_trade_date=expected_trade_date if commit else None)
    if expected_manifest_digest is not None and manifest.sha256 != expected_manifest_digest:
        raise RuntimeError("FOCUS_PREFLIGHT_MANIFEST_CHANGED_BEFORE_APPLY")
    if commit:
        if expected_trade_date is None:
            raise ValueError("--commit requires --expected-trade-date")
    elif manifest.release_gate_reasons != ("HISTORICAL_RECONSTRUCTED_INPUT",):
        raise RuntimeError("rollback rehearsal requires historical-only release gate")
    if any(decision.phase != "NEW" for decision in plan.decisions):
        raise RuntimeError("initial-day rehearsal requires all NEW episodes")
    rows = {row.key: row for row in sources.rows}
    decisions = {item.key: item for item in plan.decisions}
    by_stock = {(fact.security_id, fact.start_trade_date): fact for fact in stock_facts}
    baskets_by_sector = {basket.sector_id: basket for basket in baskets}
    if set(rows) != {item.key for item in observations}:
        raise RuntimeError("initial-day source/observation set mismatch")
    run_id = "focus-run-" + digest({"manifest": manifest.sha256,
                                    "closure": closure.input_digest})[:32]
    before = None
    delta = None
    injected = False
    written_observations = 0
    committed = False
    identity = dict(trade_date=sources.trade_date, revision=1,
                    run_id=run_id,
                    source_identity_digest=sources.source_identity_digest,
                    observation_input_digest=closure.input_digest,
                    state_contract_id=manifest.payload["state_contract_id"],
                    parameter_set_id=manifest.payload["parameter_set_id"],
                    dependency_lock_hash=manifest.payload["dependency_lock_hash"])
    with PostgresRepository(dsn=_dsn()) as repo:
        con = repo.connection
        assert con is not None
        try:
            with con.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))",
                            ("FOCUS_INITIAL_CORE_" + sources.trade_date.isoformat(),))
                before = _counts(cur)
                if commit:
                    require_core_publication_ready(
                        manifest=manifest, sources=sources, plan=plan,
                        expected_trade_date=expected_trade_date, repository=repo)
                slot_state = inspect_run_slot(repo, **identity)
                if commit and slot_state == "ALREADY_ACTIVATED":
                    if not verify_current_projection(repo, focus_run_id=run_id):
                        raise RuntimeError("idempotent run projection is inconsistent")
                    con.rollback()
                    print({"mode": "IDEMPOTENT_ALREADY_ACTIVATED",
                           "focus_run_id": run_id,
                           "trade_date": str(sources.trade_date),
                           "closure_digest": closure.input_digest})
                    return 0
                cur.execute("select count(*) from workbench.focus_trade_date_heads")
                if cur.fetchone()[0] != 0:
                    raise RuntimeError("initial core rehearsal requires no Focus heads")
                cur.execute("""select publication_id from workbench.publication_heads
                               where trade_date=%s""", (sources.trade_date,))
                head = cur.fetchone()
                if head is None or str(head[0]) != sources.publication_id:
                    raise RuntimeError("accepted source publication changed")
            live = read_accepted_sources(repo, sources.trade_date)
            if live.source_identity_digest != sources.source_identity_digest:
                raise RuntimeError("accepted source digest changed before transaction")
            payload = manifest.payload
            if slot_state != "NEW":
                raise RuntimeError("initial core slot is not new")
            with con.cursor() as cur:
                cur.execute("""insert into workbench.focus_runs
                    (focus_run_id,trade_date,revision,publication_id,
                     source_authority_contract_id,source_family_set,family_capabilities,
                     source_identity_digest,calendar_digest,observation_input_digest,
                     state_contract_id,parameter_set_id,price_basis,dependency_lock_hash,
                     evaluation_basis,core_publication_status)
                    values (%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,'BUILDING')""",
                    (run_id, sources.trade_date, sources.publication_id,
                     SOURCE_AUTHORITY_CONTRACT,
                     Jsonb(sorted(sources.capabilities)), Jsonb(sources.capabilities),
                     sources.source_identity_digest, payload["calendar_digest"],
                     closure.input_digest, payload["state_contract_id"],
                     payload["parameter_set_id"], "TDX_NATIVE_AFFINE_QFQ",
                     payload["dependency_lock_hash"], basis))
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
                    decision, row = decisions[key], rows[key]
                    episode = observation.episode_id
                    cur.execute("""insert into workbench.focus_episodes
                        (episode_id,source_family,entity_type,entity_id,
                         selection_contract_family,first_trade_date,first_focus_run_id)
                        values (%s,%s,%s,%s,%s,%s,%s)""",
                        (episode, key.source_family, key.entity_type, key.entity_id,
                         key.selection_contract_family, sources.trade_date, run_id))
                    cur.execute("""insert into workbench.focus_episode_segments
                        (segment_id,episode_id,segment_type,start_trade_date,
                         source_model_contract_id,state_contract_id,parameter_set_id,
                         boundary_reason,focus_run_id)
                        values (%s,%s,'SOURCE_MODEL',%s,%s,%s,%s,'FIRST_FOCUS',%s)""",
                        (segment_id(episode, "SOURCE_MODEL", sources.trade_date,
                                    row.source_contract_id, STATE_CONTRACT),
                         episode, sources.trade_date, row.source_contract_id,
                         STATE_CONTRACT, payload["parameter_set_id"], run_id))
                    cur.execute("""insert into workbench.focus_episode_transitions
                        (episode_id,focus_run_id,source_revision,transition_trade_date,
                         effective_trade_date,confirmation_trade_date,transition_type,
                         from_membership,to_membership,reason_codes)
                        values (%s,%s,1,%s,%s,%s,'NEW','NONE',%s,%s)""",
                        (episode, run_id, sources.trade_date, sources.trade_date,
                         sources.trade_date, decision.membership,
                         Jsonb([decision.reason])))
                    if len(decision.anchors) != 1 or decision.anchors[0][0] != "FIRST_FOCUS":
                        raise RuntimeError("unexpected initial anchor plan")
                    stock_fact = (by_stock[(key.entity_id, sources.trade_date)]
                                  if key.entity_type == "STOCK" else None)
                    input_hash = (stock_fact.input_digest if stock_fact else
                                  baskets_by_sector[key.entity_id].basket_digest)
                    cur.execute("""insert into workbench.focus_episode_anchors
                        (anchor_id,episode_id,anchor_type,trade_date,focus_run_id,
                         source_revision,reference_price,price_basis,quality_status,
                         source_fact_digest)
                        values (%s,%s,'FIRST_FOCUS',%s,%s,1,%s,%s,%s,%s)""",
                        (decision.anchors[0][1], episode, sources.trade_date, run_id,
                         stock_fact.close_price if stock_fact else None,
                         "TDX_NATIVE_AFFINE_QFQ" if stock_fact else "FROZEN_BASKET_NAV",
                         stock_fact.quality_status if stock_fact else "NO_BASE_PRICE",
                         input_hash))
                    cur.execute("""insert into workbench.focus_episode_observations
                        (episode_id,focus_run_id,trade_date,source_revision,
                         evaluation_mode,state_contract_id,source_membership_state,
                         membership_phase,validity_state,followup_state,
                         current_path_state,lifetime_path_tags,continuity_quality,
                         close_price,return_since_first,drawdown_from_peak,
                         adjustment_source_hash,quality_status,fact_digest,facts)
                        values (%s,%s,%s,1,'AS_RECORDED',%s,%s,%s,%s,%s,%s,%s,
                                'FIRST_DAY',%s,%s,%s,%s,%s,%s,%s)""",
                        (episode, run_id, sources.trade_date, STATE_CONTRACT,
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
                    written_observations += 1
                    if written_observations == inject_after_observations:
                        raise InjectedCoreFailure("FOCUS_CORE_INJECTED_AFTER_OBSERVATIONS")
                    evaluation_id = "focus-eval-" + digest({"episode": episode,
                        "day": sources.trade_date, "revision": 1,
                        "state": STATE_CONTRACT})[:32]
                    cur.execute("""insert into workbench.focus_state_evaluations
                        (state_evaluation_id,episode_id,trade_date,source_revision,
                         state_contract_id,parameter_set_id,evaluation_mode,
                         validity_state,current_path_state,quality_status,evidence_digest)
                        values (%s,%s,%s,1,%s,%s,'AS_RECORDED',%s,%s,%s,%s)""",
                        (evaluation_id, episode, sources.trade_date, STATE_CONTRACT,
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
                    cur.execute("""insert into workbench.focus_current_projection
                        (source_family,entity_type,entity_id,active_episode_id,
                         last_episode_id,latest_trade_date,latest_focus_run_id,
                         source_membership_state,membership_phase,validity_state,
                         followup_state,current_path_state,projection_digest)
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (key.source_family, key.entity_type, key.entity_id,
                         episode, episode, sources.trade_date, run_id,
                         observation.source_membership_state,
                         observation.membership_phase, observation.validity_state,
                         observation.followup_state, observation.current_path_state,
                         digest({"episode": episode,
                                 "observation": observation.fact_digest})))
                    if key.entity_type == "SECTOR":
                        insert_entry_basket(repo, episode_id=episode,
                                            focus_run_id=run_id,
                                            publication_id=sources.publication_id,
                                            basket=baskets_by_sector[key.entity_id])
                cur.execute("""update workbench.focus_runs
                               set core_publication_status='READY'
                               where focus_run_id=%s""", (run_id,))
                activate_core_head(repo, focus_run_id=run_id,
                                   trade_date=sources.trade_date, revision=1)
                if inspect_run_slot(repo, **identity) != "ALREADY_ACTIVATED":
                    raise RuntimeError("exact rerun identity not recognized")
                try:
                    inspect_run_slot(repo, **{**identity,
                                              "observation_input_digest": "0" * 64})
                except ValueError as exc:
                    if "immutable Focus run/revision conflict" not in str(exc):
                        raise
                else:
                    raise RuntimeError("changed input reused run/revision slot")
                # Deliberately discard the write-time projection and rebuild it
                # from immutable AS_RECORDED observations inside this transaction.
                cur.execute("delete from workbench.focus_current_projection")
                rebuild_current_projection(repo, focus_run_id=run_id)
                if not verify_current_projection(repo, focus_run_id=run_id):
                    raise RuntimeError("projection rebuild verification failed")
                inside = _counts(cur)
                delta = tuple(after - prior for after, prior in zip(inside, before))
                expected_delta = (
                    1, len(sources.rows), len(observations), len(observations),
                    len(observations), len(observations), len(observations),
                    len(observations),
                    sum(len(item.observation.evidence["path_predicates"])
                        for item in observations),
                    len(observations), 1, len(baskets))
                if delta != expected_delta:
                    raise RuntimeError("full core row count mismatch: " + str(delta))
            if commit:
                con.commit()
                committed = True
        except InjectedCoreFailure:
            injected = True
        finally:
            if not committed:
                con.rollback()
        with con.cursor() as cur:
            after = _counts(cur)
        if commit:
            if tuple(value - old for value, old in zip(after, before)) != delta:
                raise RuntimeError("committed core row counts differ from verified batch")
            if not verify_current_projection(repo, focus_run_id=run_id):
                raise RuntimeError("committed projection verification failed")
            if inspect_run_slot(repo, **identity) != "ALREADY_ACTIVATED":
                raise RuntimeError("committed run/head idempotency verification failed")
            con.rollback()
            print({"mode": "COMMITTED_REAL_FORWARD_INITIAL_RUN",
                   "focus_run_id": run_id, "trade_date": str(sources.trade_date),
                   "inserted": delta, "projection_rebuild_verified": True})
            return 0
        con.rollback()
        if after != before:
            raise RuntimeError("full core rollback left business rows")
    if inject_after_observations is not None and not injected:
        raise RuntimeError("requested failure injection did not fire")
    print({"mode": "INJECTED_FAILURE_ROLLBACK" if injected else "ROLLBACK_ONLY",
           "source_date": str(sources.trade_date),
           "closure_digest": closure.input_digest,
           "inserted_before_rollback": delta,
           "projection_rebuild_verified": not injected,
           "observations_before_failure": written_observations if injected else None,
           "post_rollback_counts": after, "unchanged": True})
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inject-after-observations", type=int)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--expected-trade-date")
    parser.add_argument("--expected-manifest-digest")
    args = parser.parse_args()
    raise SystemExit(main(
        inject_after_observations=args.inject_after_observations,
        commit=args.commit,
        expected_trade_date=(date.fromisoformat(args.expected_trade_date)
                             if args.expected_trade_date else None),
        expected_manifest_digest=args.expected_manifest_digest))
