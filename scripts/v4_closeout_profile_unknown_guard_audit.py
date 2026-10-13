"""Locate only the 18 remaining failed clauses using their static masking proof."""
import json
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_04_machine_executor_r4 import execute_rule
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    target=OUT/'PROFILE_UNKNOWN_GUARD_DISCREPANCY_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_PRIOR_GUARD_AUDIT')
    first=json.loads((OUT/'PROFILE_FULL_RULE_ORACLE_R6_R1.json').read_bytes())
    continuation=json.loads((OUT/'PROFILE_HORIZON_CONTINUATION_R6_R1.json').read_bytes())
    candidate=json.loads(checked(ROOT,first['candidate']).read_bytes());day=candidate['accepted_trade_date']
    contract=json.loads((ROOT/'config/v4_04_algorithm_contracts_v3.json').read_bytes())
    p={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}
    affected=[]
    for row in rows(ROOT,candidate['owners'][day]['profile']):
        for field,key in (('compression_state','COMPRESSION_STATE_V1'),('core_extension_risk','EXTENSION_RISK_V1')):
            cell=row['states'][field];e=cell['evidence']
            if cell['value']!='UNKNOWN':continue
            if field=='compression_state':
                masked=any(isinstance(e.get(k),(int,float)) and e[k]>=p['V4_04_COMPRESS_EXTREME'] for k in ('atr_ratio','vol_ratio'))
            else:
                a=e.get('amount_ratio20');v=e.get('ret1');t=e.get('ret5');atr=e.get('atr20');close=e.get('close')
                masked=e.get('bias20_atr') is not None and ((a is not None and a<p['V4_04_EXTENSION_AMOUNT']) or (v is not None and v>0) or (t is not None and atr is not None and close and t<p['V4_04_EXTENSION_RET5_ATR']*atr/close))
            if not masked:continue
            # Only statically identified original failures are executed here.
            machine=execute_rule(contract['rules'],key,e,p)
            if machine=='UNKNOWN':raise ValueError('GUARD_FAILURE_LOCALIZATION_INCOMPLETE')
            affected.append(dict(security_id=row['security_id'],field=field,evidence=e,actual=cell['value'],machine_ast=machine))
    if len(affected)!=18 or len(affected)+continuation['original_errors_accounted_for']!=first['error_count']:raise ValueError('FULL_ORIGINAL_FAILURE_ACCOUNTING')
    result=dict(contract_id='V4_PROFILE_MACHINE_AST_MISSING_INPUT_GUARD_AUDIT_R1',audit_id='V4-PROFILE-UNKNOWN-GUARD-20261013',acceptance='OPEN_CONTRACT_DISCREPANCY',T0=day,candidate=first['candidate'],original_error_count=first['error_count'],horizon_adapter_failures_resolved=continuation['original_errors_accounted_for'],remaining_failures=len(affected),affected=affected,production_values_fail_closed=True,product_source_changed=False,previous_pass_checks_reexecuted=0,contract=ref(ROOT,ROOT/'config/v4_04_algorithm_contracts_v3.json'),scope='Exact 12 compression and 6 extension missing-input guard discrepancies; original machine contract does not declare the producer guard. Explicit versioned contract resolution required before full numeric admission')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],remaining=len(affected))))

if __name__=='__main__':main()
