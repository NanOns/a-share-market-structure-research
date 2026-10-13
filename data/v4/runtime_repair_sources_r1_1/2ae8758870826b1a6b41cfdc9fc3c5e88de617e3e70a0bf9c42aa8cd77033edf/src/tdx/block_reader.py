from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re

from .security_master import MARKET_NUMBER_TO_NAME


MEMBER_RE = re.compile(r"([012])#(\d{6})")


def read_industry_names(path: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    text = path.read_bytes().decode("gb18030", errors="replace")
    for line in text.splitlines():
        fields = line.strip().split("|")
        if len(fields) >= 6 and fields[5]:
            names[fields[5]] = fields[0]
    return names


def build_industry_memberships(assignments: list[dict], names: dict[str, str]) -> list[dict]:
    result = []
    for item in assignments:
        code = item.get("industry_code")
        if not code:
            continue
        result.append(
            {
                "sector_type": "industry",
                "sector_code": code,
                "sector_name": names.get(code, code),
                "security_id": item["security_id"],
                "membership_basis": "CURRENT_TDX_MEMBERSHIP",
                "source": "tdxhy.cfg",
            }
        )
    return result


def read_infoharbor_memberships(path: Path) -> tuple[list[dict], dict]:
    text = path.read_bytes().decode("gb18030", errors="replace")
    memberships: list[dict] = []
    header_counts: Counter[str] = Counter()
    sector_headers: list[dict] = []
    current: tuple[str, str, str] | None = None
    prefix_map = {"GN": "concept", "FG": "style", "ZS": "index_group"}
    for line in text.splitlines():
        if line.startswith("#"):
            header = line[1:].split(",")
            label = header[0]
            if "_" not in label:
                current = None
                continue
            prefix, name = label.split("_", 1)
            header_counts[prefix] += 1
            sector_type = prefix_map.get(prefix)
            if not sector_type:
                current = None
                continue
            sector_code = header[2].strip() if len(header) > 2 and header[2].strip() else name
            current = (sector_type, sector_code, name)
            sector_headers.append(
                {"sector_type": sector_type, "sector_code": sector_code, "sector_name": name}
            )
            continue
        if not current:
            continue
        for match in MEMBER_RE.finditer(line):
            market_number, code = match.groups()
            memberships.append(
                {
                    "sector_type": current[0],
                    "sector_code": current[1],
                    "sector_name": current[2],
                    "security_id": f"{MARKET_NUMBER_TO_NAME[market_number]}.{code}",
                    "membership_basis": "CURRENT_TDX_MEMBERSHIP",
                    "source": "infoharbor_block.dat",
                }
            )
    return memberships, {
        "headers_by_prefix": dict(sorted(header_counts.items())),
        "sector_headers": sector_headers,
    }


def membership_audit(
    memberships: list[dict],
    known_security_ids: set[str],
    valid_latest_ids: set[str],
    a_stock_ids: set[str],
    minimums: dict[str, int] | None = None,
    minimum_valid_on_date: int = 5,
    minimum_coverage: float = 0.70,
) -> dict:
    minimums = minimums or {"industry": 5, "concept": 8, "style": 8}
    exact_keys = [
        (m["sector_type"], m["sector_code"], m["security_id"])
        for m in memberships
        if m["sector_type"] in minimums
    ]
    duplicate_count = len(exact_keys) - len(set(exact_keys))
    groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for item in memberships:
        if item["sector_type"] in minimums:
            groups[(item["sector_type"], item["sector_code"], item["sector_name"])].add(item["security_id"])

    rows = []
    for (sector_type, sector_code, sector_name), members in groups.items():
        resolved = members & known_security_ids
        a_members = resolved & a_stock_ids
        valid = a_members & valid_latest_ids
        coverage = len(valid) / len(a_members) if a_members else 0.0
        min_members = minimums[sector_type]
        eligible = (
            len(a_members) >= min_members
            and len(valid) >= minimum_valid_on_date
            and coverage >= minimum_coverage
        )
        rows.append(
            {
                "sector_type": sector_type,
                "sector_code": sector_code,
                "sector_name": sector_name,
                "total_member_count": len(members),
                "resolved_member_count": len(resolved),
                "a_stock_member_count": len(a_members),
                "valid_latest_member_count": len(valid),
                "member_coverage_ratio": round(coverage, 6),
                "eligible": eligible,
            }
        )

    by_type = {}
    for sector_type in minimums:
        typed = [row for row in rows if row["sector_type"] == sector_type]
        by_type[sector_type] = {
            "sector_count": len(typed),
            "eligible_sector_count": sum(row["eligible"] for row in typed),
            "member_records": sum(row["total_member_count"] for row in typed),
            "resolved_member_records": sum(row["resolved_member_count"] for row in typed),
            "a_stock_member_records": sum(row["a_stock_member_count"] for row in typed),
            "valid_latest_member_records": sum(row["valid_latest_member_count"] for row in typed),
        }

    all_members = [m for m in memberships if m["sector_type"] in minimums]
    unresolved = sorted({m["security_id"] for m in all_members if m["security_id"] not in known_security_ids})
    return {
        "membership_record_count": len(all_members),
        "unique_membership_count": len(set(exact_keys)),
        "duplicate_membership_count": duplicate_count,
        "unmatched_security_count": len(unresolved),
        "unmatched_security_samples": unresolved[:30],
        "by_type": by_type,
        "validity_parameters": {
            "min_sector_members": minimums,
            "min_valid_members_on_date": minimum_valid_on_date,
            "min_member_coverage_ratio": minimum_coverage,
        },
        "sector_samples": sorted(rows, key=lambda row: (row["sector_type"], row["sector_code"]))[:30],
    }
