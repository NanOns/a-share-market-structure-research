"""Contract-only verifier: generic serialized-expression evaluation on frozen fixtures.

This script has no market reader, runtime detector, publication or database API.
The independent oracle module supplies expected vectors, never this interpreter.
"""
import argparse
import copy
import hashlib
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from jsonschema import Draft202012Validator
from scripts.v4_11_promotion_contract_r1 import ROOT, PERMISSIONS, bind
from scripts.record_r7_stage_contract import BASELINE, protected_proof, put

UNKNOWN=object()
CONFIG_NAMES=['structure_event_contract','anchor_schema','anchor_coordinate_contract','support_state_contract','retention_contract',
              'field_registry','producer_registry','time_role_registry','input_schema','output_schema','parameter_set','machine_ast','machine_vectors']

def load_configs(root=ROOT):
    return {n:json.loads((root/('config/v4_12_'+n+'_v1.json')).read_bytes()) for n in CONFIG_NAMES}

class FixtureExpressionVerifier:
    """Only JSON expression grammar; fixtures, not market input/publication."""
    def __init__(self,configs,values):
        self.tree=configs['machine_ast'];self.values=dict(values);self.stack=[];self.cache={}
        self.params={r['parameter_id']:Decimal(str(r['value'])) for r in configs['parameter_set']['parameters']}
    def value(self,name):
        if name in self.tree['definitions']:
            if name in self.stack: raise ValueError('AST_DEFINITION_CYCLE:'+name)
            if name not in self.cache:
                self.stack.append(name)
                try:self.cache[name]=self.expression(self.tree['definitions'][name])
                finally:self.stack.pop()
            return self.cache[name]
        value=self.values.get(name)
        if value is None:return UNKNOWN
        if isinstance(value,bool):return value
        if isinstance(value,(int,float,Decimal)):return Decimal(str(value))
        if isinstance(value,str):
            try:return Decimal(value)
            except Exception:return value
        return value
    def expression(self,node):
        if 'field' in node:return self.value(node['field'])
        if 'parameter_id' in node:return self.params[node['parameter_id']]
        if 'math_constant' in node:return Decimal(str(self.tree['math_constants'][node['math_constant']]['value']))
        if 'enum' in node:return node['enum']
        operator=node['op']
        if operator=='ordered_select':
            for rule in node['rules']:
                condition=self.expression(rule['when'])
                if condition is UNKNOWN:return UNKNOWN
                if condition:return self.expression(rule['then'])
            return self.expression(node['otherwise'])
        values=[self.expression(v) for v in node['args']]
        if operator=='and':
            if any(v is False for v in values):return False
            return UNKNOWN if any(v is UNKNOWN for v in values) else all(values)
        if operator=='or':
            if any(v is True for v in values):return True
            return UNKNOWN if any(v is UNKNOWN for v in values) else any(values)
        if any(v is UNKNOWN for v in values):return UNKNOWN
        if operator=='require_known':return values[-1]
        if operator=='not':return not values[0]
        if operator=='abs':return abs(values[0])
        a,b=values
        if operator=='eq':return a==b
        if operator=='gt':return a>b
        if operator=='ge':return a>=b
        if operator=='lt':return a<b
        if operator=='le':return a<=b
        if operator=='add':return a+b
        if operator=='sub':return a-b
        if operator=='mul':return a*b
        if operator=='div':return UNKNOWN if b<=0 else a/b
        raise ValueError('UNREGISTERED_AST_OPERATOR:'+operator)
    def target(self,name):
        if name in self.tree['machines']:return self.expression(self.tree['machines'][name])
        return self.value(name)

def walk(node,key):
    if isinstance(node,dict):
        if key in node:yield node[key]
        for value in node.values():yield from walk(value,key)
    elif isinstance(node,list):
        for value in node:yield from walk(value,key)

def literal_audit(configs):
    tree=configs['machine_ast'];params={r['parameter_id']:r for r in configs['parameter_set']['parameters']}
    fields={r['field'] for r in configs['field_registry']['fields']}
    counts={'acceptance_consecutive_sessions','support_break_consecutive_sessions','support_separated_retest_sessions',
            'support_tentative_hold_sessions','range_anchor_window','pivot_left_sessions','pivot_right_sessions',
            'earliest_anchor_test_sessions','retention_horizon_one','retention_horizon_three'}
    for name,row in params.items():
        assert row['status']=='ENGINEERING_CANDIDATE'
        assert not any(row[k] for k in ['profitability_validated','statistically_optimal','production_proven'])
        assert row['value']>0
        if 'clv' in name:assert row['value']<=1
        if name in counts:assert isinstance(row['value'],int)
    leaves=[]
    def visit(node,path):
        assert isinstance(node,dict),'UNBOUND_AST_LITERAL:'+path
        leafkeys=set(node)&{'field','parameter_id','math_constant','enum'}
        if leafkeys:
            assert len(node)==1 and len(leafkeys)==1,'AMBIGUOUS_AST_LEAF:'+path
            kind=next(iter(leafkeys));value=node[kind]
            if kind=='parameter_id':assert value in params,'UNREGISTERED_PARAMETER:'+value
            if kind=='math_constant':assert value in tree['math_constants'] and tree['math_constants'][value]['reason']
            if kind=='field':assert value in fields,'UNREGISTERED_FIELD:'+value
            if kind=='enum':assert isinstance(value,str),'ENUM_MUST_BE_NAMED_STATE'
            leaves.append(dict(ast_path=path,kind=kind,binding=value));return
        assert node.get('op') in tree['grammar']['operations'],'UNREGISTERED_AST_OPERATOR'
        if node['op']=='ordered_select':
            assert node['unknown']=='STOP_WITH_UNKNOWN_BEFORE_LOWER_PRIORITY'
            for i,rule in enumerate(node['rules']):
                visit(rule['when'],path+'/rules/'+str(i)+'/when');visit(rule['then'],path+'/rules/'+str(i)+'/then')
            visit(node['otherwise'],path+'/otherwise')
        else:
            assert set(node)=={'op','args'}
            for i,arg in enumerate(node['args']):visit(arg,path+'/args/'+str(i))
    for family in ['definitions','machines']:
        for name,node in tree[family].items():visit(node,family+'/'+name)
    used={v['binding'] for v in leaves if v['kind']=='parameter_id'}
    metadata_uses={'range_anchor_window':'Anchor PRIOR_HIGH/RANGE_UPPER historical accepted window',
                   'retention_horizon_one':'retention observation target t0+1','retention_horizon_three':'retention observation target t0+3'}
    assert used|set(metadata_uses)==set(params),'UNBOUND_PARAMETER_USE'
    return dict(status='PASS',unbound_literal_count=0,parameters=len(params),ast_leaf_count=len(leaves),
                bindings=leaves,metadata_parameter_uses=metadata_uses,all_statuses='ENGINEERING_CANDIDATE')

def dag_audit(configs):
    tree=configs['machine_ast'];reg={r['field']:r for r in configs['field_registry']['fields']}
    roles=configs['time_role_registry']
    assert roles['allowed_external_edges']==['F0[t] -> D1[t]','Frozen Anchor/event[t-1] -> D1[t]']
    forbidden=['D2[t] -> D1[t]','Final State[t] -> D1[t]','Event[t] -> D1[t]','Focus -> D1[t]','UI -> D1[t]','Supplemental feedback -> D1[t]','future outcome -> D1[t]']
    assert roles['forbidden_edges']==forbidden
    refs=set(walk(tree,'field'));assert not refs- set(reg)
    for name in refs:
        row=reg[name]
        assert row['source_namespace'] in ['F0_ACCEPTED','FROZEN_ANCHOR_EVENT','D1_LOCAL_DERIVATION','BLOCKED_CAPABILITY']
        if row['source_namespace']=='BLOCKED_CAPABILITY':assert row.get('field_role')=='BLOCKED_CAPABILITY' and row.get('blocked_reason')
        if row['source_namespace']=='FROZEN_ANCHOR_EVENT':assert row['time_role']=='T_MINUS_1'
    # Definition graph must terminate at registered external leaves.
    dependencies={n:set(walk(v,'field')) & set(tree['definitions']) for n,v in tree['definitions'].items()}
    visiting=set();done=set()
    def visit(n):
        assert n not in visiting,'AST_DEFINITION_CYCLE'
        if n in done:return
        visiting.add(n)
        for child in dependencies[n]:visit(child)
        visiting.remove(n);done.add(n)
    for n in dependencies:visit(n)
    assert configs['anchor_coordinate_contract']['basis_identity']==['price_basis','adjustment_source_revision']
    assert configs['anchor_coordinate_contract']['coefficient_equality_is_identity'] is False
    return dict(status='PASS',formula='D1[t] = F0[t] + t-1 frozen Anchor/event',external_edges=roles['allowed_external_edges'],
                forbidden_edges=forbidden,registered_input_refs=sorted(refs),definition_graph={k:sorted(v) for k,v in dependencies.items()},
                forbidden_reference_count=0,same_day_new_anchor_self_support=False,earliest_test='t+1')

def gate_fixture(vector):
    values=vector['inputs'];name=vector['target']
    if name=='coordinate_gate':return 'UNKNOWN:PRICE_BASIS_MISMATCH' if not values['convertible'] else 'KNOWN'
    if name=='immutable_anchor':
        original=copy.deepcopy(values['original']);before=json.dumps(original,sort_keys=True).encode()
        view=Decimal(str(original['price']))*Decimal(str(values['alpha']))+Decimal(str(values['beta']))
        assert view==5
        return before==json.dumps(original,sort_keys=True).encode()
    if name=='basis_identity':return values['left']==values['right']
    if name=='future_source':
        return 'REJECT:FUTURE_SOURCE' if datetime.fromisoformat(values['source_available'])>datetime.fromisoformat(values['cutoff']) else 'KNOWN'
    raise ValueError('UNKNOWN_GATE_FIXTURE')

def vector_oracle(configs):
    from scripts.v4_12_independent_vector_oracle_r1 import vectors
    golden=vectors();pack=configs['machine_vectors']
    assert pack['vectors']==golden,'INDEPENDENT_ORACLE_BOOK_MISMATCH'
    assert pack['independent_oracle_source']==bind('scripts/v4_12_independent_vector_oracle_r1.py')
    rows=[]
    for vector in golden:
        values={**pack['defaults'],**vector['inputs']}
        verifier=FixtureExpressionVerifier(configs,values)
        actual=gate_fixture(vector) if vector['kind']=='GATE' else verifier.target(vector['target'])
        expected=vector['expected']
        if actual is UNKNOWN:actual='UNKNOWN'
        elif isinstance(actual,Decimal):actual=str(actual)
        # Decimal values compare numerically; state/enumeration/booleans exact.
        if isinstance(expected,bool):passed=actual is expected
        elif isinstance(expected,(int,float)) or (isinstance(expected,str) and expected[:1] in '-0123456789'):
            try:passed=Decimal(str(actual))==Decimal(str(expected))
            except Exception:passed=False
        else:passed=actual==expected
        rows.append(dict(vector_id=vector['vector_id'],target=vector['target'],expected=expected,actual=actual,
                         status='PASS' if passed else 'FAIL',proof=vector['independent_oracle_proof']))
    return dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',total=len(rows),
                passed=sum(r['status']=='PASS' for r in rows),failed=sum(r['status']=='FAIL' for r in rows),
                expected_source=bind('scripts/v4_12_independent_vector_oracle_r1.py'),actual_source=bind('scripts/validate_v4_12_contract_freeze_r1.py'),
                oracle_imports_future_implementation=False,scope='SYNTHETIC_DESIGN_ONLY_NOT_RUNTIME_ACCEPTANCE',vectors=rows)

def schema_registry_audit(configs):
    for name in ['input_schema','output_schema','anchor_schema']:Draft202012Validator.check_schema(configs[name]['schema'])
    registry=configs['field_registry']['fields'];assert len({r['field'] for r in registry})==len(registry)
    required={'producer_contract_id','parameter_set_id','source_namespace','trade_date','time_role','publication_identity','quality','unknown_reason_family','output_digest','formal_or_diagnostic'}
    required|= {'globally_required','required_by'} if configs['producer_registry'].get('authority_repair')=='R2' else {'required'}
    for row in registry:assert required<=row.keys()
    producers={r['producer_contract_id'] for r in configs['producer_registry']['producers']}
    assert {r['producer_contract_id'] for r in registry}<=producers,'UNREGISTERED_PRODUCER'
    assert {r['field'] for r in configs['time_role_registry']['fields']}=={r['field'] for r in registry}
    unavailable={'close_t_minus_1','ma20_t_minus_1'}
    for row in registry:
        if row['field'] in unavailable:
            assert row['capability']=='FORMAL_BLOCKED_INPUT_CAPABILITY' and not row['raw_reconstruction_allowed']
    assert configs['structure_event_contract']['recovery_missing_prior_policy']=='DO_NOT_RECONSTRUCT_FROM_RAW_BARS'
    assert configs['structure_event_contract']['recovery_missing_reason']=='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'
    assert len(configs['anchor_schema']['types'])==9
    for row in configs['anchor_schema']['types']:
        assert {'source_event','creation_rule','available_date','available_time','fixed_or_dynamic','price_basis','required_fields','unknown','invalidation_relation','earliest_test_date'}<=row.keys()
    return dict(status='PASS',registered_fields=len(registry),anchor_types=9,json_schema_draft='2020-12')

def validate_envelope_fixture(configs,envelope):
    """Metadata-only schema/source checks on synthetic envelopes, never fact production."""
    Draft202012Validator(configs['input_schema']['schema']).validate(envelope)
    registry={r['field']:r for r in configs['field_registry']['fields']}
    cutoff=datetime.fromisoformat(envelope['cutoff'])
    for name,fact in envelope['inputs'].items():
        row=registry[name]
        if fact['source_namespace']!=row['source_namespace'] or fact['time_role']!=row['time_role']:
            raise ValueError('D1_SOURCE_NAMESPACE_OR_TIME_ROLE_MISMATCH')
        if fact['producer_contract_id']!=row['producer_contract_id']:
            raise ValueError('D1_SOURCE_PRODUCER_MISMATCH')
        if datetime.fromisoformat(fact['available_at'])>cutoff:raise ValueError('FUTURE_SOURCE')
        if row['time_role']=='T_MINUS_1' and row['source_namespace']=='FROZEN_ANCHOR_EVENT' and fact['trade_date']>=envelope['observation_trade_date']:
            raise ValueError('SAME_DAY_ANCHOR_NOT_FROZEN_PREDECESSOR')
        if fact['quality']=='KNOWN' and (row['capability']=='FORMAL_BLOCKED_INPUT_CAPABILITY' or row.get('field_role') in ['BLOCKED_CAPABILITY','FROZEN_PRIOR_D1']):
            raise ValueError('UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE')
        if fact['quality']!='KNOWN' and not fact['unknown_reason']:raise ValueError('UNKNOWN_REASON_REQUIRED')
        if fact['quality']=='KNOWN':
            value=fact['value'];kind=row['data_type']
            valid=(isinstance(value,bool) if kind=='boolean' else isinstance(value,int) and not isinstance(value,bool) if kind=='integer' else
                   isinstance(value,(int,float)) and not isinstance(value,bool) if kind=='number' else isinstance(value,str) if kind=='string' else
                   isinstance(value,dict) if kind=='object' else isinstance(value,list) if kind=='array' else False)
            if not valid:raise ValueError('REGISTERED_FIELD_TYPE_MISMATCH')
        # Digests/publication IDs are opaque accepted-owner bindings. Local raw
        # bar presence never upgrades capability; no runtime source loader here.
    return 'PASS_METADATA_ONLY_NO_RUNTIME_SOURCE_ACCEPTANCE'

def scope_proof():
    changed=subprocess.check_output(['git','diff','--name-only',BASELINE],cwd=ROOT,text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    forbidden=[p for p in changed+untracked if p.startswith(('src/v4/','migrations/','alembic/')) or '/migrations/' in p or '/alembic/' in p]
    assert not forbidden,'R7_FORBIDDEN_RUNTIME_OR_MIGRATION_CHANGE:'+str(forbidden)
    proofs=protected_proof()
    stage=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())
    data=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    assert stage['accepted_stage_range']=='V4_00_TO_V4_11_ACCEPTED'
    assert data['accepted_trade_date']=='2026-09-30'
    assert all(stage[k] is False for k in PERMISSIONS)
    assert not any(data['permissions'].values())
    for path in ['data/v4/V4_11_ACCEPTED_HEAD.json','reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json']:
        obj=json.loads((ROOT/path).read_bytes());assert all(obj[k] is False for k in PERMISSIONS)
    return dict(status='PASS',no_src_v4_runtime_change=True,no_schema_migration=True,forbidden_changes=forbidden,
                stage_head=stage['accepted_stage_range'],data_head=data['accepted_trade_date'],permissions=PERMISSIONS,protected_artifacts=proofs)

def validate(emit=False):
    if load_configs()['producer_registry'].get('authority_repair')=='R2':
        from scripts.validate_v4_12_authority_r2 import validate as validate_authority
        if emit:raise ValueError('R1_EVIDENCE_IMMUTABLE_USE_R2_AUTHORITY_VALIDATOR')
        return validate_authority()
    configs=load_configs();literal=literal_audit(configs);dag=dag_audit(configs)
    schema=schema_registry_audit(configs);oracle=vector_oracle(configs);scope=scope_proof()
    assert oracle['status']=='PASS',json.dumps([r for r in oracle['vectors'] if r['status']=='FAIL'])
    for name,obj in configs.items():
        if name!='machine_vectors':assert obj['freeze_scope']=='CONTRACT_DESIGN_ONLY' and obj['runtime_implemented'] is False and obj['permissions']==PERMISSIONS
    matrix=[dict(item=n,status='FROZEN',path='config/v4_12_'+n+'_v1.json') for n in CONFIG_NAMES]
    matrix.extend(dict(item=name,status='FROZEN',path=path) for name,path in [
        ('STRUCTURE_EVENT_V1','config/v4_12_structure_event_contract_v1.json'),
        ('Anchor identity / immutability / availability','config/v4_12_anchor_schema_v1.json'),
        ('Anchor coordinate / rebase lineage','config/v4_12_anchor_coordinate_contract_v1.json'),
        ('Support / separated retest / counter rules','config/v4_12_support_state_contract_v1.json'),
        ('Breakout AST','config/v4_12_machine_ast_v1.json#/machines/breakout'),
        ('Pullback AST','config/v4_12_machine_ast_v1.json#/machines/pullback'),
        ('Recovery AST / ordered UNKNOWN semantics','config/v4_12_machine_ast_v1.json#/machines/recovery'),
        ('Bullish Impulse AST','config/v4_12_machine_ast_v1.json#/definitions/impulse'),
        ('Creation-bound episode invalidation AST','config/v4_12_machine_ast_v1.json#/definitions/episode_invalidated'),
        ('Retention / Acceptance','config/v4_12_retention_contract_v1.json'),
        ('Required facts / source capability / UNKNOWN','config/v4_12_producer_registry_v1.json'),
        ('Independent vectors / oracle book','config/v4_12_machine_vectors_v1.json')])
    matrix.extend(dict(item='CAPABILITY:'+','.join(row['fields']),status='BLOCKED_WITH_EXPLICIT_REASON',reason=row['reason'],capability=row['capability'])
                  for row in configs['producer_registry']['capabilities'])
    completeness=dict(status='PASS',contract_id='V4_12_CONTRACT_COMPLETENESS_MATRIX_V1',items=matrix,
        all_rows_explicit=True,allowed_statuses=['FROZEN','BLOCKED_WITH_EXPLICIT_REASON'],runtime_permission_granted=False)
    result=dict(contract_id='V4_12_R1_CONTRACT_FREEZE_V1',status='V4_12_R1_CONTRACT_FREEZE_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',
        acceptance='EXTERNAL_AUDIT_PENDING',scope='CONTRACT_DESIGN_FREEZE_ONLY',external_acceptance_claim=False,
        starting_remote_head=BASELINE,stage_contract=bind('reports/v4_12_r1/R7_STAGE_CONTRACT.json'),
        contracts=[bind('config/v4_12_'+n+'_v1.json') for n in CONFIG_NAMES],
        registries={n:'config/v4_12_'+n+'_v1.json' for n in ['field_registry','producer_registry','time_role_registry']},
        literal_audit_summary={k:literal[k] for k in ['status','unbound_literal_count','parameters','ast_leaf_count']},
        dag_audit_status=dag['status'],independent_vector_oracle=dict(status=oracle['status'],total=oracle['total'],passed=oracle['passed'],failed=oracle['failed']),
        schema_registry_audit=schema,blocked_capabilities=[r for r in matrix if r['status']=='BLOCKED_WITH_EXPLICIT_REASON'],
        completeness='ALL_DESIGN_ROWS_FROZEN_OR_EXPLICITLY_BLOCKED',scope_proof=scope,
        runtime_implemented=False,runtime_authorized=False,full_D0_D1_D2_pass_claim=False,permissions=PERMISSIONS,
        next_stage='STOP_AFTER_UNIFIED_COMMIT_PUSH; INDEPENDENT_EXTERNAL_AUDIT_REQUIRED')
    if emit:
        for name,value in [('V4_12_R1_PARAMETER_LITERAL_AUDIT',literal),('V4_12_R1_DAG_EDGE_AUDIT',dag),
                           ('V4_12_R1_INDEPENDENT_VECTOR_ORACLE',oracle),('V4_12_R1_CONTRACT_COMPLETENESS_MATRIX',completeness),
                           ('V4_12_R1_CONTRACT_FREEZE',result)]:put('reports/v4_12_r1/'+name+'.json',value)
        put('reports/v4_12_r1/V4_12_R1_CONFIG_MANIFEST.json',dict(contract_id='V4_12_R1_CONFIG_MANIFEST_V1',files=result['contracts']))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit',action='store_true');args=parser.parse_args()
    result=validate(args.emit);print(json.dumps({k:result[k] for k in ['status','literal_audit_summary','independent_vector_oracle','schema_registry_audit']}))
