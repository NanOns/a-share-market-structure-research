"""Capability downgrade gate and report for M8C-03."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


CONTRACT_VERSION = "REFERENCE_CAPABILITY_GATE_V1_0"
CAPABILITY_STATES = ("EXACT", "APPROXIMATE", "UNKNOWN")


class ReferenceGateError(ValueError):
    pass


def _date(value: Any):
    try:
        return pd.Timestamp(value).date()
    except (TypeError, ValueError) as exc:
        raise ReferenceGateError("GATE_DATE_INVALID") from exc


def _bool(value: Any) -> bool:
    if value is None:
        return False
    try:
        return bool(value) if not pd.isna(value) else False
    except (TypeError, ValueError):
        return False


def _state(value: Any, *, exact: bool = False, approximate: bool = False) -> str:
    if exact:
        return "EXACT"
    if approximate:
        return "APPROXIMATE"
    return str(value).upper() if str(value).upper() in CAPABILITY_STATES else "UNKNOWN"


def assess_reference_row(reference: Mapping[str, Any], limit_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Classify one date/security row; unverified data cannot become AVAILABLE."""
    quote = _state(reference.get("quote_capability"), exact=reference.get("quote_capability") == "EXACT", approximate=str(reference.get("reference_basis") or "").upper() in {"APPROXIMATE", "RAW_PREV_CLOSE_APPROXIMATE"})
    shares = _state(reference.get("shares_capability"), exact=reference.get("shares_capability") == "EXACT", approximate=str(reference.get("shares_basis") or "").upper() in {"APPROXIMATE", "ESTIMATED"})
    limit_result = limit_result or {}
    rule_verified = _bool(limit_result.get("rule_verified"))
    if limit_result and not rule_verified:
        limit = "UNKNOWN"
    elif limit_result and str(limit_result.get("limit_state") or "UNKNOWN") in {"LIMIT_UP", "LIMIT_DOWN", "NOT_LIMIT", "SUSPENDED"}:
        limit = "EXACT"
    else:
        limit = "UNKNOWN"
    turnover = "EXACT" if shares == "EXACT" else "APPROXIMATE" if shares == "APPROXIMATE" else "UNKNOWN"
    reference_state = "UNKNOWN" if "UNKNOWN" in {quote, shares} else "APPROXIMATE" if "APPROXIMATE" in {quote, shares} else "EXACT"
    quality = []
    if quote != "EXACT":
        quality.append("QUOTE_NOT_EXACT")
    if shares != "EXACT":
        quality.append("SHARES_NOT_EXACT")
    if limit_result and not rule_verified:
        quality.append("RULE_NOT_VERIFIED")
    available = reference_state == "EXACT" and limit == "EXACT"
    return {
        "security_id": str(reference.get("security_id")),
        "trade_date": _date(reference.get("trade_date")),
        "reference_capability": reference_state,
        "limit_capability": limit,
        "turnover_capability": turnover,
        "available": available,
        "rule_verified": rule_verified,
        "quality_codes": sorted(set(quality)),
        "contract_id": CONTRACT_VERSION,
    }


def build_capability_gate(
    references: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    limit_results: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build per-security/date rows and exact/approximate/unknown summaries."""
    frame = references.copy() if isinstance(references, pd.DataFrame) else pd.DataFrame(list(references))
    if not {"security_id", "trade_date"}.issubset(frame.columns):
        raise ReferenceGateError("GATE_INPUT_COLUMNS_MISSING")
    if frame[["security_id", "trade_date"]].duplicated().any():
        raise ReferenceGateError("GATE_DUPLICATE_SECURITY_DATE")
    limit_map = {}
    for item in limit_results or ():
        key = (str(item.get("security_id")), _date(item.get("trade_date")))
        if key in limit_map:
            raise ReferenceGateError("GATE_LIMIT_DUPLICATE_SECURITY_DATE")
        limit_map[key] = item
    items = [assess_reference_row(row, limit_map.get((str(row["security_id"]), _date(row["trade_date"])))) for _, row in frame.sort_values(["trade_date", "security_id"], kind="mergesort").iterrows()]
    item_frame = pd.DataFrame(items)
    summary_rows = []
    for trade_date, group in item_frame.groupby("trade_date", sort=True):
        summary_rows.append({
            "trade_date": trade_date,
            "contract_id": CONTRACT_VERSION,
            "exact_count": int(group.reference_capability.eq("EXACT").sum()),
            "approximate_count": int(group.reference_capability.eq("APPROXIMATE").sum()),
            "unknown_count": int(group.reference_capability.eq("UNKNOWN").sum()),
            "exact_ratio": float(group.reference_capability.eq("EXACT").mean()),
            "approximate_ratio": float(group.reference_capability.eq("APPROXIMATE").mean()),
            "unknown_ratio": float(group.reference_capability.eq("UNKNOWN").mean()),
            "available_count": int(group.available.eq(True).sum()),
            "available": bool(group.available.all()),
        })
    summary = pd.DataFrame(summary_rows)
    return {"contract_id": CONTRACT_VERSION, "items": item_frame, "summary": summary, "policy": {"unverified_is_available": False, "unknown_is_not_none": True, "external_data_used": False}}


def json_report(result: Mapping[str, Any]) -> dict[str, Any]:
    def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
        clean = frame.astype(object).where(pd.notna(frame), None)
        values = clean.to_dict("records")
        for record in values:
            for key, value in record.items():
                if hasattr(value, "isoformat") and not isinstance(value, (str, bytes)):
                    record[key] = value.isoformat()
        return values
    return {"contract_id": result["contract_id"], "items": records(result["items"]), "summary": records(result["summary"]), "policy": result["policy"]}


def write_json_report(path: str | Path, result: Mapping[str, Any]) -> Path:
    """Write the report atomically; caller remains responsible for scope checks."""
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(json.dumps(json_report(result), ensure_ascii=False, sort_keys=True, default=str, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
