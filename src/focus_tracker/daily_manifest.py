"""Build the accepted-day Focus input manifest."""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.basket_resolution import resolve_baskets
from src.focus_tracker.contracts import digest
from src.focus_tracker.daily_plan import build_day_plan
from src.focus_tracker.dependency_lock import verify_dependency_lock
from src.focus_tracker.input_manifest import build_manifest, read_authority_bindings
from src.focus_tracker.history_window import required_history_start
from src.focus_tracker.materialize import (read_full_master_calendar,
                                           read_verified_slice, stock_paths_from_slice)
from src.focus_tracker.member_strength import read_accepted_member_strength
from src.focus_tracker.previous_reader import read_predecessor
from src.focus_tracker.sector_basket import baskets_from_accepted_publication
from src.focus_tracker.sector_path import frozen_sector_path
from src.focus_tracker.settlement import (due_outcome_episodes,
                                          due_outcome_keys,
                                          pending_followup_episodes,
                                          pending_followup_keys)
from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository


def build_daily_manifest(*, evaluation_basis="HISTORICAL_RECONSTRUCTED",
                         expected_trade_date: date | None = None):
    with PostgresRepository(dsn=_dsn()) as repo:
        with repo.connection.cursor() as cur:
            cur.execute("set transaction read only")
            if expected_trade_date is None:
                cur.execute("select max(trade_date) from workbench.publication_heads")
                trade_date = cur.fetchone()[0]
            else:
                trade_date = expected_trade_date
        accepted = read_accepted_sources(repo, trade_date)
        predecessor = read_predecessor(repo, trade_date)
        with repo.connection.cursor() as cur:
            cur.execute("""select sha256 from workbench_meta.artifact_catalog
                           where relative_path=%s and availability='AVAILABLE'
                           order by discovered_at desc limit 1""",
                        ("data/normalized/adjusted_daily.parquet",))
            artifact = cur.fetchone()
        if artifact is None:
            raise RuntimeError("NO_AVAILABLE_NORMALIZED_ARTIFACT")
        full_calendar = read_full_master_calendar(
            normalized_path=Path("data/normalized/adjusted_daily.parquet"),
            expected_sha256=str(artifact[0]), trade_date=trade_date)
        today_position = full_calendar.index(trade_date)
        if predecessor.trade_date is not None and (
                today_position < 1 or full_calendar[today_position - 1] != predecessor.trade_date):
            raise RuntimeError("FOCUS_PREDECESSOR_NOT_PREVIOUS_MASTER_SESSION")
        pending = pending_followup_keys(repo, as_of_trade_date=trade_date)
        due = due_outcome_keys(repo, calendar=full_calendar,
                               as_of_trade_date=trade_date)
        episode_refs = { (ref.key, ref.episode_id): ref for ref in (
            *pending_followup_episodes(repo, as_of_trade_date=trade_date),
            *due_outcome_episodes(repo, calendar=full_calendar,
                                  as_of_trade_date=trade_date)) }
        planned = build_day_plan(sources=accepted, previous=predecessor.previous,
                                 pending_followup=pending, due_outcomes=due,
                                 required_episodes=tuple(episode_refs.values()))
        sectors = {row.key.entity_id for row in accepted.rows
                   if row.key.entity_type == "SECTOR"}
        contemporary = baskets_from_accepted_publication(repo, accepted.publication_id, sectors)
        resolved = resolve_baskets(
            repository=repo, plan=planned,
            contemporary={item.sector_id: item for item in contemporary})
        baskets_by_episode = resolved.entry_frozen_by_episode
        baskets = tuple(baskets_by_episode.values())
        sector_episode_ids = {item.episode_id for item in
                              (planned.episode_tracking or planned.decisions)
                              if item.key.entity_type == "SECTOR" and item.episode_id}
        if set(baskets_by_episode) != sector_episode_ids:
            raise ValueError("tracking sector episode basket set mismatch")
        strength = read_accepted_member_strength(
            repo, trade_date=trade_date, publication_id=accepted.publication_id,
            domain="LOCAL_RECONSTRUCTED",
            baskets=baskets_by_episode)
        bindings = read_authority_bindings(repo, sources=accepted,
                                           strengths=strength)
        repo.connection.rollback()
    minimum_date = required_history_start(
        trade_date=trade_date, calendar=full_calendar,
        stock_paths=planned.stock_path_requests)
    stock_ids = {request.security_id for request in planned.stock_path_requests}
    member_ids = {sid for basket in baskets for sid in basket.security_ids}
    normalized = read_verified_slice(
        normalized_path=Path("data/normalized/adjusted_daily.parquet"),
        expected_sha256=str(artifact[0]),
        minimum_date=minimum_date,
        trade_date=trade_date,
        security_ids=stock_ids | member_ids)
    earlier = [day for day in normalized.calendar if day < trade_date]
    if not earlier:
        raise RuntimeError("PREVIOUS_MASTER_SESSION_UNAVAILABLE")
    previous = earlier[-1]
    facts = stock_paths_from_slice(
        normalized=normalized, trade_date=trade_date,
        requests=planned.stock_path_requests)
    sectors_one_day = [frozen_sector_path(
        basket=basket, sessions=[previous, trade_date],
        member_rows=normalized.by_security)[-1] for basket in baskets]
    focus_sources = sorted(Path("src/focus_tracker").glob("*.py"))
    implementation = digest(
        [(path.name, path.read_bytes().hex()) for path in focus_sources] +
        [("focus_core_release_gate_v1.json",
          Path("config/focus_core_release_gate_v1.json").read_bytes().hex())])
    dependency = verify_dependency_lock(Path("config/focus_dependency_lock_v1.json"))
    manifest = build_manifest(
        sources=accepted, plan=planned, bindings=bindings,
        calendar=full_calendar,
        calendar_artifact_sha256=normalized.artifact_sha256,
        normalized_sha256=normalized.artifact_sha256,
        stock_facts=facts,
        baskets=baskets_by_episode,
        strengths=strength,
        state_contract_id="FOCUS_PATH_STATE_V1",
        parameter_set_id="FOCUS_STOCK_PATH_PARAMS_V1_CANDIDATE+FOCUS_SECTOR_PATH_PARAMS_V1_CANDIDATE",
        implementation_digest=implementation,
        dependency_lock_hash=dependency,
        evaluation_basis=evaluation_basis,
        calendar_scope="MASTER_COMPLETE",
        dependency_lock_kind="VERSIONED_LOCK")
    summary = {"trade_date": str(trade_date), "previous_session": str(previous),
           "source_rows": len(accepted.rows), "source_stock_rows": sum(
               row.key.entity_type == "STOCK" for row in accepted.rows),
           "tracking_keys": len(planned.tracking_keys),
           "predecessor_focus_run_id": predecessor.focus_run_id,
           "publication_source_identity_kind": bindings.publication_source_identity_kind,
           "tracking_plan_digest": planned.plan_digest,
           "entry_frozen_baskets": len(resolved.entry_frozen_by_episode),
           "unique_stock_facts": len(facts), "shared_security_scan_count": len(stock_ids | member_ids),
           "stock_quality": dict(Counter(f.quality_status for f in facts)),
           "sector_quality": dict(Counter(day.one_day.quality_status for day in sectors_one_day)),
           "sector_strength_quality": dict(Counter(item.quality_status for item in strength.values())),
           "sector_width_min": str(min(item.width for item in strength.values()
                                        if item.width is not None)),
           "sector_coverage_min": str(min(day.one_day.coverage for day in sectors_one_day)),
           "input_set_digest": digest({"source": accepted.source_identity_digest,
                                        "artifact": normalized.artifact_sha256,
                                        "calendar": normalized.calendar,
                                        "stock_facts": [(f.security_id, f.input_digest) for f in facts],
                                        "sector_days": [(d.one_day.sector_id,
                                                         d.one_day.basket_digest,
                                                         d.one_day.coverage,
                                                         d.one_day.median_return)
                                                        for d in sectors_one_day],
                                        "member_strength": [(sector, item.fact_digest)
                                                            for sector, item in sorted(strength.items())]}),
           "manifest_digest": manifest.sha256,
           "manifest_release_gate_reasons": manifest.release_gate_reasons}
    return manifest, summary

