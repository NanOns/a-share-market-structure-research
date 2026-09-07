from __future__ import annotations

from collections import Counter
from pathlib import Path
import re


MARKET_NUMBER_TO_NAME = {"0": "SZ", "1": "SH", "2": "BJ"}
TNF_HEADER_LENGTH = 50
TNF_RECORD_LENGTH = 360


def decode_text(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("gb18030", errors="replace").strip()


def read_tnf(path: Path, market: str) -> tuple[dict[str, str], dict]:
    raw = path.read_bytes()
    remainder = (len(raw) - TNF_HEADER_LENGTH) % TNF_RECORD_LENGTH
    names: dict[str, str] = {}
    invalid_codes = 0
    if len(raw) >= TNF_HEADER_LENGTH:
        payload = raw[TNF_HEADER_LENGTH : len(raw) - remainder if remainder else len(raw)]
        for offset in range(0, len(payload), TNF_RECORD_LENGTH):
            record = payload[offset : offset + TNF_RECORD_LENGTH]
            code = decode_text(record[0:6])
            if not re.fullmatch(r"\d{6}", code):
                invalid_codes += 1
                continue
            # Current TNF records place the GB18030 name at byte 31.  Byte 30
            # is a zero separator; starting there would silently erase names.
            name = decode_text(record[31:55])
            names[f"{market.upper()}.{code}"] = name
    return names, {
        "path": str(path),
        "header_length": TNF_HEADER_LENGTH,
        "record_length": TNF_RECORD_LENGTH,
        "record_count": max(0, (len(raw) - TNF_HEADER_LENGTH) // TNF_RECORD_LENGTH),
        "tail_remainder": remainder,
        "valid_code_records": len(names),
        "invalid_code_records": invalid_codes,
    }


def read_industry_assignments(path: Path) -> list[dict]:
    assignments: list[dict] = []
    text = path.read_bytes().decode("gb18030", errors="replace")
    for line_number, line in enumerate(text.splitlines(), 1):
        fields = line.strip().split("|")
        if len(fields) < 3 or fields[0] not in MARKET_NUMBER_TO_NAME:
            continue
        code = fields[1]
        if not re.fullmatch(r"\d{6}", code):
            continue
        assignments.append(
            {
                "security_id": f"{MARKET_NUMBER_TO_NAME[fields[0]]}.{code}",
                "market": MARKET_NUMBER_TO_NAME[fields[0]],
                "code": code,
                "industry_code": fields[2] or None,
                "line_number": line_number,
            }
        )
    return assignments


def classify_security(market: str, code: str, current_a_stock_ids: set[str]) -> str:
    security_id = f"{market.upper()}.{code}"
    # tdxhy.cfg also contains B shares.  Those explicit non-A ranges must be
    # rejected before industry membership is used as positive evidence.
    if (market.upper() == "SH" and code.startswith("900")) or (
        market.upper() == "SZ" and code.startswith("200")
    ):
        return "B_STOCK"
    if security_id in current_a_stock_ids:
        return "A_STOCK"
    if market.upper() == "SH":
        if re.match(r"^(600|601|603|605|688|689)\d{3}$", code):
            return "A_STOCK"
        if code.startswith("000"):
            return "INDEX"
        if code.startswith(("110", "111", "113", "118")):
            return "CONVERTIBLE_BOND"
        if code.startswith(("50", "51", "52", "56", "58")):
            return "FUND_OR_ETF"
    elif market.upper() == "SZ":
        if re.match(r"^(000|001|002|003|300|301)\d{3}$", code):
            return "A_STOCK"
        if code.startswith("399"):
            return "INDEX"
        if code.startswith(("123", "127", "128")):
            return "CONVERTIBLE_BOND"
        if code.startswith(("15", "16", "18")):
            return "FUND_OR_ETF"
    elif market.upper() == "BJ":
        if code.startswith(("4", "8", "92")):
            return "A_STOCK"
        if code.startswith("899"):
            return "INDEX"
    return "OTHER"


def current_a_stock_ids(assignments: list[dict]) -> set[str]:
    """Return current A-share ids, excluding the known local B-share ranges."""
    return {
        item["security_id"]
        for item in assignments
        if not (
            (item["market"] == "SH" and item["code"].startswith("900"))
            or (item["market"] == "SZ" and item["code"].startswith("200"))
        )
    }


def summarize_types(day_results: list[dict], current_a_stock_ids: set[str]) -> dict:
    counts = Counter(
        classify_security(item["market"], item["code"], current_a_stock_ids)
        for item in day_results
    )
    return dict(sorted(counts.items()))
