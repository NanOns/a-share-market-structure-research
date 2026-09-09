"""Reference-price and share-capital capability contract (M8C-01)."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state


CONTRACT_VERSION = "REFERENCE_CAPABILITY_V1_0"
KNOWN_SHARE_UNITS = frozenset({"SHARES", "SHARE", "股"})
KNOWN_SHARE_BASES = frozenset({"FLOAT_SHARES", "FREE_FLOAT", "FREE_FLOAT_SHARES", "流通股本"})


class ReferenceCapabilityError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and not pd.isna(value) and np.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _value(row: pd.Series, *names: str) -> Any:
    for name in names:
        value = row.get(name)
        if value is None:
            continue
        try:
            if bool(pd.isna(value)):
                continue
        except (TypeError, ValueError):
            pass
        return value
    return None


def _status(value: Any, source_ref: Any, *, positive: bool = True) -> tuple[str, str | None]:
    if value is None or (not _finite(value)):
        return "UNAVAILABLE", "VALUE_MISSING"
    if positive and float(value) <= 0:
        return "UNKNOWN", "VALUE_NONPOSITIVE"
    if not str(source_ref or "").strip():
        return "UNKNOWN", "SOURCE_REF_MISSING"
    return "EXACT", None


def normalize_reference_rows(
    rows: pd.DataFrame | Iterable[dict[str, Any]],
    *,
    cutoff: Any | None = None,
    rule_id: str | None = None,
) -> pd.DataFrame:
    """Normalize local reference records without converting unknown units."""
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    for name in ("security_id", "trade_date"):
        if name not in frame.columns:
            raise ReferenceCapabilityError(f"REFERENCE_INPUT_COLUMNS_MISSING:{name}")
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="raise").dt.date
    if cutoff is not None and (frame["trade_date"] > pd.Timestamp(cutoff).date()).any():
        raise ReferenceCapabilityError("REFERENCE_INPUT_AFTER_CUTOFF")
    if frame[["security_id", "trade_date"]].duplicated().any():
        raise ReferenceCapabilityError("REFERENCE_DUPLICATE_SECURITY_DATE")
    result: list[dict[str, Any]] = []
    for _, row in frame.sort_values(["trade_date", "security_id"], kind="mergesort").iterrows():
        source_ref = _value(row, "source_ref", "source_id", "reference_source")
        quote = _value(row, "quote_prev_close", "reference_prev_close", "prev_close", "pre_close")
        float_shares = _value(row, "float_shares", "free_float_shares")
        unit = _value(row, "shares_unit", "float_shares_unit")
        basis = _value(row, "shares_basis")
        quote_status, quote_reason = _status(quote, source_ref)
        shares_status, shares_reason = _status(float_shares, source_ref)
        normalized_unit = str(unit).upper() if unit is not None else None
        normalized_basis = str(basis).upper() if basis is not None else None
        quality: list[str] = []
        if quote_reason:
            quality.append("QUOTE_" + quote_reason)
        if shares_reason:
            quality.append("SHARES_" + shares_reason)
        if shares_status == "EXACT" and normalized_unit not in KNOWN_SHARE_UNITS:
            shares_status = "UNKNOWN"
            quality.append("SHARES_UNIT_UNKNOWN")
        if shares_status == "EXACT" and normalized_basis not in KNOWN_SHARE_BASES:
            shares_status = "UNKNOWN"
            quality.append("SHARES_BASIS_UNKNOWN")
        turnover_status = "EXACT" if shares_status == "EXACT" else "UNKNOWN" if float_shares is not None else "UNAVAILABLE"
        if turnover_status != "EXACT":
            quality.append("TURNOVER_REFERENCE_INCOMPLETE")
        selected_rule = str(rule_id or _value(row, "rule_id") or "UNREGISTERED")
        result.append({
            "security_id": str(row["security_id"]),
            "trade_date": row["trade_date"],
            "quote_prev_close": float(quote) if quote_status != "UNAVAILABLE" and _finite(quote) and float(quote) > 0 else None,
            "float_shares": float(float_shares) if _finite(float_shares) and float(float_shares) > 0 else None,
            "shares_unit": normalized_unit,
            "shares_basis": normalized_basis,
            "quote_capability": quote_status,
            "shares_capability": shares_status,
            "turnover_capability": turnover_status,
            "status_known": quote_status == "EXACT" or shares_status == "EXACT",
            "rule_id": selected_rule,
            "rule_registration_status": "REGISTERED" if selected_rule != "UNREGISTERED" else "NOT_REGISTERED",
            "source_ref": str(source_ref) if source_ref is not None else None,
            "observed_at": _value(row, "observed_at", "observed_at_utc"),
            "quality_codes": sorted(set(quality)),
            "contract_id": CONTRACT_VERSION,
        })
    return pd.DataFrame(result)


def build_reference_capability_report(
    rows: pd.DataFrame | Iterable[dict[str, Any]],
    *,
    cutoff: Any | None = None,
    rule_id: str | None = None,
) -> dict[str, Any]:
    frame = normalize_reference_rows(rows, cutoff=cutoff, rule_id=rule_id)
    clean_frame = frame.astype(object).where(pd.notna(frame), None)
    def counts(field: str) -> dict[str, int]:
        return {value: int(frame[field].eq(value).sum()) for value in ("EXACT", "UNKNOWN", "UNAVAILABLE")}
    return {
        "contract_id": CONTRACT_VERSION,
        "cutoff_date": pd.Timestamp(cutoff).date().isoformat() if cutoff is not None else None,
        "row_count": int(len(frame)),
        "price_capability": counts("quote_capability") if len(frame) else {"EXACT": 0, "UNKNOWN": 0, "UNAVAILABLE": 0},
        "shares_capability": counts("shares_capability") if len(frame) else {"EXACT": 0, "UNKNOWN": 0, "UNAVAILABLE": 0},
        "turnover_capability": counts("turnover_capability") if len(frame) else {"EXACT": 0, "UNKNOWN": 0, "UNAVAILABLE": 0},
        "items": clean_frame.to_dict("records"),
        "policy": {"missing_values": "NULL", "unknown_units": "UNKNOWN", "volume_as_shares": False, "external_data_used": False},
    }


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    """Convert capability rows to the existing 007 reference table shape."""
    rows = []
    for row in frame.itertuples():
        rows.append((slice_id, row.security_id, row.quote_prev_close, None, None, row.float_shares, row.shares_basis, bool(row.status_known), row.rule_id, row.source_ref, row.observed_at))
    return rows


def insert_market_reference_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from market_reference_daily where slice_id=?", [slice_id]).fetchall()
    try:
        already_present = immutable_slice_state(existing, rows, key_indexes=(1, 2), conflict_code="REFERENCE_SLICE_IDENTITY_CONFLICT")
    except ValueError as exc:
        raise ReferenceCapabilityError(str(exc)) from exc
    if already_present:
        return len(rows)
    connection.executemany("insert into market_reference_daily (slice_id,security_id,quote_prev_close,limit_up_price,limit_down_price,float_shares,shares_basis,status_known,rule_id,source_ref,observed_at) values (?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)
