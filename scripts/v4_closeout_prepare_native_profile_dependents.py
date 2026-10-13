"""Prepare only bounded D0/D2 facts; existing Forward unavailable outputs retained."""
import copy,json,os
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_operational_owner_authority_v2 import load as load_owner,read as read_owner
from workbench_db.v4_profile_dependent_corrections_pg_v1 import CONTRACT,prepare,apply,validate_replacement
from v4.state_identity import digest

def main():
    report=OUT/'NATIVE_PROFILE_DEPENDENT_PREPARATION_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_NATIVE_PROFILE_DEPENDENTS')
    original=json.loads((OUT/'NATIVE_PROFILE_SEMANTIC_PREPARATION_R6_R1.json').read_bytes());material=json.loads((OUT/'BOUNDED_PROFILE_D2_CORRECTION_R6_R2.json').read_bytes());oracle=json.loads((OUT/'BOUNDED_D2_UNKNOWN_BRANCH_ORACLE_R6_R2.json').read_bytes());forward=json.loads((OUT/'BOUNDED_FORWARD_SEMANTIC_CORRECTION_R6_R1.json').read_bytes())
    if oracle['acceptance']!='PASS_CHANGED_INPUT_BRANCH_SCOPE' or oracle['errors'] or forward['changed_observations']!=0 or forward['unavailable_observations_preserved']!=2:raise ValueError('BOUNDED_DEPENDENCY_PROOF_REQUIRED')
    candidate=json.loads(checked(ROOT,original['candidate']).read_bytes());credentials=load_credentials(ROOT/'config/native_pg_roles.dpapi');os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[0]];authority=load_owner(ROOT,candidate);patches={};comparisons=0
    folder=ROOT/'data/v4/profile_dependent_correction_documents_v1'/original['candidate']['sha256']
    for date in material['dates']:
        day=date['T0'];document=json.loads(checked(ROOT,date['source']).read_bytes());corrections={r['entity_id']:r for r in document['rows']};prewatch={r['security_id']:r['prewatch'] for r in document['prewatch_calculations']};patches[day]={}
        for domain in ('focus','prewatch'):
            raw=read_owner(ROOT,authority,day,domain,candidate['owners'][day][domain]);data=[]
            for row in raw:
                sid=row['entity_id'] if domain=='focus' else row['security_id']
                if sid not in corrections:continue
                replacement=copy.deepcopy(row)
                if domain=='focus':replacement.update(corrections[sid])
                else:replacement['prewatch']=prewatch[sid]
                validate_replacement(domain,row,replacement);comparisons+=1
                data.append(dict(entity_id=sid,original_row_digest=digest(row),replacement=replacement))
            if len(data)!=13:raise ValueError('BOUNDED_DEPENDENT_ROW_SCOPE')
            path=folder/(day+'_'+domain+'.json')
            if path.exists():raise ValueError('PRESERVE_DEPENDENT_PATCH_DOCUMENT')
            patch=dict(contract_id=CONTRACT,T0=day,domain=domain,original=candidate['owners'][day][domain],producing_source=date['source'],rows=data,PIT_ELIGIBLE=False,AS_RECORDED=False,publication_ready=False)
            atomic_json(ROOT,path,patch);patches[day][domain]=ref(ROOT,path)
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[1]];prepare(ROOT,candidate,patches)
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[0]];reads=0
    for day in patches:
        for domain in ('focus','prewatch'):
            raw=read_owner(ROOT,authority,day,domain,candidate['owners'][day][domain]);result=apply(ROOT,candidate,day,domain,raw)
            if len(result)!=len(raw):raise ValueError('DEPENDENT_READER_FULL_DENOMINATOR_CHANGED')
            reads+=13
    target=folder/'CANDIDATE_WITH_NATIVE_DEPENDENTS_R1.json';atomic_json(ROOT,target,candidate)
    result=dict(contract_id=CONTRACT,acceptance='PASS_NATIVE_DEPENDENT_PATCH_ONLY',candidate=ref(ROOT,target),patched_rows=reads,original_lifecycle_business_state_conservation=comparisons,patches=patches,forward_business_payload_changed=False,independent_d2_branch_checks=oracle['checks'],previous_full_focus_price_and_settlement_recomputed=False,publication=False,current_http_acceptance=False,next='Only changed D0 priority/D2 provenance consumer assertions, source closure and metadata admission')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],rows=reads)))

if __name__=='__main__':main()
