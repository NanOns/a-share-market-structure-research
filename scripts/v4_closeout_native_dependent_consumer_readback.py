"""Changed risk dependencies and newly uncovered Source path checks only."""
import json,os
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.r43_operational_bff import OperationalResearchBFF

def main():
    target=OUT/'NATIVE_DEPENDENT_CONSUMER_READBACK_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_NATIVE_DEPENDENT_CONSUMER_READBACK')
    preparation=json.loads((OUT/'NATIVE_PROFILE_DEPENDENT_PREPARATION_R6_R1.json').read_bytes());scope=json.loads((OUT/'EXTENSION_CHANGED_SCOPE_SIX_DATES_R6_R1.json').read_bytes())
    candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate);bff=OperationalResearchBFF(api,None);checks=0;errors=[]
    for dated in scope['dates']:
        day=dated['T0'];wanted={r['security_id']:r for r in dated['corrections']}
        focus={r['entity_id']:r for r in api.read('focus',day,api.token)['rows'] if r['entity_id'] in wanted}
        prewatch={r['security_id']:r for r in api.read('prewatch',day,api.token)['rows'] if r['security_id'] in wanted}
        stocks={r['entity_id']:r for r in bff.project('stocks',day) if r['entity_id'] in wanted}
        for sid,expected in wanted.items():
            for label,actual,required in (('D2_input_risk',focus[sid]['input_provenance']['risk']['value'],expected['new_risk']),('D2_input_quality',focus[sid]['input_provenance']['risk']['quality'],'KNOWN'),('D0_priority_risk',prewatch[sid]['prewatch']['risk_axis'],expected['new_risk']),('risk_Source_path',stocks[sid]['fields']['core_extension_risk']['source_field'],'replacement.states.core_extension_risk'),('severe_Source_path',stocks[sid]['fields']['severe_extension']['source_field'],'replacement.states.severe_extension')):
                checks+=1
                if actual!=required:errors.append(dict(T0=day,entity_id=sid,field=label,actual=actual,expected=required))
    result=dict(contract_id='V4_NATIVE_PROFILE_DEPENDENT_CONSUMER_READBACK_R1',acceptance='PASS_CHANGED_DEPENDENCIES_ONLY' if not errors else 'FAIL',candidate=preparation['candidate'],checks=checks,errors=errors,previous_162_value_quality_source_checks_reexecuted=False,previous_full_fields_oracle_reexecuted=False,scope='27 changed D2 risk values/quality, D0 priority risk, and previously uncovered two BFF Source paths; Forward unavailable branches retained',production_changed=False,current_http_acceptance=False)
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,errors=len(errors))))

if __name__=='__main__':main()
