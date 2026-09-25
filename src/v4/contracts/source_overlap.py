from __future__ import annotations

import re
from pathlib import Path

from tdx.security_master import classify_security, current_a_stock_ids, read_industry_assignments


ASSET_TYPES = ("A_STOCK", "INDEX", "ETF_LOF", "BOND_CONVERTIBLE", "REPO", "OTHER")
DAY_FIELDS = ("open", "high", "low", "close", "amount", "volume")


def core_gate(asset_results: dict[str, dict]) -> str:
    """Non-core asset differences never veto the independent A-stock Core gate."""
    core = asset_results.get("A_STOCK")
    return "ACCEPTED_SOURCE_PACKAGE" if core and core.get("acceptance") == "ACCEPTED_SOURCE_PACKAGE" else "BLOCKED"


def compare_day_values(package_values: tuple, local_values: tuple, *, source_refresh_eligible: bool = False) -> tuple[str, str | None, list[str]]:
    """Compare raw TDX values with explicit price-rounding and source-refresh reasons."""
    if len(package_values)!=6 or len(local_values)!=6:
        return "UNEXPLAINED_MISMATCH","MALFORMED_RECORD",[]
    fields=[DAY_FIELDS[i] for i,(a,b) in enumerate(zip(package_values,local_values)) if a!=b]
    if not fields:
        return "EXACT",None,[]
    price=[name for name in fields if name in {"open","high","low","close"}]
    price_ok=all(abs(package_values[DAY_FIELDS.index(name)]-local_values[DAY_FIELDS.index(name)])<=1 for name in price)
    other=[name for name in fields if name not in {"open","high","low","close"}]
    if price_ok and not other:
        return "NORMALIZED","TOLERATED_PRICE_ROUNDING",fields
    if source_refresh_eligible and set(other)=={"volume"} and price_ok:
        return "NORMALIZED","TOLERATED_SOURCE_REFRESH_VOLUME_REVISION",fields
    return "UNEXPLAINED_MISMATCH","UNEXPLAINED_MISMATCH",fields


def classify_asset(market: str, code: str, a_stock_ids: set[str]) -> str:
    market, code = market.upper(), str(code)
    if market == "SH" and code.startswith("204") or market == "SZ" and code.startswith(("131", "139")):
        return "REPO"
    kind = classify_security(market, code, a_stock_ids)
    if kind == "A_STOCK":
        return "A_STOCK"
    if kind == "INDEX":
        return "INDEX"
    if kind == "FUND_OR_ETF":
        return "ETF_LOF"
    if kind == "CONVERTIBLE_BOND":
        return "BOND_CONVERTIBLE"
    return "OTHER"


def research_a_stock_ids(metadata_root: Path) -> set[str]:
    assignments = read_industry_assignments(metadata_root / "T0002" / "hq_cache" / "tdxhy.cfg")
    return current_a_stock_ids(assignments)


def sessions_from_index_chains(package_root: Path, count: int) -> list[int]:
    sessions: set[int] = set()
    for market, code in (("sh", "000001"), ("sz", "399001")):
        path = package_root / market / "lday" / f"{market}{code}.day"
        if not path.is_file() or path.stat().st_size % 32:
            raise ValueError(f"INDEX_CHAIN_MISSING_OR_MALFORMED:{path.name}")
        with path.open("rb") as stream:
            for record in __import__("struct").iter_unpack("<IIIIIfII", stream.read()):
                sessions.add(record[0])
    ordered = sorted(sessions)
    if len(ordered) < count:
        raise ValueError(f"INSUFFICIENT_ACTUAL_SESSIONS:{len(ordered)}<{count}")
    return ordered[-count:]


def parse_security_filename(path: Path, market_dir: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"(sh|sz|bj)(\d{6})\.day", path.name.lower())
    if not match or match.group(1) != market_dir.lower():
        return None
    return match.group(1).upper(), match.group(2)

