"""Continue only failed generic-N adapter fields, retaining every prior PASS."""
import json
from pathlib import Path
from collections import Counter
from scripts.v4_04_machine_executor_r4 import execute_rule
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    target=OUT/'PROFILE_HORIZON_CONTINUATION_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_PRIOR_PROFILE_HORIZON_CONTINUATION')
    prior=OUT/'PROFILE_FULL_RULE_ORACLE_R6_R1.json';first=json.loads(prior.read_bytes());candidate=json.loads(checked(ROOT,first['candidate']).read_bytes());day=candidate['accepted_trade_date']
    source=rows(ROOT,candidate['owners'][day]['profile']);fields=('drawdown20_state','drawdown60_state','near_high20_state','near_high60_state')
    # The original adapter supplied hhv/prior_high; AST requires hhvN/prior_highN.
    # Original expected UNKNOWN for all four horizon cells. Their known-value
    # count accounts for 20783 failures, leaving 18 other clauses for audit.
    failed=sum(row['states'][field]['value']!='UNKNOWN' for row in source for field in fields)
    if failed!=20783 or first['error_count']!=20801:raise ValueError('PROFILE_FAILED_SCOPE_BOUND_REQUIRED')
    contract=json.loads((ROOT/'config/v4_04_algorithm_contracts_v3.json').read_bytes());parameters={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}
    counts=Counter();errors=[]
    for row in source:
        for field in fields:
            cell=row['states'][field]
            if cell['value']=='UNKNOWN':continue
            evidence=dict(cell['evidence']);horizon='20' if '20' in field else '60'
            if field.startswith('drawdown'):key='POSITION_STATE_V1.drawdown';evidence['hhvN']=evidence['hhv'+horizon]
            else:key='POSITION_STATE_V1.near_high';evidence['prior_highN']=evidence['prior_high'+horizon]
            expected=execute_rule(contract['rules'],key,evidence,parameters);counts[field]+=1
            if cell['value']!=expected:errors.append(dict(entity=row['security_id'],field=field,actual=cell['value'],expected=expected))
    result=dict(contract_id='V4_CURRENT_PROFILE_HORIZON_FAILED_ADAPTER_CONTINUATION_R1',acceptance='PASS_RULE_SCOPE' if not errors else 'FAIL',candidate=first['candidate'],T0=day,
        original=ref(OUT,prior),original_errors_accounted_for=failed,remaining_original_errors=first['error_count']-failed,previous_pass_checks_reused=first['total_checks']-first['error_count'],
        new_checks=dict(counts),new_check_count=sum(counts.values()),errors=errors,product_source_changed=False,
        scope='Only 20783 original failed four-horizon known branches; 18 other original failures remain unresolved; 62783 previous PASS cells retained')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],reused=result['previous_pass_checks_reused'],new=result['new_check_count'],errors=len(errors))),flush=True)

if __name__=='__main__':main()
