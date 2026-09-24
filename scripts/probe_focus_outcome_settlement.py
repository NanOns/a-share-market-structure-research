"""Rollback-only end-to-end Focus T+1 outcome settlement rehearsal."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pyarrow.dataset as ds
from psycopg.types.json import Jsonb

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.contracts import SOURCE_AUTHORITY_CONTRACT, digest
from src.focus_tracker.materialize import read_full_master_calendar, read_verified_slice
from src.focus_tracker.outcome_math import stock_outcome_path
from src.focus_tracker.outcome_math import sector_outcome_path
from src.focus_tracker.outcomes import classify_outcome
from src.focus_tracker.outcome_monitor import settlement_monitor_snapshot
from src.focus_tracker.price_path import reanchor_from_frozen_coefficients
from src.focus_tracker.sector_basket import SectorBasket
from src.focus_tracker.settlement import (DueAnchor, HORIZONS, OutcomeRecord,
                                          REQUIRED_ANCHORS, TargetInputSeal,
                                          build_outcome_record,
                                          _insert_followup_event,
                                          _write_followup_completion,
                                          due_anchor_plan,
                                          materialize_due_outcomes,
                                          pending_followup_keys,
                                          pending_settlement_tasks,
                                          persist_outcome_batch,
                                          read_target_data_audits,
                                          read_target_input_seals,
                                          record_settlement_failure)
from src.workbench_db.postgres_repository import PostgresRepository


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_PATH = ROOT / "data/normalized/adjusted_daily.parquet"


def _choose_two_session_security(anchor_date: date, target_date: date) -> str:
    dataset = ds.dataset(NORMALIZED_PATH, format="parquet")
    expr = ((ds.field("date") == anchor_date) | (ds.field("date") == target_date)) & \
        (ds.field("is_master_session") == True) & (ds.field("has_actual_bar") == True)
    rows = dataset.to_table(columns=["security_id", "date"], filter=expr).to_pylist()
    seen: dict[str, set[date]] = {}
    for row in rows:
        seen.setdefault(str(row["security_id"]), set()).add(row["date"])
    match = sorted(security for security, dates in seen.items()
                   if {anchor_date, target_date}.issubset(dates))
    if not match:
        raise RuntimeError("NO_SECURITY_WITH_TWO_ACTUAL_BARS")
    return match[0]


def _insert_run(cur, *, run_id: str, trade_date: date, publication_id: str,
                calendar_digest: str, identity_digest: str,
                activated: bool) -> None:
    marker = digest({"run_id": run_id, "trade_date": trade_date})
    cur.execute("""insert into workbench.focus_runs
        (focus_run_id,trade_date,revision,publication_id,source_authority_contract_id,
         source_family_set,family_capabilities,source_identity_digest,calendar_digest,
         observation_input_digest,state_contract_id,parameter_set_id,price_basis,
         dependency_lock_hash,evaluation_basis,core_publication_status,activated_at_utc)
        values (%s,%s,1,%s,%s,'[]'::jsonb,'{}'::jsonb,%s,%s,%s,
                'PROBE_STATE_V1','PROBE_PARAMS_V1','TDX_NATIVE_AFFINE_QFQ',%s,
                'HISTORICAL_RECONSTRUCTED','ACTIVATED',
                case when %s then now() else null end)""",
        (run_id, trade_date, publication_id, SOURCE_AUTHORITY_CONTRACT,
         identity_digest, calendar_digest, marker, marker, activated))


def run() -> dict[str, object]:
    probe = uuid4().hex
    with PostgresRepository(dsn=_dsn()) as repo:
        con = repo.connection
        if con is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with con.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select publication_id from workbench.publication_heads "
                        "order by trade_date desc limit 1")
            publication = cur.fetchone()
            cur.execute("select sha256 from workbench_meta.artifact_catalog "
                        "where relative_path=%s and availability='AVAILABLE' "
                        "order by discovered_at desc limit 1",
                        ("data/normalized/adjusted_daily.parquet",))
            artifact = cur.fetchone()
        con.rollback()
        if publication is None or artifact is None:
            raise RuntimeError("ACCEPTED_PUBLICATION_AND_NORMALIZED_ARTIFACT_REQUIRED")
        publication_id, artifact_sha = str(publication[0]), str(artifact[0])
        full_calendar = read_full_master_calendar(
            normalized_path=NORMALIZED_PATH, expected_sha256=artifact_sha,
            trade_date=date.fromisoformat("2026-09-22"))
        if len(full_calendar) < 2:
            raise RuntimeError("TWO_SESSIONS_REQUIRED")
        anchor_date, target_date = full_calendar[-2:]
        security_id = _choose_two_session_security(anchor_date, target_date)
        normalized = read_verified_slice(
            normalized_path=NORMALIZED_PATH, expected_sha256=artifact_sha,
            minimum_date=anchor_date, trade_date=target_date,
            security_ids={security_id})
        path = stock_outcome_path(
            normalized=normalized, security_id=security_id,
            calendar=full_calendar, anchor_date=anchor_date, horizon=1)
        if not path.path_complete:
            raise RuntimeError("SELECTED_SECURITY_PATH_NOT_COMPLETE")
        sector_basket = SectorBasket("PROBE_SECTOR", (security_id,),
                                     "MEMBERSHIP_SNAPSHOT", "probe:1",
                                     digest({"probe_basket": security_id}))
        sector_path = sector_outcome_path(
            normalized=normalized, basket=sector_basket,
            calendar=full_calendar, anchor_date=anchor_date, horizon=1)
        if (not sector_path.path_complete or sector_path.mfe is not None or
                sector_path.mae is not None):
            raise RuntimeError("SECTOR_CLOSE_NAV_CONTRACT_FAILED")
        base_state = dict(calendar=full_calendar, anchor_date=anchor_date,
                          horizon=1, as_of_date=target_date,
                          target_input_accepted=True, target_input_sealed=True,
                          anchor_actual_bar=True, path_complete=False,
                          target_data_state="INFERRED_GAP")
        unaudited_gap = classify_outcome(**base_state)
        audited_gap = classify_outcome(**base_state,
                                       gap_audit_digest=digest({"audit": "sealed-gap"}))
        if (unaudited_gap.status != "PENDING" or
                audited_gap.status != "DATA_GAP" or not audited_gap.terminal):
            raise RuntimeError("SEALED_GAP_AUDIT_GATE_FAILED")
        anchor_bar = reanchor_from_frozen_coefficients(
            sessions=[anchor_date], rows=normalized.by_security[security_id])
        if anchor_bar is None:
            raise RuntimeError("SELECTED_SECURITY_ANCHOR_BAR_NOT_ACTUAL")

        con.rollback()
        try:
            with con.cursor() as cur:
                cur.execute("select count(*) from workbench.focus_runs")
                if int(cur.fetchone()[0]):
                    raise RuntimeError("ROLLBACK_PROBE_REQUIRES_EMPTY_FOCUS_RUNS")
                cur.execute("select count(*) from workbench.focus_outcome_settlement_batches")
                if int(cur.fetchone()[0]):
                    raise RuntimeError("ROLLBACK_PROBE_REQUIRES_EMPTY_SETTLEMENT_BATCHES")
                identity = digest({"probe": probe, "publication_id": publication_id})
                calendar_digest = digest(list(full_calendar))
                first_run = f"focus-outcome-probe-{probe}-first"
                active_run = f"focus-outcome-probe-{probe}-asof"
                _insert_run(cur, run_id=first_run, trade_date=anchor_date,
                            publication_id=publication_id,
                            calendar_digest=calendar_digest,
                            identity_digest=identity, activated=True)
                _insert_run(cur, run_id=active_run, trade_date=target_date,
                            publication_id=publication_id,
                            calendar_digest=calendar_digest,
                            identity_digest=identity, activated=True)
                episode_id = f"focus-outcome-episode-{probe}"
                anchor_id = f"focus-outcome-anchor-{probe}"
                cur.execute("""insert into workbench.focus_episodes
                    (episode_id,source_family,entity_type,entity_id,
                     selection_contract_family,first_trade_date,first_focus_run_id)
                    values (%s,'V3_SHORTLIST_STOCK','STOCK',%s,'V3_SHORTLIST',%s,%s)""",
                    (episode_id, security_id, anchor_date, first_run))
                cur.execute("""insert into workbench.focus_episode_anchors
                    (anchor_id,episode_id,anchor_type,trade_date,focus_run_id,source_revision,
                     reference_price,price_basis,quality_status,source_fact_digest)
                    values (%s,%s,'FIRST_FOCUS',%s,%s,1,%s,'TDX_NATIVE_AFFINE_QFQ','READY',%s)""",
                    (anchor_id, episode_id, anchor_date, first_run,
                     anchor_bar[0].close,
                     path.input_digest))
                cur.execute("""insert into workbench.focus_episode_observations
                    (episode_id,focus_run_id,trade_date,source_revision,evaluation_mode,
                     state_contract_id,source_membership_state,membership_phase,validity_state,
                     followup_state,current_path_state,lifetime_path_tags,continuity_quality,
                     quality_status,fact_digest,facts)
                    values (%s,%s,%s,1,'AS_RECORDED','FOCUS_PATH_STATE_V1','NONE','POST_EXIT',
                            'UNKNOWN','POST_EXIT','DATA_UNAVAILABLE','[]'::jsonb,'FIRST_DAY',
                            'DATA_UNAVAILABLE',%s,'{}'::jsonb)""",
                    (episode_id, active_run, target_date, digest({"probe": probe})))
                cur.execute("""insert into workbench.focus_trade_date_heads
                    (trade_date,source_authority_contract_id,accepted_focus_run_id,
                     accepted_revision,predecessor_focus_run_id,lineage_state,activated_at_utc)
                    values (%s,%s,%s,1,%s,'VALID',now())""",
                    (target_date, SOURCE_AUTHORITY_CONTRACT, active_run, first_run))

            due = DueAnchor(anchor_id, episode_id, "V3_SHORTLIST_STOCK", "V3_SHORTLIST",
                            "STOCK", security_id, "FIRST_FOCUS", anchor_date, 1,
                            target_date, "TDX_NATIVE_AFFINE_QFQ", None,
                            path.input_digest, "HISTORICAL_RECONSTRUCTED", None, None,
                            None)
            seal_digest = digest({"accepted_publication": publication_id,
                                  "target_date": target_date,
                                  "normalized_artifact_sha256": artifact_sha})
            seal = TargetInputSeal(target_date, True, True,
                                   digest({"publication_id": publication_id}), seal_digest)
            metrics = {"forward_return": path.forward_return, "mfe": path.mfe,
                       "mae": path.mae, "mdd": path.mdd}
            evidence = {"normalized_artifact_sha256": artifact_sha,
                        "target_source_identity_digest": seal.source_identity_digest,
                        "target_seal_digest": seal.seal_digest,
                        "path_input_digest": path.input_digest,
                        "target_trade_date": target_date.isoformat()}
            record = build_outcome_record(
                due=due, calendar=full_calendar, as_of_date=target_date,
                target_input_accepted=seal.accepted,
                target_input_sealed=seal.sealed,
                anchor_actual_bar=path.anchor_actual_bar,
                target_data_state=path.target_data_state,
                path_complete=path.path_complete,
                input_digest=path.input_digest, path_metrics=metrics,
                evidence=evidence)
            first = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=(record,))
            repeated = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=(record,))

            revised_plan = due_anchor_plan(
                repo, calendar=full_calendar, as_of_date=target_date)
            if len(revised_plan) != 1 or not revised_plan[0].source_revised:
                raise RuntimeError("accepted target source revision was not replanned")
            target_seals = read_target_input_seals(
                repo, target_dates={target_date},
                normalized_artifact_sha256=artifact_sha,
                evaluation_basis="HISTORICAL_RECONSTRUCTED")
            target_audits = read_target_data_audits(
                repo, due_anchors=revised_plan, target_seals=target_seals,
                normalized_artifact_sha256=artifact_sha)
            automatic_revision = materialize_due_outcomes(
                repo, calendar=full_calendar, as_of_trade_date=target_date,
                normalized=normalized, target_seals=target_seals,
                baskets_by_episode={}, target_audits=target_audits)
            if (len(automatic_revision) != 1 or
                    automatic_revision[0].evidence.get("revision_reason") !=
                    "ACCEPTED_TARGET_INPUT_REVISED"):
                raise RuntimeError("automatic source revision outcome was not explained")
            automatic_revision_batch = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=automatic_revision)

            revised_pending = build_outcome_record(
                due=due, calendar=full_calendar, as_of_date=target_date,
                target_input_accepted=True, target_input_sealed=True,
                anchor_actual_bar=True, target_data_state="MISSING_DATA",
                path_complete=False,
                input_digest=digest({"probe_revision": 2, "path": path.input_digest}),
                path_metrics=None,
                evidence={**evidence, "target_source_identity_digest":
                          digest({"probe_target_source_revision": 2})})
            second = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=(revised_pending,),
                force_revisions={(anchor_id, 1)})

            revised_observed = build_outcome_record(
                due=due, calendar=full_calendar, as_of_date=target_date,
                target_input_accepted=True, target_input_sealed=True,
                anchor_actual_bar=True, target_data_state="BAR",
                path_complete=True,
                input_digest=digest({"probe_revision": 3, "path": path.input_digest}),
                path_metrics=metrics,
                evidence={**evidence, "target_source_identity_digest":
                          automatic_revision[0].evidence.get(
                              "target_source_identity_digest")})
            third = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=(revised_observed,))
            with con.cursor() as cur:
                cur.execute("select accepted_target_revision from workbench.focus_outcome_heads "
                            "where anchor_id=%s and horizon=1", (anchor_id,))
                revision = cur.fetchone()
                cur.execute("select target_revision,status from workbench.focus_episode_outcomes "
                            "where anchor_id=%s and horizon=1 order by target_revision", (anchor_id,))
                revisions = cur.fetchall()
                cur.execute("select status,attempt_count from workbench.focus_outcome_settlement_tasks "
                            "where focus_run_id=%s and as_of_trade_date=%s",
                            (active_run, target_date))
                task = cur.fetchone()
                outcome_count = len(revisions)
            if (revision != (4,) or revisions != [(1, "OBSERVED"), (2, "OBSERVED"),
                                                   (3, "PENDING"), (4, "OBSERVED")] or
                    outcome_count != 4 or not repeated.get("idempotent") or
                    task != ("COMPLETE", 2)):
                raise RuntimeError("outcome head/idempotency verification failed")

            _insert_followup_event(
                repo, episode_id=episode_id, event_type="FOLLOW_UP_COMPLETED",
                event_trade_date=target_date, focus_run_id=active_run,
                settlement_batch_id=third["settlement_batch_id"],
                evidence={"probe": "all-required-outcomes-terminal"},
                reason_codes=("ALL_REQUIRED_ANCHORS_TERMINAL",))
            completed_keys = pending_followup_keys(repo, as_of_trade_date=target_date)
            if any(key.entity_id == security_id for key in completed_keys):
                raise RuntimeError("completed follow-up remained in daily union")
            _insert_followup_event(
                repo, episode_id=episode_id, event_type="SETTLEMENT_REOPENED",
                event_trade_date=target_date, focus_run_id=active_run,
                settlement_batch_id=first["settlement_batch_id"],
                evidence={"probe": "accepted-historical-revision"},
                reason_codes=("ACCEPTED_OUTCOME_REVISION",))
            reopened_keys = pending_followup_keys(repo, as_of_trade_date=target_date)
            if not any(key.entity_id == security_id for key in reopened_keys):
                raise RuntimeError("reopened follow-up missing from daily union")

            followup_anchor_date = full_calendar[-21]
            followup_start_run = f"focus-outcome-probe-{probe}-followup-start"
            followup_episode = f"focus-outcome-probe-{probe}-followup-episode"
            followup_entity = f"PROBE_FOLLOWUP_{probe}"
            with con.cursor() as cur:
                _insert_run(cur=cur, run_id=followup_start_run,
                            trade_date=followup_anchor_date,
                            publication_id=publication_id,
                            calendar_digest=digest(list(full_calendar)),
                            identity_digest=digest({"probe": probe, "followup": True}),
                            activated=True)
                cur.execute("insert into workbench.focus_episodes "
                            "(episode_id,source_family,entity_type,entity_id,"
                            "selection_contract_family,first_trade_date,first_focus_run_id) "
                            "values (%s,'V3_SHORTLIST_STOCK','STOCK',%s,'V3_SHORTLIST',%s,%s)",
                            (followup_episode, followup_entity, followup_anchor_date,
                             followup_start_run))
                followup_anchor_ids = {}
                for anchor_type in sorted(REQUIRED_ANCHORS):
                    synthetic_anchor_id = f"{followup_episode}-{anchor_type.lower()}"
                    followup_anchor_ids[anchor_type] = synthetic_anchor_id
                    cur.execute("insert into workbench.focus_episode_anchors "
                                "(anchor_id,episode_id,anchor_type,trade_date,focus_run_id,"
                                "source_revision,reference_price,price_basis,quality_status,"
                                "source_fact_digest) values (%s,%s,%s,%s,%s,1,100,"
                                "'TDX_NATIVE_AFFINE_QFQ','READY',%s)",
                                (synthetic_anchor_id, followup_episode, anchor_type,
                                 followup_anchor_date, followup_start_run,
                                 digest({"probe_anchor": synthetic_anchor_id})))
                cur.execute("insert into workbench.focus_episode_observations "
                            "(episode_id,focus_run_id,trade_date,source_revision,evaluation_mode,"
                            "state_contract_id,source_membership_state,membership_phase,"
                            "validity_state,followup_state,current_path_state,lifetime_path_tags,"
                            "continuity_quality,quality_status,fact_digest,facts) "
                            "values (%s,%s,%s,1,'AS_RECORDED','FOCUS_PATH_STATE_V1','NONE',"
                            "'POST_EXIT','UNKNOWN','POST_EXIT','DATA_UNAVAILABLE','[]'::jsonb,"
                            "'FIRST_DAY','DATA_UNAVAILABLE',%s,'{}'::jsonb)",
                            (followup_episode, active_run, target_date,
                             digest({"probe_followup_exit": followup_episode})))

            followup_due = due_anchor_plan(
                repo, calendar=full_calendar, as_of_date=target_date)
            followup_due = tuple(item for item in followup_due
                                 if item.episode_id == followup_episode)
            if len(followup_due) != len(REQUIRED_ANCHORS) * len(HORIZONS):
                raise RuntimeError("follow-up probe did not create the full due anchor grid")
            followup_target_dates = {item.target_date for item in followup_due}
            followup_seals = read_target_input_seals(
                repo, target_dates=followup_target_dates,
                normalized_artifact_sha256=artifact_sha,
                evaluation_basis="HISTORICAL_RECONSTRUCTED")

            def synthetic_outcome(item, *, status: str, revision_marker: str) -> OutcomeRecord:
                seal = followup_seals.get(item.target_date)
                source_digest = (seal.source_identity_digest if seal else
                                 digest({"probe_target_date": item.target_date}))
                observed = status == "OBSERVED"
                evidence = {"normalized_artifact_sha256": artifact_sha,
                            "target_trade_date": item.target_date.isoformat(),
                            "target_source_identity_digest": source_digest,
                            "target_input_accepted": True,
                            "target_input_sealed": True,
                            "target_data_state": "BAR" if observed else "MISSING_DATA",
                            "path_complete": observed,
                            "input_digest": digest({"probe": revision_marker,
                                                    "anchor": item.anchor_id,
                                                    "horizon": item.horizon})}
                return OutcomeRecord(
                    item.anchor_id, item.horizon, item.target_date, status,
                    "HISTORICAL_RECONSTRUCTED",
                    Decimal("0") if observed else None,
                    Decimal("0") if observed else None,
                    Decimal("0") if observed else None,
                    Decimal("0") if observed else None,
                    digest({"probe_outcome": revision_marker,
                            "anchor": item.anchor_id, "horizon": item.horizon}),
                    ("ROLLBACK_LIFECYCLE_PROBE",), evidence)

            initial_followup_rows = tuple(
                synthetic_outcome(item, status="OBSERVED", revision_marker="complete-r1")
                for item in followup_due)
            completion_batch = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=initial_followup_rows)
            auto_completed_keys = pending_followup_keys(
                repo, as_of_trade_date=target_date)
            if any(key.entity_id == followup_entity for key in auto_completed_keys):
                raise RuntimeError("all-terminal follow-up was not auto-completed")
            monitor_complete = settlement_monitor_snapshot(
                repo, calendar=full_calendar, as_of_trade_date=target_date)
            if any(item["episode_id"] == followup_episode
                   for item in monitor_complete["details"]):
                raise RuntimeError("monitor reported terminal follow-up as open")

            reopen_due = next(item for item in followup_due
                              if item.anchor_type == "FIRST_FOCUS" and item.horizon == 1)
            reopened_outcome = synthetic_outcome(
                reopen_due, status="PENDING", revision_marker="reopen-r2")
            reopen_batch = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=(reopened_outcome,),
                force_revisions={(reopen_due.anchor_id, reopen_due.horizon)})
            after_reopen_keys = pending_followup_keys(
                repo, as_of_trade_date=target_date)
            if not any(key.entity_id == followup_entity for key in after_reopen_keys):
                raise RuntimeError("outcome writer did not reopen completed follow-up")
            monitor_reopened = settlement_monitor_snapshot(
                repo, calendar=full_calendar, as_of_trade_date=target_date)
            if (monitor_reopened["due_open_count"] != 1 or
                    monitor_reopened["overdue_count"] != 1 or
                    monitor_reopened["status_counts"].get("PENDING") != 1):
                raise RuntimeError("overdue monitor missed reopened pending outcome")

            completed_again = synthetic_outcome(
                reopen_due, status="OBSERVED", revision_marker="complete-r3")
            final_batch = persist_outcome_batch(
                repo, focus_run_id=active_run, as_of_trade_date=target_date,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                normalized_artifact_sha256=artifact_sha,
                calendar=full_calendar, outcomes=(completed_again,))
            completed_again_keys = pending_followup_keys(
                repo, as_of_trade_date=target_date)
            with con.cursor() as cur:
                cur.execute("select event_type from workbench.focus_episode_followup_events "
                            "where episode_id=%s order by created_at_utc,event_id",
                            (followup_episode,))
                followup_events = [row[0] for row in cur.fetchall()]
            if (any(key.entity_id == followup_entity for key in completed_again_keys) or
                    followup_events != ["FOLLOW_UP_COMPLETED", "SETTLEMENT_REOPENED",
                                        "FOLLOW_UP_COMPLETED"]):
                raise RuntimeError("follow-up complete/reopen/complete event chain failed")
            monitor_final = settlement_monitor_snapshot(
                repo, calendar=full_calendar, as_of_trade_date=target_date)
            if any(item["episode_id"] == followup_episode
                   for item in monitor_final["details"]):
                raise RuntimeError("monitor retained completed follow-up outcome")

            record_settlement_failure(repo, focus_run_id=active_run,
                                      as_of_trade_date=target_date,
                                      error_code="PROBE_RETRY_FIRST")
            with con.cursor() as cur:
                cur.execute("select attempt_count,extract(epoch from "
                            "(next_retry_at_utc-clock_timestamp()))/60 "
                            "from workbench.focus_outcome_settlement_tasks "
                            "where focus_run_id=%s and as_of_trade_date=%s",
                            (active_run, target_date))
                first_retry = cur.fetchone()
            if (first_retry is None or first_retry[0] != 1 or
                    not 14.8 <= float(first_retry[1]) <= 15.1 or
                    pending_settlement_tasks(repo)):
                raise RuntimeError("first retry delay or backoff gate failed")
            record_settlement_failure(repo, focus_run_id=active_run,
                                      as_of_trade_date=target_date,
                                      error_code="PROBE_RETRY_SECOND")
            with con.cursor() as cur:
                cur.execute("select attempt_count,extract(epoch from "
                            "(next_retry_at_utc-clock_timestamp()))/60 "
                            "from workbench.focus_outcome_settlement_tasks "
                            "where focus_run_id=%s and as_of_trade_date=%s",
                            (active_run, target_date))
                second_retry = cur.fetchone()
                cur.execute("update workbench.focus_outcome_settlement_tasks "
                            "set next_retry_at_utc=clock_timestamp()-interval '1 second' "
                            "where focus_run_id=%s and as_of_trade_date=%s",
                            (active_run, target_date))
            ready_retries = pending_settlement_tasks(repo)
            if (second_retry is None or second_retry[0] != 2 or
                    not 29.8 <= float(second_retry[1]) <= 30.1 or
                    len(ready_retries) != 1 or
                    ready_retries[0]["focus_run_id"] != active_run):
                raise RuntimeError(f"exponential retry schedule/queue failed: "
                                   f"second={second_retry!r} retries={ready_retries!r}")
            con.rollback()
        except Exception:
            con.rollback()
            raise
    return {"mode": "ROLLBACK_ONLY", "anchor_date": str(anchor_date),
            "target_date": str(target_date), "horizon": 1,
            "security_id": security_id, "path_status": path.quality_status,
            "sector_path_status": sector_path.quality_status,
            "sector_mfe_mae": (sector_path.mfe, sector_path.mae),
            "gap_without_audit": unaudited_gap.status,
            "gap_with_audit": audited_gap.status,
            "first_batch": first, "idempotent_repeat": repeated.get("idempotent"),
            "revision_history": [(rev, status) for rev, status in revisions],
            "latest_batch": third, "head_revision_before_rollback": 4,
            "outcomes_before_rollback": outcome_count,
            "retry_backoff_minutes": (15, 30), "retry_queue_release": True,
            "automatic_source_revision_replanned": True,
            "followup_complete_then_reopened": True,
            "followup_auto_complete_reopen_complete": True,
            "overdue_monitor_tracks_reopen": True,
            "persisted_changes": 0}


if __name__ == "__main__":
    print(run())
