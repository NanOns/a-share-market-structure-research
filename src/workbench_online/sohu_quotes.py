"""Bounded single-security Sohu turnover fallback."""
from __future__ import annotations
import ast,re
from typing import Callable,Iterable
from .base import FetchResult,OnlineFetchPolicy,bounded_get

SOURCE_ID="SOHU_QUOTES_SINGLE"; CONTRACT_ID="P12_16_SOHU_TURNOVER_FALLBACK_V1"; MAX_IDS=50

def _url(sid):
 code=str(sid).split(".",1)[1];return f"https://hq.stock.sohu.com/cn/{code[-3:]}/cn_{code}-1.html"
def _num(value):
 try:return float(str(value).replace(",","").replace("%",""))
 except (TypeError,ValueError):return None
def fetch_sohu_quotes(ids:Iterable[str],policy:OnlineFetchPolicy|None=None,*,fetcher:Callable[...,FetchResult]=bounded_get):
 policy=policy or OnlineFetchPolicy(timeout_seconds=3,max_response_bytes=200000,retries=0,cache_ttl_seconds=0)
 requested=list(dict.fromkeys(map(str,ids)))
 if not requested or len(requested)>MAX_IDS:raise ValueError("SOHU_SECURITY_ID_LIMIT")
 rows=[];digests=[];last=None
 for sid in requested:
  last=fetcher(_url(sid),policy,referer=f"https://q.stock.sohu.com/cn/{sid.split('.',1)[1]}/index.shtml");digests.append(last.raw_sha256)
  text=last.body.decode("gb18030",errors="replace");a1=re.search(r"['\"]?price_A1['\"]?\s*:(\[[^\]]*\])",text);a2=re.search(r"['\"]?price_A2['\"]?\s*:(\[[^\]]*\])",text)
  try:x1=ast.literal_eval(a1.group(1)) if a1 else [];x2=ast.literal_eval(a2.group(1)) if a2 else []
  except (SyntaxError,ValueError):x1,x2=[],[]
  price=_num(x1[2]) if len(x1)>2 else None;turnover=_num(x2[6]) if len(x2)>6 else None;volume=_num(x2[8]) if len(x2)>8 else None;amount=_num(x2[12]) if len(x2)>12 else None
  if None not in (price,turnover,volume,amount):rows.append({"source_id":SOURCE_ID,"source_contract_id":CONTRACT_ID,"field_map_version":"SOHU_PRICE_A1_A2_V1","security_id":sid,"price":price,"volume":volume*100,"amount":amount*10000,"turnover_rate":turnover/100,"turnover_basis":"SOHU_SOURCE_DEFINED","normalized_turnover_basis":"SOURCE_DEFINED","basis_verification":"DECLARED_ONLY","observed_at_utc":last.received_at_utc})
 return last,rows

__all__=["CONTRACT_ID","SOURCE_ID","fetch_sohu_quotes"]
