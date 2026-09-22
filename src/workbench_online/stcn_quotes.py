"""Bounded single-security STCN turnover fallback."""
from __future__ import annotations
import json
from typing import Callable,Iterable
from .base import FetchResult,OnlineFetchPolicy,bounded_get
SOURCE_ID="STCN_QUOTES_SINGLE";CONTRACT_ID="P12_16_STCN_TURNOVER_FALLBACK_V1";MAX_IDS=50
def _symbol(sid):
 exchange,code=str(sid).split(".",1);return exchange.lower()+code
def _number(value):
 try:return float(value)
 except (TypeError,ValueError):return None
def fetch_stcn_quotes(ids:Iterable[str],policy:OnlineFetchPolicy|None=None,*,fetcher:Callable[...,FetchResult]=bounded_get):
 policy=policy or OnlineFetchPolicy(timeout_seconds=3,max_response_bytes=200000,retries=0,cache_ttl_seconds=0);requested=list(dict.fromkeys(map(str,ids)))
 if not requested or len(requested)>MAX_IDS:raise ValueError("STCN_SECURITY_ID_LIMIT")
 rows=[];last=None
 for sid in requested:
  symbol=_symbol(sid);last=fetcher(f"https://www.stcn.com/quotes/stock-info.html?stock_code={symbol}",policy,referer=f"https://www.stcn.com/quotes/index/{symbol}.html")
  try:data=json.loads(last.body.decode("utf-8"))["data"]
  except (UnicodeDecodeError,json.JSONDecodeError,KeyError,TypeError):continue
  turnover=_number(data.get("turnoverrate"));price=_number(data.get("cv"));amount=_number(data.get("amo"));volume=_number(data.get("volume"))
  if None not in (turnover,price,amount,volume) and data.get("name"):
   rows.append({"source_id":SOURCE_ID,"source_contract_id":CONTRACT_ID,"field_map_version":"STCN_STOCK_INFO_V1","security_id":sid,"price":price,"amount":amount,"volume":volume,"turnover_rate":turnover/100,"turnover_basis":"STCN_SOURCE_DEFINED","normalized_turnover_basis":"SOURCE_DEFINED","basis_verification":"DECLARED_ONLY","observed_at_utc":last.received_at_utc,"source_float_shares":_number(data.get("oc")),"source_total_shares":_number(data.get("tc"))})
 return last,rows
__all__=["CONTRACT_ID","SOURCE_ID","fetch_stcn_quotes"]
