"""V4 calendar-aligned pure rank comparison, extracted unchanged from frozen helper.

Contract V4_PURE_RANK_WINDOW_COMPARISON_R1. No repository or database capability.
"""
from typing import Any
import pandas as pd
from workbench_analysis.sector_cycle import CONTRACT_VERSION as SECTOR_CYCLE_CONTRACT

CONTRACT_ID='V4_PURE_RANK_WINDOW_COMPARISON_R1'

def _exact_cycle_delta(cycle: pd.DataFrame, today: Any, prior: Any, config: dict[str, Any]) -> pd.DataFrame:
    """Compare calendar-aligned ranks only when both cross sections are stable."""
    today, prior = pd.Timestamp(today).date(), pd.Timestamp(prior).date()
    current = cycle.loc[cycle.trade_date.eq(today), ["sector_id", "sector_type", "q5"]]
    earlier = cycle.loc[cycle.trade_date.eq(prior) & cycle.contract_id.eq(SECTOR_CYCLE_CONTRACT), ["sector_id", "sector_type", "q5"]]
    coverage = config["thresholds"]["coverage"]
    rows = []
    for sector_type, group in current.groupby("sector_type", sort=False):
        old = earlier[earlier.sector_type.eq(sector_type)]
        now_ids = set(group.loc[pd.to_numeric(group.q5, errors="coerce").notna(), "sector_id"])
        old_ids = set(old.loc[pd.to_numeric(old.q5, errors="coerce").notna(), "sector_id"])
        union = now_ids | old_ids
        change = abs(len(now_ids) - len(old_ids)) / max(len(now_ids), len(old_ids)) if union else 1.0
        overlap = len(now_ids & old_ids) / len(union) if union else 0.0
        comparable = change <= coverage["max_rank_universe_change"] and overlap >= coverage["min_rank_intersection_union"]
        old_q5 = old.set_index("sector_id").q5
        for row in group.itertuples(index=False):
            previous = old_q5.get(row.sector_id)
            value = float(row.q5 - previous) if comparable and pd.notna(row.q5) and pd.notna(previous) else None
            rows.append({"sector_id": row.sector_id, "dq5_3": value})
    return pd.DataFrame(rows, columns=["sector_id", "dq5_3"])
