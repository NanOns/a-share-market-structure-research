"""Full new-date Profile branches through the independent frozen AST executor."""
import json
from pathlib import Path
from collections import Counter
from scripts.v4_04_machine_executor_r4 import execute_rule
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')
RULES={'amount_state':'AMOUNT_VOLUME_STATE_V1.ratio','volume_state':'AMOUNT_VOLUME_STATE_V1.ratio',
 'compression_state':'COMPRESSION_STATE_V1','core_extension_risk':'EXTENSION_RISK_V1',
 'core_participation_result':'AMOUNT_VOLUME_STATE_V1.participation','drawdown20_state':'POSITION_STATE_V1.drawdown',
 'drawdown60_state':'POSITION_STATE_V1.drawdown','ma_structure_state':'MA_STRUCTURE_V1',
 'monthly_trend_state':'TREND_STATE_V1.closed_period','weekly_trend_state':'TREND_STATE_V1.closed_period',
 'near_high20_state':'POSITION_STATE_V1.near_high','near_high60_state':'POSITION_STATE_V1.near_high',
 'position_state':'POSITION_STATE_V1','relative_market_state':'RELATIVE_STATE_V1',
 'severe_extension':'EXTENSION_RISK_V1.severe','trend_state':'TREND_STATE_V1.daily'}

def main():
    target=OUT/'PROFILE_FULL_RULE_ORACLE_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_PRIOR_PROFILE_RULE_ORACLE')
    a=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R2.json').read_bytes());candidate=json.loads(checked(ROOT,a['candidate']).read_bytes());day=candidate['accepted_trade_date']
    contract=json.loads((ROOT/'config/v4_04_algorithm_contracts_v3.json').read_bytes());parameters={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}
    counts=Counter();unknown=Counter();errors=[];error_count=0
    for row in rows(ROOT,candidate['owners'][day]['profile']):
        for field,key in RULES.items():
            cell=row['states'][field];e=dict(cell['evidence'])
            if field in ('amount_state','volume_state'):e['ratio20']=e['amount_ratio20' if field=='amount_state' else 'volume_ratio20']
            if field.startswith('near_high'):e['prior_highN']=e['prior_high'+('20' if '20' in field else '60')]
            if field.startswith('drawdown'):e['hhvN']=e['hhv'+('20' if '20' in field else '60')]
            if field in ('weekly_trend_state','monthly_trend_state'):
                period='weekly' if field.startswith('weekly') else 'monthly';ma='ma5' if period=='weekly' else 'ma3'
                e.update(period_type=period,ma_current=e[ma],ma_previous=e['previous_'+ma])
            expected=execute_rule(contract['rules'],key,e,parameters);counts[field]+=1
            if expected in (None,'UNKNOWN'):unknown[field]+=1
            if cell['value']!=expected:
                error_count+=1
                if len(errors)<100:errors.append(dict(entity=row['security_id'],field=field,rule=key,actual=cell['value'],expected=expected,evidence=e))
    result=dict(contract_id='V4_CURRENT_FULL_PROFILE_INDEPENDENT_RULE_AST_ORACLE_R1',acceptance='PASS_RULE_SCOPE' if not error_count else 'FAIL',T0=day,
        candidate=a['candidate'],profile=candidate['owners'][day]['profile'],checks=dict(counts),total_checks=sum(counts.values()),unknown=dict(unknown),error_count=error_count,first_errors=errors,
        contract=ref(ROOT,ROOT/'config/v4_04_algorithm_contracts_v3.json'),verifier_source=ref(Path(__file__).resolve().parents[1],Path(__file__).resolve().parents[1]/'scripts/v4_04_machine_executor_r4.py'),
        producer_rule_functions_imported=False,previous_128_sample_checks_reexecuted=False,scope='All 16 current Profile rule branches on exact published primitive evidence; primitive, LOO and D1 structure gates are separate')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['total_checks'],errors=error_count)),flush=True)

if __name__=='__main__':main()
