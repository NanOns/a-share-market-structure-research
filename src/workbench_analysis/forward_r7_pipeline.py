"""Accepted-Head ingestion, historical reconstruction and horizon settlement."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from .forward_r7 import (build_daily_universe, load_definitions, make_observation_id,
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


def next_capture_plan(root: str | Path, *, now: datetime | None = None):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    shanghai = now.astimezone(SHANGHAI)
    sessions = official_sessions(root)
    candidates = [d for d in sessions if d >= shanghai.date().isoformat()]
    current = candidates[0] if candidates else None
    deadline = datetime.fromisoformat(current + "T15:00:00+08:00") if current else None
    if deadline and shanghai >= deadline:
        candidates = [d for d in sessions if d > current]
        current = candidates[0] if candidates else None
        deadline = datetime.fromisoformat(current + "T15:00:00+08:00") if current else None
    return dict(contract_id="V4_FORWARD_R7_NEXT_CAPTURE_PLAN_R1", status="PENDING_REAL_SESSION",
                planned_trade_date=current, capture_deadline=deadline.isoformat() if deadline else None,
                planned_at=now.isoformat(), timezone="Asia/Shanghai",
                last_accepted_head_date=_head(root).get("accepted_trade_date"),
                late_capture_dates=["2026-10-14"] if shanghai.date().isoformat() == "2026-10-14" and shanghai.hour >= 15 else [],
                auto_trading=False)


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
                                  frozen_at: str) -> dict:
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
        first_available = source_times.get("observed_at")
        accepted_at = head_accepted_at or accepted.get("head_accepted_at") or accepted.get("accepted_at")
        rows = build_daily_universe(trade_date=day,stock_rows=core,raw_rows=raw,sector_rows=sectors,
            prior_stock_rows=prior_core,prior_raw_rows=prior_raw,prior_sector_rows=prior_sectors,
            bindings=refs,captured_at=first_processed_at,lane="LIVE_OOS",membership_basis="AS_RECORDED")
        frozen_at = datetime.now(timezone.utc).isoformat()
        timing = classify_after_close_capture(trade_date=day,sessions=sessions,
            first_available_at=first_available,head_accepted_at=accepted_at,
            first_processed_at=first_processed_at,frozen_at=frozen_at)
        lane = timing["lane"]
        for row in rows:
            row.update(timing)
            row["evidence_class"] = lane
        prices = {item["security_id"]: item for item in raw if item.get("security_id")}
        settlement_schedule = build_schedules(
            rows, day, sessions, {day: prices}, frozen_at, accepted_source_dates={day})
        result = store.publish_day(trade_date=day,rows=rows,lane=lane,
            first_available_at=first_available,
            run_id=hashlib.sha256((day+frozen_at+"R7-LIVE").encode()).hexdigest(),
            settlement_rows=settlement_schedule,
            source_run={"contract_id":"V4_FORWARD_PIPELINE_R7_R2","source_hashes":{k:v["sha256"] for k,v in refs.items()},
                        "first_processed_at":first_processed_at,"frozen_at":frozen_at,
                        "head_accepted_at":accepted_at,"timing_contract":timing,
                        "head_token":hashlib.sha256(canonical_head(candidate)).hexdigest()})
        return dict(status="PUBLISHED",trade_date=day,lane=lane,captured_at=frozen_at,**timing,result=result)
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
