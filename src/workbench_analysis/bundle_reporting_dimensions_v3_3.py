"""Attach versioned same-day reporting dimensions to P12 result rows."""
from __future__ import annotations
from typing import Iterable

CONTRACT_ID="TODAY_RESEARCH_REPORTING_DIMENSIONS_V3_3_CANDIDATE_01"
MARKET_STRENGTH_CONTRACT="MARKET_RET20_MEDIAN_V1"
VOLATILITY_CONTRACT="FACTOR_VOLATILITY20_V1"

def enrich(rows:list[dict],market_rows:Iterable[dict],factor_rows:Iterable[dict],trade_date:str)->list[dict]:
 market=[row for row in market_rows if str(row.get("date"))[:10]==trade_date]
 if len(market)!=1 or market[0].get("market_ret20_median") is None:raise ValueError("MARKET_STRENGTH_UNAVAILABLE")
 strength=float(market[0]["market_ret20_median"]);factors={str(row["security_id"]):row for row in factor_rows if str(row.get("date"))[:10]==trade_date}
 output=[]
 for row in rows:
  factor=factors.get(str(row["security_id"]));value=None if not factor else factor.get("VOLATILITY20")
  if value is None:raise ValueError("VOLATILITY20_UNAVAILABLE:"+str(row["security_id"]))
  output.append({**row,"market_strength":strength,"market_strength_contract":MARKET_STRENGTH_CONTRACT,"volatility":float(value),"volatility_contract":VOLATILITY_CONTRACT})
 return output
