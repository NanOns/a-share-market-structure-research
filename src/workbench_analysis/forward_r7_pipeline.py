"""Accepted-Head ingestion, historical reconstruction and horizon settlement."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from .forward_r7 import (build_daily_universe, load_definitions, make_observation_id, canonical_bytes,
                         scheduled_sessions, summarize_universe, compute_nominal_settlement)
from .market_source_acquisition import official_sessions
from .r43_owner_replay import checked
from workbench_db.forward_r7_store import ForwardR7Store

LOG = logging.getLogger("v4.forward.r7")
SHANGHAI = ZoneInfo("Asia/Shanghai")


def _document(root: Path, binding: dict):
    path = checked(root, binding)
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        return [json.loads(line) for line in gzip.decompress(raw).splitlines() if line.strip()]
    return json.loads(raw)


def _bindings(head: dict, day: str):
    owners = head.get("owners", {}).get(day, {})
    required = ("raw", "core", "sector")
    if any(not owners.get(k) for k in required):
        raise ValueError("FORWARD_R7_ACCEPTED_SOURCE_OWNER_MISSING")
    result={k:owners[k] for k in required}
    if owners.get("lifecycle"):result["lifecycle"]=owners["lifecycle"]
    membership=owners.get("membership") or owners.get("membership_snapshot")
    if membership:result["membership"]=membership
    return result


def _head(root: Path):
    path = root / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
    head = json.loads(path.read_bytes())
    if head.get("contract_id") != "V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1":
        raise ValueError("FORWARD_R7_ACCEPTED_HEAD_CONTRACT_REQUIRED")
    return head


def _session_pair(sessions: list[str], day: str):
    index = sessions.index(day)
    return sessions[index - 1] if index else None


def accepted_prices_with_status(raw_rows: list[dict], lifecycle: dict | None, *, source_hash: str | None = None):
    """Join quote rows to accepted security-level facts without inventing quotes."""
    prices={row["security_id"]:dict(row,source_hash=row.get("source_hash") or source_hash)
            for row in raw_rows if row.get("security_id")}
    if not isinstance(lifecycle,dict):return prices
    for fact in lifecycle.get("source_rows",lifecycle.get("rows",[])):
        sid=fact.get("security_id");status=fact.get("status")
        if not sid or status not in ("NO_QUOTE","SUSPENDED"):continue
        row=prices.setdefault(sid,{})
        row["source_status"]=status
        row["source_hash"]=row.get("source_hash") or source_hash
    return prices


def reconstruct_history(root: str | Path, *, store: ForwardR7Store | None = None,
                        dates: list[str] | None = None):
    """Create Lane H from real accepted daily Owners, never from Focus/Radar."""
    root = Path(root).resolve()
    now = datetime.now(timezone.utc)
    head = _head(root)
    sessions = official_sessions(root)
    accepted = head.get("published_sessions", [])
    targets = dates or accepted
    if any(day not in accepted for day in targets):
        raise ValueError("FORWARD_R7_RETROSPECTIVE_DATE_NOT_ACCEPTED")
    all_by_day = {}
    for day in accepted:
        refs = _bindings(head, day)
        all_by_day[day] = {
            "raw": _document(root, refs["raw"]),
            "core": _document(root, refs["core"]),
            "sector": _document(root, refs["sector"]),
            "lifecycle": _document(root, refs["lifecycle"]) if refs.get("lifecycle") else None,
            "bindings": refs,
        }
    result = []
    prices_by_date = {}
    for day, bundle in all_by_day.items():
        prices_by_date[day] = accepted_prices_with_status(bundle["raw"],bundle.get("lifecycle"),
            source_hash=bundle["bindings"].get("lifecycle",{}).get("sha256"))
    for day in targets:
        prior = _session_pair(sessions, day)
        prior_bundle = all_by_day.get(prior) if prior else None
        captured = now.isoformat()
        rows = build_daily_universe(
            trade_date=day, stock_rows=all_by_day[day]["core"],
            raw_rows=all_by_day[day]["raw"], sector_rows=all_by_day[day]["sector"],
            prior_stock_rows=prior_bundle["core"] if prior_bundle else None,
            prior_raw_rows=prior_bundle["raw"] if prior_bundle else None,
            prior_sector_rows=prior_bundle["sector"] if prior_bundle else None,
            bindings=all_by_day[day]["bindings"], captured_at=captured,
            lane="RETROSPECTIVE_RESEARCH", membership_basis="MEMBERSHIP_RETRO")
        for row in rows:
            row["id"] = make_observation_id(row)
        schedules = build_schedules(rows, day, sessions, prices_by_date, captured)
        result.append(dict(trade_date=day, rows=rows, captured_at=captured,
                           source_hashes={k:v["sha256"] for k,v in all_by_day[day]["bindings"].items()},
                           aggregate=summarize_universe(rows),settlement_schedule=schedules))
    if store is not None:
        definitions, definition_sha = load_definitions(root)
        store.verify_existing_storage()
        store.register_definitions(definitions, definition_sha)
        from .fep_r7_read import read_r7_fep
        fep_projection = read_r7_fep(root)
        for projection in fep_projection.get("historical_baselines", []):
            store.publish_fep_projection(dict(projection,scope=fep_projection["scope"],
                asof=fep_projection["asof"],source_hashes={"catalog":fep_projection["source"]["sha256"],
                                                            "artifact":projection["source"]["sha256"]}))
        for projection in fep_projection.get("diagnostics", []):
            store.publish_fep_projection(dict(projection,scope=fep_projection["scope"],
                asof=fep_projection["asof"],source_hashes={"catalog":fep_projection["source"]["sha256"]}))
        for day_pack in result:
            run_id = hashlib.sha256((day_pack["trade_date"] + day_pack["captured_at"] + "R7-HISTORY").encode()).hexdigest()
            store.publish_day(trade_date=day_pack["trade_date"], rows=day_pack["rows"],
                              lane="RETROSPECTIVE_RESEARCH", run_id=run_id,
                              settlement_rows=day_pack["settlement_schedule"],
                              source_run={"contract_id":"V4_FORWARD_PIPELINE_R7_R1",
                                          "source_hashes":day_pack["source_hashes"],
                                          "aggregate":day_pack["aggregate"],
                                          "history_basis":"ACCEPTED_HEAD_OWNER_RECONSTRUCTION"})
            day_pack["publication"] = "PUBLISHED"
    return dict(status="READY", lane="RETROSPECTIVE_RESEARCH", dates=result,
                accepted_trade_date=head["accepted_trade_date"],
                source_contract=head["contract_id"], calendar_source="ACCEPTED_OFFICIAL_SESSION_CALENDAR")


def build_schedules(rows: list[dict], trade_date: str, sessions: list[str],
                    prices_by_date: dict, settled_at: str, *, accepted_source_dates=None):
    due_dates = scheduled_sessions(trade_date, sessions)
    output = []
    now = datetime.fromisoformat(settled_at)
    today = now.astimezone(SHANGHAI).date().isoformat()
    accepted_dates = set(accepted_source_dates if accepted_source_dates is not None else prices_by_date)
    for row in rows:
        if row["entity_type"] != "STOCK" or row["status"] != "MATCH":
            continue
        observation_id = make_observation_id(row)
        for horizon, due_date in due_dates.items():
            if due_date is None:
                output.append(dict(observation_id=observation_id,horizon_sessions=horizon,
                                   due_date=None,schedule_status="PENDING_FUTURE_SESSION",reason="OFFICIAL_CALENDAR_HORIZON_NOT_YET_PUBLISHED"))
                continue
            if due_date > today:
                output.append(dict(observation_id=observation_id,horizon_sessions=horizon,
                                   due_date=due_date,schedule_status="PENDING_FUTURE_SESSION",reason="FUTURE_OFFICIAL_SESSION"))
                continue
            if due_date not in accepted_dates:
                outcome = dict(status="DUE_SOURCE_NOT_ACCEPTED",reason="DUE_SESSION_NOT_IN_ACCEPTED_HEAD",due_date=due_date)
            else:
                outcome = compute_nominal_settlement(observation=row,due_date=due_date,
                    prices_by_date=prices_by_date,settlement_at=settled_at,due_source_accepted=True)
            schedule_status = outcome["status"] if outcome["status"] in ("SETTLED","NO_QUOTE","SUSPENDED","DUE_SOURCE_NOT_ACCEPTED") else "SOURCE_GAP"
            output.append(dict(observation_id=observation_id,horizon_sessions=horizon,due_date=due_date,
                               schedule_status=schedule_status,reason=outcome.get("reason"),settlement=outcome))
    return output


def _daily_job_snapshot(root: Path):
    """Read the native daily scheduler state without initializing or mutating it."""
    try:
        from workbench_db.v4_native import connection, workspace_schema
        schema = workspace_schema(root, "jobs")
        with connection(schema, read_only=True) as pg:
            policy = pg.execute("SELECT enabled,revision,updated_at FROM scheduler_policy WHERE id=1").fetchone()
            job = pg.execute("SELECT job_id,trigger,mode,through_date,status,created_at,finished_at,error "
                             "FROM update_jobs ORDER BY created_at DESC LIMIT 1").fetchone()
            days = (pg.execute("SELECT trade_date,state,attempt_count,next_retry_at,source_checks "
                               "FROM update_job_days WHERE job_id=%s ORDER BY trade_date",
                               (job[0],)).fetchall() if job else [])
        normalized_days = []
        for trade_date, state, attempts, retry_at, checks in days:
            if isinstance(checks, str):
                try: checks = json.loads(checks)
                except ValueError: checks = {}
            normalized_days.append(dict(trade_date=trade_date.isoformat() if hasattr(trade_date, "isoformat") else str(trade_date),
                state=state, attempt_count=attempts, next_retry_at=retry_at.isoformat() if hasattr(retry_at, "isoformat") else retry_at,
                source_checks=checks if isinstance(checks, dict) else {}))
        return dict(available=True, auto_enabled=bool(policy[0]) if policy else None,
            settings_revision=policy[1] if policy else None,
            settings_updated_at=policy[2].isoformat() if policy and hasattr(policy[2], "isoformat") else None,
            last_job=(dict(job_id=job[0], trigger=job[1], mode=job[2], through_date=job[3].isoformat() if hasattr(job[3], "isoformat") else str(job[3]),
                status=job[4], created_at=job[5].isoformat() if hasattr(job[5], "isoformat") else str(job[5]),
                finished_at=job[6].isoformat() if job[6] and hasattr(job[6], "isoformat") else job[6], error=job[7], days=normalized_days) if job else None))
    except Exception as exc:
        return dict(available=False, error_code=type(exc).__name__)


def next_capture_plan(root: str | Path, *, now: datetime | None = None):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    shanghai = now.astimezone(SHANGHAI)
    sessions = sorted(set(official_sessions(root)))
    head = _head(root)
    daily_job_state = _daily_job_snapshot(root)
    accepted = sorted(set(head.get("published_sessions", [])))
    if not accepted and head.get("accepted_trade_date"):
        accepted = [head["accepted_trade_date"]]
    accepted_through = max(accepted) if accepted else None
    missing = [day for day in sessions if (accepted_through is None or day > accepted_through)
               and day <= shanghai.date().isoformat()]
    registry = head.get("source_registry", {})
    job = daily_job_state.get("last_job") or {}
    checks_by_day = {item.get("trade_date"): item for item in job.get("days", [])}
    ready = []
    for day in missing:
        source = registry.get(day, {}) if isinstance(registry, dict) else {}
        freeze_ref = source.get("freeze") if isinstance(source, dict) else None
        freeze = {}
        if freeze_ref:
            try:
                freeze = _document(root, freeze_ref)
            except (OSError, ValueError, TypeError, KeyError):
                freeze = {}
        ready_at = (source.get("source_ready_at") or freeze.get("source_ready_at")
                    or freeze.get("source_complete_at"))
        job_day = checks_by_day.get(day, {})
        checks = job_day.get("source_checks") or {}
        job_freeze = checks.get("source_freeze") or checks.get("candidate") or {}
        job_ready_at = checks.get("source_ready_at") or job_freeze.get("first_available_at") or job_freeze.get("observed_at")
        if checks.get("source_ready") is True and job_ready_at:
            source = dict(source, job_state=job_day.get("state"), source_ready_at=job_ready_at)
            freeze = job_freeze
            ready_at = ready_at or job_ready_at
        if ready_at:
            ready.append((day, source, freeze, ready_at))
    sources_complete = bool(missing) and len(ready) == len(missing)
    batch_dates = missing[:] if sources_complete else []
    target = (batch_dates[-1] if batch_dates else (missing[-1] if missing else None))
    next_session = next((day for day in sessions if target and day > target), None)
    capture_end = f"{next_session}T09:30:00+08:00" if next_session else None
    target_source = next((item for item in ready if item[0] == target), None) if sources_complete else None
    source = target_source[1] if target_source else {}
    freeze = target_source[2] if target_source else {}
    source_ready_at = target_source[3] if target_source else None
    prior_attempts = []
    retry_dir = root / "runtime/forward_r7/retry_receipts"
    if retry_dir.is_dir():
        for path in sorted(retry_dir.glob("*.json")):
            if path.name.endswith(".recovered.json"):
                continue
            try:
                receipt = json.loads(path.read_bytes())
                if receipt.get("contract_id") == "V4_FORWARD_R7_RETRY_RECEIPT_R1":
                    prior_attempts.append(receipt)
            except (OSError, ValueError, TypeError):
                continue
    prior_attempts.sort(key=lambda item: item.get("captured_at", ""))
    latest_failure = prior_attempts[-1] if prior_attempts else None
    failed_statuses = {"QA_BLOCKED", "FAILED_TERMINAL", "INTERRUPTED", "CANCELLED"}
    if job.get("status") in failed_statuses:
        latest_failure = job
    retries = [item.get("next_retry_at") for item in job.get("days", [])
               if item.get("next_retry_at")]
    scheduler_enabled = daily_job_state.get("auto_enabled") is True
    next_attempt = (min(retries) if retries else (latest_failure or {}).get("next_attempt_at")) if scheduler_enabled else None
    trigger = ((latest_failure or {}).get("next_attempt_trigger") or (job.get("trigger") if next_attempt else None)) if scheduler_enabled else None
    plan_status = ("SOURCE_READY" if sources_complete else "WAIT_SOURCE_READY" if missing
                   else "WAIT_NEXT_OFFICIAL_SESSION")
    return dict(contract_id="V4_FORWARD_R7_NEXT_CAPTURE_PLAN_R2", status=plan_status,
        planned_trade_date=target, missing_sessions=missing, collection_batch_dates=batch_dates,
        signal_T0=target, valid_from_session=next_session,
        market_close_at=f"{target}T15:00:00+08:00" if target else None,
        source_ready_at=source_ready_at,
        first_available_at=freeze.get("first_available_at") or freeze.get("provider_available_at"),
        head_accepted_at=(source.get("head_accepted_at") or freeze.get("head_accepted_at")) if target_source else None,
        frozen_at=(freeze.get("frozen_at") or freeze.get("processed_at")) if target_source else None,
        capture_window_end=capture_end, next_attempt_at=next_attempt,
        next_attempt_trigger=trigger, last_successful_capture=head.get("accepted_trade_date"),
        last_failure=latest_failure, daily_job_state=daily_job_state,
        planned_at=now.isoformat(), timezone="Asia/Shanghai",
        accepted_head_date=head.get("accepted_trade_date"), auto_trading=False)


def classify_membership_provenance(*, trade_date: str, sector_rows: list[dict],
                                   binding: dict, frozen_at: str,
                                   accepted_head_binding: str | None = None,
                                   membership_binding: dict | None = None) -> dict:
    """Classify only independently bound membership snapshots as point-in-time."""
    bound_sha = binding.get("sha256")
    source_path = binding.get("path") or binding.get("relative_path")
    member_sha = (membership_binding or {}).get("sha256")
    member_path = ((membership_binding or {}).get("path")
                   or (membership_binding or {}).get("relative_path"))
    by_sector = {}
    for row in sector_rows:
        sector_id = row.get("sector_id")
        original = row.get("membership_provenance") or {}
        observed = original.get("observed_at") or row.get("membership_observed_at")
        available = original.get("first_available_at") or row.get("membership_first_available_at")
        effective = (original.get("membership_effective_T0") or row.get("membership_effective_T0")
                     or row.get("member_set_asof"))
        digest = original.get("source_sha256") or row.get("membership_source_sha256")
        path = original.get("source_path") or row.get("membership_source_path")
        basis = "UNKNOWN_MEMBERSHIP_BASIS"
        if effective and effective != trade_date:
            basis = "MEMBERSHIP_RETRO"
        elif (observed and available and effective == trade_date and digest and path
              and member_sha and member_path and digest == member_sha and path == member_path
              and (digest != bound_sha or path != source_path)):
            try:
                observed_dt = datetime.fromisoformat(observed.replace("Z", "+00:00"))
                available_dt = datetime.fromisoformat(available.replace("Z", "+00:00"))
                frozen_dt = datetime.fromisoformat(frozen_at.replace("Z", "+00:00"))
                if not all(value.tzinfo for value in (observed_dt, available_dt, frozen_dt)):
                    raise ValueError("MEMBERSHIP_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
                observed_day = observed_dt.astimezone(SHANGHAI).date().isoformat()
                if (observed_day == trade_date and observed_dt <= available_dt <= frozen_dt):
                    basis = "AS_RECORDED"
                else:
                    basis = "MEMBERSHIP_RETRO"
            except (TypeError, ValueError):
                basis = "UNKNOWN_MEMBERSHIP_BASIS"
        by_sector[sector_id] = dict(membership_basis=basis, source_path=path,
            source_sha256=digest, observed_at=observed, first_available_at=available,
            membership_effective_T0=effective, source_binding_sha256=bound_sha,
            accepted_head_binding=accepted_head_binding,
            frozen_at=frozen_at)
    values = [item["membership_basis"] for item in by_sector.values()]
    overall = ("AS_RECORDED" if values and all(v == "AS_RECORDED" for v in values)
               else "MEMBERSHIP_RETRO" if any(v == "MEMBERSHIP_RETRO" for v in values)
               else "UNKNOWN_MEMBERSHIP_BASIS")
    return dict(membership_basis=overall, by_sector=by_sector,
                as_recorded_count=sum(v == "AS_RECORDED" for v in values),
                retro_count=sum(v in ("MEMBERSHIP_RETRO", "RECONSTRUCTED") for v in values),
                unknown_count=sum(v == "UNKNOWN_MEMBERSHIP_BASIS" for v in values))


def retry_pending_capture_receipts(root: str | Path):
    """Recover failed captures as retrospective rows; never upgrade them to OOS."""
    root=Path(root).resolve()
    directory=root/'runtime/forward_r7/retry_receipts'
    if not directory.is_dir():
        return dict(status='NO_RETRY_PENDING',recovered=0)
    receipts=[]
    for path in sorted(directory.glob('*.json')):
        if path.name.endswith('.recovered.json'):
            continue
        try:
            item=json.loads(path.read_bytes())
            if item.get('contract_id')=='V4_FORWARD_R7_RETRY_RECEIPT_R1' and item.get('retryable') is True:
                receipts.append((path,item))
        except (OSError,ValueError,TypeError):
            continue
    if not receipts:
        return dict(status='NO_RETRY_PENDING',recovered=0)
    head=_head(root); accepted=set(head.get('published_sessions',[])); recovered=[]
    store=ForwardR7Store(root)
    for path,item in receipts:
        day=item.get('trade_date')
        if day not in accepted:
            continue
        receipt=reconstruct_history(root,store=store,dates=[day])
        if receipt.get('status')=='READY':
            source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
            completion=dict(contract_id='V4_FORWARD_R7_RETRY_COMPLETION_R1',trade_date=day,
                original_receipt_sha256=source_sha,recovered_at=datetime.now(timezone.utc).isoformat(),
                recovery_lane='RETROSPECTIVE_RESEARCH',live_oos_upgrade=False)
            from .operational_daily_storage_v1 import atomic_json
            atomic_json(root,path.with_name(path.stem+'.recovered.json'),completion)
            recovered.append(day)
    return dict(status='RECOVERED' if recovered else 'RETRY_REQUIRED',recovered=len(recovered),dates=recovered)


def classify_after_close_capture(*, trade_date: str, sessions: list[str], first_available_at: str | None,
                                  head_accepted_at: str | None, first_processed_at: str,
                                  frozen_at: str, source_ready_at: str | None = None) -> dict:
    """Classify first-freeze timing without conflating source, Head, and worker clocks."""
    ordered=sorted(set(sessions)); following=[d for d in ordered if d>trade_date]
    next_session=following[0] if following else None
    open_at=datetime.fromisoformat(next_session+"T09:30:00+08:00") if next_session else None
    def instant(value):
        if not value:return None
        parsed=datetime.fromisoformat(value)
        if parsed.tzinfo is None:raise ValueError("FORWARD_R7_CAPTURE_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        return parsed.astimezone(timezone.utc)
    available=instant(first_available_at);accepted=instant(head_accepted_at)
    processed=instant(first_processed_at);frozen=instant(frozen_at)
    close_at=datetime.fromisoformat(trade_date+"T15:00:00+08:00").astimezone(timezone.utc)
    open_utc=open_at.astimezone(timezone.utc) if open_at else None
    reasons=[]
    if not next_session:reasons.append("NEXT_OFFICIAL_SESSION_UNKNOWN")
    if not available:reasons.append("SOURCE_FIRST_AVAILABLE_TIME_UNKNOWN")
    elif available<close_at:reasons.append("SIGNAL_SOURCE_PRECEDES_AFTER_CLOSE_CUTOFF")
    if not accepted:reasons.append("HEAD_ACCEPTANCE_TIME_UNKNOWN")
    elif available and accepted<available:reasons.append("HEAD_ACCEPTED_BEFORE_SOURCE_AVAILABLE")
    if processed and accepted and processed<accepted:reasons.append("PROCESSING_PRECEDES_HEAD_ACCEPTANCE")
    if frozen<processed:reasons.append("FREEZE_PRECEDES_PROCESSING")
    if open_utc and frozen>=open_utc:reasons.append("FREEZE_AFTER_NEXT_SESSION_OPEN")
    lane="LIVE_OOS" if not reasons else "LATE_OBSERVED_NOT_PIT"
    return dict(lane=lane,observed_signal_T0=trade_date,first_available_at=first_available_at,
                market_close_at=trade_date+"T15:00:00+08:00",source_ready_at=source_ready_at,
                head_accepted_at=head_accepted_at,first_processed_at=first_processed_at,frozen_at=frozen_at,
                valid_from_session=next_session,
                executable_from=(next_session+"T09:30:00+08:00") if next_session else None,
                execution_semantics="RESEARCH_REFERENCE_ONLY_NOT_EXECUTED",timing_reasons=reasons,
                capture_window_end=(open_at.isoformat() if open_at else None))


def capture_after_accepted_head(root: str | Path, candidate: dict, *, dsn: str | None = None, head_accepted_at: str | None = None):
    """Post-publication live event hook; errors are logged and never roll back Head."""
    root = Path(root).resolve()
    first_processed_at = datetime.now(timezone.utc).isoformat()
    day = candidate.get("accepted_trade_date")
    task_date = datetime.fromisoformat(first_processed_at).astimezone(SHANGHAI).date().isoformat()
    # The current accepted package has no R7 source owners until the daily
    # producer creates them. Fail closed and record the exact missing inputs.
    try:
        store = ForwardR7Store(root, dsn=dsn)
        defs, digest = load_definitions(root)
        store.verify_existing_storage(); store.register_definitions(defs,digest)
        accepted = _head(root)
        refs = _bindings(accepted, day)
        raw = _document(root, refs["raw"]); core = _document(root, refs["core"]); sectors = _document(root, refs["sector"])
        if refs.get("membership"):
            _document(root, refs["membership"])
        sessions = official_sessions(root)
        prior = _session_pair(sessions, day)
        prior_refs = _bindings(accepted, prior) if prior else None
        prior_core = _document(root, prior_refs["core"]) if prior_refs else None
        prior_raw = _document(root, prior_refs["raw"]) if prior_refs else None
        prior_sectors = _document(root, prior_refs["sector"]) if prior_refs else None
        freeze_ref = accepted.get("source_registry",{}).get(day,{}).get("freeze")
        source_times = _document(root,freeze_ref) if freeze_ref else {}
        if source_times.get("target_session") != day:
            raise ValueError("FORWARD_R7_SOURCE_FREEZE_DATE_MISMATCH")
        source_ready_at = source_times.get("source_ready_at") or source_times.get("source_complete_at")
        first_available = (source_times.get("first_available_at") or source_times.get("provider_available_at"))
        accepted_at = head_accepted_at or accepted.get("head_accepted_at") or accepted.get("accepted_at")
        frozen_at = datetime.now(timezone.utc).isoformat()
        timing = classify_after_close_capture(trade_date=day,sessions=sessions,
            first_available_at=first_available,head_accepted_at=accepted_at,
            first_processed_at=first_processed_at,frozen_at=frozen_at,
            source_ready_at=source_ready_at)
        lane = timing["lane"]
        membership = classify_membership_provenance(trade_date=day,sector_rows=sectors,
            binding=refs["sector"],frozen_at=frozen_at,
            accepted_head_binding=hashlib.sha256(canonical_head(accepted)).hexdigest(),
            membership_binding=refs.get("membership"))
        rows = build_daily_universe(trade_date=day,stock_rows=core,raw_rows=raw,sector_rows=sectors,
            prior_stock_rows=prior_core,prior_raw_rows=prior_raw,prior_sector_rows=prior_sectors,
            bindings=refs,captured_at=first_processed_at,lane="LIVE_OOS",
            membership_basis=membership["membership_basis"],
            membership_provenance=membership["by_sector"])
        capture_source_digest = hashlib.sha256(canonical_bytes({k:v.get("sha256") for k,v in sorted(refs.items())})).hexdigest()
        accepted_raw_ids = {item.get("security_id") for item in raw if item.get("security_id")}
        for row in rows:
            row.update(timing)
            row_lane = lane
            if row.get("entity_type") == "SECTOR":
                provenance = membership["by_sector"].get(row.get("entity_id"), {})
                row["membership_provenance"] = provenance
                row["membership_pit_eligible"] = provenance.get("membership_basis") == "AS_RECORDED"
                row["PIT_ELIGIBLE"] = row["membership_pit_eligible"]
                if lane == "LIVE_OOS" and not row["membership_pit_eligible"]:
                    row_lane = "LATE_OBSERVED_NOT_PIT"
            else:
                available_at = first_available or source_times.get("first_available_at")
                row["price_provenance"] = dict(source_path=refs["raw"].get("path"),
                    source_sha256=refs["raw"].get("sha256"), first_available_at=available_at,
                    head_accepted_at=accepted_at, frozen_at=frozen_at,
                    accepted_head_binding=hashlib.sha256(canonical_head(accepted)).hexdigest())
                row["price_pit_eligible"] = bool(row.get("entity_id") in accepted_raw_ids
                    and lane == "LIVE_OOS" and available_at and accepted_at
                    and refs["raw"].get("sha256"))
                row["PIT_ELIGIBLE"] = row["price_pit_eligible"]
                if lane == "LIVE_OOS" and not row["price_pit_eligible"]:
                    row_lane = "LATE_OBSERVED_NOT_PIT"
            row["evidence_class"] = row_lane
            row["evidence_lane"] = row_lane
            row["capture_revision"] = 1
            row["source_digest"] = capture_source_digest
        prices = {item["security_id"]: item for item in raw if item.get("security_id")}
        settlement_schedule = build_schedules(
            rows, day, sessions, {day: prices}, frozen_at, accepted_source_dates={day})
        result = store.publish_day(trade_date=day,rows=rows,lane=lane,
            first_available_at=first_available,
            run_id=hashlib.sha256((day+frozen_at+"R7-LIVE").encode()).hexdigest(),
            settlement_rows=settlement_schedule,
            source_run={"contract_id":"V4_FORWARD_PIPELINE_R7_R2","source_hashes":{k:v["sha256"] for k,v in refs.items()},
                        "first_processed_at":first_processed_at,"frozen_at":frozen_at,
                        "head_accepted_at":accepted_at,"source_ready_at":source_ready_at,
                        "first_available_at":first_available,"timing_contract":timing,
                        "head_token":hashlib.sha256(canonical_head(candidate)).hexdigest(),
                        "membership_basis":membership["membership_basis"],
                        "membership_provenance_counts":{k:membership[k] for k in
                            ("as_recorded_count","retro_count","unknown_count")}})
        accepted_dates = set(accepted.get("published_sessions", []))
        due_prices = {}
        due_source_hashes = {}
        due_source_bindings = {}
        try:
            due_days = store.pending_due_dates(accepted_source_dates=accepted_dates)
            legacy_no_quote_days = store.legacy_no_quote_due_dates()
            source_days = sorted({d for d in [*due_days, *legacy_no_quote_days] if d in accepted_dates})
            for due_day in source_days:
                due_refs = _bindings(accepted, due_day)
                due_raw = _document(root, due_refs["raw"])
                due_lifecycle = _document(root, due_refs["lifecycle"]) if due_refs.get("lifecycle") else None
                due_prices[due_day] = accepted_prices_with_status(due_raw, due_lifecycle,
                    source_hash=due_refs.get("lifecycle", {}).get("sha256"))
                due_source_hashes[due_day] = {k:v.get("sha256") for k,v in sorted(due_refs.items())}
                due_source_bindings[due_day] = due_refs
            per_day_digests = {d:hashlib.sha256(canonical_bytes(hashes)).hexdigest()
                               for d,hashes in due_source_hashes.items()}
            legacy_review = store.review_legacy_no_quote(accepted_trade_date=day,
                accepted_source_dates=accepted_dates,prices_by_date=due_prices,
                source_digests_by_date=per_day_digests,source_bindings_by_date=due_source_bindings,
                reviewed_at=datetime.now(timezone.utc).isoformat())
            if due_days:
                advance_digest = hashlib.sha256(canonical_bytes(due_source_hashes)).hexdigest()
                advanced = store.advance_due_settlements(accepted_trade_date=day,
                    prices_by_date=due_prices, source_digest=advance_digest,
                    accepted_source_dates=accepted_dates, source_digests_by_date=per_day_digests)
            else:
                advanced = dict(status="NO_DUE_SETTLEMENTS", accepted_trade_date=day, appended=0)
            advanced["legacy_no_quote_review"] = legacy_review
        except Exception as advance_error:
            error_code = type(advance_error).__name__ + ":" + str(advance_error)
            advance_run = hashlib.sha256((day + capture_source_digest + error_code + first_processed_at).encode()).hexdigest()
            store.record_failure(stage="SETTLEMENT_ADVANCE",trade_date=day,current_head_date=day,
                run_id=advance_run,attempt=1,error_code=error_code,
                payload={"retryable":True,"accepted_due_dates":sorted(accepted_dates)})
            advanced = dict(status="RETRY_REQUIRED", accepted_trade_date=day,
                            appended=0, error_code=type(advance_error).__name__)
        return dict(timing,status="PUBLISHED",trade_date=day,lane=lane,captured_at=frozen_at,
                    settlement_advance=advanced,result=result)
    except Exception as exc:
        LOG.exception("R7 post-accepted-head capture failed for %s", day)
        error_code = type(exc).__name__ + ":" + str(exc)
        try:
            if 'store' in locals():
                store.verify_existing_storage()
                store.record_failure(stage="LIVE_CAPTURE",trade_date=day,current_head_date=day,
                    run_id=hashlib.sha256((str(day)+first_processed_at+"R7-FAIL").encode()).hexdigest(),
                    attempt=1,error_code=error_code,payload={"first_processed_at":first_processed_at,"head_accepted_at":head_accepted_at})
        except Exception:
            pass
        try:
            from .operational_daily_storage_v1 import atomic_json
            directory = root / "runtime/forward_r7/retry_receipts"
            directory.mkdir(parents=True,exist_ok=True)
            receipt = dict(contract_id="V4_FORWARD_R7_RETRY_RECEIPT_R1",trade_date=day,
                           captured_at=first_processed_at,head_accepted_at=head_accepted_at,error_code=error_code,retryable=True,
                           pg_run_persisted=False)
            name = hashlib.sha256((str(day)+first_processed_at).encode()).hexdigest()+".json"
            atomic_json(root,directory/name,receipt)
        except Exception:
            pass
        return dict(status="RETRY_REQUIRED",trade_date=day,captured_at=first_processed_at,head_accepted_at=head_accepted_at,
                    error_code=error_code,retryable=True)


def canonical_head(candidate):
    return json.dumps(candidate,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
