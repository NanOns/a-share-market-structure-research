from __future__ import annotations

"""Auditable dated code binding for the R7 300114/302132 continuation."""

SECURITY_ID = "SEC-EDEDE35FE66896ACCA0AC85EEB2F133B"
CODE_CHANGE_DAY = "20250217"


def historical_exchange_symbol(trade_date: str) -> str:
    day = str(trade_date).replace("-", "")
    return "SZ.300114" if day < CODE_CHANGE_DAY else "SZ.302132"


def board_scope_for_security(security_id: str) -> str | None:
    return "CHINEXT" if security_id == SECURITY_ID else None


def stable_security_id_for_code_change(_: str) -> str:
    """Both dated aliases represent one continuing listed security identity."""
    return SECURITY_ID
