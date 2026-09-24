"""Build the accepted-day Focus observation batch."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.basket_resolution import resolve_baskets
from src.focus_tracker.daily_manifest import build_daily_manifest
from src.focus_tracker.core_input_closure import (ObservationItem,
                                                  validate_core_input_closure)
from src.focus_tracker.daily_plan import build_day_plan
from src.focus_tracker.history_window import required_history_start
from src.focus_tracker.materialize import (read_full_master_calendar,
                                           read_verified_slice,
                                           stock_paths_from_slice)
from src.focus_tracker.member_strength import read_accepted_member_strength
from src.focus_tracker.observation import assemble_observation
from src.focus_tracker.path_fact_index import index_stock_path_facts
from src.focus_tracker.predicates import Tri, compile_v3_3_invalidation
from src.focus_tracker.predicate_requirements import plan_predicate_requirements
from src.focus_tracker.previous_reader import read_predecessor
from src.focus_tracker.source_reader import read_accepted_sources
from src.focus_tracker.tracking_context import (read_first_source_rows,
                                                resolve_tracking_contexts)
from src.focus_tracker.technical_facts import read_accepted_technical
from src.focus_tracker.v33_scanner_facts import bridge_scanner_facts
from src.focus_tracker.frozen_invalidation_facts import (derive_frozen_facts,
                                                        read_episode_fact_values)
from src.focus_tracker.sector_basket import baskets_from_accepted_publication
from src.focus_tracker.sector_path import frozen_sector_path
from src.focus_tracker.source_capabilities import require_runtime_fact_providers
from src.focus_tracker.v33_invalidation import evaluate_tracked_v33_invalidation
from src.focus_tracker.settlement import (due_outcome_episodes,
                                          due_outcome_keys,
                                          pending_followup_episodes,
                                          pending_followup_keys)
from src.workbench_db.postgres_repository import PostgresRepository


def build_focus_daily_batch(*, evaluation_basis="HISTORICAL_RECONSTRUCTED",
                           expected_trade_date: date | None = None):
    with PostgresRepository(dsn=_dsn()) as repo:
        with repo.connection.cursor() as cur:
            cur.execute("set transaction read only")
            if expected_trade_date is None:
                cur.execute("select max(trade_date) from workbench.publication_heads")
                trade_date = cur.fetchone()[0]
            else:
                trade_date = expected_trade_date
            cur.execute("""select sha256 from workbench_meta.artifact_catalog
                           where relative_path=%s and availability='AVAILABLE'
                           order by discovered_at desc limit 1""",
                        ("data/normalized/adjusted_daily.parquet",))
            artifact = cur.fetchone()
        if trade_date is None or artifact is None:
            raise RuntimeError("accepted source or normalized artifact missing")
        sources = read_accepted_sources(repo, trade_date)
        predecessor = read_predecessor(repo, trade_date)
        calendar = read_full_master_calendar(
            normalized_path=Path("data/normalized/adjusted_daily.parquet"),
            expected_sha256=str(artifact[0]), trade_date=trade_date)
        today_position = calendar.index(trade_date)
        if predecessor.trade_date is not None and (
                today_position < 1 or calendar[today_position - 1] != predecessor.trade_date):
            raise RuntimeError("FOCUS_PREDECESSOR_NOT_PREVIOUS_MASTER_SESSION")
        pending = pending_followup_keys(repo, as_of_trade_date=trade_date)
        due = due_outcome_keys(repo, calendar=calendar,
                               as_of_trade_date=trade_date)
        episode_refs = {(ref.key, ref.episode_id): ref for ref in (
            *pending_followup_episodes(repo, as_of_trade_date=trade_date),
            *due_outcome_episodes(repo, calendar=calendar,
                                  as_of_trade_date=trade_date))}
        plan = build_day_plan(sources=sources, previous=predecessor.previous,
                              pending_followup=pending, due_outcomes=due,
                              required_episodes=tuple(episode_refs.values()))
        sector_ids = {row.key.entity_id for row in sources.rows
                      if row.key.entity_type == "SECTOR"}
        contemporary = baskets_from_accepted_publication(repo, sources.publication_id,
                                                          sector_ids)
        resolved = resolve_baskets(
            repository=repo, plan=plan,
            contemporary={item.sector_id: item for item in contemporary})
        baskets_by_episode = resolved.entry_frozen_by_episode
        baskets = tuple(baskets_by_episode.values())
        sector_episode_ids = {item.episode_id for item in
                              (plan.episode_tracking or plan.decisions)
                              if item.key.entity_type == "SECTOR" and item.episode_id}
        if set(baskets_by_episode) != sector_episode_ids:
            raise ValueError("tracking sector episode basket set mismatch")
        strength = read_accepted_member_strength(
            repo, trade_date=trade_date, publication_id=sources.publication_id,
            domain="LOCAL_RECONSTRUCTED",
            baskets=baskets_by_episode)
        tracked_decisions = plan.episode_tracking or plan.decisions
        historical_episodes = {
            decision.episode_id for decision in tracked_decisions
            if decision.episode_id is not None and
            decision.phase not in {"NEW", "REENTERED", "MODEL_BASELINE"}}
        first_rows = read_first_source_rows(repo, episode_ids=historical_episodes)
        historical_frozen = read_episode_fact_values(repo, first_rows=first_rows)
        technical_error = None
        try:
            technical = read_accepted_technical(
                repo, publication_id=sources.publication_id, trade_date=trade_date,
                expected_normalized_sha256=str(artifact[0]))
        except ValueError as exc:
            technical = None
            technical_error = str(exc)
        repo.connection.rollback()
    contexts = resolve_tracking_contexts(plan=plan, sources=sources,
                                         first_source_rows=first_rows)
    invalidation_plans = {}
    tracked_decisions = plan.episode_tracking or plan.decisions
    for decision in tracked_decisions:
        key = decision.key
        if key.source_family != "V3_3_TODAY_CANDIDATE":
            continue
        identity = (key, decision.episode_id)
        context = contexts[identity]
        first_row = first_rows.get(context.episode_id, context.today_source_row)
        if first_row is None:
            raise ValueError("V3.3 episode first source unavailable")
        frozen = historical_frozen.get(context.episode_id)
        if frozen is None:
            frozen = {fact.key: fact.value for fact in derive_frozen_facts(first_row)}
        ast = compile_v3_3_invalidation(
            str(first_row.source_facts["primary_category"]), frozen)
        invalidation_plans[identity] = (frozen, ast, plan_predicate_requirements(ast))
    member_ids = {security for basket in baskets for security in basket.security_ids}
    stock_ids = {request.security_id for request in plan.stock_path_requests}
    minimum_date = required_history_start(
        trade_date=trade_date, calendar=calendar,
        stock_paths=plan.stock_path_requests,
        previous_sessions=max(1, *(item[2].required_sessions - 1
                                   for item in invalidation_plans.values())))
    previous_session = calendar[calendar.index(trade_date) - 1]
    normalized = read_verified_slice(
        normalized_path=Path("data/normalized/adjusted_daily.parquet"),
        expected_sha256=str(artifact[0]),
        minimum_date=minimum_date, trade_date=trade_date,
        security_ids=stock_ids | member_ids)
    facts = stock_paths_from_slice(normalized=normalized, trade_date=trade_date,
                                   requests=plan.stock_path_requests)
    by_stock = index_stock_path_facts(requests=plan.stock_path_requests, facts=facts)
    observations = []
    for decision in tracked_decisions:
        key = decision.key
        identity = (key, decision.episode_id)
        context = contexts[identity]
        if key.entity_type == "STOCK":
            stock_fact = by_stock[(key.entity_id, context.first_trade_date)]
            technical_fact = technical.facts.get(key.entity_id) if technical else None
            price_compatible = False
            if technical_fact and technical_fact.price_basis == "TDX_NATIVE_QFQ" and stock_fact.close_price:
                try:
                    price_compatible = (
                        Decimal(str(technical_fact.adjusted_close)).quantize(Decimal("0.01"))
                        == Decimal(stock_fact.close_price).quantize(Decimal("0.01")))
                except (InvalidOperation, TypeError, ValueError):
                    price_compatible = False
            predicate_facts = {
                "ma5": technical_fact.ma5 if price_compatible else None,
                "ma20": technical_fact.ma20 if price_compatible else None,
                "r5": technical_fact.ret5 if price_compatible else None,
                "technical_price_compatible": price_compatible,
                "technical_fact_digest": technical_fact.fact_digest if technical_fact else None,
                "technical_value_hash": technical.value_hash if technical else None,
                "technical_fact_status": "READY" if technical else "UNAVAILABLE",
                "technical_fact_reason": technical_error,
                "exited": decision.membership == "NONE",
            }
            invalidation = Tri.UNKNOWN
            if key.source_family == "V3_3_TODAY_CANDIDATE":
                frozen, ast, requirements = invalidation_plans[identity]
                first_row = first_rows.get(context.episode_id, context.today_source_row)
                if context.today_source_row is None:
                    predicate_facts["invalidation_unavailable_reason"] = (
                        "CURRENT_SCANNER_SOURCE_ROW_ABSENT")
                sessions = calendar[max(0, today_position - requirements.required_sessions + 1):
                                    today_position + 1]
                sessions = tuple(day for day in sessions
                                 if day >= context.first_trade_date)
                invalidation, invalidation_evidence, invalidation_meta = (
                    evaluate_tracked_v33_invalidation(
                        ast=ast, frozen=frozen, first_row=first_row,
                        today_source_row=context.today_source_row,
                        scanner_evidence=(context.source_facts.get("scanner_evidence")
                                          if context.today_source_row is not None else None),
                        security_id=key.entity_id, trade_date=trade_date,
                        first_trade_date=context.first_trade_date,
                        sessions=sessions,
                        required_fields=requirements.required_fields,
                        normalized=normalized))
                predicate_facts["invalidation_fact_digest"] = invalidation_meta["fact_digest"]
                predicate_facts["invalidation_provider_contract_id"] = invalidation_meta["contract_id"]
                predicate_facts["invalidation_provider_gaps"] = invalidation_meta["provider_gaps"]
                if invalidation == Tri.UNKNOWN and invalidation_meta["provider_gaps"]:
                    existing_reason = predicate_facts.get("invalidation_unavailable_reason")
                    predicate_facts["invalidation_unavailable_reason"] = sorted({
                        *([existing_reason] if existing_reason else []),
                        *invalidation_meta["provider_gaps"]})
                predicate_facts["structure_break"] = invalidation_meta["structure_break_v3"]
                predicate_facts["invalidation_requirements"] = {
                    "contract_id": requirements.contract_id,
                    "sessions": requirements.required_sessions,
                    "fields": sorted(requirements.required_fields),
                    "frozen_facts": sorted(requirements.required_frozen_facts)}
                predicate_facts["invalidation_evidence"] = invalidation_evidence
        else:
            stock_fact = None
            invalidation = Tri.UNKNOWN
            basket = baskets_by_episode[context.episode_id]
            sector_day = frozen_sector_path(
                basket=basket, sessions=[previous_session, trade_date],
                member_rows=normalized.by_security)[-1]
            one_day = sector_day.one_day
            sector_strength = strength[context.episode_id]
            predicate_facts = {
                "basket_digest": basket.basket_digest,
                "strength_fact_digest": sector_strength.fact_digest,
                "coverage_ready": one_day is not None and one_day.quality_status == "READY"
                                  and sector_strength.quality_status == "READY",
                "sret1": str(one_day.median_return) if one_day and one_day.median_return is not None else None,
                "swidth": str(sector_strength.width) if sector_strength.width is not None else None,
                "exited": decision.membership == "NONE",
            }
        observation = assemble_observation(
            decision=decision, source_contract_id=context.source_contract_id,
            stock_fact=stock_fact, predicate_facts=predicate_facts,
            invalidation=invalidation,
            pending_settlement=(decision.membership == "NONE" and
                                key in set(plan.pending_followup_keys)))
        require_runtime_fact_providers(
            key.source_family, context.source_contract_id,
            observation.evidence["predicate_facts"],
            invalidation_supplied="invalidation" in observation.evidence)
        observations.append(ObservationItem(key, observation))
    manifest, _ = build_daily_manifest(evaluation_basis=evaluation_basis,
                                       expected_trade_date=trade_date)
    closure = validate_core_input_closure(
        manifest=manifest, sources=sources, plan=plan,
        stock_facts=facts, observations=observations)
    return manifest, sources, plan, facts, tuple(observations), tuple(baskets), closure

