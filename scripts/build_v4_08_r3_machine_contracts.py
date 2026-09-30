from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json,sha
from sector.machine_ast_r3 import ast_digest,validate_ast

def main():
    registry=json.loads((ROOT/'config/v4_08_sector_field_registry_v1.json').read_text(encoding='utf-8'))
    registry['field_registry_id']='V4_08_SECTOR_FIELD_REGISTRY_V2';registry['version']='2.0.0'
    for field in registry['fields']:
        field['time_role']='TARGET_CUTOFF';field['quality_requirement']=['ACCEPTED'];field['unknown_behavior']='UNKNOWN'
    extra={
      'membership_ready':('V4_08_PIT_MEMBERSHIP','TARGET_CUTOFF','bool'),
      'basket_cumulative_return':('ROTATION_CORE_V1','PULSE_FROZEN_PATH','ratio'),
      'strong_prev':('ROTATION_CORE_V1','PRIOR_FROZEN_SESSION','members'),
      'strong_member_retention_1':('ROTATION_CORE_V1','PULSE_FROZEN_PATH','ratio'),
      'pulse_age_sessions':('ROTATION_CORE_V1','ACCEPTED_CALENDAR_SESSION_DISTANCE','sessions'),
      'pulse_active':('ROTATION_CORE_V1','PULSE_FROZEN_EPISODE','bool'),
      'prior_rotation_state':('ROTATION_CORE_V1','PRIOR_FROZEN_SESSION','enum'),
      'entered_count':('V4_08_SECTOR_NATIVE_V1','COMMON_EVALUABLE_MEMBER_SET','members'),
      'net_entered_count':('V4_08_SECTOR_NATIVE_V1','COMMON_EVALUABLE_MEMBER_SET','members'),
      'yesterday_dq5':('V4_08_SECTOR_NATIVE_V1','PRIOR_FROZEN_SESSION','points'),
      'early_retained':('ROTATION_CORE_V1','PULSE_FROZEN_PATH','bool'),
      'mature_retained':('ROTATION_CORE_V1','PULSE_FROZEN_PATH','bool'),
      'prior_maturity_state':('ROTATION_CORE_V1','PRIOR_FROZEN_SESSION','enum'),
      'negative_out_consecutive_evaluable_sessions':('ROTATION_CORE_V1','ACCEPTED_CALENDAR_EVALUABLE_SESSION_SEQUENCE','sessions'),
      'episode_accepted':('ROTATION_CORE_V1','PULSE_FROZEN_EPISODE','bool'),
      'episode_terminated':('ROTATION_CORE_V1','PULSE_FROZEN_EPISODE','bool'),
    }
    for key,(producer,role,unit) in extra.items():
        registry['fields'].append({'field_id':key,'producer':producer,'time_role':role,'unit':unit,'quality_requirement':['ACCEPTED'],'unknown_behavior':'UNKNOWN'})
    for field in registry['fields']:
        if field['field_id'] in ('base_seed_retention','breadth_retention'):field['time_role']='PULSE_FROZEN_PATH'
    reg_path=ROOT/'config/v4_08_sector_field_registry_v2.json';atomic_json(reg_path,registry)
    fields={x['field_id']:x for x in registry['fields']}
    def leaf(field,operator,parameter=None,constant=None):
        result={'field_id':field,'operator':operator,'producer':fields[field]['producer'],'time_role':fields[field]['time_role'],'quality_requirement':['ACCEPTED'],'unknown_behavior':'UNKNOWN'}
        result['parameter_id' if parameter else 'constant']=parameter if parameter else constant
        return result
    def ref(rule):return {'operator':'REF','rule_id':rule}
    def AND(*children):return {'operator':'AND','children':list(children)}
    def OR(*children):return {'operator':'OR','children':list(children)}
    safety=AND(leaf('membership_ready','EQ',constant=True),leaf('sector_member_count','GTE','V4_08_SECTOR_MIN_MEMBERS'),leaf('sector_quote_coverage','GTE','V4_08_SECTOR_MIN_QUOTE_COVERAGE'))
    b0={'sector_safety':safety,'prewatch_raw':AND(ref('sector_safety'),leaf('dq5','GTE','V4_08_PREWATCH_DQ5_MIN'),OR(leaf('breadth_delta3','GT',constant=0),leaf('ma20_delta3','GT',constant=0)),leaf('base_seed_width_adjusted','GTE','V4_08_PREWATCH_SEED_WIDTH_MIN'))}
    b1={'sector_safety':safety,
        'pulse':AND(ref('sector_safety'),leaf('dq5','GTE','V4_08_ROTATION_PULSE_DQ5_MIN'),leaf('breadth_delta1','GTE','V4_08_ROTATION_PULSE_BREADTH_DELTA1_MIN')),
        'early_retained':AND(leaf('basket_cumulative_return','GT',constant=0),OR(leaf('base_seed_retention','GTE','V4_08_EARLY_SEED_RETENTION_MIN'),leaf('breadth_retention','GTE','V4_08_EARLY_BREADTH_RETENTION_MIN')),leaf('breadth_delta1','GTE','V4_08_EARLY_BREADTH_DELTA_MIN'),leaf('top1_concentration','LTE','V4_08_EARLY_TOP1_CONCENTRATION_MAX')),
        'mature_retained':{'operator':'NOT_APPLICABLE_IF','condition':leaf('strong_prev','LTE',constant=0),'then_state':'NOT_APPLICABLE','else':AND(ref('early_retained'),leaf('strong_member_retention_1','GTE','V4_08_MATURE_STRONG_RETENTION_MIN'))},
        'diffusion':AND(leaf('net_entered_count','GT',constant=0),leaf('breadth_delta1','GT',constant=0),leaf('top1_concentration','LTE','V4_08_ROTATION_DIFFUSION_TOP1_MAX')),
        'ROTATION_IN':AND(ref('sector_safety'),leaf('pulse_active','EQ',constant=True),leaf('pulse_age_sessions','GTE',constant=1),ref('early_retained')),
        'ROTATION_ACCEPTED':AND(ref('sector_safety'),leaf('pulse_active','EQ',constant=True),leaf('pulse_age_sessions','GTE',constant=2),ref('early_retained'),leaf('breadth_delta1','GTE',constant=-0.05)),
        'ROTATION_EXPANDING':{'operator':'NOT_APPLICABLE_IF','condition':leaf('strong_prev','LTE',constant=0),'then_state':'NOT_APPLICABLE','else':AND(ref('sector_safety'),ref('mature_retained'),ref('diffusion'),leaf('prior_rotation_state','IN',constant=['ROTATION_ACCEPTED','ROTATION_EXPANDING']),leaf('pulse_age_sessions','GTE',constant=2))},
        'ROTATION_REACCELERATING':{'operator':'NOT_APPLICABLE_IF','condition':leaf('strong_prev','LTE',constant=0),'then_state':'NOT_APPLICABLE','else':AND(ref('sector_safety'),ref('mature_retained'),ref('pulse'),leaf('prior_maturity_state','IN',constant=['WARM','CONFIRMED']),leaf('yesterday_dq5','LTE',constant=0))},
        'ROTATION_FAILED':AND(ref('sector_safety'),leaf('pulse_active','EQ',constant=True),leaf('pulse_age_sessions','GTE',constant=1),leaf('pulse_age_sessions','LTE',constant=5),leaf('basket_cumulative_return','LTE',constant=0),leaf('breadth_delta1','LTE',constant=-0.05)),
        'ROTATION_OUT':AND(ref('sector_safety'),leaf('prior_maturity_state','IN',constant=['WARM','CONFIRMED']),leaf('negative_out_consecutive_evaluable_sessions','GTE',constant=2)),
        'ROTATION_PULSE':AND(ref('sector_safety'),leaf('pulse_active','EQ',constant=False),ref('pulse')),
        'HOLD_PREVIOUS_ELIGIBLE':AND(ref('sector_safety'),leaf('pulse_active','EQ',constant=True),leaf('episode_terminated','EQ',constant=False),OR(leaf('pulse_age_sessions','LTE',constant=5),leaf('episode_accepted','EQ',constant=True))),
        'UNACCEPTED_EPISODE_EXPIRED':AND(ref('sector_safety'),leaf('pulse_active','EQ',constant=True),leaf('episode_accepted','EQ',constant=False),leaf('pulse_age_sessions','GT',constant=5)),
        'NO_ACTIVE_EPISODE':AND(ref('sector_safety'),leaf('pulse_active','EQ',constant=False)),
    }
    # These state vectors freeze independent predicate premises, not runtime thresholds.
    vectors={'vector_set_id':'V4_08_R3_ROTATION_MACHINE_VECTORS_V1','parameter_set_id':'V4_08_ALGORITHM_PARAMETER_SET_V1','status':'SYNTHETIC_PREDICATE_PREMISES_ONLY','formal_consumer_enabled':False,'vectors':[
        {'id':'R1A','scenario':{'pulse':True,'strong_prev':0,'basket_return_positive':True,'seed_retention_pass':True,'breadth_retention_pass':True,'breadth_delta_pass':True,'top1_concentration_pass':True,'pulse_age_sessions':1,'acceptance_breadth_floor_pass':True,'diffusion_pass':True,'prior_state':'ROTATION_ACCEPTED'},'expected':{'rotation_in_possible':True,'rotation_accepted_possible':False,'rotation_expanding_allowed':False,'rotation_reaccelerating_allowed':False}},
        {'id':'R1B','scenario':{'pulse':True,'strong_prev':0,'basket_return_positive':True,'seed_retention_pass':True,'breadth_retention_pass':True,'breadth_delta_pass':True,'top1_concentration_pass':True,'pulse_age_sessions':2,'acceptance_breadth_floor_pass':True,'breadth_delta1':-0.04,'diffusion_pass':True,'prior_state':'ROTATION_ACCEPTED'},'expected':{'rotation_in_possible':True,'rotation_accepted_possible':True,'rotation_expanding_allowed':False,'rotation_reaccelerating_allowed':False}},
        {'id':'R2','scenario':{'pulse':False,'strong_prev':12,'basket_return_positive':True,'seed_retention_pass':False,'breadth_retention_pass':False,'breadth_delta_pass':False,'top1_concentration_pass':True,'pulse_age_sessions':3,'acceptance_breadth_floor_pass':False,'diffusion_pass':False,'prior_state':'ROTATION_ACCEPTED'},'expected':{'rotation_in_possible':False,'rotation_accepted_possible':False,'rotation_expanding_allowed':False,'rotation_reaccelerating_allowed':False}},
        {'id':'R3','scenario':{'pulse':True,'strong_prev':5,'basket_return_positive':True,'seed_retention_pass':True,'breadth_retention_pass':True,'breadth_delta_pass':True,'top1_concentration_pass':False,'pulse_age_sessions':3,'acceptance_breadth_floor_pass':True,'diffusion_pass':False,'prior_state':'ROTATION_IN'},'expected':{'rotation_in_possible':False,'rotation_accepted_possible':False,'rotation_expanding_allowed':False,'rotation_reaccelerating_allowed':False}},
    ]}
    vector_path=ROOT/'config/v4_08_rotation_machine_vectors_v2.json';atomic_json(vector_path,vectors)
    param_path=ROOT/'config/v4_08_algorithm_parameter_set_v1.json';parameters={x['parameter_id']:x['value'] for x in json.loads(param_path.read_text(encoding='utf-8'))['parameters']}
    for model,rules,file in [('V4_08_SECTOR_PREWATCH_B0_V2',b0,'v4_08_sector_prewatch_contract_v2.json'),('ROTATION_CORE_V1_R3',b1,'v4_08_rotation_core_contract_v2.json')]:
        validate_ast(rules,fields,parameters)
        atomic_json(ROOT/'config'/file,{'model_contract_id':model,'version':'2.0.0','status':'STRUCTURED_AST_ENGINEERING_CANDIDATE','parameter_set_id':'V4_08_ALGORITHM_PARAMETER_SET_V1','parameter_set_sha256':sha(param_path.read_bytes()),'rules':rules,'ast_digest':ast_digest(rules),'field_registry_path':reg_path.relative_to(ROOT).as_posix(),'field_registry_digest':sha(reg_path.read_bytes()),'machine_vector_set_path':vector_path.relative_to(ROOT).as_posix(),'machine_vector_set_digest':sha(vector_path.read_bytes()),'pending_parameter_ids':[k for k,v in parameters.items() if v is None],'formal_consumer_enabled':False,'scope':'B0 PREWATCH or B1 IN/ACCEPTED/EXPANDING/REACCELERATING qualification primitives; terminal FSM reduction remains V4-10','strong_prev_zero':'mature retention NOT_APPLICABLE; early IN/ACCEPTED never depends on mature retention','forbidden_inputs':['same-day final stock PREWATCH','Focus','Radar','Support','V4-06 turnover','future confirmation','future outcomes']})
    path=ROOT/'config/v4_08_rotation_core_contract_v2.json'
    contract=json.loads(path.read_text(encoding='utf-8'))
    contract['scope']='Complete B1 qualification and terminal/fallback predicates; production FSM integration remains V4-10'
    contract['ordered_reduction']=['BRANCH_REQUIRED_UNKNOWN_PAUSE','ROTATION_FAILED','ROTATION_OUT','ROTATION_REACCELERATING','ROTATION_EXPANDING','ROTATION_ACCEPTED','ROTATION_IN','ROTATION_PULSE','HOLD_PREVIOUS_ELIGIBLE','UNACCEPTED_EPISODE_EXPIRED','NO_ACTIVE_EPISODE']
    contract['fallback_outputs']={'HOLD_PREVIOUS_ELIGIBLE':'PRIOR_ROTATION_STATE','UNACCEPTED_EPISODE_EXPIRED':'ROTATION_FAILED','NO_ACTIVE_EPISODE':'NONE'}
    contract['unknown_reduction']='Unknown necessary inputs pause only the current applicable branch and episode evaluation count; mature-only unknown does not poison early; strong_prev=0 makes mature_retained NOT_APPLICABLE and cannot qualify expansion/reacceleration.'
    contract['not_applicable_semantics']={'AND':'FALSE dominates; otherwise UNKNOWN propagates; N/A branches are skipped; all N/A yields N/A; TRUE with N/A yields TRUE.','OR':'TRUE dominates; otherwise UNKNOWN propagates; N/A branches are skipped; FALSE with N/A yields FALSE; all N/A yields UNKNOWN with NO_USABLE_RETENTION_BRANCH.','early_retention_or':'One N/A and one TRUE yields TRUE; one N/A and one FALSE yields FALSE; both N/A yields UNKNOWN / NO_USABLE_RETENTION_BRANCH.','mature_retained':'strong_prev <= 0 yields NOT_APPLICABLE with STRONG_PREV_EMPTY; it is not a failed retention reason.','rotation_expanding_and_reaccelerating':'A branch-local strong_prev <= 0 guard returns NOT_APPLICABLE at each output; this cannot qualify either state. ROTATION_IN and ROTATION_ACCEPTED remain independent of mature retention.'}
    contract['sequence_field_contract']={'negative_out_consecutive_evaluable_sessions':{'predicate_fields':['dq5','breadth_delta1'],'operators':['LT','LT'],'constants':[0,0],'producer':'ROTATION_CORE_V1','time_role':'ACCEPTED_CALENDAR_EVALUABLE_SESSION_SEQUENCE','unknown_behavior':'PAUSE_COUNT','membership_changes_count_as_entered_or_exited':False}}
    atomic_json(path,contract)
    print('B0/B1 structured AST and hash bindings frozen; five retention parameters remain pending.')

if __name__=='__main__':main()
