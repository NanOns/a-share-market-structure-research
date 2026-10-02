"""Independent persisted episode oracle. Standard library only; no runtime helpers."""
import gzip,json,hashlib
from decimal import Decimal
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
OUT='reports/v4_12_runtime_r13/'
EXPECTED={
 'no_event': [('2026-09-23','r1','NO_BREAKOUT',0)],
 'near':[('2026-09-23','r1','APPROACHING',0)],
 'unknown_empty':[('2026-09-23','r1','UNKNOWN',0)],
 'holds':[('2026-09-23','r1','BREAKOUT_TENTATIVE',1),('2026-09-24','r1','TESTING',1),('2026-09-28','r1','BREAKOUT_ACCEPTED',1)],
 'retained':[('2026-09-23','r1','BREAKOUT_TENTATIVE',1),('2026-09-24','r1','BREAKOUT_TENTATIVE',1)],
 'duplicate':[('2026-09-23','r1','BREAKOUT_TENTATIVE',1),('2026-09-24','r1','BREAKOUT_TENTATIVE',1)],
 'display_switch':[('2026-09-23','r1','BREAKOUT_TENTATIVE',1),('2026-09-24','r1','TESTING',1)],
 'terminal':[('2026-09-23','r1','BREAKOUT_TENTATIVE',1),('2026-09-24','r1','BREAKOUT_TENTATIVE',1),('2026-09-28','r1','FAILED_BREAKOUT',1),('2026-09-29','r1','BREAKOUT_TENTATIVE',2)],
 'revisions':[('2026-09-23','r1','BREAKOUT_TENTATIVE',1),('2026-09-24','r1','TESTING',1),('2026-09-24','r2','UNKNOWN',1),('2026-09-24','r3','BREAKOUT_TENTATIVE',1)]}
def sha(v):return hashlib.sha256((json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
def read(path):return json.loads((ROOT/path).read_bytes())
def raw(ref,checkout=False):
 p=(ROOT/ref['path']).resolve();assert p.is_relative_to(ROOT.resolve())
 b=p.read_bytes();expected=ref.get('checkout_sha256',ref['sha256']) if checkout else ref['sha256'];size=ref.get('checkout_bytes',ref['bytes']) if checkout else ref['bytes'];assert hashlib.sha256(b).hexdigest()==expected and len(b)==size,ref['path'];return b
def exact(ref):return json.loads(raw(ref))
def lines(ref):
 b=raw(ref);return [json.loads(l) for l in (gzip.decompress(b) if ref['path'].endswith('.gz') else b).splitlines()]
def load(base):
 ref=read(base+'/snapshot_ref.json');m=exact(ref);source=exact(m['source_runtime_manifest']);rows=lines(m['snapshot_bundle']);index=exact(m['security_index'])['rows'];art={Path(r['path']).name:r for r in source['artifacts']};runs=lines(art['runtime_security.jsonl.gz'])
 assert m['contract_id']=='V4_12_FROZEN_D1_BREAKOUT_EXTENSION_V1' and source['contract_id']=='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST'
 assert m['episode_contract']==source['episode_contract']==read(OUT+'R13A_CONTRACT_LOCAL_GATE.json')['contract']
 assert m['row_count']==len(rows)==len(runs) and m['security_ids_digest']==sha(sorted(index))
 assert m['formal_accepted'] is False and m['AS_RECORDED'] is False and m['knowledge_lineage']=='RECONSTRUCTED_CORRECTED'
 assert all(source[n]==0 for n in ['raw_fallback_count','provider_replacement_count','V4_11_candidate_substitution_count']) and source['common_F0_bind_count']==len(rows)
 for row,run in zip(rows,runs):
  sid=row['security_id'];assert run['identity']['security_id']==sid and index[sid]['row_digest']==sha(row) and row['source_runtime_manifest_digest']==m['source_runtime_manifest']['sha256']
  assert run['common_F0_bind_count']==1 and row['anchor_states']==run['anchor_states'] and row['breakout_episodes']==run['breakout_episodes']
  assert row['active_projection']==run['active_projection']
  obs=row['global_state_observations']['breakout'];assert run['basic_breakout_state']==obs['state'] and run['breakout_projection_quality']==obs['quality'] and run['breakout_projection_reason']==obs['reason']
  for n in ['basic_breakout_state','breakout_episode_id','breakout_owner_anchor_id','breakout_projection_quality','breakout_projection_reason']:assert run[n]==run['active_projection'][n]
  states={s['anchor_id']:s for s in row['anchor_states']};episodes=row['breakout_episodes'];ids=set()
  for e in episodes:
   assert e['breakout_episode_id'] not in ids;ids.add(e['breakout_episode_id'])
   assert e['breakout_episode_id']==sha(dict(security_id=sid,event_id=e['event_id'],owning_anchor_id=e['owning_anchor_id']))
   owner=states[e['owning_anchor_id']];assert owner['anchor']['anchor_type']=='PRIOR_HIGH' and owner['event']['event_id']==e['event_id']
   if e['created_trade_date']==row['trade_date']:assert e['state']=='BREAKOUT_TENTATIVE' and all(v==0 for v in owner['counter_state'].values()) and owner['state_observations']['support']['state']=='IDLE'
  for s in states.values():assert s['counter_state_digest']==sha(s['counter_state']) and s['owning_anchor_id']==s['anchor_id'] and s['owning_episode_id']==s['event']['event_id'] and s['output_envelope']['retest_count']==s['counter_state']['test_count']
  if run['breakout_episode_id']:assert run['breakout_owner_anchor_id']==next(e['owning_anchor_id'] for e in episodes if e['breakout_episode_id']==run['breakout_episode_id'])
 return dict(ref=ref,manifest=m,source=source,rows=rows,runs=runs,transitions=lines(art['transitions.jsonl']))
def validate(checkout=False):
 proofs=[];revisions=[]
 for name,steps in EXPECTED.items():
  dates={}
  for date,rev,state,count in steps:
   loaded=load(OUT+'synthetic/'+name+'/'+date+'/'+rev);row=loaded['rows'][0];run=loaded['runs'][0]
   assert run['basic_breakout_state']==state,(name,date,rev,run['basic_breakout_state'],state)
   assert len(row['breakout_episodes'])==count
   earlier=sorted(d for d in dates if d<date);previous=dates[earlier[-1]] if earlier else None
   if previous:
    old=previous['rows'][0];oldactive=next((e for e in old['breakout_episodes'] if e['breakout_episode_id']==old['active_breakout_episode_id']),None)
    assert loaded['source']['prior']==dict(frozen_manifest_episode=previous['ref']) and row['prior_state_ref']['row_digest']==sha(old)
    oldstates={s['anchor_id']:s for s in old['anchor_states']};newstates={s['anchor_id']:s for s in row['anchor_states']};assert set(oldstates)<=set(newstates)
    for aid,s in oldstates.items():assert newstates[aid]['anchor']==s['anchor'] and newstates[aid]['event']==s['event']
    if oldactive:
     current=next(e for e in row['breakout_episodes'] if e['breakout_episode_id']==oldactive['breakout_episode_id'])
     assert current['owning_anchor_id']==oldactive['owning_anchor_id'] and current['event_id']==oldactive['event_id'] and current['prior_episode_ref']['episode_digest']==sha(oldactive) and current['prior_episode_ref']['snapshot']['row_digest']==sha(old)
     binding=run['breakout_input_bindings']['prior_breakout_exists'];assert binding['value'] is True and binding['quality']=='KNOWN' and binding['source_digest']==row['prior_state_ref']['sha256'] and binding['trade_date']==old['trade_date']
     assert len(row['breakout_episodes'])==len(old['breakout_episodes']) and not any(s['created_this_session'] and s['anchor']['anchor_type'] in ['PRIOR_HIGH','BREAKOUT_LEVEL'] for s in newstates.values())
     changes=[t for t in loaded['transitions'] if t['machine']=='breakout'];expected=oldactive['quality']==run['breakout_projection_quality']=='KNOWN' and oldactive['state']!=state
     assert len(changes)==int(expected)
     for t in changes:assert t['breakout_episode_id']==oldactive['breakout_episode_id'] and t['event_id']==oldactive['event_id'] and t['owning_anchor_id']==oldactive['owning_anchor_id'] and t['from_state']==oldactive['state'] and t['to_state']==state and t['prior_session_state_ref']==row['prior_state_ref']
   if name=='display_switch' and date=='2026-09-24':assert row['active_anchor_id']!=run['breakout_owner_anchor_id'] and next(s['anchor']['anchor_type'] for s in row['anchor_states'] if s['anchor_id']==row['active_anchor_id'])=='BULLISH_IMPULSE_BODY'
   if name=='terminal' and date=='2026-09-29':assert row['breakout_episodes'][0]['validity']=='TERMINAL' and row['breakout_episodes'][0]==previous['rows'][0]['breakout_episodes'][0] and row['breakout_episodes'][1]['breakout_episode_id']!=row['breakout_episodes'][0]['breakout_episode_id']
   if name=='holds' and date=='2026-09-28':assert next(s['counter_state']['held_count'] for s in row['anchor_states'] if s['anchor_id']==run['breakout_owner_anchor_id'])==2
   if name=='revisions' and date=='2026-09-24':revisions.append(row['breakout_episodes'][0]['prior_episode_ref'])
   if rev=='r1':dates[date]=loaded
   proofs.append(dict(path=name+'/'+date+'/'+rev,state=state,episodes=count,status='PASS'))
 assert len(revisions)==3 and revisions[0]==revisions[1]==revisions[2]
 registry=read('config/v4_12_field_registry_v1.json')['fields'];blocked={r['field']:r['blocked_reason'] for r in registry if r['field_role']=='BLOCKED_CAPABILITY'};cache={};real=[];prior=None
 for date in ['2026-09-29','2026-09-30']:
  loaded=load(OUT+'real/'+date+'/r1');assert len(loaded['rows'])==5224
  if prior:assert loaded['source']['prior']==dict(frozen_manifest_episode=prior['ref'])
  for row,run in zip(loaded['rows'],loaded['runs']):
   assert not row['anchor_states'] and not row['breakout_episodes'] and run['basic_breakout_state']=='UNKNOWN' and row['breakout_episode_set_quality']=='UNKNOWN'
   if prior:assert row['prior_state_ref']['candidate_manifest']==prior['ref']
   for n,reason in blocked.items():assert run['common_facts'][n]['value'] is None and run['common_facts'][n]['quality']=='UNKNOWN' and run['common_facts'][n]['reason']==reason
   for field in registry:
    if field['field_role']!='UPSTREAM_ACCEPTED':continue
    fact=run['common_facts'][field['field']];pub=field['target_publications'].get(date)
    if not pub or not field['target_publication_available']:assert fact['quality']=='UNKNOWN' and fact['value'] is None;continue
    ref=pub['artifact'];key=ref['sha256']
    if key not in cache:cache[key]={r['security_id']:r for r in exact(ref)['rows']}
    owner=cache[key].get(row['security_id']);assert fact['source_digest']==ref['sha256'] and fact['source_publication_id']==ref['sha256'] and fact['trade_date']==pub['trade_date']
    if owner is None:assert fact['quality']=='UNKNOWN' and fact['value'] is None;continue
    if 'fields' in owner:item=owner['fields'].get(field['accepted_source_field'],{});value=item.get('value');quality=item.get('quality_state')=='OBSERVED' and value is not None
    else:value=owner.get(field['accepted_source_field']);quality=owner.get(pub['quality_field'])=='READY' and value is not None
    assert fact['quality']==('KNOWN' if quality else 'UNKNOWN')
    if quality:assert Decimal(str(fact['value']))==Decimal(str(value)) if field['data_type'] in ['number','integer'] else fact['value']==value
    else:assert fact['value'] is None
  real.append(dict(date=date,securities=5224,episodes=0,state='UNKNOWN',accepted_source_parity='PASS',blocked_fields=len(blocked)));prior=loaded
 for ref in read(OUT+'R13_STAGE_CONTRACT.json')['protected']:raw(ref,checkout)
 out=dict(status='PASS',independent_oracle='HAND_WRITTEN_NO_RUNTIME_IMPORTS',cases=['E%02d'%i for i in range(1,13)],paths=proofs,same_day_predecessor='PASS',real=real,protected_exact='PASS',production=False,shadow=False,focus=False,global_mandatory_adoption=False)
 return out
if __name__=='__main__':
 out=validate();(ROOT/(OUT+'R13_INDEPENDENT_RUNTIME_ORACLE.json')).write_bytes((json.dumps(out,sort_keys=True,indent=2)+'\n').encode());print('R13_INDEPENDENT_PERSISTED_ORACLE_PASS')
