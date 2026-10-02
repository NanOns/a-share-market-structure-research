"""Persisted supplemental known/missing paths, independently authored literal oracle."""
import gzip,json,subprocess,sys
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r11_chain import canon,sha,read,lines,equal

BASE='reports/v4_12_runtime_r11/projection_closure_paths/'
BOOK=[('2026-09-21',True,11,10,.7,'IDLE','IDLE',0,0),('2026-09-22',True,11,10,.4,'TESTING','TESTING',0,1),('2026-09-23',True,11,10,.7,'RECLAIMED','RECLAIMED',1,2),('2026-09-24',True,11,10,.4,'HELD_TENTATIVE','HELD_TENTATIVE',1,3),('2026-09-28',False,11,11,.4,'UNKNOWN','HELD_TENTATIVE',1,3),('2026-09-29',True,11,11,.4,'APPROACHING','APPROACHING',1,4),('2026-09-30',True,8,8,.4,'BROKEN','BROKEN',1,5)]
def replay():
    previous=None
    for date,ev,c,l,clv,*_ in BOOK:
        fixture=dict(scope='SYNTHETIC_ENGINEERING_ONLY_NOT_ACCEPTED_SOURCE',values=dict(C=c,L=l,H=12,O=10,CLV=clv,evaluable=ev,price_basis='SYNTHETIC_QFQ',adjustment_source_revision='SYNTHETIC_REV',amount_ratio20=2 if date=='2026-09-21' else 0,rel_market_1=1 if date=='2026-09-21' else 0,prior_high_view=100,prior_range20_atr=100,atr_prior_view=1))
        p=ROOT/(BASE+'fixtures/'+date+'.json');p.parent.mkdir(parents=True,exist_ok=True);raw=canon(fixture)
        if p.exists():assert p.read_bytes()==raw
        else:p.write_bytes(raw)
        directory=BASE+date+'/r1';cmd=[sys.executable,'-m','scripts.run_v4_12_r11_day','--date',date,'--directory',directory,'--fixture',p.relative_to(ROOT).as_posix()]
        if previous:cmd+=['--prior',previous]
        subprocess.run(cmd,cwd=ROOT,check=True);previous=directory+'/snapshot_ref.json'
    return validate()

def validate():
    proofs=[];prior=None;anchor=None
    for date,ev,c,l,clv,state,last,test,count in BOOK:
        directory=ROOT/(BASE+date+'/r1');m=read(json.loads((directory/'snapshot_ref.json').read_bytes()));r=lines(m['snapshot_bundle'])[0];run=read(m['source_runtime_manifest']);refs={Path(x['path']).name:x for x in run['artifacts']};o=lines(refs['runtime_observations.jsonl.gz'])[0];e=o['frozen_output_envelope'];transitions=lines(refs['transitions.jsonl'])
        assert r['support_state']==state and e['last_known_support_state']==r['last_known_support_state']==last,(date,state,r['support_state'])
        assert e['retest_count']==r['counter_state']['test_count']==test and r['counter_state']['post_creation_evaluable_sessions']==count
        if anchor is None:anchor=r['anchor']
        assert r['anchor']==anchor
        expected=[]
        if prior:
            for machine,current in o['outputs'].items():
                old=prior['state_observations'][machine]
                if machine!='retention' and current['quality']==old['quality']=='KNOWN' and current['value']!=old['value']:expected.append((machine,old['value'],current['value']))
        assert sorted((t['machine'],t['from_state'],t['to_state']) for t in transitions)==sorted(expected)
        if state=='BROKEN':
            fact=e['invalidation_facts'][0]
            assert fact['deep_breach']['value'] is True and fact['episode_owns_anchor']['value'] is True and fact['threshold']['parameter_id']=='support_break_consecutive_sessions'
            assert fact['anchor_ref']['anchor_id']==anchor['anchor_id'] and fact['event_ref']['event_id']==anchor['source_event_id']
        else:assert e['invalidation_facts']==[]
        proofs.append(dict(date=date,support=state,last_known=last,retest_count=test,evaluable_count=count,transitions=len(transitions),snapshot=m['snapshot_bundle']))
        prior=r
    return dict(status='PASS',oracle='INDEPENDENT_LITERAL_BOOK',paths=['TESTING_TO_RECLAIMED','RECLAIMED_TO_HELD_TENTATIVE','KNOWN_TO_MISSING','MISSING_TO_RESUME','DEEP_BREACH_TRIGGER_FACTS','SAME_STATE_OBSERVATION_ONLY'],proofs=proofs)

if __name__=='__main__':
    if '--validate-only' in sys.argv:r=validate()
    else:r=replay();(ROOT/'reports/v4_12_runtime_r11/R11B_PROJECTION_PATH_ORACLE.json').write_bytes(canon(r))
    print(json.dumps(dict(status=r['status'],paths=len(r['paths']))))
