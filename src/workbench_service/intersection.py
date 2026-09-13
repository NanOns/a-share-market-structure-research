"""Pure request and filtering rules for M11-02 collection queries."""

from __future__ import annotations

import math
from typing import Any, Mapping


CONTRACT_ID = "M11_SECTOR_INTERSECTION_V1_0"
P10_CONTRACT_ID = "V3_P10_SECTOR_SET_LINKAGE_V1_0"
OPERATORS = {"INTERSECTION", "UNION"}
ALLOWED_FILTERS = {"queues_any", "bands", "new_high_window", "ma_alignment", "amount_vs_prior20_min", "rps20_min"}
ALLOWED_QUEUES = {"STEADY_QUEUE", "PULLBACK_QUEUE", "BREAKOUT_QUEUE", "LEADER_QUEUE", "EARLY_QUEUE"}
ALLOWED_BANDS = {"CORE_RESEARCH", "SUPPORTED_RESEARCH", "DIAGNOSTIC_ONLY"}
ALLOWED_HIGH_WINDOWS = {20, 30, 60, 100}
ALLOWED_MA = {"BULL", "BULLISH", "BEAR", "BEARISH", "MIXED", "NORMAL"}
ALLOWED_SORTS = {"rps20.desc", "ret20.desc", "amount_vs_prior20.desc", "member_rank.asc", "security_id.asc"}
ALLOWED_MEMBER_ROLES = {"TODAY_LEADER", "CURRENT_RESEARCH", "EARLY_WATCH", "ALL_MEMBERS"}


def unique_ids(value: object, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field}_MUST_BE_ARRAY")
    result = []
    seen = set()
    for raw in value:
        item = str(raw or "").strip()
        if not item:
            raise ValueError(f"{field}_CONTAINS_EMPTY_ID")
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def unique_names(value: object, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field}_MUST_BE_ARRAY")
    result = []
    seen = set()
    for raw in value:
        item = str(raw or "").strip()
        if not item:
            raise ValueError(f"{field}_CONTAINS_EMPTY_NAME")
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def normalize_request(body: Mapping[str, object]) -> dict[str, Any]:
    publication_id = str(body.get("publication_id") or "").strip()
    if not publication_id:
        raise ValueError("PUBLICATION_ID_REQUIRED")
    include = unique_ids(body.get("include_sector_ids"), "INCLUDE_SECTOR_IDS")
    include_names = unique_names(body.get("include_sector_names"), "INCLUDE_SECTOR_NAMES")
    if not include and not include_names:
        raise ValueError("INCLUDE_SECTOR_IDS_MIN_2")
    if len(include) + len(include_names) > 4:
        raise ValueError("INCLUDE_SECTOR_IDS_MAX_4")
    operator = str(body.get("operator") or "INTERSECTION").strip().upper()
    if operator not in OPERATORS:
        raise ValueError("COLLECTION_OPERATOR_UNSUPPORTED")
    exclude = unique_ids(body.get("exclude_sector_ids", []), "EXCLUDE_SECTOR_IDS")
    exclude_names = unique_names(body.get("exclude_sector_names", []), "EXCLUDE_SECTOR_NAMES")
    if len(exclude) + len(exclude_names) > 20:
        raise ValueError("EXCLUDE_SECTOR_IDS_MAX_20")
    research_context_id = str(body.get("research_context_id") or "").strip() or None
    member_role = str(body.get("member_role") or "").strip().upper() or None
    if member_role and member_role not in ALLOWED_MEMBER_ROLES:
        raise ValueError("MEMBER_ROLE_UNSUPPORTED")
    basis = str(body.get("basis") or "AUTO").strip().upper()
    if basis not in {"AUTO", "OBSERVED", "RECONSTRUCTED"}:
        raise ValueError("BASIS_UNSUPPORTED")
    trade_date = str(body.get("trade_date") or "").strip() or None
    filters = body.get("filters", {})
    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        raise ValueError("FILTERS_MUST_BE_OBJECT")
    unknown = sorted(set(filters) - ALLOWED_FILTERS)
    if unknown:
        raise ValueError("FILTER_UNSUPPORTED:" + ",".join(unknown))
    normalized_filters = dict(filters)
    for key in ("queues_any", "bands"):
        if key in normalized_filters:
            values = normalized_filters[key]
            if not isinstance(values, list):
                raise ValueError(f"{key.upper()}_MUST_BE_ARRAY")
            values = [str(value or "").strip().upper() for value in values]
            if any(not value for value in values):
                raise ValueError(f"{key.upper()}_CONTAINS_EMPTY_VALUE")
            allowed = ALLOWED_QUEUES if key == "queues_any" else ALLOWED_BANDS
            if any(value not in allowed for value in values):
                raise ValueError(f"{key.upper()}_UNSUPPORTED")
            normalized_filters[key] = list(dict.fromkeys(values))
    if "new_high_window" in normalized_filters:
        try:
            normalized_filters["new_high_window"] = int(normalized_filters["new_high_window"])
        except (TypeError, ValueError):
            raise ValueError("NEW_HIGH_WINDOW_UNSUPPORTED")
        if normalized_filters["new_high_window"] not in ALLOWED_HIGH_WINDOWS:
            raise ValueError("NEW_HIGH_WINDOW_UNSUPPORTED")
    if "ma_alignment" in normalized_filters:
        normalized_filters["ma_alignment"] = str(normalized_filters["ma_alignment"] or "").strip().upper()
        if normalized_filters["ma_alignment"] not in ALLOWED_MA:
            raise ValueError("MA_ALIGNMENT_UNSUPPORTED")
    for key in ("amount_vs_prior20_min", "rps20_min"):
        if key in normalized_filters:
            try:
                value = float(normalized_filters[key])
            except (TypeError, ValueError):
                raise ValueError(f"{key.upper()}_UNSUPPORTED")
            if not math.isfinite(value):
                raise ValueError(f"{key.upper()}_UNSUPPORTED")
            normalized_filters[key] = value
    sort = str(body.get("sort") or "rps20.desc").strip().lower()
    if sort not in ALLOWED_SORTS:
        raise ValueError("COLLECTION_SORT_UNSUPPORTED")
    try:
        page = max(1, int(body.get("page", 1)))
        page_size = max(1, min(100, int(body.get("page_size", 50))))
    except (TypeError, ValueError):
        raise ValueError("COLLECTION_PAGINATION_INVALID")
    result = {
        "publication_id": publication_id,
        "include_sector_ids": include,
        "exclude_sector_ids": exclude,
        "operator": operator,
        "basis": basis,
        "trade_date": trade_date,
        "filters": normalized_filters,
        "sort": sort,
        "page": page,
        "page_size": page_size,
    }
    if include_names:
        result["include_sector_names"] = include_names
    if exclude_names:
        result["exclude_sector_names"] = exclude_names
    if research_context_id:
        result["research_context_id"] = research_context_id
    if member_role:
        result["member_role"] = member_role
    return result


def finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def safe_value(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe_value(item) for item in value]
    return value


def queue_hits(value: object) -> set[str]:
    if isinstance(value, str):
        try:
            import json
            value = json.loads(value)
        except (TypeError, ValueError):
            return set()
    if not isinstance(value, dict):
        return set()
    return {str(name).upper() for name, state in value.items() if isinstance(state, dict) and state.get("hit") is True}


def passes_filters(item: Mapping[str, object], filters: Mapping[str, object]) -> bool:
    queues = filters.get("queues_any")
    if queues and not queue_hits(item.get("queues_json")) & set(queues):
        return False
    if "bands" in filters:
        bands = filters["bands"]
        if not bands or item.get("research_band") not in bands:
            return False
    if "new_high_window" in filters:
        state = item.get("new_high_state")
        if not isinstance(state, dict) or state.get("window") != filters["new_high_window"] or state.get("new_high") is not True:
            return False
    if "ma_alignment" in filters:
        actual = str(item.get("ma_alignment") or "").upper()
        expected = str(filters["ma_alignment"])
        aliases = {"BULL": "BULLISH", "BEAR": "BEARISH"}
        if actual != aliases.get(expected, expected):
            return False
    if "amount_vs_prior20_min" in filters:
        value = finite(item.get("amount_vs_prior20"))
        if value is None or value < filters["amount_vs_prior20_min"]:
            return False
    if "rps20_min" in filters:
        value = finite(item.get("rps20"))
        if value is None or value < filters["rps20_min"]:
            return False
    return True


def sort_items(items: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    field = sort.split(".", 1)[0]
    if sort.endswith(".asc"):
        return sorted(items, key=lambda item: (finite(item.get(field)) is None, finite(item.get(field)) if finite(item.get(field)) is not None else 0, str(item.get("security_id") or "")))
    return sorted(items, key=lambda item: (finite(item.get(field)) is None, -(finite(item.get(field)) or 0), str(item.get("security_id") or "")))
