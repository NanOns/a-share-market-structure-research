from __future__ import annotations

"""Deterministic stable security entity IDs, separate from provider/source symbols."""

import hashlib
import re
from datetime import date

_SYMBOL = re.compile(r"^(SH|SZ|BJ)\.([0-9]{6})$", re.IGNORECASE)


def stable_security_id(exchange: str, lifecycle_anchor_symbol: str, list_date: str | date) -> str:
    """Return a stable opaque entity identifier from independently sourced identity facts."""
    market = exchange.upper()
    anchor = lifecycle_anchor_symbol.upper()
    if market not in {"SH", "SZ", "BJ"}:
        raise ValueError("IDENTITY_EXCHANGE_INVALID")
    match = _SYMBOL.fullmatch(anchor)
    if not match or match.group(1) != market:
        raise ValueError("IDENTITY_ANCHOR_SYMBOL_INVALID")
    effective_list_date = list_date if isinstance(list_date, date) else date.fromisoformat(list_date)
    fact_key = f"{market}\0{anchor}\0{effective_list_date.isoformat()}".encode("ascii")
    return "SEC-" + hashlib.sha256(fact_key).hexdigest()[:32].upper()


def bao_source_entity(exchange: str, code: str, ipo_date: str | None) -> dict[str, str | None]:
    """Bind a BaoStock code to a candidate stable identity; missing dates stay unresolved."""
    market = exchange.upper()
    symbol = code.upper()
    match = _SYMBOL.fullmatch(symbol)
    if not match or match.group(1) != market:
        raise ValueError("BAOSTOCK_SOURCE_SYMBOL_INVALID")
    if not ipo_date:
        return {"security_id": None, "identity_quality": "UNRESOLVED_LIST_DATE", "identity_anchor_symbol": symbol}
    try:
        entity_id = stable_security_id(market, symbol, ipo_date)
    except ValueError:
        return {"security_id": None, "identity_quality": "UNRESOLVED_LIST_DATE", "identity_anchor_symbol": symbol}
    return {"security_id": entity_id, "identity_quality": "BAOSTOCK_LISTING_ANCHOR_CANDIDATE",
            "identity_anchor_symbol": symbol}


def bse_alias_entity(old_code: str, new_code: str, list_date: str) -> dict[str, str | None]:
    """Bind an official BSE predecessor/current-code pair to one entity ID."""
    old_symbol = "BJ." + old_code
    new_symbol = "BJ." + new_code
    old_match, new_match = _SYMBOL.fullmatch(old_symbol), _SYMBOL.fullmatch(new_symbol)
    if not old_match or not new_match:
        raise ValueError("BSE_ALIAS_SYMBOL_INVALID")
    entity_id = stable_security_id("BJ", old_symbol, list_date)
    return {"security_id": entity_id, "identity_quality": "BSE_OFFICIAL_OLD_NEW_ALIAS",
            "identity_anchor_symbol": old_symbol, "old_symbol": old_symbol, "new_symbol": new_symbol}
