"""Descriptive evaluation of sealed forward observations; never model fitting."""
from __future__ import annotations
import hashlib,json
import numpy as np
import pandas as pd

VERSION="forward-evaluation-contract-v1.0"
MIN_OBSERVED_ROWS=30
MIN_SIGNAL_DATES=5
QUEUES={"STEADY":"steady_queue_tier","PULLBACK":"pullback_queue_tier","BREAKOUT":"breakout_queue_tier","LEADER":"leader_queue_tier","EARLY":"early_queue_tier"}

def bind_outcomes(observations:pd.DataFrame,outcomes:pd.DataFrame)->pd.DataFrame:
    if outcomes.empty:return pd.DataFrame()
    keys=["security_id","signal_observation_id","horizon","target_revision"]
    if outcomes.duplicated(keys).any():
        groups=outcomes.groupby(keys,dropna=False).apply(lambda x:len({hashlib.sha256(json.dumps(r,sort_keys=True,default=str).encode()).hexdigest() for r in x.to_dict("records")}),include_groups=False)
        if (groups>1).any():raise RuntimeError("CONFLICTING_OUTCOME_KEYS")
        outcomes=outcomes.drop_duplicates(keys)
    signal=observations.rename(columns={"observation_id":"signal_observation_id","observation_date":"signal_date_bound"})
    keep=["security_id","signal_observation_id","signal_date_bound",*[c for c in QUEUES.values() if c in signal]]
    if signal.duplicated(["security_id","signal_observation_id"]).any():raise RuntimeError("DUPLICATE_SIGNAL_BINDING")
    out=outcomes.merge(signal[keep],on=["security_id","signal_observation_id"],how="left",validate="many_to_one",indicator=True)
    if out._merge.ne("both").any():raise RuntimeError("UNBOUND_OUTCOME_SIGNAL")
    if "signal_date" in out and (out.signal_date.astype(str)!=out.signal_date_bound.astype(str)).any():raise RuntimeError("SIGNAL_DATE_BINDING_MISMATCH")
    return out.drop(columns=["_merge"])

def evaluate(bound:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for queue,tier_col in QUEUES.items():
        if bound.empty or tier_col not in bound:continue
        for (tier,horizon),g in bound[bound[tier_col].notna()].groupby([tier_col,"horizon"],dropna=False):
            observed=g[g.outcome_status.eq("OBSERVED")].copy();ret=pd.to_numeric(observed.forward_return,errors="coerce");high=pd.to_numeric(observed.max_high_return,errors="coerce");dd=pd.to_numeric(observed.max_drawdown,errors="coerce");valid=ret.notna()&high.notna()&dd.notna();observed=observed[valid];ret=ret[valid];high=high[valid];dd=dd[valid]
            dates=int(observed.signal_date_bound.astype(str).nunique());n=len(observed);sufficient=n>=MIN_OBSERVED_ROWS and dates>=MIN_SIGNAL_DATES
            rows.append({"queue":queue,"tier":tier,"horizon":int(horizon),"due_count":len(g),"observed_count":n,"data_unavailable_count":int(g.outcome_status.eq("DATA_UNAVAILABLE").sum()),"signal_date_count":dates,"sample_status":"SUFFICIENT_FOR_DESCRIPTION" if sufficient else "DATA_INSUFFICIENT","median_forward_return":float(ret.median()) if sufficient else None,"p25_forward_return":float(ret.quantile(.25)) if sufficient else None,"p75_forward_return":float(ret.quantile(.75)) if sufficient else None,"observed_positive_ratio":float((ret>0).mean()) if sufficient else None,"median_max_high_return":float(high.median()) if sufficient else None,"median_max_drawdown":float(dd.median()) if sufficient else None})
    return pd.DataFrame(rows)
