import json
from workbench_online.base import FetchResult,OnlineFetchPolicy
from workbench_online.sohu_quotes import fetch_sohu_quotes
from workbench_online.stcn_quotes import fetch_stcn_quotes

def result(body):return FetchResult("a","b",200,"text/plain",body,"url")
def test_sohu_single_normalizes_quote():
 body=b"'price_A1':['','','10.5'],'price_A2':['','','','','','','3.2','','123','','','','456']"
 _,rows=fetch_sohu_quotes(["SZ.000001"],OnlineFetchPolicy(),fetcher=lambda *_a,**_k:result(body))
 assert rows[0]["turnover_rate"]==.032 and rows[0]["volume"]==12300 and rows[0]["amount"]==4560000
def test_stcn_single_normalizes_quote():
 body=json.dumps({"data":{"name":"A","turnoverrate":"4.5","cv":"10","amo":"1000","volume":"200","oc":"300","tc":"400"}}).encode()
 _,rows=fetch_stcn_quotes(["SH.600000"],OnlineFetchPolicy(),fetcher=lambda *_a,**_k:result(body))
 assert rows[0]["turnover_rate"]==.045 and rows[0]["source_float_shares"]==300
def test_router_contract_uses_requested_priority():
 from pathlib import Path
 root=Path(__file__).resolve().parents[2];value=json.loads((root/"config/p12_16_turnover_fallback_router_v1.json").read_text(encoding="utf-8"))
 assert value["priority"]==["TENCENT_QUOTES_LATEST","SOHU_QUOTES_SINGLE","STCN_QUOTES_SINGLE"]
