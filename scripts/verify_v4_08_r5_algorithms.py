"""Independent synthetic expectations, binding perturbations and feedback evidence."""
from pathlib import Path
import sys,json,hashlib,copy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json
from sector.legacy_b2_r5 import evaluate_b2
from sector.rotation_r5 import resolve_package,evaluate_b0,advance_rotation
from sector.machine_ast_r3 import evaluate_ast

def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def report(name,value):atomic_json(ROOT/f'reports/v4_08/V4_08_R5_{name}.json',value)
def main():
    ast=read('config/v4_08_b2_machine_ast_r5.json')
    def actual_sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    def b2(raw):return evaluate_b2({k:dict(value=v,quality='ACCEPTED') for k,v in raw.items()},ast,source_sha256=actual_sha(ast['source_path']),source_parameter_sha256=actual_sha(ast['source_parameter_path']),parameter_set_sha256=actual_sha('config/v4_08_algorithm_parameter_set_r5.json'))
    base=dict(allowed_sector_type=True,normal_rank_eligible=True,total_member_count=10,quote_coverage=1,market_ok=True,type_cross_section_coverage=1,m1=.02,b1=.8,rel1=.01,p1=.9,positive_count=8,top1_positive_share=.2)
    vectors=[('positive',{},'TRUE'),('negative_return',{'m1':-.01},'FALSE'),('unknown_breadth',{'b1':None},'UNKNOWN'),('inclusive_boundary',{'b1':.6,'p1':.8,'rel1':.003,'positive_count':3,'top1_positive_share':.5},'TRUE'),('same_shape_concentration',{'top1_positive_share':.7},'FALSE'),('market_gate_dominates_false',{'market_ok':False,'m1':-.01},'UNKNOWN'),('amount_a_affected',{'amount_A':2},'TRUE')]
    gold=[]
    for name,patch,expected in vectors:
        result=b2({**base,**patch})
        if result['confirmed_diagnostic']!=expected or result['warm_raw']!='UNKNOWN':raise ValueError('INDEPENDENT_B2_EXPECTATION_FAILED:'+name)
        gold.append(dict(case=name,inputs={**base,**patch},expected_confirmed_diagnostic=expected,actual_confirmed_diagnostic=result['confirmed_diagnostic'],warm_raw=result['warm_raw'],warm_reason=result['warm_reason'],predicates=result['predicates']))
    warm={**base,'current':False,'weak':False,'m1':-.005,'b1':.5,'ma20_width':.6,'extended_share':.1,'risk_coverage':1,'dq5_3':.2,'b_delta3':.2,'ma20_delta3':.1,'early_width':.2,'early_count':3,'q20':.6,'setup_count':3,'setup_evaluable_count':10,'prior_current_within10':True}
    for amount,expected in [(1.1,'TRUE'),(None,'UNKNOWN'),(.1,'FALSE')]:
        inputs={**warm,'amount_A':amount};result=b2(inputs)
        if result['warm_diagnostic']!=expected or result['warm_raw']!='UNKNOWN':raise ValueError('AMOUNT_A_DIAGNOSTIC_GOLDEN_FAILED')
        gold.append(dict(case='amount_a_branch_'+expected,inputs=inputs,expected_warm_diagnostic=expected,actual_warm_diagnostic=result['warm_diagnostic'],formal_warm_raw='UNKNOWN',predicates=result['predicates']))
    report('B2_GOLDEN_VECTORS',dict(status='PASS',expected_origin='HAND_AUTHORED_SOURCE_SEMANTICS_NOT_PRODUCER_OUTPUT',vectors=gold,source_sha256=ast['source_sha256'],ast_digest=ast['ast_digest']))
    registry=read('config/v4_08_sector_field_registry_r5.json');contract=read('config/v4_08_rotation_core_contract_r5.json');params_path=ROOT/'config/v4_08_algorithm_parameter_set_r5.json';params=read(params_path.relative_to(ROOT));values,fields=resolve_package(contract,params,params_path.read_bytes(),registry)
    perturb=[]
    for pid,field,rule in [('V4_08_EARLY_SEED_RETENTION_MIN','base_seed_retention','early_retained'),('V4_08_EARLY_BREADTH_RETENTION_MIN','breadth_retention','early_retained'),('V4_08_EARLY_BREADTH_DELTA_MIN','breadth_delta1','early_retained'),('V4_08_EARLY_TOP1_CONCENTRATION_MAX','top1_concentration','early_retained'),('V4_08_MATURE_STRONG_RETENTION_MIN','strong_member_retention_1','mature_retained')]:
        raw={'basket_cumulative_return':.1,'base_seed_retention':1,'breadth_retention':1,'breadth_delta1':.1,'top1_concentration':.1,'strong_prev':5,'strong_member_retention_1':1}
        if field=='base_seed_retention':raw['breadth_retention']=0
        if field=='breadth_retention':raw['base_seed_retention']=0
        raw[field]=values[pid];facts={f:{**fields[f],'value':v,'quality':'ACCEPTED'} for f,v in raw.items()}
        original=evaluate_ast(rule,contract['rules'],facts,values)
        fixture=copy.deepcopy(params);changed_value=values[pid]+(-.01 if field=='top1_concentration' else .01)
        next(p for p in fixture['parameters'] if p['parameter_id']==pid)['value']=changed_value
        fixture_bytes=json.dumps(fixture,ensure_ascii=False,sort_keys=True).encode();fixture_contract={**contract,'parameter_set_sha256':hashlib.sha256(fixture_bytes).hexdigest()}
        changed,_=resolve_package(fixture_contract,fixture,fixture_bytes,registry)
        actual=evaluate_ast(rule,contract['rules'],facts,changed)
        if original is not True or actual is not False:raise ValueError('PARAMETER_NOT_BOUND:'+pid)
        perturb.append(dict(parameter_id=pid,registered_value=values[pid],fixture_changed_value=changed[pid],rule_id=rule,original=True,perturbed=False,expected_origin='SEMANTIC_BOUNDARY'))
    report('PARAMETER_BINDING_PERTURBATION',dict(status='PASS',independent_verifier_reads_parameter_instance=True,parameter_set_sha256=hashlib.sha256(params_path.read_bytes()).hexdigest(),tests=perturb))
    b0contract=read('config/v4_08_sector_prewatch_contract_r5.json');native=dict(sector_id='SYNTHETIC',target_trade_date='2026-09-30',membership_snapshot_id='SYNTHETIC_SNAPSHOT',member_ids=[],fields={})
    def rotation(n):return advance_rotation(n,{},prior_publication=None,prior_members=None,prior_core=None,calendar_sessions=['2026-09-30'],contract=contract,registry=registry,parameters=values)
    feedback=[]
    for key in ('PREWATCH','Focus','Radar','Support','V4_06_turnover','future_confirmation','future_outcome'):
        a=copy.deepcopy(native);b=copy.deepcopy(native);a[key]=True;b[key]=False
        checks=dict(B0=evaluate_b0(a,b0contract,values)==evaluate_b0(b,b0contract,values),B1=rotation(a)==rotation(b),B2=b2({**base,key:True})==b2({**base,key:False}))
        if not all(checks.values()):raise ValueError('FEEDBACK_LEAK')
        feedback.append(dict(mutated_input=key,checks=checks))
    report('FEEDBACK_ISOLATION',dict(status='PASS',same_day_final_outputs_and_future_facts_excluded=True,cases=feedback))
    report('B2_INDEPENDENT_POSTCHECK',dict(status='PASS_ENGINEERING_EXPECTATIONS',source_binding_verified=hashlib.sha256((ROOT/ast['source_path']).read_bytes()).hexdigest()==ast['source_sha256'],golden_vector_count=len(gold),formal_non_amount_a_branch='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE',all_three_warm_branches='DIAGNOSTIC_AMOUNT_A_OPEN',external_acceptance_pending=True))
    print(json.dumps({'status':'PASS','golden_vectors':len(gold),'parameter_perturbations':len(perturb),'feedback_mutations':len(feedback)}))
if __name__=='__main__':main()
