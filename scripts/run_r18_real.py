"""Capability-scoped replay of exact, promoted owner publications only."""
import sys,json,gzip,subprocess,os
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_authority import ReplayAuthority
from workbench_analysis.v4_14_replay_io import publish,ref,digest,exact
from scripts.v4_14_independent_oracle import exact as checked,read,require

def gz(binding):
    with gzip.open(checked(ROOT,binding),'rt',encoding='utf8') as f:return json.load(f)
def sources(a):
    h=read(ROOT,a.owners['v4_11']);d=read(ROOT,h['evidence_bindings']['reports/v4_11_r5/V4_11_R5_D2_READBACK.json']);events=read(ROOT,h['evidence_bindings']['reports/v4_11_r5/V4_11_R5_EVENT_REPLAY.json'])
    return d,events
def worker(mode,prior_ref=None):
    start=datetime.now(timezone.utc).isoformat();a=ReplayAuthority(ROOT);d,ev=sources(a);date='2026-09-29' if mode=='prior' else '2026-09-30'
    source=d['prior' if mode=='prior' else 'current'];native=gz(source);rows=native['rows'];counts=Counter(r['final_eligibility'] for r in rows)
    output=dict(evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED',trade_date=date,previous_market_session=a.previous(date),current_owner_publication=source,owner_rows=len(rows),final_eligibility_counts=dict(counts),state_freshness_counts=dict(Counter(r['state_freshness'] for r in rows)),knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,quality='DEGRADED',authority_bindings=a.bindings(),contract_package_digest=a.package_digest,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',raw_provider_fallback=False,production=False,shadow=False,focus=False,ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT')
    if mode=='target':
        prior_binding=json.loads(prior_ref);prior=read(ROOT,prior_binding);require(prior['trade_date']==a.previous(date) and prior['current_owner_publication']==d['prior'],'REAL_EXACT_PREVIOUS_OWNER_REQUIRED');output['previous_replay_publication']=prior_binding
        events=gz(ev['events']);events=events['rows'] if isinstance(events,dict) else events
        require(len(events)==len(rows),'REAL_EVENT_FULL_UNIVERSE')
        output['event_counts']=dict(Counter(r['effective_event'] for r in events));output['event_quality_counts']=dict(Counter(r['event_quality'] for r in events));output['event_source']=ev['events'];output['prior_evidence']='RECONSTRUCTED_LEFT_CENSORED'
        require(output['event_counts']==ev['event_counts'] and output['event_quality_counts']==ev['event_quality_counts'],'REAL_EVENT_DEGRADATION_CHANGED')
        manifest=read(ROOT,a.head['candidate']);require(manifest['AS_RECORDED'] is False and manifest['knowledge_lineage']=='RECONSTRUCTED_CORRECTED','REAL_R6_LINEAGE_CHANGED')
        observations=[];quality=Counter();ids=set()
        with gzip.open(checked(ROOT,manifest['artifacts'][0]),'rt',encoding='utf8') as f:
            for line in f:
                row=json.loads(line);require(row['trade_date']==date and row['AS_RECORDED'] is False and row['raw_qualification_before']==row['raw_qualification_after'],'REAL_PROFILE_FEEDBACK_OR_LINEAGE')
                require(row['security_id'] not in ids,'REAL_DUPLICATE_PROFILE');ids.add(row['security_id']);quality.update(v['quality'] for v in row['fields'].values());observations.append(dict(security_id=row['security_id'],source_digest=digest(row),field_qualities={k:v['quality'] for k,v in row['fields'].items()}))
        context_count=0;context_keys=set();b2=Counter();rotation=Counter()
        with gzip.open(checked(ROOT,manifest['artifacts'][1]),'rt',encoding='utf8') as f:
            for line in f:
                row=json.loads(line);require(row['trade_date']==date and row['membership_basis']=='PIT_OBSERVED' and row['excluded_target_id']==row['security_id'] and row['security_id'] not in row['member_ids'],'REAL_TARGET_EXCLUSION_OR_MEMBERSHIP')
                key=(row['security_id'],row['sector_id']);require(key not in context_keys,'REAL_CONTEXT_DUPLICATE');context_keys.add(key);context_count+=1;b2[row['b2']['confirmed_raw']]+=1;rotation[row['rotation']['output_state']]+=1
        require(len(ids)==manifest['profile_count']==5224 and context_count==manifest['context_count']==50162,'REAL_FULL_READBACK_COUNTS')
        output.update(accepted_r6_manifest=a.head['candidate'],profile_source=manifest['artifacts'][0],context_source=manifest['artifacts'][1],profile_count=len(ids),context_count=context_count,field_quality_counts=dict(quality),b2_state_counts=dict(b2),rotation_state_counts=dict(rotation),membership_snapshot_identity=manifest['membership_snapshot_identity'],profile_readback_observations=observations,prior_loo_context='UNKNOWN_NO_ACCEPTED_PRIOR_LOO_CONTEXT',capability_scope='PERSISTED_OWNER_READBACK_AND_GATE_B_WIRING_NOT_HISTORICAL_EFFECTIVENESS')
    publication=publish(ROOT,'reports/v4_14_replay_r18/real/'+date+'/r1/manifest.json',output)
    receipt=dict(pid=os.getpid(),started_at=start,finished_at=datetime.now(timezone.utc).isoformat(),publication=publication,previous_readback=json.loads(prior_ref) if prior_ref else None,calendar_binding=a.calendar_ref,in_memory_prior=False)
    return receipt
def run():
    receipts=[];prior=None
    for mode in ['prior','target']:
        args=[sys.executable,'-m','scripts.run_r18_real',mode]
        if prior:args.append(json.dumps(prior))
        p=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8',errors='replace');out,err=p.communicate(timeout=600)
        if p.returncode:raise RuntimeError(err)
        r=json.loads(out);require(r['pid']==p.pid,'REAL_PID_MISMATCH');r.update(exited_at=datetime.now(timezone.utc).isoformat(),producer_exited=p.poll() is not None,os_wait_completed=True,exit_code=p.returncode)
        if receipts:require(r['pid']!=receipts[-1]['pid'] and r['started_at']>receipts[-1]['exited_at'],'REAL_CROSS_PROCESS_SEQUENCE')
        receipts.append(r);prior=r['publication']
    gate=dict(R18_REAL_ACCEPTED_SOURCE_REPLAY='PASS_CAPABILITY_SCOPED',evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED',receipts=receipts,publication=prior,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT')
    return publish(ROOT,'reports/r18c/real_scoped_gate.json',gate)
if __name__=='__main__':print(json.dumps(worker(*sys.argv[1:]) if len(sys.argv)>1 else run(),sort_keys=True))
