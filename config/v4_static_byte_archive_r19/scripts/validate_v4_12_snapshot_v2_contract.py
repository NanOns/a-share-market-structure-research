"""Independent R12A contract gate and cardinality/ownership negative vectors."""
import copy,hashlib,json
from scripts.v4_11_promotion_contract_r1 import ROOT
PATH='config/v4_12_frozen_snapshot_contract_v2.json'
SORT=['not invalidated','distance_to_C / ATR ascending','anchor_date descending','anchor_id ascending']
def validate_contract(c):
    assert c['contract_id']=='V4_12_FROZEN_D1_CANDIDATE_SNAPSHOT_V2' and c['version']=='2.0.0'
    assert c['selector']['active_anchor_sort']==SORT and c['selector']['first_item_fallback'] is False
    assert c['common_F0_bind_count']==1 and c['source_reconstruction'] is False
    assert c['transition_identity']==['security_id','anchor_id','machine','trade_date']
    assert c['retention_is_transition'] is False and c['terminal_lifecycle']=='NO_HISTORICAL_CLOSURE_AUTHORIZED_ALL_STATES_PERSIST'
    assert set(['pullback','recovery','support','acceptance','retention'])==set(c['per_anchor_machines'])
    assert c['new_anchor']['all_counters']==0 and c['new_anchor']['state_observations']['support']=='IDLE'
    assert all(v is False for v in c['permissions'].values())
    frozen=json.loads((ROOT/'config/v4_12_output_schema_v1.json').read_bytes());assert frozen['active_anchor_sort']==SORT
    v1=json.loads((ROOT/'config/v4_12_frozen_snapshot_contract_v1.json').read_bytes());assert c['fact_projections']==v1['fact_projections']
    return True
def validate_shape(c,row,transitions=()):
    assert all(k in row for k in c['required_fields']) and 'anchor' not in row and 'event' not in row
    states=row['anchor_states'];assert isinstance(states,list)
    assert len({s['anchor_id'] for s in states})==len(states)
    for s in states:
        assert all(k in s for k in c['anchor_state_required'])
        assert s['anchor_id']==s['anchor']['anchor_id']==s['event']['anchor_id']==s['owning_anchor_id']
        assert s['event']['event_id']==s['anchor']['source_event_id']==s['owning_episode_id']
        if s['created_this_session']:
            assert all(s['counter_state'][n]==0 for n in c['counter_fields'])
            assert s['state_observations']['support']['state']=='IDLE'
    if row['active_anchor_id'] is not None:assert row['active_anchor_id'] in {s['anchor_id'] for s in states}
    for t in transitions:assert all(k in t for k in c['transition_required']) and (t['anchor_id'] in {s['anchor_id'] for s in states} or t['machine']=='breakout' and t['anchor_id'] is None)
    return True
def gate():
    c=json.loads((ROOT/PATH).read_bytes());validate_contract(c)
    state={k:None for k in c['anchor_state_required']};state.update(anchor_id='A',anchor=dict(anchor_id='A',source_event_id='EA'),event=dict(anchor_id='A',event_id='EA'),owning_anchor_id='A',owning_episode_id='EA',created_this_session=True,counter_state={n:0 for n in c['counter_fields']},state_observations={'support':{'state':'IDLE'}})
    row={k:None for k in c['required_fields']};row.update(anchor_states=[state],active_anchor_id='A');validate_shape(c,row)
    bad=[]
    for name in ['scalar_only','duplicate','anchor_event','owning_mutation','new_nonzero','transition_missing_anchor']:
        r=copy.deepcopy(row);ts=[]
        if name=='scalar_only':r.pop('anchor_states');r['anchor']=state['anchor']
        elif name=='duplicate':r['anchor_states'].append(copy.deepcopy(state))
        elif name=='anchor_event':r['anchor_states'][0]['event']['anchor_id']='B'
        elif name=='owning_mutation':r['anchor_states'][0]['owning_anchor_id']='B'
        elif name=='new_nonzero':r['anchor_states'][0]['counter_state']['held_count']=1
        else:ts=[dict(security_id='X',machine='support')]
        try:validate_shape(c,r,ts)
        except (AssertionError,KeyError):bad.append(dict(case=name,status='PASS'))
        else:raise AssertionError('NEGATIVE_ACCEPTED:'+name)
    for name in ['selector_order','first_item_fallback']:
        d=copy.deepcopy(c)
        if name=='selector_order':d['selector']['active_anchor_sort'].reverse()
        else:d['selector']['first_item_fallback']=True
        try:validate_contract(d)
        except AssertionError:bad.append(dict(case=name,status='PASS'))
        else:raise AssertionError('NEGATIVE_ACCEPTED:'+name)
    before=json.loads((ROOT/'reports/v4_12_runtime_r12/R12_STAGE_CONTRACT.json').read_bytes())['protected']
    for p,h in before.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    return dict(status='PASS',candidate_status='V4_12_R12A_MULTI_ANCHOR_STATE_CONTRACT_V2_READY',contract=dict(path=PATH,sha256=hashlib.sha256((ROOT/PATH).read_bytes()).hexdigest()),negative_vectors=bad,protected_exact=True)
if __name__=='__main__':
    r=gate();(ROOT/'reports/v4_12_runtime_r12/R12A_CONTRACT_LOCAL_GATE.json').write_bytes((json.dumps(r,sort_keys=True)+'\n').encode());print(json.dumps(r))
