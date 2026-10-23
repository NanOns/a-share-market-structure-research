"""Fail-closed temporal and source guards for V4-05 target-date adapters."""
from __future__ import annotations


CONTRACT_ID = "V4_05_R3_REPLAY_TEMPORAL_GUARDS_V1"


def _yyyymmdd(value) -> int:
    text = str(value).replace("-", "")
    if len(text) != 8 or not text.isdigit():
        raise ValueError("TARGET_TRADE_DATE_INVALID")
    return int(text)


def require_source_identity(actual_sha256: str, accepted_sha256: str) -> None:
    if actual_sha256 != accepted_sha256:
        raise ValueError("ACCEPTED_SOURCE_IDENTITY_MISMATCH")


def require_factor_visibility(fields: dict, formal_publication_at: str, target_date) -> None:
    target = _yyyymmdd(target_date)
    for name, item in fields.items():
        if _yyyymmdd(item.get("max_source_trade_date", target)) > target:
            raise ValueError(f"FUTURE_FACTOR_SOURCE:{name}")
        if item.get("available_at", formal_publication_at) > formal_publication_at:
            raise ValueError(f"PROVIDER_AFTER_FORMAL_PUBLICATION:{name}")


def require_market_dates(rows: list[dict], target_date) -> None:
    target = _yyyymmdd(target_date)
    if any(_yyyymmdd(row["trade_date"]) > target for row in rows):
        raise ValueError("FUTURE_MARKET_REGIME_INPUT")
