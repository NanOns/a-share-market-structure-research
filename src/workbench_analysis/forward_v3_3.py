"""Immutable daily observations and descriptive forward reports for P12-08."""
from __future__ import annotations
import hashlib,json,os,tempfile
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

CONTRACT_ID="TODAY_RESEARCH_FORWARD_V3_3_CANDIDATE_04"
EPISODE_ID_CONTRACT="FORWARD_EPISODE_ID_V1"
MIN_SIGNAL_DAYS=20
MIN_EPISODES=50

def canonical(value:Any)->bytes:return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def digest(value:Any)->str:return hashlib.sha256(canonical(value)).hexdigest()
def atomic_write(path:Path,value:Any)->None:
 path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix="."+path.name+".",suffix=".tmp",dir=path.parent)
 try:
  with os.fdopen(fd,"wb") as stream:stream.write(canonical(value));stream.flush();os.fsync(stream.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def relation_band(count:int|None)->str:
 if count is None:return "UNKNOWN"
 return "1-2" if count<=2 else "3-5" if count<=5 else "6+"

def _episode_id(security_id:str,category:str|None,started_on:str)->str:
 value={"episode_id_contract":EPISODE_ID_CONTRACT,"security_id":security_id,"primary_category":category,"started_on":started_on}
 return "episode-"+digest(value)[:24]

def build_observation(active:dict,results:list[dict],relations:dict[str,dict]|None=None,previous:dict|None=None)->dict:
 relations=relations or {};rows=[];trade_date=active["identity"]["trade_date"]
 prior={row["security_id"]:row for row in (previous or {}).get("rows",[])}
 for item in results:
  sid=str(item["security_id"]);category=item.get("primary_category");rel=relations.get(sid,{});old=prior.get(sid)
  continues=bool(old and old.get("primary_category")==category and old.get("episode_id"))
  started_on=old.get("episode_started_on") if continues else trade_date
  episode_id=old.get("episode_id") if continues else _episode_id(sid,category,started_on)
  rows.append({"security_id":sid,"episode_id":episode_id,"episode_id_contract":EPISODE_ID_CONTRACT,"episode_started_on":started_on,"primary_category":category,"matched_categories":item.get("matched_categories",[]),"selection_mode":item.get("selection_mode"),"rank_status":item.get("rank_status"),"category_rank":item.get("category_rank"),"category_score":item.get("category_score"),"liq20_amount":item.get("liq20_amount"),"rps20":item.get("rps20"),"rps5_delta3":item.get("rps5_delta3"),"slope20":item.get("slope20"),"r2_20":item.get("r2_20"),"bias20":item.get("bias20"),"freshness":item.get("freshness"),"signal_age":item.get("signal_age"),"market_strength":item.get("market_strength"),"volatility":item.get("volatility"),"sector_relations_tested":rel.get("sector_relations_tested"),"relationship_band":relation_band(rel.get("sector_relations_tested")),"industry_relations_count":rel.get("industry_relations_count"),"theme_relations_count":rel.get("theme_relations_count"),"industry_support":rel.get("industry_support"),"theme_support":rel.get("theme_support")})
 logical={"contract_id":CONTRACT_ID,"trade_date":trade_date,"bundle_digest":active["output_digest"],"research_run_id":active["identity"]["research_run_id"],"rows":rows}
 return {**logical,"observation_digest":digest(logical)}

def transitions(previous:dict|None,current:dict)->dict:
 before={x["security_id"]:x for x in (previous or {}).get("rows",[])};after={x["security_id"]:x for x in current["rows"]};keys=sorted(set(before)|set(after));counts=Counter();items=[]
 for sid in keys:
  old,new=before.get(sid),after.get(sid)
  kind="ENTERED" if old is None else "EXITED" if new is None else "CATEGORY_CHANGED" if old.get("primary_category")!=new.get("primary_category") else "MODE_CHANGED" if old.get("selection_mode")!=new.get("selection_mode") else "CONTINUED"
  counts[kind]+=1;items.append({"security_id":sid,"transition":kind,"from_category":old and old.get("primary_category"),"to_category":new and new.get("primary_category"),"from_mode":old and old.get("selection_mode"),"to_mode":new and new.get("selection_mode")})
 return {"from_date":previous and previous.get("trade_date"),"to_date":current["trade_date"],"counts":dict(counts),"items":items}

def report(observations:list[dict])->dict:
 observations=sorted(observations,key=lambda x:x["trade_date"]);scenario=Counter();relation=defaultdict(Counter);episodes=set();candidate_rows=0;all_rows=[]
 for obs in observations:
  for row in obs["rows"]:
   candidate_rows+=1;all_rows.append(row);scenario[row.get("primary_category") or "UNKNOWN"]+=1;relation[row.get("relationship_band") or "UNKNOWN"][row.get("selection_mode") or "UNKNOWN"]+=1
   if row.get("episode_id"):episodes.add(row["episode_id"])
 trans=[transitions(observations[i-1] if i else None,obs) for i,obs in enumerate(observations)]
 gate={"minimum_signal_days":MIN_SIGNAL_DAYS,"minimum_independent_episodes":MIN_EPISODES,"signal_days":len(observations),"sealed_independent_episodes":len(episodes),"candidate_episode_upper_bound":candidate_rows,"episode_identity_status":"AVAILABLE" if candidate_rows and len(episodes)==candidate_rows else "INCOMPLETE"}
 def stats(field):
  values=sorted(float(row[field]) for row in all_rows if row.get(field) is not None)
  if not values:return {"available":0,"missing":len(all_rows),"status":"UNAVAILABLE"}
  pick=lambda q:values[round((len(values)-1)*q)]
  return {"available":len(values),"missing":len(all_rows)-len(values),"status":"AVAILABLE" if len(values)==len(all_rows) else "PARTIAL","min":values[0],"p25":pick(.25),"median":pick(.5),"p75":pick(.75),"max":values[-1]}
 durations=Counter(row["episode_id"] for row in all_rows if row.get("episode_id"));overlap=Counter(str(len(row.get("matched_categories") or [])) for row in all_rows)
 dimensions={"liquidity":stats("liq20_amount"),"volatility":stats("volatility"),"market_strength":stats("market_strength"),"industry_relation_coverage":stats("industry_relations_count"),"theme_relation_coverage":stats("theme_relations_count"),"overlap_degree_counts":dict(overlap),"episode_duration_observed_sessions":dict(Counter(str(value) for value in durations.values()))}
 return {"contract_id":CONTRACT_ID,"status":"EFFECT_OBSERVATION_READY" if gate["signal_days"]>=MIN_SIGNAL_DAYS and gate["sealed_independent_episodes"]>=MIN_EPISODES else "EFFECT_OBSERVATION_PENDING","gate":gate,"scenario_counts":dict(scenario),"relationship_band_by_mode":{k:dict(v) for k,v in relation.items()},"reporting_dimensions":dimensions,"transitions":trans,"observation_digests":[x["observation_digest"] for x in observations]}

def seal(root:Path,observation:dict)->dict:
 target=Path(root)/observation["trade_date"]/(observation["observation_digest"]+".json")
 if target.exists():
  if json.loads(target.read_text(encoding="utf-8"))!=observation:raise ValueError("FORWARD_OBSERVATION_DIGEST_CONFLICT")
  return {"path":str(target),"reused":True}
 atomic_write(target,observation);return {"path":str(target),"reused":False}
