"""Read-only inventory of structured candidate scenario evidence."""
from __future__ import annotations

from collections import Counter, defaultdict

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository


def main() -> int:
    with PostgresRepository(dsn=_dsn()) as repo:
        with repo.connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select max(trade_date) from workbench.publication_heads")
            day = cur.fetchone()[0]
        sources = read_accepted_sources(repo, day)
        repo.connection.rollback()
    candidates = [row for row in sources.rows
                  if row.key.source_family == "V3_3_TODAY_CANDIDATE"]
    categories = Counter(row.source_focus_class for row in candidates)
    factor_keys = defaultdict(Counter)
    scanner_keys = defaultdict(Counter)
    scanner_types = defaultdict(Counter)
    nested_keys = defaultdict(Counter)
    nested_flags = defaultdict(Counter)
    check_keys = defaultdict(Counter)
    check_values = defaultdict(Counter)
    for row in candidates:
        category = row.source_focus_class
        factors = row.source_facts.get("factor_evidence") or {}
        scanner = row.source_facts.get("scanner_evidence") or {}
        for key, value in factors.items():
            if value is not None:
                factor_keys[category][key] += 1
        for key, value in scanner.items():
            scanner_keys[category][key] += 1
            scanner_types[category][f"{key}:{type(value).__name__}"] += 1
            if isinstance(value, dict):
                for nested, nested_value in value.items():
                    nested_keys[f"{category}/{key}"][nested] += 1
                    if isinstance(nested_value, bool) or nested_value is None:
                        nested_flags[f"{category}/{key}"][f"{nested}:{nested_value}"] += 1
                    if nested == "checks" and isinstance(nested_value, dict):
                        for check in nested_value:
                            check_keys[f"{category}/{key}"][check] += 1
                        for check in ("NOT_STRUCTURE_BREAK", "NOT_EXTENDED"):
                            if check in nested_value:
                                check_values[f"{category}/{key}"][f"{check}:{nested_value[check]}"] += 1
    watched = {"phh20", "ma5", "ma20", "reclaim_ma5", "reclaim_ma20",
               "rps20", "rps20_delta3", "structure_break_v3",
               "structure_break", "extended", "pullback_invalid_low",
               "trend_key_low"}
    print({"trade_date": str(day), "categories": dict(categories),
           "factor_presence": {category: {key: count for key, count in counts.items()
                                            if key in watched}
                               for category, counts in factor_keys.items()},
           "scanner_keys": {category: dict(counts)
                            for category, counts in scanner_keys.items()},
           "scanner_types": {category: dict(counts)
                             for category, counts in scanner_types.items()},
           "nested_keys": {category: dict(counts)
                           for category, counts in nested_keys.items()},
           "nested_flags": {category: dict(counts)
                            for category, counts in nested_flags.items()},
           "check_keys": {category: dict(counts)
                          for category, counts in check_keys.items()},
           "check_values": {category: dict(counts)
                            for category, counts in check_values.items()}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
