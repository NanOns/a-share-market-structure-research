"""Read-only current-publication LOO breadth and relationship opportunity probe."""
from __future__ import annotations
import hashlib,json,os,sys,tempfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.today_research_rank_loo_v3_3 import current_loo,support_audit
OUT=ROOT/'reports/p12_04/current_loo_probe.json';DB=ROOT/'data/database/market_research.duckdb'
def main():
 with duckdb.connect(str(DB),read_only=True) as c:
  run,pub,target=c.execute("select run_id,publication_id,trade_date from research_runs where status='COMPLETE' order by trade_date desc,completed_at desc limit 1").fetchone();scope,rev,attrs=c.execute('select source_scope,revision_no,attribute_version_id from relation_publication_bindings where publication_id=?',[pub]).fetchone()
  snapshot=c.execute("select snapshot_id from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'",[pub]).fetchone()[0]
  tslice=c.execute("select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='technical' and trade_date=?",[snapshot,target]).fetchone()[0]
  edges=c.execute("""select distinct e.sector_id,e.security_id,a.type from relation_edge_intervals e join sector_attribute_revision_bindings ab on ab.source_scope=e.source_scope and ab.sector_id=e.sector_id and ab.from_attribute_revision<=? and (ab.to_attribute_revision is null or ab.to_attribute_revision>?) join sector_attribute_versions a on a.source_scope=ab.source_scope and a.sector_id=ab.sector_id and a.attribute_version_id=ab.attribute_version_id where e.source_scope=? and e.from_revision<=? and (e.to_revision is null or e.to_revision>?) and a.type in ('INDUSTRY','THEME')""",[rev,rev,scope,rev,rev]).fetchall()
  returns=dict(c.execute('select security_id,quote_ret1 from technical_result_daily where slice_id=?',[tslice]).fetchall());tracks=dict(c.execute('select sector_id,current_eligible from research_sector_states where run_id=?',[run]).fetchall())
 bysector=defaultdict(list);bystock=defaultdict(list)
 for sec,sid,typ in edges:bysector[sec].append({'security_id':sid,'ret1':returns.get(sid),'actual_bar':returns.get(sid) is not None});bystock[sid].append((sec,typ))
 audits={};cases=[]
 for sid,rels in sorted(bystock.items()):
  details=[]
  for sec,typ in rels:
   x=current_loo(sid,bysector[sec],tracks.get(sec));details.append({'sector_id':sec,'sector_type':typ,**x})
  audit=support_audit(details);audits[sid]=audit
  if len(cases)<6:cases.append({'security_id':sid,'relations':details,'audit':audit})
 bands={'1-2':Counter(),'3-5':Counter(),'6+':Counter()}
 for x in audits.values():
  band='1-2' if x['sector_relations_tested']<=2 else '3-5' if x['sector_relations_tested']<=5 else '6+'
  bands[band][str(x['support'])]+=1
 result={'stage_contract':'P12-04_CURRENT_LOO_PROBE_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'input_identity':{'run_id':run,'publication_id':pub,'trade_date':target.isoformat(),'snapshot_id':snapshot,'source_scope':scope,'relation_revision':rev,'attribute_version_id':attrs,'technical_slice':tslice},'unique_edges':len(edges),'stocks_with_relations':len(audits),'support_counts':dict(Counter(str(x['support']) for x in audits.values())),'relationship_band_support':{k:dict(v) for k,v in bands.items()},'stock_support_audit':audits,'six_real_stock_cases':cases,'support_method':'TRACK_PLUS_LOO_MEMBERS_V1','full_track_recomputed_without_target':False,'historical_change_loo_status':'UNKNOWN_HISTORIC_MEMBERSHIP','acceptance_result':'DEGRADED_PASS','next_stage':'P12-04_RANK_AND_LOO_V3_3_CONTINUE'}
 if len(cases)!=6 or sum(sum(v.values()) for v in bands.values())!=len(audits):result.update(acceptance_result='BLOCKED',next_stage='P12-04_REPAIR')
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2,allow_nan=False);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('LOO probe blocked')
 print(OUT)
if __name__=='__main__':main()
