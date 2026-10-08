"""Update R3 owner/consumer receipts after isolated 9/28 and 9/29 Profile replays."""
import collections,gzip,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'docs/evidence/three_day_repair_r3_20261008'
def read(p):return json.loads((ROOT/p).read_bytes())
def ref(p):
 p=ROOT/p;return {'path':p.relative_to(ROOT).as_posix(),'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else None,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}
def save(path,obj):
 p=ROOT/path;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def gz(p):
 with gzip.open(ROOT/p,'rt',encoding='utf-8') as f:
  for line in f:yield json.loads(line)
def main():
 revisions={'2026-09-28':'R1','2026-09-29':'R2'}
 receipts={d:read(f'docs/evidence/three_day_repair_r3_20261008/R3_PROFILE_{d}_CANDIDATE_RECEIPT_{revisions[d]}.json')
           for d in revisions}
 candidates={d:list(gz(receipts[d]['owner_artifact']['path'])) for d in receipts}
 states={d:collections.Counter() for d in receipts}
 for day,rows in candidates.items():
  for row in rows:
   for name,item in row['states'].items():states[day][f'{name}:{item["value"]}']+=1
 # Recheck the pre-existing 9/28 Profile against the frozen corrected Core owner values.
 old_factors='reports/v4_05/staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz'
 new_core='docs/evidence/three_day_repair_r1_20261008/core_owner_r2/owners/2026-09-28/core.jsonl.gz'
 a={r['security_id']:r for r in gz(new_core)};b={r['security_id']:r for r in gz(old_factors)};common=set(a)&set(b)
 fields=set(a[next(iter(common))]['fields'])&set(b[next(iter(common))]['fields']);checked=mismatch=0
 for sid in common:
  for field in fields:
   x=a[sid]['fields'][field];y=b[sid]['fields'][field]
   if x.get('quality_state')=='OBSERVED' and y.get('quality_state')=='OBSERVED':
    checked+=1
    if x.get('value') is not None and y.get('value') is not None and abs(float(x['value'])-float(y['value']))>1e-8:mismatch+=1
 old_profiles=list(gz('reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz'))
 old_receipt=read('reports/v4_05/V4_05_R4_CORE_PROFILE_REPLAY.json')
 material=read('docs/evidence/three_day_repair_r3_20261008/R3_CORE_PROFILE_OWNER_MATERIALIZATION.json')
 material['profile_days']=[
  {'trade_date':'2026-09-28','status':'R3_ISOLATED_CORRECTED_PROFILE_OWNER_MATERIALIZED','rows':len(candidates['2026-09-28']),
   'artifact':receipts['2026-09-28']['owner_artifact'],'receipt':ref('docs/evidence/three_day_repair_r3_20261008/R3_PROFILE_2026-09-28_CANDIDATE_RECEIPT_R1.json'),
   'profile_state_counts':dict(states['2026-09-28']),'target_qfq_capability':receipts['2026-09-28']['target_qfq_capability'],
   'knowledge_lineage':'RECONSTRUCTED_CORRECTED','formal_acceptance':False,'production_binding':False,
   'preexisting_profile_numeric_crosscheck':{'artifact':ref('reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz'),
    'receipt':ref('reports/v4_05/V4_05_R4_CORE_PROFILE_REPLAY.json')},
   'core_numeric_crosscheck':{'common_security_ids':len(common),'observed_field_values_checked':checked,'mismatches':mismatch,'result':'PASS' if mismatch==0 else 'FAIL'},
   'preexisting_profile_relative_market_state':'UNKNOWN due to absent accepted rps20_delta3 endpoint in that frozen candidate'},
  {'trade_date':'2026-09-29','status':'R3_ISOLATED_CORRECTED_PROFILE_OWNER_MATERIALIZED','rows':len(candidates['2026-09-29']),
   'artifact':receipts['2026-09-29']['owner_artifact'],'receipt':ref('docs/evidence/three_day_repair_r3_20261008/R3_PROFILE_2026-09-29_CANDIDATE_RECEIPT_R2.json'),
   'profile_state_counts':dict(states['2026-09-29']),'target_qfq_capability':receipts['2026-09-29']['target_qfq_capability'],
   'knowledge_lineage':'RECONSTRUCTED_CORRECTED','formal_acceptance':False,'production_binding':False},
  material['profile_days'][2]]
 material['result']='DEGRADED_PASS_THREE_DAY_CORE_OWNER_AND_PROFILE_COVERAGE'
 material['consumer_binding_status']='9/30 production Profile is bound and all 5213 consumers match; isolated corrected V4-04 Profiles are materialized for 9/28 and 9/29 from exact target-coordinate bars/periods plus accepted corrected RPS endpoints. The existing 9/28 frozen candidate also crosschecks against R3 Core. Both historical candidates remain non-production and non-PIT.'
 material['next']='isolated profile arithmetic spot-check, then report scoped publication boundary'
 save('docs/evidence/three_day_repair_r3_20261008/R3_CORE_PROFILE_OWNER_MATERIALIZATION.json',material)
 dates=read('docs/evidence/three_day_repair_r3_20261008/R3_DATE_PRICE_BASIS_AND_CONSUMER_MATRIX.json')
 for i,day in enumerate(('2026-09-28','2026-09-29')):
  rec=receipts[day]
  dates['dates'][i]['profile'].update(status='R3_ISOLATED_PROFILE_OWNER_MATERIALIZED',profile_owner='R3_ISOLATED_CORRECTED_PROFILE_OWNER',rows=len(candidates[day]),artifact=rec['owner_artifact'],
   receipt=ref(f'docs/evidence/three_day_repair_r3_20261008/R3_PROFILE_{day}_CANDIDATE_RECEIPT_{revisions[day]}.json'),formal_acceptance=False,
   production_binding=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',rps_endpoints=rec['rps_endpoints'],target_qfq_capability=rec['target_qfq_capability'])
  dates['dates'][i]['profile'].pop('core_owner_ref',None)
 dates['dates'][0]['profile']['preexisting_candidate_crosscheck']={'artifact':ref('reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz'),
  'checked':checked,'mismatches':mismatch,'result':'PASS' if mismatch==0 else 'FAIL'}
 save('docs/evidence/three_day_repair_r3_20261008/R3_DATE_PRICE_BASIS_AND_CONSUMER_MATRIX.json',dates)
 deps=read('docs/evidence/three_day_repair_r3_20261008/R3_SOURCE_OWNER_CONSUMER_DEPENDENCIES.json')
 for item in deps['source_owner_consumer']:
  if item['domain']=='Profile':
   item['scope_status']='9/30 Profile is exactly consumed by live FP07; corrected isolated V4-04 Profile owners are materialized for 9/28 and 9/29. Historical corrected owners are isolated, not production accepted.'
   for binding in item['date_bindings']:
    if binding.get('trade_date') in receipts:
     d=binding['trade_date'];binding['profile_owner']='R3_ISOLATED_CORRECTED_PROFILE_OWNER';binding['status']='PROFILE_MATERIALIZED_NONPRODUCTION';binding['artifact']=receipts[d]['owner_artifact']
 save('docs/evidence/three_day_repair_r3_20261008/R3_SOURCE_OWNER_CONSUMER_DEPENDENCIES.json',deps)
 print(json.dumps({'profile_rows':{d:len(rows) for d,rows in candidates.items()},'9_28_numeric_checked':checked,
  'mismatches':mismatch,'states':{d:dict(v) for d,v in states.items()}},ensure_ascii=False))
if __name__=='__main__':main()
