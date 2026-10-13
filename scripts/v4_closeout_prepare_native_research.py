"""Native business-reference preparation from already completed sidecars."""
import json,os
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_membership_reference_pg_v1 import prepare_research,read_research,KEY
from workbench_analysis.producer_bootstrap_v1 import optional_step

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    report=OUT/'NATIVE_RESEARCH_REFERENCE_PREPARATION_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_NATIVE_RESEARCH_PREPARATION')
    sidecars=json.loads((OUT/'RESEARCH_SIDECAR_PREPARATION_R6_R1.json').read_bytes());input_candidate=sidecars['candidate'];candidate=json.loads(checked(ROOT,input_candidate).read_bytes());day=candidate['accepted_trade_date']
    original_authority=json.loads(checked(ROOT,candidate[KEY]).read_bytes());index=json.loads(checked(ROOT,sidecars['producer_index']).read_bytes());credentials=load_credentials(ROOT/'config/native_pg_roles.dpapi')
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[1]];receipt=prepare_research(ROOT,candidate,input_candidate,index)
    authority=json.loads(checked(ROOT,candidate[KEY]).read_bytes())
    if any(authority[k]!=value for k,value in original_authority.items()):raise ValueError('PRIOR_NATIVE_REFERENCES_CHANGED')
    path=ROOT/'data/v4/prepared_daily_candidates_v2'/input_candidate['sha256']/'CANDIDATE_WITH_NATIVE_RESEARCH.json';atomic_json(ROOT,path,candidate)
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[0]];verified={}
    for name,entry in authority['research']['documents'].items():
        expected=json.loads(checked(ROOT,entry['source']).read_bytes());actual=read_research(ROOT,candidate,day,entry['source'])
        if actual!=expected:raise ValueError('NATIVE_RESEARCH_FORMAL_READER_DIFFERENCE:'+name)
        verified[name]=dict(source=entry['source'],complete_payload_equal=True,rows=len(actual.get('rows',actual.get('signals',[]))))
    # Check the newly repaired metadata status without rerunning the producer.
    first=sidecars['result']['first_observed_state']['candidate']
    truthful=optional_step(lambda:first)
    if truthful['status']!='SOURCE_INCOMPLETE' or 'candidate' in truthful or truthful.get('observed_count') is not None:raise ValueError('FIRST_CAPTURE_STATUS_WRAPPER_FALSE_SUCCESS')
    result=dict(contract_id='V4_NATIVE_RESEARCH_REFERENCE_PREPARATION_R1',acceptance='PASS_REFERENCE_AND_STATUS_ONLY',candidate=ref(ROOT,path),receipt=receipt,
        full_payload_readbacks=verified,reader_role=ROLES[0],prior_native_references_preserved=True,truthful_first_observed_state=truthful,
        math_producers_reexecuted=False,publication=False,current_http_candidate_route='PENDING_CURRENT_ACCEPTED_HEAD')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],documents=sorted(verified),first_observed_state=truthful['status'])),flush=True)

if __name__=='__main__':main()
