from __future__ import annotations
import hashlib,json,sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from adjustment.tdx_adjustment import XrxdEvent,xrxd_from_gbbq
from common.paths import resolve_tdx_root
from tdx.gbbq_reader import read_gbbq
from tdx.security_master import read_tnf
from workbench_analysis.forward_outcome_materializer_v3_3 import CONTRACT_ID,materialize
from workbench_analysis.forward_v3_3 import atomic_write,digest

PARQUET=ROOT/"data/normalized/adjusted_daily.parquet"

def freeze_evaluation_source(plan:dict)->dict:
 due=[row for row in plan["rows"] if row["status"]=="DUE_UNMATERIALIZED"]
 if not due:return {"contract_id":"P12_FORWARD_EVALUATION_SOURCE_V1","bars":[],"events":[],"source_digest":"NOT_CONSUMED_NOT_DUE"}
 securities=sorted({row["security_id"] for row in due});start=min(row["signal_date"] for row in due);end=max(row["end_date"] for row in due)
 with duckdb.connect(database=":memory:") as connection:
  rows=connection.execute("select security_id,cast(date as varchar),raw_high,raw_low,raw_close,has_actual_bar from read_parquet(?) where security_id in (select unnest(?)) and date between ? and ? order by security_id,date",[str(PARQUET),securities,start,end]).fetchall()
 tdx=resolve_tdx_root(ROOT);current_ids=set()
 for filename,market in (("shs.tnf","SH"),("szs.tnf","SZ"),("bjs.tnf","BJ")):
  path=tdx/"T0002/hq_cache"/filename
  if path.is_file():current_ids.update(read_tnf(path,market)[0])
 bars=[{"security_id":sid,"trade_date":day,"raw_high":float(hi) if hi is not None else None,"raw_low":float(lo) if lo is not None else None,"raw_close":float(close) if close is not None else None,"has_actual_bar":bool(actual),"no_quote_status":None if actual else ("SUSPENDED" if sid in current_ids else "DELISTED")} for sid,day,hi,lo,close,actual in rows]
 present={(row["security_id"],row["trade_date"]) for row in bars}
 for item in due:
  key=(item["security_id"],item["end_date"])
  if key not in present:
   bars.append({"security_id":key[0],"trade_date":key[1],"raw_high":None,"raw_low":None,"raw_close":None,"has_actual_bar":False,"no_quote_status":"SUSPENDED" if key[0] in current_ids else "DELISTED"})
 events=[];wanted=set(securities);gbbq=resolve_tdx_root(ROOT)/"T0002/hq_cache/gbbq"
 for record in read_gbbq(gbbq):
  if record.category==1 and record.security_id in wanted and int(start.replace('-',''))<record.event_date<=int(end.replace('-','')):events.append(xrxd_from_gbbq(record).as_dict())
 logical={"contract_id":"P12_FORWARD_EVALUATION_SOURCE_V1","signal_date_from":start,"evaluation_date_to":end,"security_ids":securities,"bars":bars,"events":events,"adjusted_daily_sha256":hashlib.sha256(PARQUET.read_bytes()).hexdigest(),"gbbq_sha256":hashlib.sha256(gbbq.read_bytes()).hexdigest()}
 source={**logical,"source_digest":digest(logical)};atomic_write(ROOT/"data/forward_v3_3/evaluation_sources"/(source["source_digest"]+".json"),source);return source

def restore_events(source:dict)->dict[str,list[XrxdEvent]]:
 grouped=defaultdict(list)
 for row in source["events"]:
  grouped[row["security_id"]].append(XrxdEvent(row["security_id"],row["event_date"],Decimal(str(row["cash_dividend"])),Decimal(str(row["rights_price"])),Decimal(str(row["bonus_transfer"])),Decimal(str(row["rights_ratio"])),row["source_record_index"]))
 return grouped

def main():
 plan=json.loads((ROOT/"reports/p12_08/outcome_plan.json").read_text(encoding="utf-8"));source=freeze_evaluation_source(plan)
 result=materialize(plan,source["bars"],restore_events(source),evaluation_source_hash=source["source_digest"]);out=ROOT/"reports/p12_08/outcome_results.json";atomic_write(out,result)
 due=sum(row["status"]!="NOT_DUE" for row in plan["rows"]);accounted=sum(result["summary"].get(key,0) for key in ("OBSERVED","DATA_GAP","SUSPENDED","DELISTED"))
 acceptance="DEGRADED_PASS" if accounted==due else "BLOCKED"
 gaps=[{"security_id":row["security_id"],"status":row["status"],"reason":row["reason"]} for row in result["rows"] if row["status"] in ("DATA_GAP","SUSPENDED","DELISTED")]
 receipt={"stage":"P12-08C_FORWARD_OUTCOME_MATERIALIZATION","contract_id":CONTRACT_ID,"evaluation_source_contract":source["contract_id"],"evaluation_source_digest":source["source_digest"],"acceptance":acceptance,"result_path":str(out),"result_digest":result["result_digest"],"summary":result["summary"],"real_due_rows":due,"data_gaps":gaps,"effect_status":"EFFECT_OBSERVATION_PENDING","tdx_modified":False,"next_stage":"NEXT_REAL_CLOSE_OBSERVATION" if acceptance!="BLOCKED" else "P12-08C_REPAIR"}
 atomic_write(ROOT/"reports/p12_08/p12_08c_stage_gate.json",receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
 if acceptance=="BLOCKED":raise SystemExit("P12_08C_MATERIALIZATION_BLOCKED")
if __name__=="__main__":main()
