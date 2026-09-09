"""Pure, versioned history-window planning for M7B-02."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Sequence


CONTRACT_VERSION = "history-window-dependency-v1.0"
MAX_OUTPUT_DAYS = 250


@dataclass(frozen=True)
class WindowDependency:
    domain: str
    consumer: str
    windows: tuple[int, ...]
    lookback_sessions: int
    reason: str


def load_dependencies(root: str | Path) -> tuple[WindowDependency, ...]:
    path = Path(root) / "config/history_windows.yaml"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("WINDOW_DEPENDENCY_CONTRACT_MISMATCH")
    result = []
    for item in payload.get("dependencies", []):
        windows = tuple(sorted({int(window) for window in item["windows"]}))
        lookback = int(item["lookback_sessions"])
        if not windows or lookback < max(windows):
            raise ValueError(f"WINDOW_DEPENDENCY_INVALID:{item.get('domain')}")
        result.append(WindowDependency(item["domain"], item["consumer"], windows, lookback, item["reason"]))
    if not result or max(item.lookback_sessions for item in result) != 100:
        raise ValueError("WINDOW_DEPENDENCY_MAX_LOOKBACK_INVALID")
    return tuple(result)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _normal_dates(values: Iterable[date]) -> list[date]:
    return sorted(set(values))


def _expected_sessions_between(sessions: Sequence[date], start: date | None, end: date | None) -> list[date]:
    if start is None or end is None:
        return []
    return [session for session in sessions if start <= session <= end]


def _calendar_gaps(sessions: Sequence[date]) -> list[date]:
    """Return weekday gaps as diagnostics, never infer them as trading days."""
    if len(sessions) < 2:
        return []
    known = set(sessions)
    gaps = []
    cursor = sessions[0] + timedelta(days=1)
    while cursor < sessions[-1]:
        if cursor.weekday() < 5 and cursor not in known:
            gaps.append(cursor)
        cursor += timedelta(days=1)
    return gaps


def plan_window(
    sessions: Iterable[date],
    *,
    cutoff_date: date,
    output_days: int = MAX_OUTPUT_DAYS,
    observed_sessions: Iterable[date] | None = None,
    dependencies: Sequence[WindowDependency] = (),
) -> dict:
    """Plan one cutoff without reading rows or calculating any historical factor."""
    if output_days < 1 or output_days > MAX_OUTPUT_DAYS:
        raise ValueError("OUTPUT_DAYS_OUT_OF_RANGE")
    calendar = [session for session in _normal_dates(sessions) if session <= cutoff_date]
    if not calendar:
        raise ValueError("NO_SESSIONS_AT_OR_BEFORE_CUTOFF")
    observed = set(_normal_dates(observed_sessions if observed_sessions is not None else calendar))
    output = calendar[-output_days:]
    output_start = output[0]
    output_end = output[-1]
    dependencies = tuple(dependencies) or (
        WindowDependency("history", "history", (1,), 0, "no dependency registry supplied"),
    )
    max_lookback = max(item.lookback_sessions for item in dependencies)
    first_index = calendar.index(output_start)
    read_start = calendar[max(0, first_index - max_lookback)]
    warmup_available = first_index - max(0, first_index - max_lookback)
    required = _expected_sessions_between(calendar, read_start, output_end)
    missing = sorted(set(required) - observed)
    calendar_gaps = _calendar_gaps(required)
    domains = []
    for dependency in dependencies:
        domain_start = calendar[max(0, first_index - dependency.lookback_sessions)]
        domain_warmup_available = first_index - max(0, first_index - dependency.lookback_sessions)
        domain_required = _expected_sessions_between(calendar, domain_start, output_end)
        domain_missing = sorted(set(domain_required) - observed)
        available = [session for session in domain_required if session in observed]
        output_coverage = len(output) / output_days
        input_coverage = len(available) / len(domain_required) if domain_required else 0.0
        capability = "AVAILABLE" if output_coverage == 1.0 and not domain_missing else "PARTIAL"
        if not available:
            capability = "UNAVAILABLE"
        domains.append({
            "domain": dependency.domain,
            "consumer": dependency.consumer,
            "windows": list(dependency.windows),
            "required_history": dependency.lookback_sessions,
            "warmup_available_sessions": domain_warmup_available,
            "warmup_shortfall": max(0, dependency.lookback_sessions - domain_warmup_available),
            "left_truncated": domain_warmup_available < dependency.lookback_sessions,
            "output_start": _iso(output_start),
            "output_end": _iso(output_end),
            "read_start": _iso(domain_start),
            "read_end": _iso(output_end),
            "available_from": _iso(min(available) if available else None),
            "available_to": _iso(max(available) if available else None),
            "missing_dates": [_iso(value) for value in domain_missing],
            "required_input_days": len(domain_required),
            "available_input_days": len(available),
            "output_days": len(output),
            "field_coverage": {"input": round(input_coverage, 8), "output": round(output_coverage, 8)},
            "capability": capability,
            "analysis_capability": "NOT_BUILT",
            "reason": dependency.reason,
        })
    return {
        "contract_version": CONTRACT_VERSION,
        "calendar_basis": "MASTER_TRADING_CALENDAR",
        "cutoff_date": _iso(cutoff_date),
        "output_days_requested": output_days,
        "output_days": len(output),
        "output_start": _iso(output_start),
        "output_end": _iso(output_end),
        "read_start": _iso(read_start),
        "read_end": _iso(output_end),
        "required_history": max_lookback,
        "warmup_available_sessions": warmup_available,
        "warmup_shortfall": max(0, max_lookback - warmup_available),
        "left_truncated": warmup_available < max_lookback,
        "required_input_days": len(required),
        "available_input_days": len(set(required) & observed),
        "missing_dates": [_iso(value) for value in missing],
        "calendar_gap_diagnostics": [_iso(value) for value in calendar_gaps],
        "output_dates": [_iso(value) for value in output],
        "field_coverage": {
            "input": round(len(set(required) & observed) / len(required), 8) if required else 0.0,
            "output": round(len(output) / output_days, 8),
        },
        "domains": domains,
        "analysis_capability": "NOT_BUILT",
        "supported_basis": ["OBSERVED", "RECONSTRUCTED"],
    }
