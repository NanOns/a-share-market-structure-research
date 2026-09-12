"""V3 P04-01 minimum invalidation planning.

This module only compares versioned dependency summaries and returns a
deterministic, explainable build plan.  It does not read TDX files, write
analysis rows, publish a snapshot, or execute a writer.  P04-02 is the stage
that may consume this plan.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping, Sequence


CONTRACT_VERSION = "v3-build-plan-v1.0"
SUMMARY_CONTRACT_VERSION = "v3-dependency-summary-v1.0"

REASON_LABELS = {
    "NEW_TRADING_DAY": "只新增交易日，只追加该日必要结果",
    "PRICE_WINDOW": "原始价量修订影响滚动窗口",
    "RPS_CROSS_SECTION": "受影响日期需要全市场横截面重新排名",
    "STATE_PROPAGATION": "连续状态按受影响证券传播至数据末端",
    "RELATION_CHANGE": "概念成员关系变化，只重算受影响关系及下游",
    "SECTOR_NAME_CHANGE": "板块属性/显示名称变化",
    "TREE_PARENT_CHANGE": "树父关系变化，只重算相关父板块及下游",
    "PARAMETER_CHANGE": "算法参数或合同变化，只重算指定域及下游",
    "ADJUSTMENT_WINDOW": "复权锚变化，按复权合同传播到受影响价格窗口",
}

STOCK_DOMAINS = ("quote", "technical", "strength", "high", "structure", "summary")
SECTOR_DOMAINS = ("sector_base", "sector_cycle", "mainline")
MEMBER_DOMAIN = "member_state"

# These are the dependency limits already frozen in config/history_windows.yaml.
# Callers may pass the loaded registry explicitly; keeping the same defaults
# makes the pure planner useful in isolation and keeps the contract fail-closed.
DEFAULT_LOOKBACKS = {
    "quote": 1,
    "technical": 60,
    "strength": 60,
    "high": 100,
    "structure": 60,
    "sector_cycle": 30,
    "mainline": 30,
    "market": 60,
}

PARAMETER_DOWNSTREAM = {
    "quote": ("quote", "technical", "strength", "high", "structure", "summary"),
    "technical": ("technical", "high", "structure", "summary", "member_state"),
    "strength": ("strength", "sector_cycle", "mainline", "summary"),
    "high": ("high", "structure", "summary", "member_state"),
    "structure": ("structure", "summary", "member_state"),
    "sector_base": ("sector_base", "sector_cycle", "mainline", "member_state"),
    "sector_cycle": ("sector_cycle", "mainline", "summary"),
    "mainline": ("mainline",),
    "member_state": ("member_state", "summary"),
    "summary": ("summary",),
}


class BuildPlanError(ValueError):
    """Raised when a dependency summary or planning input is invalid."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _iso(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise BuildPlanError(f"DATE_INVALID:{value}") from exc


def _normalise_hash_map(value: Any, field_name: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise BuildPlanError(f"SUMMARY_FIELD_INVALID:{field_name}")
    result = {}
    for key, digest in value.items():
        if not isinstance(key, str) or not key:
            raise BuildPlanError(f"SUMMARY_KEY_INVALID:{field_name}")
        if digest is None:
            result[key] = ""
        elif isinstance(digest, str):
            result[key] = digest
        else:
            raise BuildPlanError(f"SUMMARY_HASH_INVALID:{field_name}:{key}")
    return dict(sorted(result.items()))


@dataclass(frozen=True)
class DependencySummary:
    """Versioned, content-only dependency identity for one build input."""

    trading_days: tuple[str, ...] = ()
    quote: Mapping[str, str] = field(default_factory=dict)
    relationships: Mapping[str, str] = field(default_factory=dict)
    sector_names: Mapping[str, str] = field(default_factory=dict)
    hierarchy: Mapping[str, str] = field(default_factory=dict)
    parameters: Mapping[str, str] = field(default_factory=dict)
    adjustments: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "DependencySummary":
        if payload is None:
            return cls()
        if not isinstance(payload, Mapping):
            raise BuildPlanError("DEPENDENCY_SUMMARY_OBJECT_REQUIRED")
        version = payload.get("contract_version", SUMMARY_CONTRACT_VERSION)
        if version != SUMMARY_CONTRACT_VERSION:
            raise BuildPlanError("DEPENDENCY_SUMMARY_CONTRACT_MISMATCH")
        raw_days = payload.get("trading_days", [])
        if not isinstance(raw_days, (list, tuple)):
            raise BuildPlanError("SUMMARY_FIELD_INVALID:trading_days")
        days = tuple(sorted({_iso(item) for item in raw_days}))
        return cls(
            trading_days=days,
            quote=_normalise_hash_map(payload.get("quote"), "quote"),
            relationships=_normalise_hash_map(payload.get("relationships"), "relationships"),
            sector_names=_normalise_hash_map(payload.get("sector_names"), "sector_names"),
            hierarchy=_normalise_hash_map(payload.get("hierarchy"), "hierarchy"),
            parameters=_normalise_hash_map(payload.get("parameters"), "parameters"),
            adjustments=_normalise_hash_map(payload.get("adjustments"), "adjustments"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "contract_version": SUMMARY_CONTRACT_VERSION,
            "trading_days": list(self.trading_days),
            "quote": dict(sorted(self.quote.items())),
            "relationships": dict(sorted(self.relationships.items())),
            "sector_names": dict(sorted(self.sector_names.items())),
            "hierarchy": dict(sorted(self.hierarchy.items())),
            "parameters": dict(sorted(self.parameters.items())),
            "adjustments": dict(sorted(self.adjustments.items())),
        }

    @property
    def digest(self) -> str:
        return _sha256(self.to_payload())


@dataclass(frozen=True)
class ChangeEvent:
    kind: str
    key: str
    effective_date: str | None
    security_id: str | None
    sector_id: str | None
    parameter_domain: str | None
    before_hash: str | None
    after_hash: str | None
    reason_code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "key": self.key,
            "effective_date": self.effective_date,
            "security_id": self.security_id,
            "sector_id": self.sector_id,
            "parameter_domain": self.parameter_domain,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "reason_code": self.reason_code,
            "reason": REASON_LABELS[self.reason_code],
        }


def _split_key(key: str, expected: int, field_name: str) -> tuple[str, ...]:
    parts = tuple(key.split("|"))
    if len(parts) != expected or any(part == "" for part in parts):
        raise BuildPlanError(f"SUMMARY_KEY_INVALID:{field_name}:{key}")
    return parts


def _diff_events(field_name: str, before: Mapping[str, str], after: Mapping[str, str]) -> Iterable[tuple[str, str | None, str | None]]:
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if old != new:
            yield key, old, new


def diff_dependency_summaries(
    previous: DependencySummary | Mapping[str, Any] | None,
    current: DependencySummary | Mapping[str, Any],
) -> list[ChangeEvent]:
    """Return only changed dependency identities in deterministic order."""

    before = previous if isinstance(previous, DependencySummary) else DependencySummary.from_payload(previous)
    after = current if isinstance(current, DependencySummary) else DependencySummary.from_payload(current)
    new_days = set(after.trading_days) - set(before.trading_days)
    events: list[ChangeEvent] = []

    for day in sorted(new_days):
        events.append(ChangeEvent("NEW_TRADING_DAY", day, day, None, None, None, None, day, "NEW_TRADING_DAY"))

    for key, old, new in _diff_events("quote", before.quote, after.quote):
        day, security_id = _split_key(key, 2, "quote")
        if day in new_days:
            continue
        events.append(ChangeEvent("PRICE_REVISION", key, _iso(day), security_id, None, None, old, new, "PRICE_WINDOW"))

    for key, old, new in _diff_events("relationships", before.relationships, after.relationships):
        parts = _split_key(key, 3, "relationships")
        day, sector_id, security_id = parts
        events.append(ChangeEvent("RELATION_CHANGE", key, _iso(day), security_id, sector_id, None, old, new, "RELATION_CHANGE"))

    for key, old, new in _diff_events("sector_names", before.sector_names, after.sector_names):
        events.append(ChangeEvent("SECTOR_NAME_CHANGE", key, None, None, key, None, old, new, "SECTOR_NAME_CHANGE"))

    for key, old, new in _diff_events("hierarchy", before.hierarchy, after.hierarchy):
        day, sector_id = _split_key(key, 2, "hierarchy")
        events.append(ChangeEvent("TREE_PARENT_CHANGE", key, _iso(day), None, sector_id, None, old, new, "TREE_PARENT_CHANGE"))

    for key, old, new in _diff_events("parameters", before.parameters, after.parameters):
        events.append(ChangeEvent("PARAMETER_CHANGE", key, None, None, None, key, old, new, "PARAMETER_CHANGE"))

    for key, old, new in _diff_events("adjustments", before.adjustments, after.adjustments):
        parts = _split_key(key, 2, "adjustments")
        security_id, day = parts
        events.append(ChangeEvent("ADJUSTMENT_ANCHOR_CHANGE", key, _iso(day), security_id, None, None, old, new, "ADJUSTMENT_WINDOW"))

    return sorted(
        events,
        key=lambda item: (
            item.kind,
            item.effective_date or "",
            item.security_id or "",
            item.sector_id or "",
            item.parameter_domain or "",
            item.key,
        ),
    )


def _normalise_ids(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    result = tuple(sorted({str(value) for value in values if str(value)}))
    if not result and field_name == "sessions":
        raise BuildPlanError("SESSIONS_REQUIRED")
    return result


def _normalise_members(mapping: Mapping[str, Iterable[str]] | None) -> dict[str, tuple[str, ...]]:
    if mapping is None:
        return {}
    result = {}
    for key, values in mapping.items():
        if not isinstance(key, str) or not key:
            raise BuildPlanError("MEMBERSHIP_KEY_INVALID")
        result[key] = tuple(sorted({str(value) for value in values if str(value)}))
    return result


def _date_span(sessions: Sequence[str], start: str, end_index: int, count: int | None = None) -> tuple[str, ...]:
    if start not in sessions:
        raise BuildPlanError(f"DATE_NOT_IN_CALENDAR:{start}")
    first = sessions.index(start)
    last = len(sessions) if count is None else min(len(sessions), first + max(1, int(count)))
    return tuple(sessions[first:last]) if first <= end_index else ()


def _future_dates(sessions: Sequence[str], start: str, cutoff: str, count: int | None = None) -> tuple[str, ...]:
    if start not in sessions:
        raise BuildPlanError(f"DATE_NOT_IN_CALENDAR:{start}")
    first = sessions.index(start)
    last = sessions.index(cutoff)
    if first > last:
        return ()
    if count is not None:
        last = min(last, first + max(1, int(count)) - 1)
    return tuple(sessions[first : last + 1])


def _coerce_lookbacks(value: Mapping[str, int] | None) -> dict[str, int]:
    result = dict(DEFAULT_LOOKBACKS)
    if value:
        for domain, lookback in value.items():
            if int(lookback) < 1:
                raise BuildPlanError(f"LOOKBACK_INVALID:{domain}")
            result[str(domain)] = int(lookback)
    return result


def _coerce_summary(value: DependencySummary | Mapping[str, Any] | None) -> DependencySummary:
    return value if isinstance(value, DependencySummary) else DependencySummary.from_payload(value)


def _event_id(event: ChangeEvent) -> str:
    return _sha256(event.to_dict())[:16]


def build_plan(
    previous: DependencySummary | Mapping[str, Any] | None,
    current: DependencySummary | Mapping[str, Any],
    *,
    sessions: Iterable[date | str],
    security_ids: Iterable[str] = (),
    sector_ids: Iterable[str] = (),
    security_to_sectors: Mapping[str, Iterable[str]] | None = None,
    sector_members: Mapping[str, Iterable[str]] | None = None,
    cutoff_date: date | str | None = None,
    lookbacks: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Build the smallest explainable task set for changed dependencies.

    ``sector_members`` accepts either ``sector_id`` or ``trade_date|sector_id``
    keys.  The latter is preferred when membership is date-sensitive.
    """

    before = _coerce_summary(previous)
    after = _coerce_summary(current)
    calendar = tuple(sorted({_iso(value) for value in sessions}))
    if not calendar:
        raise BuildPlanError("SESSIONS_REQUIRED")
    cutoff = _iso(cutoff_date) if cutoff_date is not None else (after.trading_days[-1] if after.trading_days else calendar[-1])
    if cutoff not in calendar:
        raise BuildPlanError(f"CUTOFF_NOT_IN_CALENDAR:{cutoff}")
    calendar = tuple(day for day in calendar if day <= cutoff)
    if not calendar:
        raise BuildPlanError("NO_SESSIONS_AT_OR_BEFORE_CUTOFF")

    securities = _normalise_ids(security_ids, "security_ids")
    sectors = set(_normalise_ids(sector_ids, "sector_ids"))
    security_sector_map = {str(key): tuple(sorted({str(value) for value in values if str(value)})) for key, values in (security_to_sectors or {}).items()}
    member_map = _normalise_members(sector_members)
    for values in security_sector_map.values():
        sectors.update(values)
    for key in member_map:
        sectors.add(key.split("|", 1)[-1])
    lookback = _coerce_lookbacks(lookbacks)
    events = diff_dependency_summaries(before, after)
    tasks: dict[tuple[str, str, str | None, str | None], dict[str, Any]] = {}

    def add_task(
        domain: str,
        day: str,
        *,
        security_id: str | None = None,
        sector_id: str | None = None,
        reason_code: str,
        scope: str,
        mode: str,
        end_date: str | None = None,
        event: ChangeEvent,
    ) -> None:
        if day not in calendar:
            raise BuildPlanError(f"DATE_NOT_IN_PLAN_CALENDAR:{day}")
        if domain not in set(STOCK_DOMAINS) | set(SECTOR_DOMAINS) | {MEMBER_DOMAIN, "market"}:
            raise BuildPlanError(f"DOMAIN_UNKNOWN:{domain}")
        key = (domain, day, security_id, sector_id)
        item = tasks.setdefault(
            key,
            {
                "domain": domain,
                "trade_date": day,
                "security_id": security_id,
                "sector_id": sector_id,
                "scope": scope,
                "reason_codes": set(),
                "event_ids": set(),
                "propagation": {"mode": mode, "start_date": day, "end_date": end_date or day},
            },
        )
        item["reason_codes"].add(reason_code)
        item["event_ids"].add(_event_id(event))
        if end_date and end_date > item["propagation"]["end_date"]:
            item["propagation"]["end_date"] = end_date
        if item["propagation"]["mode"] != mode:
            item["propagation"]["mode"] = "COMBINED"

    def dates_from(day: str, domain: str, *, to_cutoff: bool = False) -> tuple[str, ...]:
        return _future_dates(calendar, day, cutoff, None if to_cutoff else lookback.get(domain, 1))

    def sectors_for(event: ChangeEvent) -> tuple[str, ...]:
        found = set()
        if event.sector_id:
            found.add(event.sector_id)
        if event.security_id:
            found.update(security_sector_map.get(event.security_id, ()))
        return tuple(sorted(found))

    def members_for(day: str, sector_id: str, fallback: str | None = None) -> tuple[str, ...]:
        values = member_map.get(f"{day}|{sector_id}") or member_map.get(sector_id) or ()
        if values:
            return values
        return (fallback,) if fallback else securities

    for event in events:
        if event.kind == "NEW_TRADING_DAY":
            day = event.effective_date
            assert day is not None
            for security_id in securities:
                for domain in STOCK_DOMAINS:
                    add_task(domain, day, security_id=security_id, reason_code=event.reason_code, scope="SECURITY", mode="SINGLE_DAY", event=event)
            for sector_id in sorted(sectors):
                for domain in SECTOR_DOMAINS:
                    add_task(domain, day, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR", mode="SINGLE_DAY", event=event)
                for security_id in members_for(day, sector_id):
                    add_task(MEMBER_DOMAIN, day, security_id=security_id, sector_id=sector_id, reason_code=event.reason_code, scope="MEMBER", mode="SINGLE_DAY", event=event)
            add_task("market", day, reason_code=event.reason_code, scope="MARKET", mode="SINGLE_DAY", event=event)
            continue

        if event.kind == "SECTOR_NAME_CHANGE":
            add_task("sector_base", cutoff, sector_id=event.sector_id, reason_code=event.reason_code, scope="SECTOR_DISPLAY", mode="ATTRIBUTE_ONLY", event=event)
            continue

        if event.kind == "PARAMETER_CHANGE":
            domains = PARAMETER_DOWNSTREAM.get(event.parameter_domain or "", ())
            for domain in domains:
                if domain in STOCK_DOMAINS:
                    for security_id in securities or (None,):
                        add_task(domain, cutoff, security_id=security_id, reason_code=event.reason_code, scope="SECURITY" if security_id else "MARKET", mode="NEW_CONTRACT", event=event)
                elif domain == MEMBER_DOMAIN:
                    for sector_id in sorted(sectors) or (None,):
                        add_task(domain, cutoff, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR" if sector_id else "MARKET", mode="NEW_CONTRACT", event=event)
                else:
                    for sector_id in sorted(sectors) or (None,):
                        add_task(domain, cutoff, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR" if sector_id else "MARKET", mode="NEW_CONTRACT", event=event)
            continue

        if event.effective_date is None:
            raise BuildPlanError(f"EVENT_DATE_REQUIRED:{event.kind}")

        if event.kind == "PRICE_REVISION":
            day = event.effective_date
            security_id = event.security_id
            if not security_id:
                raise BuildPlanError("PRICE_REVISION_SECURITY_REQUIRED")
            quote_dates = (day,)
            for item_day in quote_dates:
                add_task("quote", item_day, security_id=security_id, reason_code=event.reason_code, scope="SECURITY", mode="SINGLE_DAY", event=event)
            for item_day in dates_from(day, "technical"):
                add_task("technical", item_day, security_id=security_id, reason_code=event.reason_code, scope="SECURITY", mode="ROLLING_WINDOW", end_date=item_day, event=event)
            for item_day in dates_from(day, "strength"):
                # RPS is a cross-sectional output: every universe member on the
                # affected date must be planned, not only the corrected stock.
                for member_id in securities or (None,):
                    add_task("strength", item_day, security_id=member_id, reason_code="RPS_CROSS_SECTION", scope="MARKET" if member_id is None else "SECURITY", mode="CROSS_SECTION", event=event)
            for domain in ("high", "structure", "summary"):
                for item_day in dates_from(day, domain, to_cutoff=True):
                    add_task(domain, item_day, security_id=security_id, reason_code="STATE_PROPAGATION", scope="SECURITY", mode="STATE_TO_CUTOFF", end_date=cutoff, event=event)
            for sector_id in sectors_for(event):
                for item_day in dates_from(day, "sector_cycle"):
                    add_task("sector_cycle", item_day, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR", mode="ROLLING_WINDOW", event=event)
                    add_task("mainline", item_day, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR", mode="ROLLING_WINDOW", event=event)
                for item_day in dates_from(day, "technical"):
                    add_task("sector_base", item_day, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR", mode="ROLLING_WINDOW", event=event)
                for item_day in dates_from(day, "high", to_cutoff=True):
                    add_task(MEMBER_DOMAIN, item_day, security_id=security_id, sector_id=sector_id, reason_code="STATE_PROPAGATION", scope="MEMBER", mode="STATE_TO_CUTOFF", end_date=cutoff, event=event)
            continue

        if event.kind == "ADJUSTMENT_ANCHOR_CHANGE":
            day = event.effective_date
            security_id = event.security_id
            if not security_id:
                raise BuildPlanError("ADJUSTMENT_SECURITY_REQUIRED")
            for item_day in dates_from(day, "technical", to_cutoff=True):
                add_task("technical", item_day, security_id=security_id, reason_code=event.reason_code, scope="SECURITY", mode="ADJUSTMENT_TO_CUTOFF", end_date=cutoff, event=event)
            for item_day in dates_from(day, "strength", to_cutoff=True):
                for member_id in securities or (None,):
                    add_task("strength", item_day, security_id=member_id, reason_code="RPS_CROSS_SECTION", scope="MARKET" if member_id is None else "SECURITY", mode="CROSS_SECTION", event=event)
            for domain in ("high", "structure", "summary"):
                for item_day in dates_from(day, domain, to_cutoff=True):
                    add_task(domain, item_day, security_id=security_id, reason_code="STATE_PROPAGATION", scope="SECURITY", mode="ADJUSTMENT_TO_CUTOFF", end_date=cutoff, event=event)
            continue

        if event.kind == "RELATION_CHANGE":
            day = event.effective_date
            for sector_id in sectors_for(event):
                for domain in SECTOR_DOMAINS:
                    add_task(domain, day, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR", mode="RELATION_CHANGE", event=event)
                for member_id in members_for(day, sector_id, event.security_id):
                    for domain in (MEMBER_DOMAIN, "structure", "summary"):
                        add_task(domain, day, security_id=member_id, sector_id=sector_id, reason_code=event.reason_code, scope="MEMBER", mode="RELATION_CHANGE", event=event)
            continue

        if event.kind == "TREE_PARENT_CHANGE":
            day = event.effective_date
            for sector_id in sectors_for(event):
                for domain in SECTOR_DOMAINS:
                    add_task(domain, day, sector_id=sector_id, reason_code=event.reason_code, scope="SECTOR", mode="TREE_CHANGE", event=event)
                for member_id in members_for(day, sector_id):
                    for domain in (MEMBER_DOMAIN, "structure", "summary"):
                        add_task(domain, day, security_id=member_id, sector_id=sector_id, reason_code=event.reason_code, scope="MEMBER", mode="TREE_CHANGE", event=event)
            continue

        raise BuildPlanError(f"EVENT_KIND_UNSUPPORTED:{event.kind}")

    serialised_tasks = []
    for task in sorted(tasks.values(), key=lambda item: (item["trade_date"], item["domain"], item["security_id"] or "", item["sector_id"] or "")):
        serialised = dict(task)
        serialised["reason_codes"] = sorted(task["reason_codes"])
        serialised["reasons"] = [REASON_LABELS[code] for code in serialised["reason_codes"]]
        serialised["event_ids"] = sorted(task["event_ids"])
        serialised_tasks.append(serialised)

    payload = {
        "contract_version": CONTRACT_VERSION,
        "summary_contract_version": SUMMARY_CONTRACT_VERSION,
        "status": "PLANNED" if serialised_tasks else "NO_WORK",
        "input": {"previous_digest": before.digest, "current_digest": after.digest, "cutoff_date": cutoff},
        "events": [event.to_dict() for event in events],
        "tasks": serialised_tasks,
        "summary": {
            "event_count": len(events),
            "task_count": len(serialised_tasks),
            "planned_dates": sorted({item["trade_date"] for item in serialised_tasks}),
            "planned_domains": sorted({item["domain"] for item in serialised_tasks}),
        },
        "reason_catalog": dict(REASON_LABELS),
    }
    payload["plan_id"] = "plan-" + _sha256(payload)
    return payload


__all__ = [
    "CONTRACT_VERSION",
    "SUMMARY_CONTRACT_VERSION",
    "BuildPlanError",
    "ChangeEvent",
    "DependencySummary",
    "REASON_LABELS",
    "build_plan",
    "diff_dependency_summaries",
]
