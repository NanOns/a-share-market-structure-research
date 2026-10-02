"""R9 design fixture and semantic compatibility verifier. No runtime inputs."""
import argparse
import copy
import hashlib
import json
import subprocess
from decimal import Decimal
from scripts.repair_v4_12_time_counter_r2_1 import BASELINE,OUT,MARKET,EVAL,OLD,old
from scripts.v4_11_promotion_contract_r1 import ROOT,bind,PERMISSIONS
from scripts.record_r7_stage_contract import put
from scripts.validate_v4_12_contract_freeze_r1 import (load_configs,FixtureExpressionVerifier,UNKNOWN,walk,
    vector_oracle,literal_audit,dag_audit,schema_registry_audit,scope_proof)
from scripts.validate_v4_12_authority_r2 import authority_parity,coordinate_audit,unit_audit
from scripts.v4_12_time_counter_oracle_r2_1 import sequence_book,compatibility_vectors

def keep_proof():
    paths=['AGENTS.md','scripts/prepare_v4_11_promotion_r1.py','data/v4/V4_11_ACCEPTED_HEAD.json',
        'data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json',
        'config/v4_12_anchor_coordinate_contract_v1.json','config/v4_12_anchor_schema_v1.json','scripts/v4_12_independent_vector_oracle_r1.py',
        'scripts/v4_12_authority_oracle_r2.py']
    paths+=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'reports/next_round_r6r1','reports/v4_12_r2'],cwd=ROOT,text=True).splitlines()
    rows=[]
    for path in paths:
        before=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT);after=(ROOT/path).read_bytes();assert before==after,path
        rows.append(dict(path=path,before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest(),byte_identical=True))
    return rows

def authority_keep(configs):
    before=old('config/v4_12_field_registry_v1.json')['fields'];after={r['field']:r for r in configs['field_registry']['fields']}
    allowed_units={'prior_breach_count','prior_held_count','prior_recovery_held_count','prior_separated_sessions','prior_range20_atr'}
    total=0
    for row in before:
        if row['field_role']=='D1_LOCAL_DERIVATION' or row['field_role']=='D1_OUTPUT':continue
        current=copy.deepcopy(after[row['field']]);prior=copy.deepcopy(row)
        if row['field'] in allowed_units:
            current.pop('semantic_dimension',None);current['unit']=prior['unit']
        assert current==prior,'R2_ACCEPTED_OR_BLOCKED_AUTHORITY_CHANGED:'+row['field'];total+=1
    assert [(r['parameter_id'],r['value']) for r in configs['parameter_set']['parameters']]==[(r['parameter_id'],r['value']) for r in old('config/v4_12_parameter_set_v1.json')['parameters']]
    return dict(status='PASS_KEEP',unchanged_authority_rows=total,parameter_values_unchanged=24)

def normalize(value):
    if value is UNKNOWN:return 'UNKNOWN'
    if isinstance(value,Decimal):return int(value) if value==int(value) else str(value)
    return value

def sequence_actual(configs,sequence):
    """Synthetic sequence only: unique date membership, frozen previous-date baselines."""
    snapshots={};rows=[];dates=sequence['calendar'];available=sequence['available_date']
    for step in sequence['steps']:
        date=step['date'];earlier=sorted(d for d in snapshots if d<date)
        prior=snapshots[earlier[-1]] if earlier else None
        membership={d for d,s in snapshots.items() if available<d<date and s['qualifying_evaluable']}
        if step['evaluable'] and date>available:membership.add(date)
        market=None if dates is None else sum(available<d<=date for d in set(dates))
        calendar_previous=None if dates is None else max((d for d in dates if d<date),default=None)
        adjacent=bool(prior and earlier[-1]==calendar_previous and prior['qualifying_evaluable'])
        values={**configs['machine_vectors']['defaults'],MARKET:market,EVAL:len(membership),
            'evaluable':step['evaluable'],'C':step['C'],'L':10 if step['C'] is None or step['C']>=10 else 8,'H':11,
            'CLV':step.get('CLV',.7 if not prior else .4),'hi':10,'lo':10,'atr_prior_view':1,
            'prior_adjacent_evaluable':adjacent,'prior_held_count':prior['held_count'] if prior else 0,
            'prior_breach_count':prior['breach_count'] if prior else 0,
            'prior_support_state':prior['preserved_state'] if prior else 'IDLE',
            'prior_test_count':prior['test_count'] if prior else 0}
        verifier=FixtureExpressionVerifier(configs,values)
        observed=dict(market_age=market if market is not None else 'UNKNOWN',evaluable_count=len(membership),
            held_count=normalize(verifier.target('held_count')),breach_count=normalize(verifier.target('breach_count')),
            support=normalize(verifier.target('support')),acceptance=normalize(verifier.target('acceptance')),
            stale=not step['evaluable'] or market is None)
        # Missing observation does not overwrite the frozen previous state's meaning.
        preserved=prior['preserved_state'] if observed['support']=='UNKNOWN' and prior else observed['support']
        test_count=0 if date==available else (prior['test_count'] if not step['evaluable'] and prior else normalize(verifier.target('next_test_count')))
        snapshots[date]=dict(qualifying_evaluable=step['evaluable'],held_count=observed['held_count'],breach_count=observed['breach_count'],
            preserved_state=preserved,test_count=test_count)
        rows.append(dict(id=step['id'],date=date,revision=step['revision'],expected=step['expected'],actual=observed,
            status='PASS' if observed==step['expected'] else 'FAIL',counter_baseline_date=earlier[-1] if earlier else None,
            preserved_support_state=preserved))
    return rows

def dimensions(configs):
    fields={r['field']:r for r in configs['field_registry']['fields']};params={r['parameter_id']:r for r in configs['parameter_set']['parameters']}
    def unit_dimension(row,is_parameter=False):
        if row.get('semantic_dimension'):return row['semantic_dimension']
        unit=row['unit']
        if unit in ['adjusted_price','CNY_per_share_in_declared_common_coordinate']:return 'price'
        if unit=='ATR':return 'dimensionless_ATR_multiple' if is_parameter else 'price'
        if unit in ['ratio','ratio_unbounded','return_fraction','dimensionless']:return 'dimensionless_ratio'
        if unit=='percentage_points':return 'percentage_points'
        if row.get('data_type')=='boolean':return 'boolean'
        if row.get('data_type') in ['string','enum']:return 'enum'
        if unit in ['evaluable_sessions','actual_evaluable_sessions','test_count']:return 'actual_evaluable_count'
        return unit
    return fields,params,{n:unit_dimension(r) for n,r in fields.items()},{n:unit_dimension(r,True) for n,r in params.items()}

def compatible(left,right):
    if left==right:return True,'Same semantic dimension, independently resolved from definition/role'
    if 'mathematical_constant' in [left,right]:return True,'Explicit dimension-polymorphic mathematical constant, not a session threshold'
    if {left,right}<= {'consecutive_evaluable_count','evaluable_session_count','evaluable_session_threshold'}:
        return True,'Accepted threshold of two evaluable sessions supports cumulative PENDING and consecutive ACCEPTED; field definitions remain distinct'
    return False,'Different semantic domains; calendar age, evaluable count and actual separation are not interchangeable'

def time_audit(configs):
    fields,params,fd,pd=dimensions(configs);tree=configs['machine_ast'];rows=[]
    def dim(node):
        if 'field' in node:return fd[node['field']]
        if 'parameter_id' in node:return pd[node['parameter_id']]
        if 'math_constant' in node:return 'mathematical_constant'
        if 'enum' in node:return 'enum'
        op=node['op']
        if op in ['ge','gt','le','lt','eq','and','or','not']:return 'boolean'
        if op=='ordered_select':return dim(node['rules'][0]['then']) if node['rules'] else dim(node['otherwise'])
        ds=[dim(x) for x in node['args']]
        if op=='abs':return ds[0]
        if op=='require_known':return ds[-1]
        if op=='mul':
            if 'price' in ds and all(d in ['price','dimensionless_ATR_multiple','dimensionless_ratio','mathematical_constant'] for d in ds) and ds.count('price')==1:return 'price'
        if op=='div' and ds==['price','price']:return 'dimensionless_ATR_multiple'
        nonconstant=[d for d in ds if d!='mathematical_constant']
        assert not nonconstant or all(d==nonconstant[0] for d in nonconstant),'INCOMPATIBLE_ARITHMETIC:'+str(ds)
        return nonconstant[0] if nonconstant else 'mathematical_constant'
    def scan(node,path):
        if isinstance(node,dict):
            if node.get('op') in ['ge','gt','le','lt','eq']:
                left,right=node['args'];ld,rd=dim(left),dim(right);ok,reason=compatible(ld,rd)
                f=list(walk(node,'field'));p=list(walk(node,'parameter_id'))
                # Every comparison is covered, including threshold expressions containing ATR-price multipliers.
                rows.append(dict(field=f or None,field_semantic_dimension={n:fd[n] for n in f},field_unit={n:fields[n]['unit'] for n in f},
                    parameter=p or None,parameter_semantic_dimension={n:pd[n] for n in p},parameter_unit={n:params[n]['unit'] for n in p},
                    AST_path=path,operator=node['op'],left_expression_dimension=ld,right_expression_dimension=rd,compatible=ok,reason=reason))
            for k,v in node.items():scan(v,path+'/'+k)
        elif isinstance(node,list):
            for i,v in enumerate(node):scan(v,path+'/'+str(i))
    scan(tree['definitions'],'definitions');scan(tree['machines'],'machines')
    vectors=[]
    for v in compatibility_vectors():
        actual=compatible(fd[v['field']],pd[v['parameter']])[0]
        vectors.append(dict(**v,actual=actual,status='PASS' if actual==v['expected'] else 'FAIL'))
    counters=json.loads((ROOT/'config/v4_12_source_derivations_r2.json').read_bytes())['counters']
    return dict(status='PASS' if all(r['compatible'] for r in rows) and all(v['status']=='PASS' for v in vectors) else 'FAIL',
        incompatible_edges=sum(not r['compatible'] for r in rows),comparisons_scanned=len(rows),edges=rows,independent_vectors=vectors,
        counter_definitions=counters,method='Definition-derived dimensions and expression algebra; never unit-string equality alone')

def ast_diff(configs):
    before=old('config/v4_12_machine_ast_v1.json');after=configs['machine_ast'];changes=[]
    def compare(a,b,path):
        if isinstance(a,dict) and isinstance(b,dict):
            for k in sorted(set(a)|set(b)):compare(a.get(k),b.get(k),path+'/'+k)
        elif isinstance(a,list) and isinstance(b,list):
            assert len(a)==len(b),'RULE_ORDER_OR_COUNT_CHANGED'
            for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
        elif a!=b:
            allowed=(a==OLD and b in [MARKET,EVAL]) or path in ['/version','/semantic_amendment']
            assert allowed,'UNAUTHORIZED_AST_CHANGE:'+path
            changes.append(dict(AST_path=path,before=a,after=b,authority='R9 task sections2/3; REV4 sections41C/41D',reason='Separate market age from cumulative evaluable count',vector_impact='B03_missing corrected; other expected results unchanged'))
    compare(before,after,'')
    assert tree_fields(configs['machine_ast']['definitions']['old_anchor'])=={MARKET},'UNAUTHORIZED_AST_CHANGE:old_anchor_domain'
    assert tree_fields(configs['machine_ast']['machines']['acceptance']['rules'][3]['when'])=={EVAL},'UNAUTHORIZED_AST_CHANGE:PENDING_domain'
    return dict(status='PASS',changes=changes,business_order_unchanged=True,retention_formula_unchanged=before['definitions']['retention_value']==after['definitions']['retention_value'])
def tree_fields(node):return set(walk(node,'field'))

def validate(emit=False):
    configs=load_configs();proof=keep_proof();keep=authority_keep(configs)
    parity=authority_parity();coordinate=coordinate_audit(configs);units=unit_audit(configs)
    oracle=vector_oracle(configs);assert oracle['status']=='PASS'
    literal=literal_audit(configs);dag=dag_audit(configs);schema_registry_audit(configs)
    audit=time_audit(configs);assert audit['status']=='PASS',json.dumps([r for r in audit['edges'] if not r['compatible']])
    diff=ast_diff(configs)
    fields={r['field']:r for r in configs['field_registry']['fields']}
    for name,unit,domain in [(MARKET,'market_sessions_after_available_date','market_session_age'),(EVAL,'evaluable_sessions','evaluable_session_count')]:
        row=fields[name];assert row['unit']==unit and row['semantic_dimension']==domain and row['producer_contract_id']=='V4_12_SESSION_COUNTER_V2'
        role=next(r for r in configs['time_role_registry']['fields'] if r['field']==name)
        assert role['producer_contract_id']==row['producer_contract_id'] and role['required_by']==row['required_by']
    assert fields[EVAL]['required_by']==['acceptance.PENDING']
    book=json.loads((ROOT/'config/v4_12_time_counter_vectors_r2_1.json').read_bytes())
    assert book['sequences']==sequence_book() and book['time_domain_vectors']==compatibility_vectors()
    old_vectors={r['vector_id']:r for r in old('config/v4_12_machine_vectors_v1.json')['vectors']}
    assert len(oracle['vectors'])==69
    assert all(r['expected']==old_vectors[r['vector_id']]['expected'] for r in oracle['vectors'] if r['vector_id']!='B03_missing')
    assert next(r for r in oracle['vectors'] if r['vector_id']=='B03_missing')['expected']=='PENDING'
    sequences=[dict(id=s['id'],steps=sequence_actual(configs,s)) for s in sequence_book()]
    assert all(r['status']=='PASS' for s in sequences for r in s['steps']),json.dumps(sequences)
    forbidden=subprocess.check_output(['git','diff','--name-only',BASELINE],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('src/','data/','migrations/','alembic/')) or '/migrations/' in p for p in forbidden)
    assert OLD not in set(walk(configs['machine_ast'],'field'))
    result=dict(status='V4_12_R2_1_TIME_COUNTER_SEMANTICS_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',starting_remote_head=BASELINE,
        authority_parity=parity,authority_keep=keep,coordinate_authority=coordinate,unit_parity=units,time_domain_compatibility=audit,
        independent_vector_oracle=oracle,sequence_vectors=sequences,AST_diff=diff,protected_and_keep_proof=proof,scope_proof=scope_proof(),
        completeness=dict(authority_parity='PASS',blocked_anchor_types=old('reports/v4_12_r2/V4_12_R2_CONTRACT_COMPLETENESS_MATRIX.json')['blocked_anchor_types']),
        runtime_implemented=False,runtime_authorized=False,schema_migration=False,permissions=PERMISSIONS,external_acceptance=False,next_stage='COMMIT_PUSH_STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    if emit:
        for name,value in [('V4_12_R2_1_TIME_DOMAIN_COMPATIBILITY_AUDIT',audit),('V4_12_R2_1_EXACT_AST_DIFF',diff),('V4_12_R2_1_SEQUENCE_ORACLE',dict(status='PASS',sequences=sequences)),
            ('V4_12_R2_1_AMENDED_69_VECTOR_ORACLE',oracle),('V4_12_R2_1_PARAMETER_LITERAL_AUDIT',literal),('V4_12_R2_1_DAG_EDGE_AUDIT',dag),('V4_12_R2_1_TIME_COUNTER_SEMANTICS',result)]:put(OUT+name+'.json',value)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--emit',action='store_true');a=p.parse_args();r=validate(a.emit)
    print(json.dumps(dict(status=r['status'],incompatible_edges=r['time_domain_compatibility']['incompatible_edges'],prior_vectors=r['independent_vector_oracle']['passed'],sequence_steps=sum(len(s['steps']) for s in r['sequence_vectors']))))
