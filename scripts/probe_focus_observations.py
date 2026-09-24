"""Read-only accepted-day six-dimension Focus observation rehearsal."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.probe_focus_full_day_inputs import build_probe_manifest
from src.focus_tracker.core_input_closure import (ObservationItem,
                                                  validate_core_input_closure)
from src.focus_tracker.daily_plan import build_day_plan
from src.focus_tracker.materialize import (read_full_master_calendar,
                                           read_verified_slice,
                                           stock_paths_from_slice)
from src.focus_tracker.member_strength import read_accepted_member_strength
from src.focus_tracker.observation import assemble_observation
from src.focus_tracker.predicates import Tri, compile_v3_3_invalidation, evaluate
from src.focus_tracker.previous_reader import read_predecessor
from src.focus_tracker.source_reader import read_accepted_sources
from src.focus_tracker.technical_facts import read_accepted_technical
from src.focus_tracker.v33_scanner_facts import bridge_scanner_facts
from src.focus_tracker.sector_basket import baskets_from_accepted_publication
from src.focus_tracker.sector_path import frozen_sector_path
from src.focus_tracker.settlement import (due_outcome_keys,
                                          pending_followup_keys)
from src.workbench_db.postgres_repository import PostgresRepository


def build_observation_batch(*, evaluation_basis="HISTORICAL_RECONSTRUCTED",
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
        pending = pending_followup_keys(repo, as_of_trade_date=trade_date)
        due = due_outcome_keys(repo, calendar=calendar,
                               as_of_trade_date=trade_date)
        sector_ids = {row.key.entity_id for row in sources.rows
                      if row.key.entity_type == "SECTOR"}
        baskets = baskets_from_accepted_publication(repo, sources.publication_id,
                                                     sector_ids)
        strength = read_accepted_member_strength(
            repo, trade_date=trade_date, publication_id=sources.publication_id,
            domain="LOCAL_RECONSTRUCTED",
            baskets={item.sector_id: item for item in baskets})
        technical_error = None
        try:
            technical = read_accepted_technical(
                repo, publication_id=sources.publication_id, trade_date=trade_date,
                expected_normalized_sha256=str(artifact[0]))
        except ValueError as exc:
            technical = None
            technical_error = str(exc)
        repo.connection.rollback()
    plan = build_day_plan(sources=sources, previous=predecessor.previous,
                          pending_followup=pending, due_outcomes=due)
    member_ids = {security for basket in baskets for security in basket.security_ids}
    stock_ids = {row.key.entity_id for row in sources.rows
                 if row.key.entity_type == "STOCK"}
    normalized = read_verified_slice(
        normalized_path=Path("data/normalized/adjusted_daily.parquet"),
        expected_sha256=str(artifact[0]),
        minimum_date=trade_date - timedelta(days=14), trade_date=trade_date,
        security_ids=stock_ids | member_ids)
    facts = stock_paths_from_slice(normalized=normalized, trade_date=trade_date,
                                   requests=plan.stock_path_requests)
    by_stock = {(fact.security_id, fact.start_trade_date): fact for fact in facts}
    by_entity = {(decision.key.source_family, decision.key.entity_id): decision
                 for decision in plan.decisions}
    observations = []
    previous_sessions = [day for day in normalized.calendar if day < trade_date]
    if not previous_sessions:
        raise RuntimeError("previous master session unavailable")
    previous_session = previous_sessions[-1]
    basket_by_sector = {item.sector_id: item for item in baskets}
    for row in sources.rows:
        decision = by_entity[(row.key.source_family, row.key.entity_id)]
        if row.key.entity_type == "STOCK":
            stock_fact = by_stock[(row.key.entity_id, trade_date)]
            technical_fact = technical.facts.get(row.key.entity_id) if technical else None
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
            }
            invalidation = Tri.UNKNOWN
            if row.key.source_family == "V3_3_TODAY_CANDIDATE":
                bridge = bridge_scanner_facts(
                    evidence=row.source_facts["scanner_evidence"],
                    security_id=row.key.entity_id, trade_date=trade_date)
                predicate_facts["structure_break"] = bridge["structure_break_v3"]
                ast = compile_v3_3_invalidation(
                    str(row.source_facts["primary_category"]), {})
                invalidation, _ = evaluate(
                    ast, trade_date=trade_date, sessions=[trade_date],
                    facts_by_date={trade_date: {
                        "has_actual_bar": stock_fact.quality_status == "READY",
                        "close": stock_fact.close_price,
                        "structure_break_v3": bridge["structure_break_v3"]}},
                    frozen_signal={}, frozen_episode={})
        else:
            stock_fact = None
            invalidation = Tri.UNKNOWN
            basket = basket_by_sector[row.key.entity_id]
            sector_day = frozen_sector_path(
                basket=basket, sessions=[previous_session, trade_date],
                member_rows=normalized.by_security)[-1]
            one_day = sector_day.one_day
            sector_strength = strength[row.key.entity_id]
            predicate_facts = {
                "basket_digest": basket.basket_digest,
                "strength_fact_digest": sector_strength.fact_digest,
                "coverage_ready": one_day is not None and one_day.quality_status == "READY"
                                  and sector_strength.quality_status == "READY",
                "sret1": str(one_day.median_return) if one_day and one_day.median_return is not None else None,
                "swidth": str(sector_strength.width) if sector_strength.width is not None else None,
            }
        observation = assemble_observation(
            decision=decision, source_contract_id=row.source_contract_id,
            stock_fact=stock_fact, predicate_facts=predicate_facts,
            invalidation=invalidation)
        observations.append(ObservationItem(row.key, observation))
    manifest, _ = build_probe_manifest(evaluation_basis=evaluation_basis,
                                       expected_trade_date=trade_date)
    closure = validate_core_input_closure(
        manifest=manifest, sources=sources, plan=plan,
        stock_facts=facts, observations=observations)
    return manifest, sources, plan, facts, tuple(observations), tuple(baskets), closure


def main() -> int:
    manifest, sources, plan, facts, observations, baskets, closure = build_observation_batch()
    trade_date = sources.trade_date
    values = [item.observation for item in observations]
    print({"trade_date": str(trade_date), "evaluation_basis": "HISTORICAL_RECONSTRUCTED",
           "observations": len(values),
           "family": dict(Counter(item.evidence["key"]["family"] for item in values)),
           "validity": dict(Counter(item.validity_state for item in values)),
           "path": dict(Counter(item.current_path_state for item in values)),
           "followup": dict(Counter(item.followup_state for item in values)),
           "closure_digest": closure.input_digest,
           "writes": 0})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
