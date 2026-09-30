"""Write deterministic, source-bound R4 four-state AST acceptance evidence."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json
from sector.machine_ast_r3 import NOT_APPLICABLE,evaluate_ast_explain,ast_digest

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def bind(path):return {'path':path,'sha256':sha(path),'byte_count':(ROOT/path).stat().st_size}

STATES=[True,False,None,NOT_APPLICABLE]
def logical_expected(operator,left,right):
    values=[left,right]
    if operator=='AND':
        if False in values:return False,'REQUIRED_BRANCH_FALSE'
        if None in values:return None,'REQUIRED_VALUE_UNKNOWN'
        if all(value is NOT_APPLICABLE for value in values):return NOT_APPLICABLE,'ALL_REQUIRED_BRANCHES_NOT_APPLICABLE'
        return True,'NOT_APPLICABLE_BRANCH_SKIPPED' if NOT_APPLICABLE in values else None
    if True in values:return True,None
    if None in values:return None,'REQUIRED_VALUE_UNKNOWN'
    if all(value is NOT_APPLICABLE for value in values):return None,'NO_USABLE_RETENTION_BRANCH'
    return False,'NOT_APPLICABLE_BRANCH_SKIPPED' if NOT_APPLICABLE in values else None

def fact(value):
    return {'value':value,'quality':NOT_APPLICABLE if value is NOT_APPLICABLE else 'ACCEPTED','producer':'R4_SYNTHETIC_VECTOR','time_role':'TEST_ONLY','reason_code':'SYNTHETIC_UNAVAILABLE' if value is NOT_APPLICABLE else None}

def binary_rule(operator):
    leaf=lambda name:{'operator':'EQ','field_id':name,'constant':True,'producer':'R4_SYNTHETIC_VECTOR','time_role':'TEST_ONLY','quality_requirement':['ACCEPTED'],'unknown_behavior':'UNKNOWN'}
    return {'synthetic':{'operator':operator,'children':[leaf('left'),leaf('right')]}}

def main():
    contract_path='config/v4_08_rotation_core_contract_v2.json'
    contract=read(contract_path);parameters=read('config/v4_08_algorithm_parameter_set_v1.json')
    parameter_values={item['parameter_id']:item['value'] for item in parameters['parameters']}
    expected_pending={'V4_08_EARLY_SEED_RETENTION_MIN','V4_08_EARLY_BREADTH_RETENTION_MIN','V4_08_EARLY_BREADTH_DELTA_MIN','V4_08_EARLY_TOP1_CONCENTRATION_MAX','V4_08_MATURE_STRONG_RETENTION_MIN'}
    pending={key for key,value in parameter_values.items() if value is None}
    if pending!=expected_pending:raise ValueError('R4 requires all five approved retention values to remain pending')

    truth=[]
    for operator in ['AND','OR']:
        rules=binary_rule(operator)
        for left in STATES:
            for right in STATES:
                expected,expected_reason=logical_expected(operator,left,right)
                result=evaluate_ast_explain('synthetic',rules,{'left':fact(left),'right':fact(right)},{})
                row={'operator':operator,'left':left,'right':right,'expected_state':expected,'actual_state':result.state,'expected_reason_code':expected_reason,'actual_reason_code':result.reason_code,'passed':result.state==expected and result.reason_code==expected_reason}
                truth.append(row)
    canonical_or=contract['rules']['early_retained']['children'][1]
    early_vectors=[]
    # These test-only comparison values exercise the exact serialized GTE subtree.
    test_parameters={**parameter_values,'V4_08_EARLY_SEED_RETENTION_MIN':0.5,'V4_08_EARLY_BREADTH_RETENTION_MIN':0.5}
    retention_fields={'base_seed_retention','breadth_retention'}
    field_by_id={item['field_id']:item for item in read(contract['field_registry_path'])['fields']}
    for left,right in [(True,NOT_APPLICABLE),(NOT_APPLICABLE,True),(False,NOT_APPLICABLE),(NOT_APPLICABLE,False),(NOT_APPLICABLE,NOT_APPLICABLE),(None,NOT_APPLICABLE),(False,None)]:
        facts={}
        for name,value in zip(sorted(retention_fields),[left,right]):
            field=field_by_id[name]
            facts[name]={'value':value,'quality':NOT_APPLICABLE if value is NOT_APPLICABLE else 'ACCEPTED','producer':field['producer'],'time_role':field['time_role'],'reason_code':'SYNTHETIC_UNAVAILABLE' if value is NOT_APPLICABLE else None}
        result=evaluate_ast_explain('early_retention_or',{'early_retention_or':canonical_or},facts,test_parameters)
        expected,reason=logical_expected('OR',left,right)
        # Existing REV2 early-retention UNKNOWN behavior is propagated unchanged.
        row={'left_test_premise':left,'right_test_premise':right,'expected_state':expected,'actual_state':result.state,'expected_reason_code':reason,'actual_reason_code':result.reason_code,'passed':result.state==expected and result.reason_code==reason}
        early_vectors.append(row)

    strong_field=field_by_id['strong_prev']
    mature_facts={'strong_prev':{'value':0,'quality':'ACCEPTED','producer':strong_field['producer'],'time_role':strong_field['time_role']}}
    mature=evaluate_ast_explain('mature_retained',contract['rules'],mature_facts,parameter_values)
    test_parameters={**parameter_values,'V4_08_EARLY_SEED_RETENTION_MIN':0.5,'V4_08_EARLY_BREADTH_RETENTION_MIN':0.5,'V4_08_EARLY_BREADTH_DELTA_MIN':0.0,'V4_08_EARLY_TOP1_CONCENTRATION_MAX':0.5}
    qualification_values={'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':True,'pulse_age_sessions':3,'basket_cumulative_return':0.1,'base_seed_retention':0.8,'breadth_retention':0.8,'breadth_delta1':0.1,'top1_concentration':0.2,'strong_prev':0,'strong_member_retention_1':0.8,'prior_rotation_state':'ROTATION_ACCEPTED','prior_maturity_state':'WARM','net_entered_count':1,'dq5':12,'yesterday_dq5':-1}
    qualification_facts={name:{'value':value,'quality':'ACCEPTED','producer':field_by_id[name]['producer'],'time_role':field_by_id[name]['time_role']} for name,value in qualification_values.items()}
    rotation_states={name:evaluate_ast_explain(name,contract['rules'],qualification_facts,test_parameters).state for name in ['ROTATION_IN','ROTATION_ACCEPTED','ROTATION_EXPANDING','ROTATION_REACCELERATING']}
    early_state=evaluate_ast_explain('early_retained',contract['rules'],qualification_facts,test_parameters).state
    ast_acceptance={
      'contract_id':'V4_08_R4_AST_NOT_APPLICABLE_ACCEPTANCE_V1',
      'status':'PASS' if all(item['passed'] for item in truth+early_vectors) and mature.state==NOT_APPLICABLE and mature.reason_code=='STRONG_PREV_EMPTY' and rotation_states['ROTATION_IN'] is True and rotation_states['ROTATION_ACCEPTED'] is True and rotation_states['ROTATION_EXPANDING'] is NOT_APPLICABLE and rotation_states['ROTATION_REACCELERATING'] is NOT_APPLICABLE else 'FAIL',
      'canonical_contract':bind(contract_path),'canonical_early_retention_or_ast_digest':ast_digest(canonical_or),
      'evaluator':bind('src/sector/machine_ast_r3.py'),'parameter_set':bind('config/v4_08_algorithm_parameter_set_v1.json'),
      'all_five_retention_parameters_null':pending==expected_pending,'pending_parameter_ids':sorted(pending),
      'strong_prev_zero_vector':{'strong_prev':0,'early_retained_test_state':early_state,'mature_retained_state':mature.state,'reason_code':mature.reason_code,'mature_retention_failed':False,'rotation_qualification_states':rotation_states,'early_in_and_accepted_remain_qualifiable':rotation_states['ROTATION_IN'] is True and rotation_states['ROTATION_ACCEPTED'] is True,'mature_na_does_not_qualify_expanding_or_reaccelerating':rotation_states['ROTATION_EXPANDING'] is NOT_APPLICABLE and rotation_states['ROTATION_REACCELERATING'] is NOT_APPLICABLE},
      'formal_consumer_enabled':contract['formal_consumer_enabled'],'test_only_threshold_overrides_persisted':False,
      'truth_table_row_count':len(truth),'canonical_early_or_vector_count':len(early_vectors),
      'test_binding':bind('tests/v4_08/test_r3_admission_and_ast.py')}
    truth_evidence={'contract_id':'V4_08_R4_AST_FOUR_STATE_TRUTH_TABLE_V1','status':'PASS' if all(item['passed'] for item in truth+early_vectors) else 'FAIL','states':['TRUE','FALSE','UNKNOWN','NOT_APPLICABLE'],'operators':{'AND':'FALSE dominates; else UNKNOWN propagates; N/A is skipped; all N/A remains N/A.','OR':'TRUE dominates; else UNKNOWN propagates; N/A is skipped; all N/A is UNKNOWN / NO_USABLE_RETENTION_BRANCH.'},'binary_truth_table':truth,'canonical_early_retention_or':{'ast_digest':ast_digest(canonical_or),'rev4_fep_r2_source':bind('reports/v4_08/source_contracts/REV4_FEP_R2_20260930.md'),'test_only_threshold_values':{'V4_08_EARLY_SEED_RETENTION_MIN':0.5,'V4_08_EARLY_BREADTH_RETENTION_MIN':0.5},'persisted_parameter_values_unchanged':all(parameter_values[key] is None for key in expected_pending),'vectors':early_vectors}}

    # Rotation vectors freeze synthetic premises only; the persisted contract still has no consumer permission.
    vector_path='config/v4_08_rotation_machine_vectors_v2.json';vector_set=read(vector_path)
    coverage=[]
    for vector in vector_set['vectors']:
        expected=vector['expected']
        state_rules=dict(contract['rules'])
        early_value=bool(vector['scenario']['basket_return_positive'] and (vector['scenario']['seed_retention_pass'] or vector['scenario']['breadth_retention_pass']) and vector['scenario']['breadth_delta_pass'] and vector['scenario']['top1_concentration_pass'])
        early_field=field_by_id['early_retained']
        state_rules['early_retained']={'operator':'EQ','field_id':'early_retained','constant':True,'producer':early_field['producer'],'time_role':early_field['time_role'],'quality_requirement':['ACCEPTED'],'unknown_behavior':'UNKNOWN'}
        values={'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':vector['scenario']['pulse'],'pulse_age_sessions':vector['scenario']['pulse_age_sessions'],'early_retained':early_value,'strong_prev':vector['scenario']['strong_prev'],'prior_rotation_state':vector['scenario'].get('prior_state'),'breadth_delta1':vector['scenario'].get('breadth_delta1',0.06),'top1_concentration':0.2,'net_entered_count':1,'dq5':12 if vector['scenario']['pulse'] else 0,'yesterday_dq5':-1}
        facts={name:{'value':value,'quality':'ACCEPTED','producer':field_by_id[name]['producer'],'time_role':field_by_id[name]['time_role']} for name,value in values.items()}
        mapping={'rotation_in_possible':'ROTATION_IN','rotation_accepted_possible':'ROTATION_ACCEPTED','rotation_expanding_allowed':'ROTATION_EXPANDING','rotation_reaccelerating_allowed':'ROTATION_REACCELERATING'}
        actual={key:evaluate_ast_explain(rule,state_rules,facts,parameter_values).state for key,rule in mapping.items()}
        passed=all((actual[key] is not True) if expected[key] is False else actual[key] is expected[key] for key in expected)
        coverage.append({'vector_id':vector['id'],'premises_are_synthetic':True,'expected':expected,'actual_canonical_ast':actual,'passed':passed})
    vector_evidence={'contract_id':'V4_08_R4_ROTATION_VECTOR_COVERAGE_V1','status':'PASS' if all(item['passed'] for item in coverage) else 'FAIL','vector_set':bind(vector_path),'canonical_contract':bind(contract_path),'evaluator':bind('src/sector/machine_ast_r3.py'),'formal_consumer_enabled':contract['formal_consumer_enabled'],'pending_parameter_ids':sorted(pending),'vectors':coverage}

    out=ROOT/'reports/v4_08'
    atomic_json(out/'V4_08_R4_AST_NOT_APPLICABLE_ACCEPTANCE.json',ast_acceptance)
    atomic_json(out/'V4_08_R4_AST_FOUR_STATE_TRUTH_TABLE.json',truth_evidence)
    atomic_json(out/'V4_08_R4_ROTATION_VECTOR_COVERAGE.json',vector_evidence)
    print(json.dumps({'ast_status':ast_acceptance['status'],'truth_table_status':truth_evidence['status'],'rotation_vector_status':vector_evidence['status'],'binary_rows':len(truth),'early_or_rows':len(early_vectors),'pending_parameters':sorted(pending)}))
    return 0 if all(item['status']=='PASS' for item in [ast_acceptance,truth_evidence,vector_evidence]) else 1

if __name__=='__main__':raise SystemExit(main())
