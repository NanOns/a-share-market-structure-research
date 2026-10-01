"""Independent literal scenario boundary oracle, explicitly synthetic only."""
from scripts.next_round_execution_r3 import *
from scripts.v4_11_candidate_inputs_r1 import positive_values
from src.v4.confirmation import package,SCENARIO_KEYS
from copy import deepcopy

def verify():
    c,m,p,a,scanner=package();records=[]
    for scenario,threshold in [('LAUNCH_CONFIRM',1.20),('RECOVERY_TURN',1.05)]:
        for case,value,expected in [('TRUE',threshold+.01,True),('FALSE',threshold-.01,False),('BOUNDARY',threshold,True),('UNKNOWN',None,None)]:
            inputs=positive_values();inputs['amr20_mean_prior']=value;output=scanner(inputs)[SCENARIO_KEYS[scenario]]
            if output['eligible'] is not expected:raise ValueError('INDEPENDENT_LITERAL_SCENARIO_ORACLE_MISMATCH')
            records.append(dict(scenario=scenario,case=case,source_kind='SYNTHETIC_ORACLE_ONLY',input=inputs,literal_expected=expected,
                actual=output['eligible'],checks=output['checks'],threshold=threshold,real_market_TRUE_fabricated=False))
    return dict(status='PASS',scope='SYNTHETIC_FORMULA_ORACLE_ONLY',cases=records,legacy_source=m['legacy_source'],parameters=c['parameters'],scenario_priority=c['machine_ast'])

def main():
    r3a=read('reports/v4_11_r3a/INDEPENDENT_ORACLE.json')
    if r3a['status'] not in ('PASS','PASS_INDEPENDENT_SOURCE_ORACLE','PASS_REAL_SOURCE_ARITHMETIC_ORACLE'):raise ValueError('R3A_INDEPENDENT_ORACLE_REQUIRED')
    result=verify();result.update(R3A_independent_source_oracle=bind('reports/v4_11_r3a/INDEPENDENT_ORACLE.json'),
        real_market_summary=bind('reports/v4_11_r3/V4_11_R3_FULL_MARKET_SUMMARY.json'),R3B_negative_contract=bind('reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json'),
        current_D2_rule_readback=bind('reports/v4_11_r3/V4_11_R3_D2_READBACK.json'))
    write('reports/v4_11_r3/V4_11_R3_INDEPENDENT_ORACLE.json',result);print('PASS')
if __name__=='__main__':main()
