"""Freeze R5 parameter instance and source-bound B2 AST; no dataset fitting."""
from pathlib import Path
import sys
import json
import hashlib
import copy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json

def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    params=copy.deepcopy(read('config/v4_08_algorithm_parameter_set_v1.json'))
    params.update(parameter_set_id='V4_08_ALGORITHM_PARAMETER_SET_R5',version='5.0.0',status='FROZEN_ENGINEERING_CANDIDATE')
    decisions=[
        ('V4_08_EARLY_SEED_RETENTION_MIN',2/3,[.5,2/3,.8],'Require two thirds of the frozen seed cohort; tolerates one third attrition without accepting a bare half.', 'GTE', 'early_retained'),
        ('V4_08_EARLY_BREADTH_RETENTION_MIN',.6,[.5,.6,.75],'Require a strict majority with a ten point margin of the frozen positive cohort.', 'GTE','early_retained'),
        ('V4_08_EARLY_BREADTH_DELTA_MIN',0,[-.05,0,.05],'Acceptance requires nondecreasing common-member breadth; pulse separately requires positive expansion.', 'GTE','early_retained'),
        ('V4_08_EARLY_TOP1_CONCENTRATION_MAX',1/3,[.25,1/3,.5],'One member cannot exceed one third of observed amount, stricter than the one half diffusion ceiling.', 'LTE','early_retained'),
        ('V4_08_MATURE_STRONG_RETENTION_MIN',.75,[.6,.75,.9],'Mature extension preserves three quarters of the prior strong cohort; stronger than early breadth preservation.', 'GTE','mature_retained')]
    package=[]
    for pid,value,candidates,meaning,op,rule in decisions:
        p=next(p for p in params['parameters'] if p['parameter_id']==pid)
        p.update(value=value,comparison=op,status='FROZEN_CANDIDATE',authority='R5 semantic decision package; external validation pending')
        probes=sorted(set([0,1,value,*candidates,*[(a+b)/2 for a,b in zip(sorted(candidates),sorted(candidates)[1:])]]))
        package.append(dict(parameter_id=pid,candidate_range=[min(candidates),max(candidates)],tested_values=candidates,
            selected=value,semantic_meaning=meaning,monotonicity='Increasing threshold tightens qualification' if op=='GTE' else 'Increasing ceiling loosens qualification',
            affected_rules=[rule],affected_states=['ROTATION_IN','ROTATION_ACCEPTED','ROTATION_EXPANDING','ROTATION_REACCELERATING'] if rule=='early_retained' else ['ROTATION_EXPANDING','ROTATION_REACCELERATING'],
            sensitivity=[dict(threshold=t,probe_truth=[v>=t if op=='GTE' else v<=t for v in probes]) for t in candidates],probes=probes,
            selection_reason=meaning,rejected_alternatives=[dict(value=t,reason='Looser admits excessive attrition/concentration' if (t<value if op=='GTE' else t>value) else 'Stricter excludes the intended semantic boundary') for t in candidates if t!=value],
            future_outcome_data_used=False,market_candidate_counts_used_for_selection=False,probability_claim=False))
    atomic_json(ROOT/'config/v4_08_algorithm_parameter_set_r5.json',params)
    binding=sha('config/v4_08_algorithm_parameter_set_r5.json')
    registry=read('config/v4_08_sector_field_registry_v2.json')
    registry.update(version='5.0.0',field_registry_id='V4_08_SECTOR_FIELD_REGISTRY_R5')
    known={f['field_id'] for f in registry['fields']}
    extra=['sector_rs1','sector_rs60','sector_rs20_pct','sector_rs60_pct','breadth_ret5','breadth_ret20','ma20_delta1','strong_member','strong_member_retention','seed_width','seed_retention','participation_proxy','pos60','mdd20','top3_concentration','sector_price_retention_core']
    for field in extra:
        if field not in known:registry['fields'].append(dict(field_id=field,producer='ROTATION_CORE_V1' if field=='sector_price_retention_core' else 'V4_08_SECTOR_NATIVE_V1',time_role='PULSE_FROZEN_PATH' if field=='sector_price_retention_core' else 'TARGET_CUTOFF',unit='member_set' if field=='strong_member' else 'ratio_or_percentile_points_as_field_contract',unknown_behavior='UNKNOWN'))
    atomic_json(ROOT/'config/v4_08_sector_field_registry_r5.json',registry)
    atomic_json(ROOT/'reports/v4_08/V4_08_R5_RETENTION_PARAMETER_DECISION_PACKAGE.json',dict(status='FROZEN_ENGINEERING_CANDIDATE',parameter_set_id=params['parameter_set_id'],parameter_set_sha256=binding,decisions=package,external_acceptance_pending=True))
    for source,out in [('config/v4_08_sector_prewatch_contract_v2.json','config/v4_08_sector_prewatch_contract_r5.json'),('config/v4_08_rotation_core_contract_v2.json','config/v4_08_rotation_core_contract_r5.json')]:
        contract=read(source);contract.update(parameter_set_id=params['parameter_set_id'],parameter_set_sha256=binding,pending_parameter_ids=[],runtime_implementation='src/sector/rotation_r5.py',field_registry_digest=digest(registry),field_registry_path='config/v4_08_sector_field_registry_r5.json')
        atomic_json(ROOT/out,contract)
    native=read('config/v4_08_sector_native_contract_v1.json');native.update(parameters='config/v4_08_algorithm_parameter_set_r5.json',runtime_implementation='src/sector/native_r5.py',full_market_materialization_enabled=True,field_registry='config/v4_08_sector_field_registry_r5.json')
    native['scope']['full_market_materialization']='ENGINEERING_CANDIDATE_ONLY'
    atomic_json(ROOT/'config/v4_08_sector_native_contract_r5.json',native)
    legacy='src/workbench_analysis/sector_attention.py';legacy_params='config/research_attention_v3.yaml'
    cfg=read(legacy_params)['thresholds'];rules={};fields={}
    def leaf(field,op,constant):
        fields[field]={'field_id':field,'producer':'V4_08_B2_CORE_ADAPTER','time_role':'TARGET_CUTOFF','unit':'ratio_or_boolean_as_source','unknown_behavior':'UNKNOWN'}
        return dict(field_id=field,operator=op,constant=constant,producer='V4_08_B2_CORE_ADAPTER',time_role='TARGET_CUTOFF',quality_requirement=['ACCEPTED'],unknown_behavior='UNKNOWN')
    def AND(*children):return {'operator':'AND','children':list(children)}
    def OR(*children):return {'operator':'OR','children':list(children)}
    cov=cfg['coverage'];c=cfg['current'];common=cfg['potential_common'];branches=cfg['potential_branches']
    current_specs=[('allowed_sector_type','EQ',True),('normal_rank_eligible','EQ',True),('total_member_count','GTE',cov['min_sector_members']),('quote_coverage','GTE',cov['min_member_quote_coverage']),('market_ok','EQ',True),('type_cross_section_coverage','GTE',cov['min_sector_cross_section_coverage']),('m1','GT',c['m1_gt']),('b1','GTE',c['b1_gte']),('rel1','GTE',c['rel1_gte']),('p1','GTE',c['p1_gte']),('positive_count','GTE',c['min_positive_count']),('top1_positive_share','LTE',c['top1_positive_share_lte'])]
    rules['confirmed_raw']=AND(*(leaf(*s) for s in current_specs))
    rules['weak']=OR(AND(leaf('m1','LT',c['weak_m1_lt']),leaf('b1','LT',c['weak_b1_lt'])),AND(leaf('m1','LT',c['weak_m1_lt']),leaf('b_delta3','LTE',c['weak_b_delta3_lte'])))
    base=[leaf('normal_rank_eligible','EQ',True),leaf('total_member_count','GTE',cov['min_sector_members']),leaf('current','EQ',False),leaf('weak','EQ',False),leaf('m1','GTE',common['m1_gte']),leaf('ma20_width','GTE',common['ma20_width_gte']),leaf('risk_coverage','GTE',cov['min_risk_coverage']),leaf('extended_share','LTE',common['extended_member_share_lte'])]
    b=branches['BREADTH_BUILD'];rules['BREADTH_BUILD']=AND(*base,leaf('dq5_3','GTE',b['dq5_3_gte']),leaf('b_delta3','GTE',b['b_delta3_gte']),leaf('ma20_delta3','GTE',b['ma20_delta3_gte']),leaf('early_width','GTE',b['early_width_gte']),leaf('early_count','GTE',common['min_early_watch_count']),leaf('amount_A','GTE',b['amount_A_gte']))
    b=branches['BASE_BUILD'];rules['BASE_BUILD']=AND(*base,leaf('q20','GTE',b['q20_gte']),leaf('ma20_width','GTE',b['ma20_width_gte']),leaf('ma20_delta3','GTE',b['ma20_delta3_gte']),leaf('setup_count_gate','EQ',True),leaf('amount_A','GTE',b['amount_A_min']),leaf('amount_A','LTE',b['amount_A_max']),leaf('b_delta3','GTE',b['b_delta3_gte']))
    b=branches['RECOVERY_BUILD'];rules['RECOVERY_BUILD']=AND(*base,leaf('prior_current_within10','EQ',True),leaf('rel1','GT',b['rel1_gt']),leaf('b_delta3','GTE',b['b_delta3_gte']),leaf('ma20_delta3','GTE',b['ma20_delta3_gte']),leaf('amount_A','GTE',b['amount_A_gte']),leaf('early_count','GTE',b['recovery_or_setup_count_min']))
    rules['warm_diagnostic']=OR(*[{'operator':'REF','rule_id':r} for r in branches])
    ast=dict(model_contract_id='V4_08_SECTOR_LEGACY_ADAPTER_B2_R5',rules=rules,fields=fields,
        ast_digest=digest(rules),source_path=legacy,source_sha256=sha(legacy),source_parameter_path=legacy_params,source_parameter_sha256=sha(legacy_params),parameter_set_id=params['parameter_set_id'],parameter_set_sha256=binding,
        field_registry_digest=digest(fields),current_market_gate='UNKNOWN_IF_MARKET_OK_NOT_TRUE',warm_formal='UNKNOWN_AMOUNT_A_AUDIT_OPEN',
        setup_count_gate=dict(formula='setup_count >= max(setup_count_min, ceil(setup_count_ratio * setup_evaluable_count))',parameters=branches['BASE_BUILD']),
        source_units={'returns':'decimal','p1/q20/dq5_3':'ratio; V4 percentile points require division by 100','amount_A':'actual sector_amount_vs_prior20 only; no participation proxy'},
        source_time='accepted target cutoff; history accepted prior publications only',unknown_behavior='preserve source three-valued logic; no unavailable inputs coerced to bool or integer')
    atomic_json(ROOT/'config/v4_08_b2_machine_ast_r5.json',ast)
    atomic_json(ROOT/'reports/v4_08/V4_08_R5_B2_MACHINE_AST.json',ast)
    extraction=dict(status='EXACT_SOURCE_AST_EXTRACTED_ENGINEERING_CANDIDATE',source_path=legacy,source_sha256=sha(legacy),symbols=['build_sector_current','build_sector_potential','_tri_all','_truth'],
        call_graph={'build_sector_current':['_sector_semantics','_finite','_tri_all'],'build_sector_potential':['_finite','_truth','_tri_all']},
        ast_path='config/v4_08_b2_machine_ast_r5.json',ast_sha256=sha('config/v4_08_b2_machine_ast_r5.json'),
        parameters_path=legacy_params,parameters_sha256=sha(legacy_params),input_dependencies=list(fields),
        output_states=['TRUE','FALSE','UNKNOWN'],amount_a_scope='ALL_POTENTIAL_BRANCHES_DIAGNOSTIC; CURRENT_QUALIFICATION_NON_AMOUNT_A',
        excluded_source_side_effects=['display sorting by amount_A','progress_potential_episode','final stock signals'],
        source_units=ast['source_units'],source_time=ast['source_time'],unknown_behavior=ast['unknown_behavior'],
        early_width_scope='UNAVAILABLE_UNTIL_EXACT_PURE_CORE_SETUP_RECOVERY_PRODUCERS_ACCEPTED; BASE_SEED_NOT_SUBSTITUTED',
        setup_count_gate=ast['setup_count_gate'])
    atomic_json(ROOT/'reports/v4_08/V4_08_R5_B2_LEGACY_SOURCE_EXTRACTION.json',extraction)
    print(json.dumps({'status':'FROZEN','parameter_sha256':binding,'b2_ast_digest':ast['ast_digest']}))

if __name__=='__main__':main()
