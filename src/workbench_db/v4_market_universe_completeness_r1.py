"""Independent, typed market-universe coverage contract for V4 daily results.

This contract evaluates an independently accepted, date-scoped universe
snapshot against Core IDs. It never derives the denominator from Core rows or
the producer's own TDX row-count fact.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from typing import Any, Mapping, Sequence

CONTRACT_ID = "V4_MARKET_UNIVERSE_COMPLETENESS_R1"
CONTRACT_VERSION = "1.0.0"
_STATUSES = {"ACTIVE", "SUSPENDED", "NEWLY_LISTED", "DELISTED", "CODE_MIGRATION", "UNKNOWN"}
_ASSET_CLASSES = {"COMMON_STOCK", "PREFERRED_STOCK", "ETF", "INDEX", "BOND", "OTHER", "UNKNOWN"}
_SHARE_CLASSES = {"A", "B", "NOT_APPLICABLE", "UNKNOWN"}
_EXCHANGE_SCOPE = {"SSE", "SZSE", "BSE"}


class MarketUniverseError(ValueError):
    pass


def _day(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise MarketUniverseError("UNIVERSE_TRADE_DATE_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise MarketUniverseError("UNIVERSE_TRADE_DATE_INVALID") from exc
    if parsed.isoformat() != value:
        raise MarketUniverseError("UNIVERSE_TRADE_DATE_NONCANONICAL")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MarketUniverseError("UNIVERSE_CANONICALIZATION_FAILED") from exc


def _is_expected_security(row: Mapping[str, Any]) -> bool:
    # Explicit scope: only common-equity shares on the named mainland
    # exchanges count. Fund/index/bond and unknown classes stay visible in the
    # reconciliation but cannot silently enter the denominator.
    return row["asset_class"] == "COMMON_STOCK" and row["share_class"] == "A" and row["exchange"] in _EXCHANGE_SCOPE and row["status"] in {
        "ACTIVE", "SUSPENDED", "NEWLY_LISTED", "CODE_MIGRATION"
    }


def evaluate_market_universe_completeness(
    *,
    trade_date: str,
    universe_snapshot: Mapping[str, Any] | None,
    core_rows: Sequence[Mapping[str, Any]],
    accepted_source_package_plan: Mapping[str, Any] | None = None,
    source_universe_fact_key: str = "security_universe",
) -> dict[str, Any]:
    """Compare Core rows with an authority-bound, same-T0 security universe.

    If the signed accepted package or its separately named universe fact is
    absent, this returns an explicit BLOCKED state, never a guessed denominator.
    """
    target = _day(trade_date)
    source_state = "BLOCKED_NO_INDEPENDENT_UNIVERSE_AUTHORITY"
    source_digest = None
    try:
        if not isinstance(accepted_source_package_plan, Mapping) or accepted_source_package_plan.get("status") != "ACCEPTED":
            raise MarketUniverseError("UNIVERSE_ACCEPTED_SOURCE_PACKAGE_REQUIRED")
        from .v4_daily_source_ingest_r6 import _verify_independent_acceptance_authority
        _verify_independent_acceptance_authority(accepted_source_package_plan)
        fact = next((row for row in accepted_source_package_plan.get("source_facts", ())
                     if row.get("source_key") == source_universe_fact_key), None)
        if not isinstance(fact, Mapping):
            raise MarketUniverseError("UNIVERSE_INDEPENDENT_SOURCE_FACT_MISSING")
        source_digest = fact.get("source_fact_sha256")
        if not isinstance(universe_snapshot, Mapping):
            raise MarketUniverseError("UNIVERSE_SNAPSHOT_REQUIRED")
        source_state = "INDEPENDENT_UNIVERSE_SOURCE_VERIFIED"
    except (MarketUniverseError, ValueError) as exc:
        source_state = "BLOCKED:" + str(exc)

    if source_state != "INDEPENDENT_UNIVERSE_SOURCE_VERIFIED":
        return {
            "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
            "trade_date": target, "source_internal_integrity_status": "NOT_EVALUATED",
            "market_universe_completeness_status": "BLOCKED", "status": "BLOCKED",
            "reason": source_state, "universe_id": None, "universe_sha256": None,
            "expected_count": None, "core_count": len(core_rows), "coverage_ratio": None,
            "reconciliation": [], "category_counts": {}, "source_fact_sha256": source_digest,
            "independent_denominator": True,
        }

    if universe_snapshot.get("contract_id") != CONTRACT_ID or universe_snapshot.get("trade_date") != target:
        raise MarketUniverseError("UNIVERSE_SNAPSHOT_CONTRACT_OR_T0_MISMATCH")
    scope = universe_snapshot.get("exchange_scope")
    if not isinstance(scope, Sequence) or isinstance(scope, (str, bytes)) or set(scope) != _EXCHANGE_SCOPE:
        raise MarketUniverseError("UNIVERSE_EXCHANGE_SCOPE_MUST_BE_EXPLICIT")
    entries = universe_snapshot.get("securities")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)) or not entries:
        raise MarketUniverseError("UNIVERSE_SECURITIES_REQUIRED")
    universe_id = universe_snapshot.get("universe_id")
    if not isinstance(universe_id, str) or not universe_id.strip():
        raise MarketUniverseError("UNIVERSE_ID_REQUIRED")
    normalized = []
    seen = set()
    for item in entries:
        if not isinstance(item, Mapping):
            raise MarketUniverseError("UNIVERSE_SECURITY_ROW_INVALID")
        security_id = str(item.get("security_id") or "").strip().upper()
        if not security_id or security_id in seen:
            raise MarketUniverseError("UNIVERSE_SECURITY_ID_MISSING_OR_DUPLICATE")
        seen.add(security_id)
        asset_class = item.get("asset_class")
        status = item.get("status")
        exchange = item.get("exchange")
        share_class = item.get("share_class")
        if (asset_class not in _ASSET_CLASSES or status not in _STATUSES
                or exchange not in (_EXCHANGE_SCOPE | {"OTHER", "UNKNOWN"})
                or share_class not in _SHARE_CLASSES):
            raise MarketUniverseError("UNIVERSE_CLASSIFICATION_INVALID")
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise MarketUniverseError("UNIVERSE_ROW_SOURCE_REQUIRED")
        normalized.append({"security_id": security_id, "asset_class": asset_class,
                           "share_class": share_class, "exchange": exchange,
                           "status": status, "source_id": source_id})
    universe_digest = hashlib.sha256(_canonical({
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "trade_date": target, "universe_id": universe_id,
        "exchange_scope": sorted(scope), "securities": sorted(normalized, key=lambda x:x["security_id"]),
    })).hexdigest()
    if universe_snapshot.get("universe_sha256") != universe_digest:
        raise MarketUniverseError("UNIVERSE_SNAPSHOT_DIGEST_MISMATCH")
    package_fact = next((row for row in accepted_source_package_plan.get("source_facts", ())
                         if row.get("source_key") == source_universe_fact_key), None)
    locator = package_fact.get("record_locator") if isinstance(package_fact, Mapping) else None
    if (not isinstance(locator, Mapping) or locator.get("universe_id") != universe_id
            or locator.get("universe_sha256") != universe_digest
            or locator.get("record_count") != len(normalized)
            or package_fact.get("source_fact_sha256") != source_digest):
        raise MarketUniverseError("UNIVERSE_SOURCE_FACT_BINDING_MISMATCH")

    core_ids = []
    for row in core_rows:
        sid = str(row.get("security_id") or "").strip().upper()
        if not sid:
            raise MarketUniverseError("CORE_SECURITY_ID_MISSING")
        core_ids.append(sid)
    if len(core_ids) != len(set(core_ids)):
        raise MarketUniverseError("CORE_SECURITY_ID_DUPLICATE")
    core_set = set(core_ids)
    entries_by_id = {item["security_id"]: item for item in normalized}
    expected = {sid for sid, item in entries_by_id.items() if _is_expected_security(item)}
    extra_core = sorted(core_set - expected)
    categories = {name: 0 for name in (
        "source_present", "core_present", "suspended", "newly_listed", "delisted",
        "code_migration", "unknown_identity", "ignored_asset_class", "missing_core", "unexpected_core",
    )}
    reconciliation = []
    for sid in sorted(entries_by_id):
        item = entries_by_id[sid]
        expected_row = _is_expected_security(item)
        in_core = sid in core_set
        category = item["status"].lower()
        if item["asset_class"] in {"ETF", "INDEX", "BOND", "PREFERRED_STOCK", "OTHER"} or item["share_class"] == "B":
            category = "ignored_asset_class"
        elif (item["asset_class"] == "UNKNOWN" or item["status"] == "UNKNOWN"
              or item["exchange"] == "UNKNOWN" or item["share_class"] == "UNKNOWN"):
            category = "unknown_identity"
        if expected_row:
            categories["source_present"] += 1
            if in_core:
                categories["core_present"] += 1
            else:
                categories["missing_core"] += 1
            if item["status"] == "SUSPENDED": categories["suspended"] += 1
            if item["status"] == "NEWLY_LISTED": categories["newly_listed"] += 1
            if item["status"] == "CODE_MIGRATION": categories["code_migration"] += 1
        elif category == "unknown_identity":
            categories["unknown_identity"] += 1
        elif item["status"] == "DELISTED":
            categories["delisted"] += 1
            category = "delisted"
        else:
            categories["ignored_asset_class"] += 1
            category = "ignored_asset_class"
        reconciliation.append({
            "security_id": sid, "source_present": True, "core_present": in_core,
            "expected_in_denominator": expected_row, "category": category,
            "asset_class": item["asset_class"], "share_class": item["share_class"], "exchange": item["exchange"],
            "status": item["status"], "source_id": item["source_id"],
        })
    for sid in extra_core:
        categories["unexpected_core"] += 1
        reconciliation.append({"security_id": sid, "source_present": False, "core_present": True,
                               "expected_in_denominator": False, "category": "unexpected_core",
                               "asset_class": None, "share_class": None, "exchange": None, "status": "UNKNOWN",
                               "source_id": "CORE_RESULT"})
    missing = expected - core_set
    coverage = (len(expected & core_set) / len(expected)) if expected else None
    blockers = []
    if not expected: blockers.append("UNIVERSE_DENOMINATOR_EMPTY")
    if missing: blockers.append("UNIVERSE_REQUIRED_SECURITIES_MISSING")
    if extra_core: blockers.append("CORE_SECURITY_OUTSIDE_UNIVERSE")
    if categories["unknown_identity"]: blockers.append("UNIVERSE_UNKNOWN_IDENTITY_PRESENT")
    status = "PASS" if not blockers else "BLOCKED"
    return {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "trade_date": target,
        "source_internal_integrity_status": "NOT_EVALUATED_SEPARATE_CONTRACT",
        "market_universe_completeness_status": status, "status": status,
        "reason": blockers or ["INDEPENDENT_UNIVERSE_COVERAGE_VERIFIED"],
        "universe_id": universe_id, "universe_sha256": universe_digest,
        "source_fact_sha256": source_digest, "expected_count": len(expected),
        "core_count": len(core_ids), "coverage_ratio": coverage,
        "reconciliation": reconciliation, "category_counts": categories,
        "independent_denominator": True,
    }


def seal_universe_snapshot(*, trade_date: str, universe_id: str, exchange_scope: Sequence[str], securities: Sequence[Mapping[str, Any]], source_fact_sha256: str) -> dict[str, Any]:
    """Canonicalizer for test/producer use; the result still needs signed-source binding."""
    target = _day(trade_date)
    rows = sorted(({
        "security_id": str(row.get("security_id") or "").strip().upper(),
        "asset_class": row.get("asset_class"), "share_class": row.get("share_class"), "exchange": row.get("exchange"),
        "status": row.get("status"), "source_id": row.get("source_id"),
    } for row in securities), key=lambda x:x["security_id"])
    digest = hashlib.sha256(_canonical({
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "trade_date": target, "universe_id": universe_id,
        "exchange_scope": sorted(exchange_scope), "securities": rows,
    })).hexdigest()
    return {"contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
            "trade_date": target, "universe_id": universe_id,
            "exchange_scope": list(exchange_scope), "securities": rows,
            "universe_sha256": digest}
