"""Dated identity and publication gates for go-forward PIT candidates."""

from __future__ import annotations

from datetime import datetime


def target_identity(accepted: set[str], target_bars: set[str], records: list[dict], target: str) -> tuple[dict[str, dict], list[str]]:
    active: dict[str, dict] = {}
    ambiguous: set[str] = set()
    for row in records:
        key = row["source_security_key"]
        if (row.get("security_type") != "A_STOCK" or not key.startswith(("SH.", "SZ."))
                or not (key.startswith("SH.60") or key.startswith("SH.68")
                        or key.startswith("SZ.00") or key.startswith("SZ.30"))):
            continue
        if (row.get("list_date") and row["list_date"] > target
                or row.get("delist_date") and row["delist_date"] < target
                or row.get("symbol_effective_from") and row["symbol_effective_from"] > target
                or row.get("symbol_effective_to") and row["symbol_effective_to"] < target):
            continue
        if key in active and active[key]["security_id"] != row["security_id"]:
            ambiguous.add(key)
        active[key] = row
    required = accepted | target_bars
    unresolved = sorted((target_bars - active.keys()) | ambiguous)
    return {key: active[key] for key in sorted(required & active.keys())}, unresolved


def publication_time(target_trade_date: int, max_source_trade_date: int, official_raw_source_published_at: str,
                     project_raw_source_available_at: str, adjustment_source_available_at: str,
                     formal_publication_at: str) -> dict:
    if max_source_trade_date > target_trade_date:
        raise ValueError("TEMPORAL_LEAKAGE_FUTURE_RAW")
    times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in
             (official_raw_source_published_at, project_raw_source_available_at,
              adjustment_source_available_at, formal_publication_at)]
    if any(value.tzinfo is None for value in times):
        raise ValueError("PUBLICATION_TIMESTAMP_MISSING_TIMEZONE")
    if times[3] < max(times[:3]):
        raise ValueError("PUBLICATION_BEFORE_REQUIRED_SOURCE_AVAILABILITY")
    return {"target_trade_date": target_trade_date, "max_source_trade_date": max_source_trade_date,
            "official_raw_source_published_at": official_raw_source_published_at,
            "project_raw_source_available_at": project_raw_source_available_at,
            "adjustment_source_available_at": adjustment_source_available_at,
            "formal_publication_at": formal_publication_at,
            "knowledge_lineage": "PIT_OBSERVED_AFTER_FORMAL_PUBLICATION"}
