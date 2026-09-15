from __future__ import annotations
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from production.release import atomic_write_json
from workbench_analysis.bundle_reporting_dimensions_v3_3 import CONTRACT_ID as DIMENSION_CONTRACT,MARKET_STRENGTH_CONTRACT,VOLATILITY_CONTRACT,enrich
from workbench_service.research_bundle_v3_3 import activate_bundle,build_bundle,read_active
BUNDLE_CONTRACT="TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02";POINTER=ROOT/"data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 rank=json.loads((ROOT/"reports/p12_04/current_rank_probe.json").read_text(encoding="utf-8"));previous=read_active(POINTER);day=rank["input_identity"]["trade_date"]
 if previous["identity"]["trade_date"]!=day:raise ValueError("ACTIVE_BASE_BUNDLE_DATE_MISMATCH")
 market_path=ROOT/"data/market/market_regime_daily.parquet";factor_path=ROOT/"data/factors/factors_daily.parquet"
 with duckdb.connect(database=":memory:") as connection:
  market=connection.execute("select date,market_ret20_median from read_parquet(?) where date=?",[str(market_path),day]).fetchdf().to_dict("records")
  ids=[row["security_id"] for row in rank["ranked_rows"]];factors=connection.execute("select security_id,date,VOLATILITY20 from read_parquet(?) where date=? and security_id in (select unnest(?))",[str(factor_path),day,ids]).fetchdf().to_dict("records")
 results=enrich(rank["ranked_rows"],market,factors,day);source_hashes={"rank":sha(ROOT/"reports/p12_04/current_rank_probe.json"),"market":sha(market_path),"factors":sha(factor_path)}
 identity={**previous["identity"],"research_run_id":"p12-08e-"+hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()[:24],"parameter_hash":hashlib.sha256(b"parameters-v3_3-candidate-02-reporting-dimensions").hexdigest()}
 contracts={"bundle":BUNDLE_CONTRACT,"reporting_dimensions":DIMENSION_CONTRACT,"market_strength":MARKET_STRENGTH_CONTRACT,"volatility":VOLATILITY_CONTRACT,"source_hashes":source_hashes,"effect_status":"EFFECT_OBSERVATION_PENDING"}
 built=build_bundle(ROOT/"data/research_bundles_v3_3",identity,results,contracts,bundle_contract=BUNDLE_CONTRACT);active=activate_bundle(Path(built["path"]),POINTER);verified=read_active(POINTER)
 receipt={"stage":"P12-08E_REPORTING_DIMENSIONS_BUNDLE","acceptance":"DEGRADED_PASS","bundle":built,"active_contract":active["contract_id"],"trade_date":day,"result_rows":len(results),"market_strength_available":sum(row["market_strength"] is not None for row in results),"volatility_available":sum(row["volatility"] is not None for row in results),"source_hashes":source_hashes,"pointer_verified":verified["output_digest"]==built["output_digest"],"previous_bundle_digest":previous["output_digest"],"tdx_modified":False,"next_stage":"P12_08E_FORWARD_RESEAL"}
 atomic_write_json(ROOT/"reports/p12_08/p12_08e_stage_gate.json",receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
