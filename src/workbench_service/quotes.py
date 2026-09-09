"""Quote binding and safe single-day return calculation for M7A."""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path
from typing import Mapping

import pyarrow.parquet as pq

from workbench_service.universe import is_a_share_security_id


CONTRACT_ID = "workbench-quote-v2.1"
SOURCE_PATH = "data/normalized/adjusted_daily.parquet"
REFERENCE_KEYS = ("reference_prev_close", "quote_prev_close", "prev_close", "pre_close")


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _truth(value: object) -> bool:
    return value is True or str(value).strip().upper() in {"TRUE", "1", "YES", "Y", "OK"}


def _reference_prev_close(row: Mapping[str, object]) -> float | None:
    for key in REFERENCE_KEYS:
        value = _number(row.get(key))
        if value is not None and value > 0:
            return value
    return None


def _ordinary_bar(row: Mapping[str, object] | None) -> bool:
    return bool(
        row
        and _truth(row.get("has_actual_bar"))
        and _truth(row.get("tradable"))
        and _truth(row.get("data_observed"))
        and _number(row.get("raw_close")) is not None
        and not _truth(row.get("is_synthetic_fill"))
        and str(row.get("missing_state") or "BAR").upper() == "BAR"
    )


def _adjustment_changed(current: Mapping[str, object], previous: Mapping[str, object]) -> bool:
    keys = ("qfq_mul", "qfq_add", "adjustment_version", "adjustment_status")
    return any(current.get(key) != previous.get(key) for key in keys if current.get(key) is not None and previous.get(key) is not None)


def build_quote(
    current: Mapping[str, object],
    previous: Mapping[str, object] | None = None,
    *,
    publication_id: str,
    source_identity_sha256: str | None = None,
    source_path: str = SOURCE_PATH,
) -> dict:
    """Build one explainable quote row without mixing adjusted prices into RET1."""
    security_id = str(current.get("security_id") or "")
    quote_date = current.get("date")
    raw_close = _number(current.get("raw_close"))
    reference_prev_close = _reference_prev_close(current)
    previous_close = None
    ret1 = None
    basis = "UNAVAILABLE"
    state = "NO_ACTUAL_BAR"

    if raw_close is not None and reference_prev_close is not None:
        previous_close = reference_prev_close
        ret1 = raw_close / reference_prev_close - 1 if reference_prev_close > 0 else None
        basis = "REFERENCE_PREV_CLOSE"
        state = "VALID" if ret1 is not None else "INVALID_REFERENCE_PREV_CLOSE"
    elif _ordinary_bar(current) and _ordinary_bar(previous):
        if _adjustment_changed(current, previous):
            basis = "CORPORATE_ACTION_UNSAFE"
            state = "UNKNOWN_CORPORATE_ACTION"
        else:
            previous_close = _number(previous.get("raw_close"))
            ret1 = raw_close / previous_close - 1 if raw_close is not None and previous_close and previous_close > 0 else None
            basis = "RAW_CLOSE_PREVIOUS_TRADING_DAY"
            state = "VALID_DEGRADED" if ret1 is not None else "MISSING_PREVIOUS_CLOSE"
    elif raw_close is not None:
        basis = "NO_VERIFIED_PREVIOUS_CLOSE"
        state = "MISSING_PREVIOUS_CLOSE"

    result = {
        "quote_contract_id": CONTRACT_ID,
        "security_id": security_id,
        "quote_date": quote_date.isoformat() if isinstance(quote_date, date) else str(quote_date) if quote_date is not None else None,
        "raw_open": _number(current.get("raw_open")),
        "raw_high": _number(current.get("raw_high")),
        "raw_low": _number(current.get("raw_low")),
        "raw_close": raw_close,
        "latest_price": raw_close,
        "raw_amount": _number(current.get("raw_amount")),
        "turnover_amount": _number(current.get("raw_amount")),
        "quote_prev_close": previous_close,
        "quote_ret1": ret1,
        "quote_ret1_basis": basis,
        "quote_state": state,
        "RET1": ret1,
        "price_basis": "RAW",
        "has_actual_bar": _truth(current.get("has_actual_bar")),
        "missing_state": current.get("missing_state"),
        "source_ref": f"{source_path}#security_id={security_id}&date={quote_date}",
        "source_identity_sha256": source_identity_sha256,
        "publication_id": publication_id,
    }
    return result


class QuoteService:
    """Read frozen normalized rows and bind them to one selected publication."""

    def __init__(self, parquet_path: str | Path):
        self.parquet_path = Path(parquet_path)

    def load(self, *, trade_date: date, publication_id: str, source_identity_sha256: str | None = None,
             expected_file_sha256: str | None = None, source_path: str = SOURCE_PATH) -> dict[str, dict]:
        if not self.parquet_path.is_file():
            return {}
        if expected_file_sha256:
            digest = hashlib.sha256()
            with self.parquet_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_file_sha256:
                return {}
        lookback_start = trade_date - timedelta(days=14)
        columns = [
            "security_id", "date", "raw_open", "raw_high", "raw_low", "raw_close", "raw_amount",
            "qfq_mul", "qfq_add", "adjustment_status", "adjustment_version", "tradable",
            "has_actual_bar", "data_observed", "is_synthetic_fill", "missing_state",
            "security_type", "universe_status",
            "is_master_session",
        ]
        rows = pq.read_table(
            self.parquet_path,
            columns=columns,
            filters=[("date", ">=", lookback_start), ("date", "<=", trade_date)],
        ).to_pylist()
        rows = [row for row in rows if is_a_share_security_id(row.get("security_id"))]
        sessions = sorted({row["date"] for row in rows if row.get("date") and _truth(row.get("is_master_session"))})
        previous_session = max((item for item in sessions if item < trade_date), default=None)
        current_rows = {row["security_id"]: row for row in rows if row.get("date") == trade_date}
        previous_rows = {
            row["security_id"]: row for row in rows if previous_session is not None and row.get("date") == previous_session
        }
        return {
            security_id: build_quote(
                current,
                previous_rows.get(security_id),
                publication_id=publication_id,
                source_identity_sha256=source_identity_sha256,
                source_path=source_path,
            )
            for security_id, current in current_rows.items()
        }
