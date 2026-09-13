"""P10-03 read-only signal outcome evaluation.

The evaluator intentionally lives outside the research-run writer.  Signal
rows are immutable inputs; this module only derives outcome rows and, when
explicitly asked by a task, writes those rows to ``research_signal_outcomes``.
Future observations never participate in the signal identity hash.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
import math
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

import duckdb


CONTRACT_ID = "V3_P10_SIGNAL_EVALUATION_V1_0"
EVAL_VERSION = "V3_P10_SIGNAL_EVALUATION_V1_0"
HORIZONS = (3, 5)
OUTCOME_STATUSES = {"PENDING", "OBSERVED", "DATA_GAP"}
EVALUATION_BASES = {"HISTORICAL_RECONSTRUCTED", "REAL_FORWARD"}
BASELINE_TYPES = ("NON_CURRENT_QUALIFIED", "Q20_NON_CURRENT", "DQ5_3_NON_CURRENT")
MIN_SIGNAL_DAYS = 20
MIN_INDEPENDENT_EPISODES = 50
RETURN_COVERAGE_MIN = 0.70

# These are the fields known on the signal day.  In particular, no due date,
# future current state, outcome status, or future return is accepted here.
SIGNAL_IDENTITY_FIELDS = (
    "signal_run_id", "run_id", "sector_id", "episode_id", "signal_date",
    "first_seen_date", "sector_type", "potential_branch", "potential_eligible",
    "current_eligible", "algorithm_version", "parameter_hash", "snapshot_id",
    "membership_snapshot_id", "signal_contract_id", "evaluation_basis",
)


class SignalEvaluationError(ValueError):
    """Raised when an evaluation input would make the result ambiguous."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise SignalEvaluationError("SIGNAL_DATE_INVALID") from exc


def _date_or_none(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return _date(value)


def _truth(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value).strip().upper()
    if text in {"TRUE", "1", "YES", "Y"}:
        return True
    if text in {"FALSE", "0", "NO", "N"}:
        return False
    return None


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _signal_date(row: Mapping[str, Any]) -> date:
    for key in ("signal_date", "trade_date", "first_seen_date"):
        if row.get(key) not in (None, ""):
            return _date(row[key])
    raise SignalEvaluationError("SIGNAL_DATE_REQUIRED")


def _basis(row: Mapping[str, Any]) -> str:
    value = str(row.get("evaluation_basis") or "HISTORICAL_RECONSTRUCTED").strip().upper()
    aliases = {"RECONSTRUCTED": "HISTORICAL_RECONSTRUCTED", "HISTORICAL": "HISTORICAL_RECONSTRUCTED", "REAL": "REAL_FORWARD"}
    value = aliases.get(value, value)
    if value not in EVALUATION_BASES:
        raise SignalEvaluationError("EVALUATION_BASIS_UNSUPPORTED")
    return value


def seal_episode_id(*, sector_id: Any, first_seen_date: Any, contract_id: str = CONTRACT_ID) -> str:
    """Return a stable episode identity from signal-day facts only."""
    if not str(sector_id or "").strip():
        raise SignalEvaluationError("EPISODE_SECTOR_REQUIRED")
    payload = {"contract_id": str(contract_id), "sector_id": str(sector_id), "first_seen_date": _date(first_seen_date).isoformat()}
    return "episode-" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:32]


def signal_identity_hash(row: Mapping[str, Any]) -> str:
    """Hash only facts available at the signal day.

    Callers may pass a larger row containing future observations; those keys
    are deliberately ignored so adding t+5 data cannot mutate the hash.
    """
    signal_date = _signal_date(row)
    payload: dict[str, Any] = {}
    for key in SIGNAL_IDENTITY_FIELDS:
        if key in row and row[key] not in (None, ""):
            value = row[key]
            payload[key] = value.isoformat() if isinstance(value, (date, datetime)) else value
    payload["signal_date"] = signal_date.isoformat()
    payload["contract_id"] = str(row.get("signal_contract_id") or CONTRACT_ID)
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def episode_first_signals(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep exactly one non-CURRENT first signal for each independent episode."""
    candidates: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        signal_date = _signal_date(row)
        episode_id = str(row.get("episode_id") or "").strip()
        if not episode_id:
            episode_id = seal_episode_id(sector_id=row.get("sector_id"), first_seen_date=signal_date)
        row["episode_id"] = episode_id
        row["signal_date"] = signal_date
        row["evaluation_basis"] = _basis(row)
        row["current_eligible"] = row.get("current_eligible", row.get("current"))
        row["potential_eligible"] = row.get("potential_eligible", row.get("potential"))
        if _truth(row.get("potential_eligible")) is not True:
            continue
        candidates.append(row)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        grouped[row["episode_id"]].append(row)
    first: list[dict[str, Any]] = []
    for episode_id, items in grouped.items():
        items.sort(key=lambda item: (item["signal_date"], str(item.get("signal_run_id") or item.get("run_id") or ""), str(item.get("sector_id") or "")))
        earliest = items[0]
        # A signal that was already CURRENT is not an early signal sample.
        if _truth(earliest.get("current_eligible")) is True:
            continue
        earliest["episode_id"] = episode_id
        earliest["signal_hash"] = signal_identity_hash(earliest)
        earliest["first_signal"] = True
        first.append(earliest)
    return sorted(first, key=lambda item: (item["signal_date"], str(item.get("sector_id") or ""), item["episode_id"]))


def _normal_sessions(sessions: Iterable[Any], signal_date: date) -> list[date]:
    result = sorted({_date(item) for item in sessions})
    if signal_date not in result:
        result.append(signal_date)
        result.sort()
    return result


def due_date_for_horizon(signal_date: Any, horizon: int, sessions: Iterable[Any]) -> date | None:
    if int(horizon) not in HORIZONS:
        raise SignalEvaluationError("HORIZON_UNSUPPORTED")
    signal_day = _date(signal_date)
    calendar = _normal_sessions(sessions, signal_day)
    index = calendar.index(signal_day)
    target = index + int(horizon)
    return calendar[target] if target < len(calendar) else None


def _rows_for_sector(future_rows: Any, signal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if isinstance(future_rows, Mapping):
        sector_id = str(signal.get("sector_id") or "")
        if sector_id in future_rows:
            future_rows = future_rows[sector_id]
        elif signal.get("episode_id") in future_rows:
            future_rows = future_rows[signal["episode_id"]]
        else:
            selected = []
            for key, values in future_rows.items():
                if isinstance(key, tuple) and len(key) == 2 and str(key[0]) == sector_id:
                    selected.append({"trade_date": key[1], "current_eligible": values})
            if selected:
                return selected
            future_rows = []
    result = []
    for raw in future_rows or []:
        row = raw if isinstance(raw, Mapping) else {}
        if row.get("sector_id") not in (None, "", signal.get("sector_id")):
            continue
        if row.get("trade_date", row.get("date")) in (None, ""):
            continue
        item = dict(row)
        item["trade_date"] = _date(item.get("trade_date", item.get("date")))
        result.append(item)
    return sorted(result, key=lambda item: item["trade_date"])


def _members_for_signal(members: Any, signal: Mapping[str, Any]) -> list[str] | None:
    if isinstance(members, Mapping):
        key = str(signal.get("episode_id") or "")
        if key in members:
            members = members[key]
        elif str(signal.get("sector_id") or "") in members:
            members = members[str(signal.get("sector_id"))]
        else:
            return None
    if members is None:
        return None
    result: list[str] = []
    for item in members:
        security_id = item.get("security_id") if isinstance(item, Mapping) else item
        if str(security_id or "").strip() and str(security_id) not in result:
            result.append(str(security_id))
    return result


def _price_map(prices: Any) -> dict[tuple[date, str], float]:
    result: dict[tuple[date, str], float] = {}
    if isinstance(prices, Mapping):
        for key, value in prices.items():
            if isinstance(key, tuple) and len(key) == 2:
                number = _number(value)
                if number is not None:
                    result[(_date(key[0]), str(key[1]))] = number
            elif isinstance(value, Mapping):
                for security_id, price in value.items():
                    number = _number(price)
                    if number is not None:
                        result[(_date(key), str(security_id))] = number
        return result
    for raw in prices or []:
        if not isinstance(raw, Mapping):
            continue
        trade_date = raw.get("trade_date", raw.get("date"))
        security_id = raw.get("security_id")
        price = raw.get("adj_close", raw.get("adjusted_close"))
        if trade_date in (None, "") or security_id in (None, ""):
            continue
        number = _number(price)
        if number is not None:
            result[(_date(trade_date), str(security_id))] = number
    return result


def _outcome_evidence(*, signal: Mapping[str, Any], horizon: int, status: str, due_date: date | None, reasons: list[str], current_dates: list[date], coverage: float | None, return_count: int, return_gate: str | None = None) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "eval_version": EVAL_VERSION,
        "signal_hash": signal.get("signal_hash") or signal_identity_hash(signal),
        "signal_day": _signal_date(signal).isoformat(),
        "due_date": due_date.isoformat() if due_date else None,
        "current_observed_dates": [item.isoformat() for item in current_dates],
        "status_reasons": reasons,
        "signal_day_current_excluded": True,
        "future_data_used": status != "PENDING",
        "return_diagnostic": True,
        "return_coverage_gate": RETURN_COVERAGE_MIN,
        "return_count": return_count,
        "return_gate": return_gate,
    }


def evaluate_episode(signal: Mapping[str, Any], horizon: int, *, sessions: Iterable[Any], future_rows: Iterable[Mapping[str, Any]] = (), members: Iterable[Any] | None = None, prices: Any = (), as_of_date: Any | None = None, evaluated_at: Any | None = None) -> dict[str, Any]:
    """Evaluate one sealed first signal at a 3/5-session due date."""
    horizon = int(horizon)
    if horizon not in HORIZONS:
        raise SignalEvaluationError("HORIZON_UNSUPPORTED")
    signal_day = _signal_date(signal)
    due_date = due_date_for_horizon(signal_day, horizon, sessions)
    as_of = _date_or_none(as_of_date)
    future = _rows_for_sector(future_rows, signal)
    observed_dates = [row["trade_date"] for row in future if row["trade_date"] > signal_day]
    observed_through = as_of or (max(observed_dates) if observed_dates else signal_day)
    common = {
        "signal_run_id": str(signal.get("signal_run_id") or signal.get("run_id") or ""),
        "sector_id": str(signal.get("sector_id") or ""),
        "horizon": horizon,
        "eval_version": EVAL_VERSION,
        "episode_id": str(signal.get("episode_id") or seal_episode_id(sector_id=signal.get("sector_id"), first_seen_date=signal_day)),
        "due_date": due_date,
        "evaluated_at": evaluated_at or datetime.now(timezone.utc),
        "evaluation_basis": _basis(signal),
        "confirmed_date": None,
        "confirmed_within_h": None,
        "lead_sessions": None,
        "member_forward_median": None,
        "member_forward_coverage": None,
    }
    if due_date is None or due_date > observed_through:
        common["status"] = "PENDING"
        common["evidence"] = _outcome_evidence(signal=signal, horizon=horizon, status="PENDING", due_date=due_date, reasons=["DUE_DATE_NOT_OBSERVED"], current_dates=[], coverage=None, return_count=0)
        return common
    due_rows = [row for row in future if row["trade_date"] == due_date]
    if not due_rows:
        common["status"] = "DATA_GAP"
        common["evidence"] = _outcome_evidence(signal=signal, horizon=horizon, status="DATA_GAP", due_date=due_date, reasons=["DUE_DATE_DATA_MISSING"], current_dates=[], coverage=None, return_count=0)
        return common

    current_dates: list[date] = []
    confirmed: tuple[date, int] | None = None
    calendar = _normal_sessions(sessions, signal_day)
    index = calendar.index(signal_day)
    for row in future:
        trade_date = row["trade_date"]
        if not signal_day < trade_date <= due_date:
            continue
        current = _truth(row.get("current_eligible", row.get("current")))
        if current is not None:
            current_dates.append(trade_date)
        if current is True and confirmed is None:
            confirmed = (trade_date, calendar.index(trade_date) - index)
    expected_dates = [item for item in calendar if signal_day < item <= due_date]
    missing_current_dates = [item for item in expected_dates if item not in {row["trade_date"] for row in future}]
    unknown_current_dates = [
        row["trade_date"] for row in future
        if signal_day < row["trade_date"] <= due_date
        and _truth(row.get("current_eligible", row.get("current"))) is None
    ]
    if confirmed:
        common["confirmed_date"], common["lead_sessions"] = confirmed
        common["confirmed_within_h"] = True
    elif any(_truth(row.get("current_eligible", row.get("current"))) is None for row in future if signal_day < row["trade_date"] <= due_date):
        common["confirmed_within_h"] = None
    else:
        common["confirmed_within_h"] = False

    fixed_members = _members_for_signal(members, signal)
    price_lookup = _price_map(prices)
    reasons: list[str] = []
    return_values: list[float] = []
    if fixed_members is None or not fixed_members:
        common["status"] = "DATA_GAP"
        reasons.append("MEMBER_BASIS_UNKNOWN")
    else:
        base_valid = 0
        for security_id in fixed_members:
            base = price_lookup.get((signal_day, security_id))
            target = price_lookup.get((due_date, security_id))
            if base is None or target is None or base <= 0:
                continue
            base_valid += 1
            return_values.append(target / base - 1.0)
        coverage = base_valid / len(fixed_members)
        common["member_forward_coverage"] = coverage
        if not return_values:
            common["status"] = "DATA_GAP"
            reasons.append("FIXED_MEMBER_QUOTES_MISSING")
        else:
            common["status"] = "OBSERVED"
            if coverage >= RETURN_COVERAGE_MIN:
                common["member_forward_median"] = median(return_values)
            else:
                reasons.append("FIXED_MEMBER_COVERAGE_BELOW_070")
    if common["status"] == "OBSERVED" and not current_dates:
        # The due-date row itself is present, but CURRENT is unknown across
        # the window.  This is data quality, not a negative confirmation.
        common["status"] = "DATA_GAP"
        reasons.append("CURRENT_STATE_DATA_MISSING")
    if missing_current_dates:
        common["status"] = "DATA_GAP"
        reasons.append("FUTURE_SESSION_DATA_MISSING")
    if unknown_current_dates:
        common["status"] = "DATA_GAP"
        reasons.append("CURRENT_STATE_DATA_MISSING")
    if common["status"] == "OBSERVED" and not reasons:
        reasons.append("DUE_DATE_OBSERVED")
    return_gate = "PASS" if common["member_forward_coverage"] is not None and common["member_forward_coverage"] >= RETURN_COVERAGE_MIN else "DIAGNOSTIC_UNAVAILABLE"
    common["evidence"] = _outcome_evidence(signal=signal, horizon=horizon, status=common["status"], due_date=due_date, reasons=reasons, current_dates=current_dates, coverage=common["member_forward_coverage"], return_count=len(return_values), return_gate=return_gate)
    return common


def _select_for_signal(source: Any, signal: Mapping[str, Any]) -> Any:
    if isinstance(source, Mapping):
        for key in (str(signal.get("episode_id") or ""), str(signal.get("sector_id") or "")):
            if key and key in source:
                return source[key]
    return source


def build_outcome_rows(signal_rows: Iterable[Mapping[str, Any]], *, sessions: Iterable[Any], future_rows: Any = (), members_by_episode: Any = (), prices: Any = (), as_of_date: Any | None = None, evaluated_at: Any | None = None) -> list[dict[str, Any]]:
    """Build one 3-session and one 5-session row per independent episode."""
    first = episode_first_signals(list(signal_rows))
    rows: list[dict[str, Any]] = []
    for signal in first:
        for horizon in HORIZONS:
            rows.append(evaluate_episode(signal, horizon, sessions=sessions, future_rows=_select_for_signal(future_rows, signal), members=_select_for_signal(members_by_episode, signal), prices=prices, as_of_date=as_of_date, evaluated_at=evaluated_at))
    return rows


def build_equal_size_baselines(signal_rows: Iterable[Mapping[str, Any]], universe_rows: Iterable[Mapping[str, Any]], *, display_count_by_day: Mapping[Any, int] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Select the three §14.2 same-day equal-sized descriptive baselines."""
    signals = episode_first_signals(signal_rows)
    target_counts: dict[tuple[date, str], int] = defaultdict(int)
    for signal in signals:
        target_counts[(_signal_date(signal), str(signal.get("sector_type") or ""))] += 1
    universe = []
    for raw in universe_rows:
        row = dict(raw)
        row["trade_date"] = _date(row.get("trade_date", row.get("signal_date")))
        row["sector_type"] = str(row.get("sector_type") or "")
        universe.append(row)
    output = {name: [] for name in BASELINE_TYPES}
    for (trade_date, sector_type), default_count in sorted(target_counts.items()):
        count = int((display_count_by_day or {}).get(trade_date, default_count))
        target_ids = {str(item.get("sector_id")) for item in signals if _signal_date(item) == trade_date and str(item.get("sector_type") or "") == sector_type}
        candidates = [item for item in universe if item["trade_date"] == trade_date and item["sector_type"] == sector_type and str(item.get("sector_id")) not in target_ids and _truth(item.get("current_eligible", item.get("current"))) is not True]
        qualified = [item for item in candidates if _truth(item.get("qualified", item.get("potential_eligible", True))) is True]
        q20 = sorted(candidates, key=lambda item: ((-_number(item.get("q20")) if _number(item.get("q20")) is not None else math.inf), str(item.get("sector_id") or "")))
        dq5 = sorted(candidates, key=lambda item: ((-_number(item.get("dq5_3")) if _number(item.get("dq5_3")) is not None else math.inf), str(item.get("sector_id") or "")))
        selections = {"NON_CURRENT_QUALIFIED": sorted(qualified, key=lambda item: str(item.get("sector_id") or "")), "Q20_NON_CURRENT": q20, "DQ5_3_NON_CURRENT": dq5}
        for name, selected in selections.items():
            output[name].extend(selected[:max(0, count)])
    return output


def sample_gate(signal_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    first = episode_first_signals(signal_rows)
    signal_days = len({_signal_date(row) for row in first})
    episodes = len({str(row.get("episode_id")) for row in first})
    enough = signal_days >= MIN_SIGNAL_DAYS and episodes >= MIN_INDEPENDENT_EPISODES
    return {
        "signal_days": signal_days,
        "independent_episodes": episodes,
        "minimum_signal_days": MIN_SIGNAL_DAYS,
        "minimum_independent_episodes": MIN_INDEPENDENT_EPISODES,
        "status": "EFFECT_SAMPLE_GATE_MET" if enough else "EFFECT_INSUFFICIENT",
        "display_status": "效果观察·样本门槛已达到" if enough else "规则观察·效果验证中",
        "can_claim_effect": False,
        "outcome_count": len(list(outcome_rows)) if not isinstance(outcome_rows, Sequence) else len(outcome_rows),
        "basis": "DESCRIPTIVE_DIAGNOSTIC_NOT_BACKTEST",
    }


OUTCOME_DDL = """
CREATE TABLE IF NOT EXISTS research_signal_outcomes (
    signal_run_id VARCHAR NOT NULL,
    sector_id VARCHAR NOT NULL,
    horizon INTEGER NOT NULL,
    eval_version VARCHAR NOT NULL,
    episode_id VARCHAR,
    due_date DATE,
    evaluated_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    confirmed_date DATE,
    confirmed_within_h BOOLEAN,
    lead_sessions INTEGER,
    member_forward_median DOUBLE,
    member_forward_coverage DOUBLE,
    evaluation_basis VARCHAR NOT NULL,
    evidence JSON NOT NULL,
    PRIMARY KEY (signal_run_id, sector_id, horizon, eval_version),
    CHECK (horizon IN (3, 5)),
    CHECK (status IN ('PENDING', 'OBSERVED', 'DATA_GAP')),
    CHECK (evaluation_basis IN ('HISTORICAL_RECONSTRUCTED', 'REAL_FORWARD'))
)
"""


class ResearchSignalOutcomeStore:
    """Idempotent writer restricted to outcome rows."""

    def __init__(self, connection: duckdb.DuckDBPyConnection, *, ensure_schema: bool = True):
        self.connection = connection
        if ensure_schema:
            self.connection.execute(OUTCOME_DDL)

    @staticmethod
    def _validate(row: Mapping[str, Any]) -> dict[str, Any]:
        required = ("signal_run_id", "sector_id", "horizon", "eval_version", "status", "evaluation_basis")
        missing = [key for key in required if not str(row.get(key) or "").strip()]
        if missing:
            raise SignalEvaluationError("OUTCOME_FIELD_REQUIRED:" + ",".join(missing))
        horizon = int(row["horizon"])
        if horizon not in HORIZONS:
            raise SignalEvaluationError("HORIZON_UNSUPPORTED")
        status = str(row["status"]).upper()
        if status not in OUTCOME_STATUSES:
            raise SignalEvaluationError("OUTCOME_STATUS_UNSUPPORTED")
        basis = _basis(row)
        return {
            "signal_run_id": str(row["signal_run_id"]), "sector_id": str(row["sector_id"]), "horizon": horizon,
            "eval_version": str(row["eval_version"]), "episode_id": row.get("episode_id"),
            "due_date": _date_or_none(row.get("due_date")),
            "evaluated_at": row.get("evaluated_at") or datetime.now(timezone.utc), "status": status,
            "confirmed_date": _date_or_none(row.get("confirmed_date")), "confirmed_within_h": row.get("confirmed_within_h"),
            "lead_sessions": row.get("lead_sessions"), "member_forward_median": row.get("member_forward_median"),
            "member_forward_coverage": row.get("member_forward_coverage"), "evaluation_basis": basis,
            "evidence": row.get("evidence") if isinstance(row.get("evidence"), (dict, list)) else {},
        }

    def upsert(self, rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
        normalized = [self._validate(row) for row in rows]
        inserted = updated = unchanged = 0
        try:
            self.connection.execute("BEGIN TRANSACTION")
            for row in normalized:
                key = [row["signal_run_id"], row["sector_id"], row["horizon"], row["eval_version"]]
                existing = self.connection.execute("SELECT episode_id,due_date,evaluation_basis,status,confirmed_date,confirmed_within_h,lead_sessions,member_forward_median,member_forward_coverage,evidence FROM research_signal_outcomes WHERE signal_run_id=? AND sector_id=? AND horizon=? AND eval_version=?", key).fetchone()
                if existing:
                    immutable = (existing[0], existing[1], existing[2])
                    desired = (row["episode_id"], row["due_date"], row["evaluation_basis"])
                    if immutable != desired:
                        raise SignalEvaluationError("OUTCOME_IDENTITY_CONFLICT")
                    desired_values = (row["status"], row["confirmed_date"], row["confirmed_within_h"], row["lead_sessions"], row["member_forward_median"], row["member_forward_coverage"], _canonical(row["evidence"]))
                    current_values = (existing[3], existing[4], existing[5], existing[6], existing[7], existing[8], _canonical(json.loads(existing[9]) if isinstance(existing[9], str) else existing[9]))
                    if current_values == desired_values:
                        unchanged += 1
                        continue
                    self.connection.execute("UPDATE research_signal_outcomes SET evaluated_at=?,status=?,confirmed_date=?,confirmed_within_h=?,lead_sessions=?,member_forward_median=?,member_forward_coverage=?,evidence=? WHERE signal_run_id=? AND sector_id=? AND horizon=? AND eval_version=?", [row["evaluated_at"], *desired_values, *key])
                    updated += 1
                else:
                    self.connection.execute("INSERT INTO research_signal_outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [row["signal_run_id"], row["sector_id"], row["horizon"], row["eval_version"], row["episode_id"], row["due_date"], row["evaluated_at"], row["status"], row["confirmed_date"], row["confirmed_within_h"], row["lead_sessions"], row["member_forward_median"], row["member_forward_coverage"], row["evaluation_basis"], _canonical(row["evidence"])])
                    inserted += 1
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        return {"inserted": inserted, "updated": updated, "unchanged": unchanged}

    def list_for_run(self, signal_run_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT signal_run_id,sector_id,horizon,eval_version,episode_id,due_date,evaluated_at,status,confirmed_date,confirmed_within_h,lead_sessions,member_forward_median,member_forward_coverage,evaluation_basis,evidence FROM research_signal_outcomes WHERE signal_run_id=? ORDER BY sector_id,horizon", [str(signal_run_id)]).fetchall()
        names = ("signal_run_id", "sector_id", "horizon", "eval_version", "episode_id", "due_date", "evaluated_at", "status", "confirmed_date", "confirmed_within_h", "lead_sessions", "member_forward_median", "member_forward_coverage", "evaluation_basis", "evidence")
        result = []
        for row in rows:
            item = dict(zip(names, row))
            item["evidence"] = json.loads(item["evidence"]) if isinstance(item["evidence"], str) else item["evidence"]
            result.append(item)
        return result


class ResearchSignalEvaluationTask:
    """Explicit evaluation task; it never mutates research signal states."""

    def __init__(self, connection: duckdb.DuckDBPyConnection | None = None):
        self.connection = connection

    def run(self, *, signal_rows: Iterable[Mapping[str, Any]], sessions: Iterable[Any], future_rows: Any = (), members_by_episode: Any = (), prices: Any = (), as_of_date: Any | None = None, persist: bool = True) -> dict[str, Any]:
        signal_rows = list(signal_rows)
        rows = build_outcome_rows(signal_rows, sessions=sessions, future_rows=future_rows, members_by_episode=members_by_episode, prices=prices, as_of_date=as_of_date)
        write = {"inserted": 0, "updated": 0, "unchanged": 0}
        if persist:
            if self.connection is None:
                raise SignalEvaluationError("OUTCOME_CONNECTION_REQUIRED")
            write = ResearchSignalOutcomeStore(self.connection).upsert(rows)
        return {"contract_id": CONTRACT_ID, "eval_version": EVAL_VERSION, "outcomes": rows, "write": write, "sample_gate": sample_gate(signal_rows, rows)}


__all__ = [
    "BASELINE_TYPES", "CONTRACT_ID", "EVAL_VERSION", "HORIZONS", "MIN_INDEPENDENT_EPISODES", "MIN_SIGNAL_DAYS", "OUTCOME_DDL", "RETURN_COVERAGE_MIN", "ResearchSignalEvaluationTask", "ResearchSignalOutcomeStore", "SignalEvaluationError", "build_equal_size_baselines", "build_outcome_rows", "due_date_for_horizon", "episode_first_signals", "evaluate_episode", "sample_gate", "seal_episode_id", "signal_identity_hash",
]
