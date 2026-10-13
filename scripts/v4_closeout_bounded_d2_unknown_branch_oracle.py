"""Independent current affected branch proof; no reducer/producer imports."""
import json
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    report=OUT/'BOUNDED_D2_UNKNOWN_BRANCH_ORACLE_R6_R2.json'
    if report.exists():raise ValueError('PRESERVE_BOUNDED_D2_ORACLE')
    material_path=OUT/'BOUNDED_PROFILE_D2_CORRECTION_R6_R2.json';material=json.loads(material_path.read_bytes());previous={};checks=0;errors=[]
    for date in material['dates']:
        document=json.loads(checked(ROOT,date['source']).read_bytes());facts={r['entity_id']:r['fields'] for r in document['fact_manifest']['rows']}
        for row in document['rows']:
            sid=row['entity_id'];f=facts[sid];prior=previous.get(sid)
            # CONFIRMED required UNKNOWN is an independently visible frozen
            # input, so this branch must stop before health/risk selection.
            if f['CONFIRMED']['value']!='UNKNOWN' or not f['CONFIRMED']['required']:raise ValueError('UNSUPPORTED_AFFECTED_BRANCH_SCOPE')
            if prior and prior['episode_id'] and (f['core_price_damage']['value']=='TRUE' or f['frozen_invalidation']['value']=='TRUE'):raise ValueError('HARD_INVALIDATION_BRANCH_REQUIRES_SEPARATE_ORACLE')
            expected=dict(maturity=prior['maturity'] if prior else 'NONE',health='UNKNOWN',validity='UNKNOWN',tracking=prior['tracking'] if prior else 'CLOSED',scenario=prior['scenario'] if prior else 'NONE',scenario_status='UNKNOWN',state_freshness='STALE',final_eligibility='UNKNOWN',episode_id=prior['episode_id'] if prior else None,expiry_count=prior['expiry_count'] if prior else 0,downgrade_candidate=None,downgrade_count=0,improvement_baseline=prior['improvement_baseline'] if prior else None,exit_session_index=prior['exit_session_index'] if prior else None,market_age=prior['market_age']+row['session_index']-prior['session_index'] if prior else 0,raw_qualification={k:f[k]['value'] for k in ('CONFIRMED','PREWATCH','SEED')})
            for field,value in expected.items():
                checks+=1
                if row[field]!=value:errors.append(dict(T0=date['T0'],entity_id=sid,field=field,actual=row[field],expected=value))
            checks+=1
            if row['transition_reasons']!=['REQUIRED_FACTS_UNKNOWN_PRESERVE']:errors.append(dict(T0=date['T0'],entity_id=sid,field='transition_reasons',actual=row['transition_reasons']))
            previous[sid]=row
    result=dict(contract_id='V4_BOUNDED_D2_REQUIRED_UNKNOWN_BRANCH_INDEPENDENT_ORACLE_R1',acceptance='PASS_CHANGED_INPUT_BRANCH_SCOPE' if not errors else 'FAIL',materialization=ref(OUT,material_path),checks=checks,rows=material['reducer_calls'],errors=errors,producer_or_reducer_imported=False,previous_full_focus_oracles_reexecuted=False,scope='Exactly 78 affected row required-CONFIRMED-UNKNOWN branches; no extrapolation to other reducer branches. Genuine UNKNOWN preserved despite corrected optional risk.')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,errors=len(errors))))

if __name__=='__main__':main()
