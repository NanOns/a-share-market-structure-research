"""Fail-closed temporal and source guards for V4-05 target-date adapters."""
from __future__ import annotations


CONTRACT_ID = "V4_05_R3_REPLAY_TEMPORAL_GUARDS_V1"
TARGET = 20260928


def require_source_identity(actual_sha256: str, accepted_sha256: str) -> None:
    if actual_sha256 != accepted_sha256:
        raise ValueError("ACCEPTED_SOURCE_IDENTITY_MISMATCH")


def require_factor_visibility(fields: dict, formal_publication_at: str) -> None:
    for name, item in fields.items():
        if item.get("max_source_trade_date", TARGET) > TARGET:
            raise ValueError(f"FUTURE_FACTOR_SOURCE:{name}")
        if item.get("available_at", formal_publication_at) > formal_publication_at:
            raise ValueError(f"PROVIDER_AFTER_FORMAL_PUBLICATION:{name}")


def require_market_dates(rows: list[dict]) -> None:
    if any(int(row["trade_date"].replace("-", "")) > TARGET for row in rows):
        raise ValueError("FUTURE_MARKET_REGIME_INPUT")
