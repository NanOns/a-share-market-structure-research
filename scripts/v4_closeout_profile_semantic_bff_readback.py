"""Read only changed risk/severe BFF fields from real formal SELECT-only PG."""
import json,os
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.r43_operational_bff import OperationalResearchBFF
from workbench_db.v4_profile_semantic_corrections_pg_v1 import load

def main():
    target=OUT/'PROFILE_SEMANTIC_BFF_READBACK_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_SEMANTIC_BFF_READBACK')
    preparation=json.loads((OUT/'NATIVE_PROFILE_SEMANTIC_PREPARATION_R6_R1.json').read_bytes());scope=json.loads((OUT/'EXTENSION_CHANGED_SCOPE_SIX_DATES_R6_R1.json').read_bytes())
    candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate);bff=OperationalResearchBFF(api,None);authority=load(ROOT,candidate)
    checks=0;errors=[]
    for day_scope in scope['dates']:
        day=day_scope['T0'];wanted={r['security_id']:r for r in day_scope['corrections']};projected={r['entity_id']:r for r in bff.project('stocks',day) if r['entity_id'] in wanted}
        if set(projected)!=set(wanted):raise ValueError('CORRECTED_BFF_SECURITY_SCOPE')
        for sid,expected in wanted.items():
            row=projected[sid]
            for field,value in (('core_extension_risk',expected['new_risk']),('severe_extension',expected['new_severe'])):
                cell=row['fields'][field]
                for key,actual,required in (('value',cell['value'],value),('quality',cell['quality'],'KNOWN'),('source',row['field_owner_bindings'][field],authority['dates'][day]['source'])):
                    checks+=1
                    if actual!=required:errors.append(dict(T0=day,security_id=sid,field=field,key=key,actual=actual,expected=required))
    result=dict(contract_id='V4_PROFILE_SEMANTIC_NATIVE_BFF_READBACK_R1',acceptance='PASS_CHANGED_FIELD_SCOPE' if not errors else 'FAIL',candidate=preparation['candidate'],checks=checks,errors=errors,reader_role=ROLES[0],previous_pass_fields_reexecuted=False,production_head_changed=False,current_http_acceptance=False,scope='Only 27 changed risk/severe value, quality and correction Source bindings; original other fields retained; D2/Forward dependency closure still pending')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,errors=len(errors))))

if __name__=='__main__':main()
