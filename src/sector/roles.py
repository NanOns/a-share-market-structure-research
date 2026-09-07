from __future__ import annotations


EXCLUDED_THEME_NAMES = frozenset(
    {
        "ST板块",
        "含H股",
        "含B股",
        "通达信88",
        "次新股",
        "含可转债",
    }
)


def sector_role(sector_type: str, sector_name: str) -> str:
    if sector_type == "industry":
        return "INDUSTRY"
    if sector_type == "style":
        return "STYLE"
    if sector_type == "concept" and sector_name in EXCLUDED_THEME_NAMES:
        return "EXCLUDE_FROM_THEME_RANK"
    if sector_type == "concept":
        return "THEME"
    return "STRUCTURAL_TAG"

