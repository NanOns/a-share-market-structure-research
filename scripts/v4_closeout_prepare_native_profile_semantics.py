"""Prepare and read real formal PG correction facts without publishing Heads."""
import json,os
from pathlib import Path
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_operational_owner_authority_v2 import load as load_owner,read as read_owner
from workbench_db.v4_profile_semantic_corrections_pg_v1 import prepare,apply,validate_replacement,KEY

def main():
    report=OUT/'NATIVE_PROFILE_SEMANTIC_PREPARATION_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_NATIVE_PROFILE_SEMANTICS')
    previous=json.loads((OUT/'PROFILE_SEMANTIC_PATCH_PREPARATION_R6_R1.json').read_bytes());candidate=json.loads(checked(ROOT,previous['original_candidate']).read_bytes())
    heads={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    credentials=load_credentials(ROOT/'config/native_pg_roles.dpapi');os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[1]]
    patches={d['T0']:d['patch'] for d in previous['dates']}
    saved=[]
    for path in (ROOT/'data/v4/profile_semantic_corrections_pg_v1').glob('*/AUTHORITY.json'):
        authority=json.loads(path.read_bytes())
        if {d:e['source'] for d,e in authority.get('dates',{}).items()}==patches and authority.get('source_profiles')=={d:o['profile'] for d,o in candidate['owners'].items()}:saved.append(path)
    if len(saved)>1:raise ValueError('AMBIGUOUS_EXISTING_SEMANTIC_AUTHORITY')
    if saved:
        candidate[KEY]=ref(ROOT,saved[0]);receipt=dict(rows=27,dates=6,publication=False,completed_native_preparation_reused=True)
    else:receipt=prepare(ROOT,candidate,patches)
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[0]];authority=load_owner(ROOT,candidate);checks=0;changed=0;scopes=[]
    for day,item in authority['owners'].items():
        source=candidate['owners'][day]['profile'];original=read_owner(ROOT,authority,day,'profile',source);actual=apply(ROOT,candidate,day,original)
        for before,after in zip(original,actual):
            if before==after:continue
            validate_replacement(before,after);changed+=1;checks+=2
        scopes.append(dict(T0=day,original_rows=len(original),corrected_rows=sum(b!=a for b,a in zip(original,actual))))
    if changed!=27 or any((ROOT/'data/v4'/n).read_bytes()!=raw for n,raw in heads.items()):raise ValueError('CORRECTION_SCOPE_OR_HEAD_CHANGED')
    target=ROOT/'data/v4/prepared_daily_candidates_v2'/previous['original_candidate']['sha256']/'CANDIDATE_WITH_NATIVE_PROFILE_SEMANTICS_R1.json';atomic_json(ROOT,target,candidate)
    result=dict(contract_id='V4_NATIVE_PROFILE_SEMANTIC_PREPARATION_R1',acceptance='PASS_NATIVE_PATCH_READBACK_ONLY',candidate=ref(ROOT,target),receipt=receipt,reader_role=ROLES[0],changed_field_checks=checks,scopes=scopes,sealed_owners_changed=False,publication=False,dependent_focus_forward_acceptance='PENDING_BOUNDED_REPLAY',release_ready=False)
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],changed=changed,checks=checks,publication=False)))

if __name__=='__main__':main()
