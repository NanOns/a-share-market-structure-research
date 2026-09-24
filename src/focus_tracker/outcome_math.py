"""FOCUS_OUTCOME_TARGET_PLAN_V1 local-price outcome materialization."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from .contracts import digest
from .materialize import VerifiedNormalizedSlice
from .price_path import (ACTUAL_TRADED_CONTRACT_ID, due_date, path_metrics,
                         reanchor_actual_traded_path,
                         reanchor_from_frozen_coefficients)
from .sector_basket import SectorBasket
from .sector_path import frozen_sector_path
from .session_gap_semantics import CONTRACT_ID as SESSION_GAP_CONTRACT


CONTRACT_ID = "FOCUS_OUTCOME_TARGET_PLAN_V2"
HORIZONS = (1, 3, 5, 10, 20)


@dataclass(frozen=True)
class OutcomePathMetrics:
    target_trade_date: date
    path_complete: bool
    anchor_actual_bar: bool
    target_data_state: str | None
    forward_return: Decimal | None
    mfe: Decimal | None
    mae: Decimal | None
    mdd: Decimal | None
    coverage: Decimal | None
    input_digest: str
    quality_status: str
    gap_count: int = 0
    suspended_sessions: int = 0
    unverified_gap_count: int = 0
    suspended_dates: tuple[date, ...] = ()
    unverified_gap_dates: tuple[date, ...] = ()


def _sessions(calendar: Sequence[date], anchor_date: date,
              target_date: date) -> tuple[date, ...]:
    if not calendar or list(calendar) != sorted(set(calendar)):
        raise ValueError("outcome calendar must be complete and strictly increasing")
    if anchor_date not in calendar or target_date not in calendar:
        raise ValueError("outcome anchor/target absent from frozen calendar")
    start, end = calendar.index(anchor_date), calendar.index(target_date)
    if end <= start:
        raise ValueError("outcome target must follow anchor")
    return tuple(calendar[start:end + 1])


def stock_outcome_path(*, normalized: VerifiedNormalizedSlice,
                       security_id: str, calendar: Sequence[date],
                       anchor_date: date, horizon: int) -> OutcomePathMetrics:
    target = due_date(calendar, anchor_date, horizon)
    if target is None:
        raise ValueError("target session is outside the frozen calendar")
    sessions = _sessions(calendar, anchor_date, target)
    rows = normalized.by_security.get(security_id)
    if rows is None:
        raise ValueError("security absent from verified normalized slice")
    anchor_row = rows.get(anchor_date)
    target_row = rows.get(target)
    anchor_actual = bool(anchor_row and anchor_row.get("has_actual_bar") is True)
    target_state = str(target_row.get("missing_state")) if target_row else "MISSING_DATA"
    traded = reanchor_actual_traded_path(sessions=sessions, rows=rows)
    path = traded.bars
    coverage = Decimal(len(traded.actual_sessions)) / Decimal(len(sessions))
    if path is None:
        evidence = {"contract_id": CONTRACT_ID, "kind": "STOCK",
                    "path_contract_id": ACTUAL_TRADED_CONTRACT_ID,
                    "session_gap_contract_id": SESSION_GAP_CONTRACT,
                    "artifact_sha256": normalized.artifact_sha256,
                    "security_id": security_id, "sessions": sessions,
                    "anchor_actual_bar": anchor_actual,
                    "target_data_state": target_state,
                    "suspended_sessions": traded.suspended_sessions,
                    "unverified_gap_sessions": traded.unverified_gap_sessions}
        return OutcomePathMetrics(target, False, anchor_actual, target_state,
                                  None, None, None, None, coverage, digest(evidence),
                                  "PATH_INCOMPLETE", traded.gap_count,
                                  len(traded.suspended_sessions),
                                  len(traded.unverified_gap_sessions),
                                  traded.suspended_sessions,
                                  traded.unverified_gap_sessions)
    metrics = path_metrics(path)
    evidence = {"contract_id": CONTRACT_ID, "kind": "STOCK",
                "path_contract_id": ACTUAL_TRADED_CONTRACT_ID,
                "session_gap_contract_id": SESSION_GAP_CONTRACT,
                "artifact_sha256": normalized.artifact_sha256,
                "adjustment_version": (anchor_row or {}).get("adjustment_version"),
                "security_id": security_id, "sessions": sessions,
                "actual_sessions": traded.actual_sessions,
                "suspended_sessions": traded.suspended_sessions,
                "anchor_close": path[0].close, "target_close": path[-1].close,
                "metrics": metrics}
    return OutcomePathMetrics(target, True, anchor_actual, target_state,
                              metrics["return_close"], metrics["mfe"],
                              metrics["mae"], metrics["mdd_close"],
                              coverage, digest(evidence), "READY",
                              traded.gap_count, len(traded.suspended_sessions),
                              len(traded.unverified_gap_sessions),
                              traded.suspended_sessions,
                              traded.unverified_gap_sessions)


def sector_outcome_path(*, normalized: VerifiedNormalizedSlice,
                        basket: SectorBasket, calendar: Sequence[date],
                        anchor_date: date, horizon: int) -> OutcomePathMetrics:
    target = due_date(calendar, anchor_date, horizon)
    if target is None:
        raise ValueError("target session is outside the frozen calendar")
    sessions = _sessions(calendar, anchor_date, target)
    rows = {security: normalized.by_security.get(security, {})
            for security in basket.security_ids}
    path = frozen_sector_path(basket=basket, sessions=sessions,
                              member_rows=rows)
    anchor_count = sum(reanchor_from_frozen_coefficients(
        sessions=[anchor_date], rows=rows[security]) is not None
        for security in basket.security_ids)
    session_coverages = [Decimal(anchor_count) / Decimal(len(basket.security_ids))]
    session_coverages.extend(day.one_day.coverage for day in path if day.one_day is not None)
    coverage = min(session_coverages) if session_coverages else Decimal(0)
    anchor_ready = path[0].nav is not None
    complete = anchor_ready and all(day.nav is not None for day in path)
    last_rows = [rows[sid].get(target) for sid in basket.security_ids]
    target_states = {str(row.get("missing_state")) for row in last_rows
                     if row is not None and row.get("missing_state") is not None}
    target_state = "BAR" if any(row and row.get("has_actual_bar") is True
                                for row in last_rows) else (
                                    sorted(target_states)[0] if target_states else "MISSING_DATA")
    if not complete:
        evidence = {"contract_id": CONTRACT_ID, "kind": "SECTOR",
                    "artifact_sha256": normalized.artifact_sha256,
                    "basket_digest": basket.basket_digest,
                    "sessions": sessions,
                    "nav": [day.nav for day in path],
                    "coverage": [day.one_day.coverage if day.one_day else None
                                 for day in path]}
        return OutcomePathMetrics(target, False, anchor_ready, target_state,
                                  None, None, None, None, coverage,
                                  digest(evidence), "PATH_INCOMPLETE")
    final = path[-1]
    first_nav = path[0].nav
    assert final.nav is not None and first_nav is not None and final.mdd_close is not None
    # The frozen sector contract defines close NAV only. Intraday MFE/MAE are
    # not inferred from constituent extremes or mislabeled as an index.
    evidence = {"contract_id": CONTRACT_ID, "kind": "SECTOR_CLOSE_NAV",
                "artifact_sha256": normalized.artifact_sha256,
                "basket_digest": basket.basket_digest,
                "basket_source_identity": basket.source_identity,
                "sessions": sessions,
                "nav": [day.nav for day in path],
                "coverage": [day.one_day.coverage if day.one_day else None
                             for day in path], "mdd_close": final.mdd_close,
                "intraday_extremes": "NOT_DEFINED_FOR_SYNTHETIC_SECTOR_NAV"}
    return OutcomePathMetrics(target, True, anchor_ready, target_state,
                              final.nav / first_nav - 1, None, None,
                              final.mdd_close, coverage, digest(evidence),
                              "CLOSE_NAV_ONLY")
