"""V2 research-queue ordering.  Ordering is lexicographic, never additive."""
from __future__ import annotations
import pandas as pd

VERSION = "v2-queue-ranking-contract-v1.1-quality-dimension-name"

SPECS = {
    "steady": [("up_day_ratio20", False), ("trend_r2_20", False), ("trend_r2_60", False), ("mdd20", False), ("rs20", False)],
    "pullback": [("v2_pullback_volume_confirmed", False), ("pullback_amount_ratio", True), ("TREND_R2_60", False), ("RS60", False), ("MDD20", False)],
    "breakout": [("range_contraction_ratio", True), ("realized_vol_contraction_ratio", True), ("DIST_HIGH20", False), ("TREND_R2_20", False), ("RS20", False)],
    "leader": [("quality_dimension_strong_support_count", False), ("member_rs20_pct", False), ("member_trend_r2_20_pct", False), ("member_mdd20_quality_pct", False), ("sector_rs20_pct", False)],
    "early": [("stock_rs5_pct", False), ("RET5", False), ("AMOUNT_RATIO_5_20", False), ("TREND_R2_20", False), ("POS60", True)],
}

def rank_queues(board: pd.DataFrame, details: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return one row per security with auditable queue and tier ranks.

    Tier is the first ordering key. Missing evidence is always last. security_id is
    only a stable display tie-break and does not change the dense economic rank.
    """
    result = board[["security_id"]].copy()
    for key, spec in SPECS.items():
        tier_col=f"{key}_queue_tier"; source=details[key]
        x=board[["security_id",tier_col]].merge(source[["security_id",*[c for c,_ in spec]]],on="security_id",how="left",validate="one_to_one")
        x=x[x[tier_col].notna()].copy(); x["_tier"]=x[tier_col].map({"CORE":0,"SUPPORTED":1}).fillna(2)
        sort_cols=["_tier"]
        asc=[True]
        normalized=[]
        for i,(col,ascending) in enumerate(spec):
            n=f"_k{i}"; x[n]=pd.to_numeric(x[col],errors="coerce")
            normalized.append(n);sort_cols.append(n);asc.append(ascending)
        economic=list(zip(x["_tier"],*[x[c].where(x[c].notna(), float("inf") if a else float("-inf")) for c,a in zip(normalized,[a for _,a in spec])]))
        # Factorize sorted economic tuples so exact ties share rank; code is excluded.
        ordered=x.assign(_economic=economic).sort_values(sort_cols+["security_id"],ascending=asc+[True],na_position="last")
        tuples=ordered["_economic"].tolist(); rank=[]; last=object(); current=0
        for value in tuples:
            if value!=last: current+=1;last=value
            rank.append(current)
        ordered[f"{key}_queue_rank"]=rank
        tier_rank=[];last_tier=object();last_economic=object();current=0
        for tier,value in zip(ordered[tier_col],tuples):
            evidence=value[1:]
            if tier!=last_tier: last_tier=tier;last_economic=object();current=0
            if evidence!=last_economic: current+=1;last_economic=evidence
            tier_rank.append(current)
        ordered[f"{key}_tier_rank"]=tier_rank
        result=result.merge(ordered[["security_id",f"{key}_queue_rank",f"{key}_tier_rank"]],on="security_id",how="left",validate="one_to_one")
    return result
