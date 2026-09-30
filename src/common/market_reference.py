"""Typed market-index reference data, separate from individual-stock rules."""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT = _ROOT / "config/v4_market_reference_instruments_v1.json"

def market_index_instruments() -> tuple[dict, ...]:
    contract=json.loads(_CONTRACT.read_text(encoding="utf-8"))
    if contract.get("classification")!="REFERENCE_DATA" or contract.get("contract_id")!="V4_MARKET_REFERENCE_INSTRUMENTS_V1":
        raise ValueError("MARKET_REFERENCE_CONTRACT_INVALID")
    rows=tuple(contract.get("instruments",()))
    if not rows or any(x.get("instrument_type")!="MARKET_INDEX" for x in rows):
        raise ValueError("MARKET_REFERENCE_INSTRUMENT_TYPE_INVALID")
    if len({x.get("instrument_id") for x in rows})!=len(rows):
        raise ValueError("MARKET_REFERENCE_DUPLICATE_ID")
    return rows

def market_index_identifiers() -> tuple[str, ...]:
    return tuple(x["instrument_id"] for x in market_index_instruments())

def market_index_file_parts() -> tuple[tuple[str,str], ...]:
    return tuple((x["exchange"].lower(),x["code"]) for x in market_index_instruments())

def market_session_reference_file_parts() -> tuple[tuple[str,str], ...]:
    return tuple((x["exchange"].lower(),x["code"]) for x in market_index_instruments() if x["role"] in {"SSE_SESSION_REFERENCE","SZSE_SESSION_REFERENCE"})

def market_session_reference_identifiers() -> tuple[str, ...]:
    return tuple(x["instrument_id"] for x in market_index_instruments() if x["role"] in {"SSE_SESSION_REFERENCE","SZSE_SESSION_REFERENCE"})
