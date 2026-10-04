"""Pure synthetic CUTOVER_V2 design oracle. No storage, grants or routing writes."""
from copy import deepcopy

CAPS = ('STOCK_CORE','STOCK_SECTOR_DEPENDENT','SECTOR_STAGE','ROTATION','SECTOR_RISK_CHANGE')
DEPS = {'STOCK_CORE': [], 'SECTOR_STAGE': [], 'STOCK_SECTOR_DEPENDENT': ['STOCK_CORE','SECTOR_STAGE'], 'ROTATION': ['SECTOR_STAGE'], 'SECTOR_RISK_CHANGE': ['SECTOR_STAGE']}
IDENTITY = ('model_contract_id','parameter_digest','state_lineage_id')
FIELDS = ('capability','status','shadow_sessions','unique_signal_dates','matured_events','forward_quality','migration_gate','production_permission','dependency_scope','parameter_digest','model_contract_id','state_lineage_id','source_publication','cutover_authority_id','previous_route','new_route','expected_route_head','receipt_digest')
ADDITIONAL_FIELDS = ('receipt_id','request_id','contract_digest','gate_receipt_digests','dependency_receipt_digests','previous_receipt_digest','accepted_at','external_authority_receipt','evidence_class')


def permissions(scenario):
    """Returns hypothetical design decisions only, never a production permission receipt."""
    if scenario.get('global_pass'):
        return {cap:False for cap in CAPS}
    output = {}
    for cap in ('STOCK_CORE','SECTOR_STAGE','STOCK_SECTOR_DEPENDENT','ROTATION','SECTOR_RISK_CHANGE'):
        item = scenario['capabilities'][cap]
        gates = [item.get(name) for name in ('shadow','forward','migration')]
        valid = all(g and g.get('accepted') is True and g.get('capability')==cap and g.get('active') is True and all(g.get(k)==item[k] for k in IDENTITY) for g in gates)
        shadow = item.get('shadow') or {}
        forward = item.get('forward') or {}
        migration = item.get('migration') or {}
        valid = valid and shadow.get('origin')=='PIT_OBSERVED' and shadow.get('mode')=='SHADOW' and shadow.get('consecutive_sessions',0)>=20 and shadow.get('missed_sessions',0)==0 and shadow.get('non_evaluable_sessions',0)==0 and shadow.get('p0',1)==0 and shadow.get('temporal_leakage',1)==0 and shadow.get('duplicate_episode_corruption',1)==0 and shadow.get('core_identity_violations',1)==0 and shadow.get('rollback_drill') is True
        valid = valid and forward.get('origin')=='PIT_OBSERVED' and forward.get('settlement_p0',1)==0 and forward.get('controls_quality_receipt') is True and forward.get('benchmark_quality_receipt') is True
        if cap in ('STOCK_CORE','STOCK_SECTOR_DEPENDENT'):
            events = {row['logical_event_id']:row for row in forward.get('events',[]) if row.get('status')=='OBSERVED' and row.get('horizon')==5 and row.get('event_type') in ('FIRST_PREWATCH','REENTRY_PREWATCH','NEW_CONFIRMED')}
            valid = valid and len({row['stock_id'] for row in events.values()})>=30 and len({row['signal_date'] for row in events.values()})>=5
        else:
            valid = valid and forward.get('separately_frozen_policy_receipt') is True and forward.get('per_type_quality_coverage_pass') is True
        valid = valid and migration.get('runtime_external_acceptance') is True and migration.get('scope')=='V4_18_RUNTIME_REPLAY'
        valid = valid and all(output.get(dep) is True for dep in DEPS[cap])
        output[cap] = bool(valid)
    return output


def proposal(scenario):
    permission = permissions(scenario)
    cap = scenario.get('requested_capability','STOCK_CORE')
    item = scenario['capabilities'][cap]
    receipt = scenario.get('proposed_receipt',{})
    pub = scenario.get('source_publication',{})
    reason = None
    if scenario.get('global_pass'): reason='GLOBAL_PROMOTION_FORBIDDEN'
    elif not permission[cap]: reason='CAPABILITY_PERMISSION_FALSE'
    elif any(field not in receipt for field in FIELDS+ADDITIONAL_FIELDS): reason='RECEIPT_SCHEMA_INCOMPLETE'
    elif receipt['capability']!=cap or not isinstance(receipt['dependency_scope'],dict) or sorted(receipt['dependency_scope'])!=sorted(DEPS[cap]): reason='DEPENDENCY_SCOPE_MISMATCH'
    elif receipt['production_permission'] is not True or receipt['new_route']!='V4_PRODUCTION['+cap+']' or any(receipt.get(k)!=item[k] for k in IDENTITY): reason='RECEIPT_IDENTITY_OR_ROUTE_MISMATCH'
    elif pub.get('capability')!=cap or not pub.get('accepted') or any(pub.get(k)!=item[k] for k in IDENTITY): reason='SOURCE_PUBLICATION_IDENTITY_MISMATCH'
    elif scenario.get('actual_route_head')!=receipt['expected_route_head']: reason='ROUTE_CAS_CONFLICT'
    return dict(hypothetical_permissions=permission, design_action='NO_CUTOVER' if reason else 'ELIGIBLE_DESIGN_PROPOSAL', reason=reason, route_changes=[], production_grant=False)


def rollback_scope(cap):
    affected = {cap}
    while True:
        expanded = affected | {c for c,deps in DEPS.items() if affected.intersection(deps)}
        if expanded==affected: return sorted(affected)
        affected = expanded


def fixture():
    identity = dict(model_contract_id='SIMULATED_MODEL',parameter_digest='SIMULATED_PARAMETERS',state_lineage_id='SIMULATED_LINEAGE')
    items = {}
    for cap in CAPS:
        common = dict(identity,accepted=True,active=True,capability=cap)
        events = [dict(logical_event_id=f'e{i}',stock_id=f's{i}',signal_date=f'd{i%5}',event_type=('FIRST_PREWATCH','REENTRY_PREWATCH','NEW_CONFIRMED')[i%3],horizon=5,status='OBSERVED',revision=1) for i in range(30)]
        items[cap] = dict(identity,shadow=dict(common,origin='PIT_OBSERVED',mode='SHADOW',consecutive_sessions=20,missed_sessions=0,non_evaluable_sessions=0,p0=0,temporal_leakage=0,duplicate_episode_corruption=0,core_identity_violations=0,rollback_drill=True),forward=dict(common,origin='PIT_OBSERVED',settlement_p0=0,controls_quality_receipt=True,benchmark_quality_receipt=True,events=events,separately_frozen_policy_receipt=True,per_type_quality_coverage_pass=True),migration=dict(common,runtime_external_acceptance=True,scope='V4_18_RUNTIME_REPLAY'))
    receipt = {field:'SIMULATION_ONLY' for field in FIELDS+ADDITIONAL_FIELDS}
    receipt.update(identity,capability='STOCK_CORE',dependency_scope={},dependency_receipt_digests={},gate_receipt_digests={'shadow':'SIMULATED','forward':'SIMULATED','migration':'SIMULATED'},shadow_sessions=20,unique_signal_dates=5,matured_events={'FIRST_PREWATCH':10,'REENTRY_PREWATCH':10,'NEW_CONFIRMED':10},forward_quality={'controls':'SIMULATED','benchmarks':'SIMULATED'},migration_gate={'runtime_receipt':'SIMULATED'},source_publication={'id':'SIMULATED_PUBLICATION'},expected_route_head='SIMULATED_HEAD',production_permission=True,new_route='V4_PRODUCTION[STOCK_CORE]',previous_route='LEGACY_PRODUCTION',evidence_class='CONTRACT_DESIGN_SIMULATION')
    return dict(evidence_origin='CONTRACT_DESIGN_SIMULATION',capabilities=items,actual_route_head='SIMULATED_HEAD',proposed_receipt=receipt,source_publication=dict(identity,capability='STOCK_CORE',accepted=True))


def scenario(vector):
    value = deepcopy(fixture())
    cap = value['capabilities']
    if vector in ('C02','C04','C11'): cap['SECTOR_STAGE']['forward']['accepted']=False
    if vector=='C03': cap['STOCK_CORE']['forward']['accepted']=False
    if vector=='C05': cap['STOCK_CORE']['migration']=None
    if vector=='C06': cap['STOCK_CORE']['shadow']=None
    if vector=='C07': cap['STOCK_CORE']['forward']=None
    if vector=='C08': cap['STOCK_CORE']['shadow']['parameter_digest']='WRONG'
    if vector=='C09': value['source_publication']['capability']='SECTOR_STAGE'
    if vector=='C10': value['actual_route_head']='OTHER_HEAD'
    if vector=='C12':
        value['user_pin']=True
        cap['STOCK_CORE']['forward']=None
    if vector=='C13': cap['STOCK_CORE']['shadow']['mode']='REPLAY'
    if vector=='C14': cap['STOCK_CORE']['forward']['origin']='RECONSTRUCTED_ASOF'
    if vector=='C16': value['global_pass']=True
    if vector=='C17': del value['proposed_receipt']['dependency_scope']
    if vector=='C18': cap['STOCK_CORE']['forward']['active']=False
    if vector=='C19':
        cap['STOCK_CORE']['forward']['events']=cap['STOCK_CORE']['forward']['events'][:29]
        correction=dict(cap['STOCK_CORE']['forward']['events'][0],revision=2)
        cap['STOCK_CORE']['forward']['events'].append(correction)
    if vector=='C20':
        value['shared_raw_source']=True
        cap['SECTOR_STAGE']['forward']=None
    return value


def vector_result(vector):
    value=scenario(vector)
    result=proposal(value)
    if vector=='C11': result['module_labels']={c:'PRODUCTION' if p else 'SHADOW' for c,p in result['hypothetical_permissions'].items()}
    if vector=='C15': result['rollback_affected']=rollback_scope('ROTATION'); result['rollback_preserves']=['accepted V4 facts','user pins/manual work','pending settlement ownership']
    return result
