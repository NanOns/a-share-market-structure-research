"""Independent R31 tests: scoped blocking, exact authority and no gate promotion."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from reports.r31.audit_oracle import closure_allowed, digest, final_verdict, governance, read_binding, referential_integrity, validate_contract

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'config/v4_22_independent_audit_contract_v1.json').read_bytes())


def ledger():
    owner=C['shadow_session_owner']
    common=dict(capability='STOCK_CORE',evidence_lane='SHADOW_REAL',model_contract_id='SIM_MODEL',parameter_digest='SIM_PARAMETERS',state_lineage_id='SIM_LINEAGE')
    schema=read_binding(ROOT,C['ledger_schema_binding'])
    rows={name:{k:'SIM_'+k for k in schema[key]['required']} for name,key in [('sessions','session_ledger'),('events','event_cohort_ledger'),('outcomes','due_outcome_ledger')]}
    for row in rows.values(): row.update(common,observation_namespace='SIM_NS',source_publication='SIM_PUB',source_digest='SIM_DIGEST',evidence_origin='PIT_OBSERVED',execution_mode='SHADOW')
    rows['sessions'].update(native_session_authority_id=owner['contract_id'],native_session_authority_sha256=owner['sha256'],native_session_status='ACCEPTED_ON_TIME',projection_evaluable=True,projection_evaluable_reason=None,accepted_real_publication=True,trade_date='2026-10-05',calendar_identity='SIM_CAL',publication_id='SIM_PUB',publication_revision=1)
    rows['events'].update(T0='2026-10-05',calendar_identity='SIM_CAL')
    return dict(kind='CONTRACT_DESIGN_SIMULATION',**{k:[v] for k,v in rows.items()})


def evaluate(value):
    return referential_integrity(value,C['shadow_session_owner'])


@pytest.mark.parametrize('name,vector',[('events','A22-V421-REFINT-01'),('outcomes','A22-V421-REFINT-02')])
def test_orphan_real_row_blocked_affected_scope(name,vector):
    value=ledger(); value['sessions']=[]; value['outcomes' if name=='events' else 'events']=[]
    result=evaluate(value)
    assert result['status']=='BLOCKED_AFFECTED_SCOPE'
    assert result['findings'][0]['vector']==vector
    assert result['findings'][0]['partition']['capability']=='STOCK_CORE'
    assert result['actual_real_rows_written']==0 and result['production_grant'] is False


@pytest.mark.parametrize('field,value',[('capability','ROTATION'),('evidence_lane','PRODUCTION_REAL'),('model_contract_id','OTHER'),('parameter_digest','OTHER'),('state_lineage_id','OTHER')])
@pytest.mark.parametrize('name',['events','outcomes'])
def test_cross_partition_parent_cannot_cover_orphan(field,value,name):
    rows=ledger(); rows[name][0][field]=value
    assert evaluate(rows)['status']=='BLOCKED_AFFECTED_SCOPE'


@pytest.mark.parametrize('field,value',[('native_session_status','ACCEPTED'),('native_session_status','MISSED_OBSERVATION_SLOT'),('native_session_authority_id','WRONG'),('native_session_authority_sha256','WRONG'),('evidence_origin','HISTORICAL_REPLAY'),('accepted_real_publication',False),('execution_mode','REPLAY')])
def test_unaccepted_session_cannot_cover_real_rows(field,value):
    rows=ledger(); rows['sessions'][0][field]=value
    assert evaluate(rows)['status']=='BLOCKED_AFFECTED_SCOPE'


def test_valid_parent_and_non_evaluable_native_parent_distinguished():
    value=ledger(); assert evaluate(value)['status']=='PASS_DESIGN_ONLY'
    value['sessions'][0]['projection_evaluable']=False
    assert evaluate(value)['status']=='PASS_DESIGN_ONLY'
    # This is referential acceptance only, never a real session/streak counter.
    assert 'real_accepted_sessions' not in evaluate(value)


def test_production_real_missing_native_authority_is_blocked():
    rows=ledger()
    for name in rows:
        if isinstance(rows[name],list):
            for row in rows[name]: row['evidence_lane']='PRODUCTION_REAL'
    assert evaluate(rows)['status']=='BLOCKED_AFFECTED_SCOPE'


def test_non_real_lanes_do_not_inflate_or_block_real_partition():
    value=ledger(); value['sessions']=[]
    for name in ('events','outcomes'): value[name][0]['evidence_lane']='HISTORICAL_REPLAY'
    assert evaluate(value)['status']=='PASS_DESIGN_ONLY'


def test_missing_partition_fails_closed_without_keyerror():
    value=ledger(); del value['events'][0]['parameter_digest']
    assert evaluate(value)['status']=='BLOCKED_AFFECTED_SCOPE'


def test_registry_authority_and_all_open_items():
    assert validate_contract(C,ROOT)==[]
    assert len(C['audit_domains'])==11 and len(C['open_items'])==10
    assert C['current_state']['REAL_SHADOW_OBSERVATIONS']==0
    assert all(v is False for v in C['current_state']['production_permission'].values())
    assert C['runtime_receipt_bindings']=={} and C['production_session_owner'] is None
    assert C['final_pass']=='NOT_GRANTED' and C['V4_22_ACCEPTED_HEAD']=='NOT_CREATED'
    assert set(['BLOCKED','NOT_VERIFIABLE','OPEN_NONBLOCKING_DEBT']) <= set(C['status_vocabulary'])


@pytest.mark.parametrize('index',range(10))
def test_open_item_cannot_disappear(index):
    c=deepcopy(C); del c['open_items'][index]
    assert 'OPEN_ITEM_DISAPPEARED' in validate_contract(c,ROOT)


@pytest.mark.parametrize('field',['explicit_disposition','exact_evidence','authority','date_source','independent_recheck'])
def test_closure_needs_all_independent_evidence_fields(field):
    item=C['open_items'][-1]
    receipt=dict(item_id=item['item_id'],capability_scope=item['capability_scope'],explicit_disposition='SIM',exact_evidence='SIM',authority='SIM',date_source='SIM',independent_recheck=True)
    assert closure_allowed(item,receipt)
    del receipt[field]; assert not closure_allowed(item,receipt)


def test_exact_binding_no_digest_or_path_fallback(tmp_path):
    path=tmp_path/'authority.json'; path.write_text('{"contract_id":"SIM"}')
    b=dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),contract_id='SIM')
    assert read_binding(tmp_path,b)['contract_id']=='SIM'
    for change in ({'sha256':'WRONG'},{'contract_id':'WRONG'},{'path':'../authority.json'}):
        with pytest.raises(ValueError): read_binding(tmp_path,dict(b,**change))


@pytest.mark.parametrize('delta,expected',[([], 'PASS'),(['reports/r31/result.json'],'PASS'),(['config/changed.json'],'BLOCKED'),(['reports/r31/audit_oracle.py'],'BLOCKED'),(['tests/test_changed.py'],'BLOCKED')])
def test_tested_source_evidence_only_delta(delta,expected):
    assert governance('codex/v4-system-reform','codex/v4-system-reform','SIM_SHA','SIM_SHA',True,True,delta)['status']==expected


@pytest.mark.parametrize('field',['branch','source','annotated','clean'])
def test_governance_wrong_binding_blocks(field):
    args=['codex/v4-system-reform','codex/v4-system-reform','SIM_SHA','SIM_SHA',True,True,[]]
    args[{'branch':0,'source':3,'annotated':4,'clean':5}[field]]='WRONG' if field in ('branch','source') else False
    assert governance(*args)['status']=='BLOCKED'


def test_current_real_gates_not_ready_even_if_design_items_pass():
    items=[dict(i,current_status='PASS',independent_recheck=True) for i in C['audit_items'] if i['blocking_scope']]
    result=final_verdict(C,items,{},dict(status='PASS'))
    assert result['formula_result']=='FINAL_AUDIT_NOT_READY' and result['acceptance_granted'] is False
    assert len(result['missing'])==len(items)+len(C['capabilities'])*len(C['required_real_gates'])+9


def future_simulation():
    c=deepcopy(C)
    items=[dict(i,current_status='PASS',independent_recheck=True) for i in c['audit_items'] if i['blocking_scope']]
    c['audit_receipt_bindings']={i['item_id']:dict(canonical_sha256=digest(i),authority=i['authority']) for i in items}
    receipts={}
    for capability in c['capabilities']:
        for gate in c['required_real_gates']:
            key=capability+':'+gate
            receipt=dict(capability=capability,gate=gate,authority_id='SIM_ACCEPTED_OWNER',externally_accepted=True,status='PASS',permission=True)
            receipts[key]=receipt; c['runtime_receipt_bindings'][key]=dict(canonical_sha256=digest(receipt),authority_id=receipt['authority_id'])
    return c,items,receipts


def test_formula_future_simulation_is_never_an_acceptance_grant():
    c,items,receipts=future_simulation()
    result=final_verdict(c,items,receipts,dict(status='PASS'))
    assert result['formula_result']=='FINAL_AUDIT_NOT_READY'
    assert result['acceptance_granted'] is False and result['production_grant'] is False
    assert result['evaluation_scope'].startswith('CONTRACT_DESIGN_ONLY')


@pytest.mark.parametrize('defect',['scope','duplicate','missing','status','recheck','receipt','blocker','audit_receipt'])
def test_formula_rejects_partial_or_forged_acceptance(defect):
    c,items,receipts=future_simulation(); blockers=[]
    if defect=='scope': items[0]['capability_scope']=['STOCK_CORE']
    if defect=='duplicate': items.append(items[0])
    if defect=='missing': items.pop()
    if defect=='status': items[0]['current_status']='OPEN_NONBLOCKING_DEBT'
    if defect=='recheck': items[0]['independent_recheck']=False
    if defect=='receipt': next(iter(receipts.values()))['capability']='WRONG'
    if defect=='blocker': blockers=['P0_SIM']
    if defect=='audit_receipt': c['audit_receipt_bindings'].clear()
    assert final_verdict(c,items,receipts,dict(status='PASS'),blockers)['formula_result']!='V4_22_FINAL_PASS'


def test_oracle_imports_only_standard_library_no_writers():
    tree=ast.parse((ROOT/'reports/r31/audit_oracle.py').read_text())
    modules=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): modules.extend(x.name for x in node.names)
        if isinstance(node,ast.ImportFrom): modules.append(node.module)
    assert set(modules) <= {'hashlib','json','pathlib'}
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('write_text','write_bytes','mkdir','unlink') for n in ast.walk(tree))
