"""V2.1 pullback diagnostics with one explicit, shared peak anchor."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from shadow_v2.strong_pullback import segment_status,depth_status,volume_status,classify

RULESET_ID="strong-pullback-v2.1-shadow-v1.0-recent-peak-anchor"
CONTRACT_VERSION="strong-pullback-v2.1-shadow-contract-v1.0"

def anchored_diagnostics(dates,close,amount):
    """Use the latest maximum close for date, depth, duration and amount segments."""
    x=pd.DataFrame({"date":dates,"close":pd.to_numeric(close,errors="coerce"),"amount":pd.to_numeric(amount,errors="coerce")}).dropna().tail(20).reset_index(drop=True)
    if x.empty:return _empty("NO_VALID_WINDOW")
    peak=float(x.close.max());positions=np.flatnonzero(x.close.to_numpy()==peak);pos=int(positions[-1]);row=x.iloc[pos]
    advance=x.iloc[:pos+1].amount;pullback=x.iloc[pos+1:].amount
    advance_mean=float(advance.mean()) if len(advance)>=2 else np.nan
    pullback_mean=float(pullback.mean()) if len(pullback)>=1 else np.nan
    ratio=float(pullback_mean/advance_mean) if _finite(advance_mean) and advance_mean>0 and _finite(pullback_mean) else np.nan
    return {"peak_anchor_policy":"LATEST_MAX_CLOSE_IN_LAST_20_VALID_BARS","peak_date_v21":row.date,"peak_close_v21":peak,"days_since_peak_v21":int(len(x)-1-pos),"drawdown_from_peak_v21":float(x.close.iloc[-1]/peak-1),"advance_amount_mean_v21":advance_mean,"pullback_amount_mean_v21":pullback_mean,"pullback_amount_ratio_v21":ratio,"advance_bar_count_v21":int(len(advance)),"pullback_bar_count_v21":int(len(pullback)),"peak_bar_in_advance":True,"peak_bar_in_pullback":False,"diagnostic_status_v21":"OK" if _finite(ratio) else "SEGMENT_DATA_INSUFFICIENT"}

def classify_row(v1,row):
    segment=segment_status(row["days_since_peak_v21"]);depth=depth_status(row["drawdown_from_peak_v21"]);volume=volume_status(row["advance_amount_mean_v21"],row["pullback_amount_mean_v21"],row["pullback_amount_ratio_v21"])
    klass,hit,confirmed=classify(v1,segment,depth,volume)
    return {"segment_status_v21":segment,"depth_status_v21":depth,"volume_status_v21":volume,"v21_pullback_class":klass,"v21_pullback_structure_hit":hit,"v21_pullback_volume_confirmed":confirmed}

def _empty(status):
    return {"peak_anchor_policy":"LATEST_MAX_CLOSE_IN_LAST_20_VALID_BARS","peak_date_v21":None,"peak_close_v21":np.nan,"days_since_peak_v21":np.nan,"drawdown_from_peak_v21":np.nan,"advance_amount_mean_v21":np.nan,"pullback_amount_mean_v21":np.nan,"pullback_amount_ratio_v21":np.nan,"advance_bar_count_v21":0,"pullback_bar_count_v21":0,"peak_bar_in_advance":True,"peak_bar_in_pullback":False,"diagnostic_status_v21":status}

def _finite(v):
    try:return math.isfinite(float(v))
    except (TypeError,ValueError):return False
