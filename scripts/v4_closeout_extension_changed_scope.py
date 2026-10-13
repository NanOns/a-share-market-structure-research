"""Enumerate only the actually changed Extension function across six dates."""
import gzip,json
from pathlib import Path
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_04_machine_executor_v4 import execute_rule
from v4.profile_core import extension_risk
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    target=OUT/'EXTENSION_CHANGED_SCOPE_SIX_DATES_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_CHANGED_SCOPE_RECEIPT')
    first=json.loads((OUT/'PROFILE_FAILED_SEMANTICS_CONTINUATION_R6_R1.json').read_bytes())
    candidate=json.loads(checked(ROOT,first['candidate']).read_bytes())
    contract=json.loads((ROOT/'config/v4_04_algorithm_contracts_v3.json').read_bytes())
    p={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}
    dated=[];errors=[];checks=0
    for day in candidate['dates']:
        owner=candidate['owners'][day];corrections=[]
        for row in rows(ROOT,owner['profile']):
            cell=row['states']['core_extension_risk'];e=cell['evidence'];actual=extension_risk(e)
            expected=execute_rule(contract['rules'],'EXTENSION_RISK_V1',e,p);checks+=1
            if actual.value!=expected:errors.append(dict(T0=day,security_id=row['security_id'],actual=actual.value,expected=expected))
            if actual.value!=cell['value']:
                corrections.append(dict(security_id=row['security_id'],old_risk=cell['value'],new_risk=actual.value,old_severe=row['states']['severe_extension']['value'],new_severe=actual.value=='EXTREME' if actual.value!='UNKNOWN' else None,evidence=e))
        ids={r['security_id'] for r in corrections}
        focus=json.load(gzip.open(checked(ROOT,owner['focus']),'rt',encoding='utf8'))
        forward=json.load(gzip.open(checked(ROOT,owner['forward']),'rt',encoding='utf8'))
        dated.append(dict(T0=day,profile=owner['profile'],base_profile=owner.get('base_profile'),corrections=corrections,affected_d2=[dict(entity_id=r['entity_id'],episode_id=r.get('episode_id'),scenario=r['scenario'],eligibility=r['final_eligibility']) for r in focus['rows'] if r['entity_id'] in ids],affected_forward_episode_ids=sorted(r['episode_id'] for r in forward['episodes'] if r['entity_id'] in ids),affected_current_forward_events=[dict(entity_id=r['entity_id'],episode_id=r['episode_id'],trade_date=r['trade_date']) for r in forward['events'] if r['entity_id'] in ids and r['trade_date']==day]))
    repo=Path(__file__).resolve().parents[1]
    result=dict(contract_id='V4_EXTENSION_CHANGED_FUNCTION_SIX_DATE_SCOPE_R1',acceptance='PASS_CHANGED_FUNCTION_ONLY' if not errors else 'FAIL',candidate=first['candidate'],dates=dated,checks=checks,correction_count=sum(len(r['corrections']) for r in dated),errors=errors,source=ref(repo,repo/'src/v4/profile_core.py'),previous_unchanged_fields_reexecuted=False,sealed_owner_outputs_changed=False,publication_ready=False,scope='Only genuinely changed Extension function across existing six-date scope; all unaffected Core/Profile/Focus/period arithmetic retained. Dependent output lineage requires bounded correction before release.')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,corrections=result['correction_count'],errors=len(errors))))

if __name__=='__main__':main()
