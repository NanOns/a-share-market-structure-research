"""Versioned stock-universe classification for the workbench APIs.

The classifier deliberately separates identity/scope from quote and structure
eligibility.  An unknown status is never converted into a delisted status.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from functools import lru_cache
from pathlib import Path
import re
from typing import Iterable, Mapping


CONTRACT_ID = "workbench-universe-v2.2"
DISPLAY_SCOPE_CONTRACT_ID = "workbench-display-scope-v1"
STATISTICAL_SCOPE_CONTRACT_ID = "workbench-statistical-scope-v1"
SECURITY_ID_RE = re.compile(r"^(?P<market>[A-Z][A-Z0-9_]*)\.(?P<code>\d{6})$")
A_SHARE_RE = re.compile(
    r"^(?:SH\.(?:600|601|603|605|688|689)\d{3}|"
    r"SZ\.(?:000|001|002|003|300|301|302)\d{3}|"
    r"BJ\.(?:(?:4|8)\d{5}|92\d{4}))$"
)
# Braces are doubled because callers format this template with {id}.
A_SHARE_SQL = (
    "(regexp_matches({id}, '^SH\\.(600|601|603|605|688|689)[0-9]{{3}}$') "
    "or regexp_matches({id}, '^SZ\\.(000|001|002|003|300|301|302)[0-9]{{3}}$') "
    "or regexp_matches({id}, '^BJ\\.((4|8)[0-9]{{5}}|92[0-9]{{4}})$'))"
)

B_SHARE_PREFIXES = {("SH", "900"), ("SZ", "200")}
NEW_THIRD_BOARD_MARKETS = {"NE", "NQ", "OC", "OTC", "SB", "XSB"}
A_SHARE_PREFIXES = {
    "SH": ("600", "601", "603", "605", "688", "689"),
    "SZ": ("000", "001", "002", "003", "300", "301", "302"),
    "BJ": ("4", "8", "92"),
}
UNKNOWN_STATUSES = {"UNKNOWN", "UNAVAILABLE", "UNCONFIRMED", "DATA_INSUFFICIENT", "STATUS_UNKNOWN"}
DELISTED_STATUSES = {"DELISTED", "CONFIRMED_DELISTED", "退市"}


def _normal(value: object) -> str:
    return str(value).strip().upper() if value is not None else ""


def _bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = _normal(value)
    if text in {"TRUE", "1", "YES", "Y", "OK"}:
        return True
    if text in {"FALSE", "0", "NO", "N"}:
        return False
    return None


def _is_a_prefix(market: str, code: str) -> bool:
    return market in A_SHARE_PREFIXES and any(code.startswith(prefix) for prefix in A_SHARE_PREFIXES[market])


def _is_b_prefix(market: str, code: str) -> bool:
    return (market, code[:3]) in B_SHARE_PREFIXES


@dataclass(frozen=True)
class UniverseDecision:
    security_id: str
    market: str | None
    code: str | None
    classification: str
    display_eligible: bool
    quote_eligible: bool
    structure_eligible: bool
    exclusion_reason: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def classify_security_id(security_id: object, metadata: Mapping[str, object] | None = None) -> UniverseDecision:
    """Classify an ID using its identity metadata and exchange/code prefix.

    ``metadata`` may contain ``market``, ``security_type``, ``status`` or
    ``trade_status``, ``is_delisted``, ``quote_valid``, ``structure_eligible``
    and ``in_normal_universe``.  Metadata can restrict eligibility but cannot
    promote an invalid prefix into the A-share universe.
    """
    metadata = metadata or {}
    raw = _normal(security_id)
    match = SECURITY_ID_RE.fullmatch(raw)
    if not match:
        return UniverseDecision(raw, None, None, "UNKNOWN", False, False, False, "INVALID_SECURITY_ID")

    market, code = match.group("market"), match.group("code")
    declared_market = _normal(metadata.get("market"))
    if declared_market and declared_market != market:
        return UniverseDecision(raw, market, code, "UNKNOWN", False, False, False, "IDENTITY_MARKET_MISMATCH")

    declared_type = _normal(metadata.get("security_type") or metadata.get("asset_type"))
    status = _normal(metadata.get("status") or metadata.get("trade_status") or metadata.get("universe_status"))
    explicitly_delisted = _bool(metadata.get("is_delisted")) is True or status in DELISTED_STATUSES
    status_unknown = not status or status in UNKNOWN_STATUSES or status.endswith("_UNKNOWN")

    if explicitly_delisted:
        return UniverseDecision(raw, market, code, "DELISTED", True, False, False, "EXPLICIT_DELISTED")
    if market in NEW_THIRD_BOARD_MARKETS:
        return UniverseDecision(raw, market, code, "NEW_THIRD_BOARD", True, False, False, "OUT_OF_SCOPE_NEW_THIRD_BOARD")
    if _is_b_prefix(market, code):
        return UniverseDecision(raw, market, code, "B_STOCK", True, False, False, "OUT_OF_SCOPE_B_STOCK")

    if not _is_a_prefix(market, code):
        reason = "UNKNOWN_MARKET_OR_PREFIX" if market not in A_SHARE_PREFIXES else "OUT_OF_SCOPE_SECURITY_TYPE"
        return UniverseDecision(raw, market, code, "OTHER", True, False, False, reason)
    if declared_type and declared_type not in {"A_STOCK", "A_SHARE"}:
        return UniverseDecision(raw, market, code, "UNKNOWN", True, False, False, "IDENTITY_TYPE_MISMATCH")

    quote_valid = _bool(metadata.get("quote_valid"))
    quote_eligible = quote_valid is not False
    reason = None
    if quote_valid is False:
        reason = "QUOTE_DATA_MISSING"

    structure_eligible = not status_unknown
    if _bool(metadata.get("structure_eligible")) is False or _bool(metadata.get("in_normal_universe")) is False:
        structure_eligible = False
        reason = reason or "OUTSIDE_STRUCTURE_UNIVERSE"
    if status_unknown:
        structure_eligible = False
        reason = reason or "STATUS_UNKNOWN_FOR_STRUCTURE"
    return UniverseDecision(raw, market, code, "A_STOCK", True, quote_eligible, structure_eligible, reason)


def summarize_universe(
    records: Iterable[Mapping[str, object]], *, quote_valid_ids: set[str] | None = None
) -> dict:
    """Return explainable display/quote/structure counts for one publication."""
    decisions: list[UniverseDecision] = []
    quote_ids = {str(x).upper() for x in quote_valid_ids} if quote_valid_ids is not None else None
    for record in records:
        metadata = dict(record)
        security_id = metadata.pop("security_id", "")
        if quote_ids is not None:
            metadata["quote_valid"] = str(security_id).upper() in quote_ids
        decisions.append(classify_security_id(security_id, metadata))

    excluded: dict[str, Counter[str]] = {"display": Counter(), "quote": Counter(), "structure": Counter()}
    for decision in decisions:
        reason = decision.exclusion_reason or "NOT_ELIGIBLE"
        if not decision.display_eligible:
            excluded["display"][reason] += 1
        if not decision.quote_eligible:
            excluded["quote"][reason] += 1
        if not decision.structure_eligible:
            excluded["structure"][reason] += 1

    return {
        "contract_id": CONTRACT_ID,
        "scope": {"markets": ["SH", "SZ", "BJ"], "security_type": "A_STOCK"},
        "display_count": sum(item.display_eligible for item in decisions),
        "quote_valid_count": sum(item.quote_eligible for item in decisions),
        "structure_eligible_count": sum(item.structure_eligible for item in decisions),
        "classified_counts": dict(sorted(Counter(item.classification for item in decisions).items())),
        "excluded_by_reason": {
            key: dict(sorted(value.items())) for key, value in excluded.items() if value
        },
        "items": [item.as_dict() for item in decisions],
    }


def is_a_share_security_id(security_id: object) -> bool:
    return bool(A_SHARE_RE.fullmatch(_normal(security_id)))


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config/workbench_universe.yaml"


@lru_cache(maxsize=8)
def _display_scope_from_file(path_text: str) -> dict:
    """Read the stable display block without adding a YAML dependency."""
    path = Path(path_text)
    config = {
        "version": DISPLAY_SCOPE_CONTRACT_ID,
        "show_star_stocks": True,
        "excluded_board_prefixes": (),
        "include_star_stocks": True,
        "include_bj_stocks": True,
    }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return config
    show = re.search(r"(?m)^\s+show_star_stocks:\s*(true|false)\s*$", text, re.IGNORECASE)
    if show:
        config["show_star_stocks"] = show.group(1).lower() == "true"
    statistics = re.search(r"(?m)^\s+include_star_stocks:\s*(true|false)\s*$", text, re.IGNORECASE)
    if statistics:
        config["include_star_stocks"] = statistics.group(1).lower() == "true"
    bj_statistics = re.search(r"(?m)^\s+include_bj_stocks:\s*(true|false)\s*$", text, re.IGNORECASE)
    if bj_statistics:
        config["include_bj_stocks"] = bj_statistics.group(1).lower() == "true"
    prefixes = re.search(r"(?m)^\s+excluded_board_prefixes:\s*\[(.*?)\]\s*$", text)
    if prefixes:
        try:
            values = json.loads("[" + prefixes.group(1) + "]")
            config["excluded_board_prefixes"] = tuple(
                str(value).strip().upper() for value in values if str(value).strip()
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    if config["show_star_stocks"]:
        config["excluded_board_prefixes"] = ()
    return config


def workbench_display_scope(root: str | Path | None = None) -> dict:
    path = (Path(root).resolve() / "config/workbench_universe.yaml") if root else _default_config_path()
    value = dict(_display_scope_from_file(str(path)))
    value.pop("include_star_stocks", None)
    value.pop("include_bj_stocks", None)
    value["excluded_board_prefixes"] = list(value["excluded_board_prefixes"])
    return value


def workbench_statistical_scope(root: str | Path | None = None) -> dict:
    """Return the scope used for aggregate market and sector statistics.

    This is intentionally independent from the stock-facing display scope:
    a user may hide STAR stock rows while the market/sector denominators still
    include those stocks.
    """
    path = (Path(root).resolve() / "config/workbench_universe.yaml") if root else _default_config_path()
    raw = _display_scope_from_file(str(path))
    include_star = bool(raw.get("include_star_stocks", True))
    include_bj = bool(raw.get("include_bj_stocks", True))
    excluded = []
    if not include_star:
        excluded.extend(["SH.688", "SH.689"])
    if not include_bj:
        excluded.extend(["BJ.4", "BJ.8", "BJ.92"])
    return {
        "version": STATISTICAL_SCOPE_CONTRACT_ID,
        "include_star_stocks": include_star,
        "include_bj_stocks": include_bj,
        "excluded_board_prefixes": excluded,
    }


def is_workbench_visible_security_id(security_id: object, root: str | Path | None = None) -> bool:
    """Return whether a stock may enter user-facing pages/statistics."""
    normalized = _normal(security_id)
    if not is_a_share_security_id(normalized):
        return False
    scope = workbench_display_scope(root)
    return not any(normalized.startswith(prefix) for prefix in scope["excluded_board_prefixes"])


def is_workbench_statistical_security_id(security_id: object, root: str | Path | None = None) -> bool:
    """Return whether a stock belongs to aggregate market/sector statistics."""
    normalized = _normal(security_id)
    if not is_a_share_security_id(normalized):
        return False
    scope = workbench_statistical_scope(root)
    return not any(normalized.startswith(prefix) for prefix in scope["excluded_board_prefixes"])


def workbench_scope_sql(column: str, root: str | Path | None = None) -> str:
    """SQL predicate for the configured user-facing stock scope."""
    scope = workbench_display_scope(root)
    clauses = [A_SHARE_SQL.format(id=column)]
    if scope["excluded_board_prefixes"]:
        exclusions = " or ".join(
            f"upper({column}) like '{prefix.replace('%', '%%')}%'"
            for prefix in scope["excluded_board_prefixes"]
        )
        clauses.append(f"not ({exclusions})")
    return "(" + " and ".join(clauses) + ")"


def workbench_statistical_scope_sql(column: str, root: str | Path | None = None) -> str:
    """SQL predicate for aggregate statistics, independent of row display."""
    scope = workbench_statistical_scope(root)
    clauses = [A_SHARE_SQL.format(id=column)]
    if scope["excluded_board_prefixes"]:
        exclusions = " or ".join(
            f"upper({column}) like '{prefix.replace('%', '%%')}%'"
            for prefix in scope["excluded_board_prefixes"]
        )
        clauses.append(f"not ({exclusions})")
    return "(" + " and ".join(clauses) + ")"


# Preserve the regex quantifier while leaving the column placeholder available
# to callers that use ``WORKBENCH_SCOPE_SQL.format(id=...)``.
WORKBENCH_SCOPE_SQL = re.sub(r"\{(\d+)\}", r"{{\1}}", workbench_scope_sql("{id}"))
WORKBENCH_STATISTICAL_SCOPE_SQL = re.sub(
    r"\{(\d+)\}", r"{{\1}}", workbench_statistical_scope_sql("{id}")
)
