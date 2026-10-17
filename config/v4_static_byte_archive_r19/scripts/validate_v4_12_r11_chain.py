"""Independent persisted-chain oracle: stdlib only, never builder/runtime expected."""
import argparse,gzip,hashlib,json
from decimal import Decimal
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT

OUT='reports/v4_12_runtime_r11/'
def canon(v):return (json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def sha(v):return hashlib.sha256(canon(v)).hexdigest()
def read(ref):
    raw=(ROOT/ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'];return json.loads(raw)
def lines(ref):
    raw=(ROOT/ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
    if ref['path'].endswith('.gz'):raw=gzip.decompress(raw)
    return [json.loads(line) for line in raw.splitlines()]
def equal(a,b):
    if a is None or b is None:return a is b
    try:return Decimal(str(a))==Decimal(str(b))
    except Exception:return a==b

# Hand-written expectations use frozen thresholds, never future helper output.
A_ORACLE=[('2026-09-23',0,0,0,0,'IDLE','PENDING'),('2026-09-24',1,0,0,0,'UNKNOWN','UNKNOWN'),('2026-09-28',2,1,1,0,'APPROACHING','PENDING'),('2026-09-29',3,2,2,0,'APPROACHING','ACCEPTED'),('2026-09-30',4,3,0,1,'BREACHED_SHALLOW','NOT_ACCEPTED')]
B_ORACLE=[('2026-09-23',0,0,0,0,'IDLE','PENDING'),('2026-09-24',1,0,0,0,'UNKNOWN','UNKNOWN'),('2026-09-28',2,1,1,0,'RECLAIMED','PENDING'),('2026-09-29',3,2,2,0,'HELD_TENTATIVE','ACCEPTED'),('2026-09-30',4,3,0,1,'BREACHED_SHALLOW','NOT_ACCEPTED')]

def validate(phase):
    registry=json.loads((ROOT/'config/v4_12_field_registry_v1.json').read_bytes())['fields'];blocked={r['field']:r['blocked_reason'] for r in registry if r['field_role']=='BLOCKED_CAPABILITY'}
    entry=json.loads((ROOT/'reports/v4_12/V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json').read_bytes());entry_sha=hashlib.sha256((ROOT/'reports/v4_12/V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json').read_bytes()).hexdigest()
    proofs=[];synthetic_anchor=None;previous_by_scope={};revision_predecessors=[]
    for scope in ['synthetic','real']:
        days=[x[0] for x in A_ORACLE] if scope=='synthetic' else ['2026-09-29','2026-09-30']
        for date in days:
            revisions=['r1','r2','r3'] if scope=='synthetic' and date=='2026-09-29' else ['r1']
            current=None
            for revision in revisions:
                directory=OUT+phase+('_closure_chain_' if phase=='b' else '_persisted_chain_')+scope+'/'+date+'/'+revision+'/'
                manifest_ref=json.loads((ROOT/(directory+'snapshot_ref.json')).read_bytes());m=read(manifest_ref)
                assert m['status']=='ENGINEERING_CANDIDATE_NOT_ACCEPTED' and m['formal_accepted'] is False and m['AS_RECORDED'] is False and m['knowledge_lineage']=='RECONSTRUCTED_CORRECTED'
                bundle=lines(m['snapshot_bundle']);index=read(m['security_index'])['rows'];runtime=read(m['source_runtime_manifest']);artifacts={Path(r['path']).name:r for r in runtime['artifacts']}
                observations={r['security_id']:r for r in lines(artifacts['runtime_observations.jsonl.gz'])};bindings={r['identity']['security_id']:r['fields'] for r in lines(artifacts['runtime_bindings.jsonl.gz'])}
                anchors=lines(artifacts['anchors.jsonl']);events=lines(artifacts['events.jsonl']);transitions=lines(artifacts['transitions.jsonl'])
                assert m['row_count']==len(bundle)==len(index)==len(observations)==(1 if scope=='synthetic' else 5224)
                assert m['security_ids_digest']==sha(sorted(index))
                previous=previous_by_scope.get(scope)
                if previous:assert runtime['prior']==dict(frozen_manifest=previous['ref'])
                else:assert runtime['prior'] is None
                current=dict(ref=manifest_ref,rows={r['security_id']:r for r in bundle})
                for r in bundle:
                    sid=r['security_id'];o=observations[sid];f=bindings[sid]
                    assert index[sid]['row_digest']==sha(r) and r['counter_state_digest']==sha(r['counter_state'])
                    assert r['observation_digest']==sha(o) and r['input_digest']==sha(f) and r['source_candidate_manifest_digest']==m['source_runtime_manifest']['sha256']
                    assert r['namespace']=='Frozen D1[t]' and r['trade_date']==date and r['revision']==revision and r['entry_digest']==entry_sha and r['formal_accepted'] is False
                    prior=previous['rows'][sid] if previous else None
                    if prior:
                        assert o['prior_state_ref']['row_digest']==sha(prior) and o['prior_state_ref']['candidate_manifest']==previous['ref']
                        assert prior['trade_date']<date
                    else:assert o['prior_state_ref'] is None
                    if scope=='real':
                        assert r['anchor'] is None and r['event'] is None
                        assert all(v['quality']=='UNKNOWN' for v in o['outputs'].values())
                        for n,reason in blocked.items():assert f[n]['value'] is None and f[n]['quality']=='UNKNOWN' and f[n]['reason']==reason
                        assert not anchors and not events
                    else:
                        if synthetic_anchor is None:synthetic_anchor=r['anchor']
                        assert r['anchor']==synthetic_anchor and r['event']['anchor_id']==synthetic_anchor['anchor_id']
                        oracle=next(x for x in (A_ORACLE if phase=='a' else B_ORACLE) if x[0]==date)
                        _,age,count,held,breach,support,acceptance=oracle
                        assert equal(f['post_creation_market_sessions']['value'],age) and equal(r['counter_state']['post_creation_evaluable_sessions'],count)
                        assert equal(r['counter_state']['held_count'],held) and equal(r['counter_state']['breach_count'],breach)
                        assert r['support_state']==support and r['acceptance_state']==acceptance,(date,r['support_state'],r['acceptance_state'])
                    if phase=='b':
                        e=o['frozen_output_envelope'];assert equal(e['retest_count'],r['counter_state']['test_count']) and e['last_known_support_state']==r['last_known_support_state']
                        support=o['outputs']['support'];expected=support['value'] if support['quality']=='KNOWN' else prior['last_known_support_state'] if prior else None
                        assert e['last_known_support_state']==expected
                        hard=o['derived']['hard_invalidated'];episode=o['derived']['episode_invalidated']
                        expected_invalidation=hard['value'] is True or episode['value'] is True
                        if expected_invalidation:assert e['invalidation_facts'] and e['invalidation_facts'][0]['anchor_ref'] is not None
                        elif hard['quality']==episode['quality']=='KNOWN':assert e['invalidation_facts']==[]
                        else:assert e['invalidation_facts'] is None and o['projection_quality']['invalidation_facts']['reason']
                if phase=='b':
                    expected=[]
                    for sid,o in observations.items():
                        prior=previous['rows'][sid] if previous else None
                        for machine,v in o['outputs'].items():
                            if machine=='retention' or not prior:continue
                            p=prior['state_observations'][machine]
                            if p['quality']==v['quality']=='KNOWN' and p['value']!=v['value']:expected.append((sid,machine,p['value'],v['value']))
                    actual=[(t['security_id'],t['machine'],t['from_state'],t['to_state']) for t in transitions];assert sorted(actual)==sorted(expected)
                    for t in transitions:assert t['machine']!='retention' and t['transition_kind']=='KNOWN_STATE_CHANGE' and t['prior_session_state_ref'] and t['current_observation_ref']
                    state_obs=lines(artifacts['state_observations.jsonl.gz']);assert len(state_obs)==len(observations)*6
                proofs.append(dict(scope=scope,date=date,revision=revision,manifest=manifest_ref,row_count=len(bundle),transition_count=len(transitions)))
                if date=='2026-09-29' and scope=='synthetic':revision_predecessors.append(runtime['prior'])
                if revision=='r1':first=current
            previous_by_scope[scope]=first
    assert revision_predecessors[0]==revision_predecessors[1]==revision_predecessors[2]
    protected=json.loads((ROOT/(OUT+'R11_STAGE_CONTRACT.json')).read_bytes())['protected']
    for path,sha_before in protected.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha_before
    assert not (ROOT/'data/v4/V4_12_ACCEPTED_HEAD.json').exists()
    return dict(status='PASS',phase=phase,oracle='INDEPENDENT_LITERAL_BOOK_AND_STDLIB_PROJECTION_CHECKS',proofs=proofs,same_day_isolation=True,protected_hashes=protected,raw_fallback_count=0,formal_accepted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['a','b'],required=True);p.add_argument('--emit',action='store_true');a=p.parse_args();result=validate(a.phase)
    if a.emit:(ROOT/(OUT+'R11'+a.phase.upper()+'_LOCAL_GATES.json')).write_bytes(canon(result))
    print(json.dumps(dict(status=result['status'],phase=a.phase,proofs=len(result['proofs']))))
