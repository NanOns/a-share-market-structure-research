"""Engineering replay orchestration of unchanged accepted owner implementations.

All synthetic facts remain explicitly synthetic. State is obtained exclusively
from the exact previous immutable publication supplied to this invocation.
"""
import json
from copy import deepcopy
from .v4_14_replay_io import digest,ref
from .v4_14_owner_adapters import state_book,rotation_acceptance,structure_trace,synthetic_confirmation

def calendar(authority):
    dates=[s['trade_date'] if isinstance(s,dict) else s for s in authority.calendar['session_dates']]
    return dict(lineage_id='SYNTHETIC_MARKET_CALENDAR_V1',manifest_kind='MARKET_CALENDAR',mode='SYNTHETIC_CONTRACT_VECTOR',producer_contract_id='MARKET_CALENDAR_V1',sessions=[dict(session_index=i,trade_date=d) for i,d in enumerate(dates)])

def state_input(authority,envelope,prior,values,source_outputs):
    from src.v4.state_identity import digest as owner_digest
    x=deepcopy(state_book(str(authority.root))['STOCK_PREWATCH']['input'])
    cal=calendar(authority);dates=[s['trade_date'] for s in cal['sessions']];date=envelope['target_trade_date'];index=dates.index(date)
    x.update(trade_date=date,session_index=index,cutoff=envelope['cutoff'],synthetic_calendar_manifest=cal,calendar_publication_id='SYNTHETIC_CALENDAR:'+owner_digest(cal),prior_state=prior,prior_state_binding=None)
    x['calendar_binding']=dict(publication_id=x['calendar_publication_id'],manifest_digest=owner_digest(cal),lineage_id=cal['lineage_id'])
    if prior:x['prior_state_binding']=dict(publication_id=prior['publication_id'],payload_digest=owner_digest(prior),ledger_id='SYNTHETIC_ENGINEERING_LEDGER')
    pid='SYNTHETIC_FACTS:'+owner_digest(source_outputs);x['input_publication_ids']=[pid]
    for field,f in x['input_provenance'].items():
        if f['status']=='NOT_APPLICABLE':continue
        value=values.get(field,f['value']);f.update(value=value,quality='UNKNOWN' if value=='UNKNOWN' else 'KNOWN',publication_id=pid,system_available_at=date+'T01:00:00+00:00')
        j=index if f['time_role']=='T' else index-1
        payload=dict(field=field,value=value,session_index=j,trade_date=dates[j],owner_output_digest=owner_digest(source_outputs.get(field,source_outputs)))
        if field=='frozen_invalidation':payload.update(episode_id=prior['episode_id'] if prior else None,invalidation_contract_id=prior['invalidation_contract_id'] if prior else None)
        if field=='episode_invalidation_contract_id' and prior:
            payload['value']=prior['invalidation_contract_id'] or 'FIXTURE_EPISODE_INVALIDATION_V1';f['value']=payload['value']
        f['source_field_payload']=payload;f['source_output_digest']=owner_digest(payload)
    x['input_publication_manifest_digest']=owner_digest(dict(input_publication_ids=x['input_publication_ids'],fields=x['input_provenance']))
    return x

def replay(authority,envelope,previous,_edge_prepared=None):
    if envelope['owner_inputs'].get('preexec_edge_binding'):
        from .v4_14_precall_runtime import replay as precall_replay
        return precall_replay(authority,envelope,previous)
    if envelope['owner_inputs'].get('owner_edge_complete') and _edge_prepared is None:
        from .v4_14_owner_edge_runtime import replay as edge_replay
        return edge_replay(authority,envelope,previous)
    from src.v4.base_seed import evaluate_facts
    from src.v4.stock_prewatch import evaluate,load_package
    from src.v4.confirmation import detect_confirmation
    from scripts.v4_11_candidate_inputs_r2 import projection,positive_values,seal
    from src.v4.confirmation_d2_bridge import engineering_d2_publication
    from src.v4.confirmation_events import freeze_prior_session,state_events
    from .v4_13_accepted_contract_package import AcceptedContracts
    from .v4_13_profile_runtime import sector_snapshot,copy_structure,dual_enrichment,envelope as field
    root=authority.root;choice=envelope['owner_inputs'];target=envelope['target_trade_date'];prior=previous['output']['d2']['rows'][0] if previous else None
    book=json.loads((root/'config/v4_07_machine_vectors_v1.json').read_bytes());facts={k:dict(value=True if v=='TRUE' else False if v=='FALSE' else v,reason=None) for k,v in book['base_input'].items()}
    facts['severe_extension']['value']=choice.get('severe_extension',False)
    seed=evaluate_facts(facts,json.loads((root/'config/v4_07_parameter_set_v1.json').read_bytes()))
    rotation=rotation_acceptance(root)
    prewatch=evaluate(dict(base_seed_state=seed['base_seed_state'],mandatory_core_quality_ready='TRUE',delta3=3,compression_state='COMPRESSING',ma_structure_state='BEAR_ALIGNED',core_extension_risk='LOW'),load_package(root))
    cp=projection(positive_values(),cutoff=envelope['cutoff']);cp['trade_date']=target
    for row in cp['rows']:
        row['trade_date']=target
        for f in row['facts'].values():
            f['trade_date']=envelope['previous_market_session'] if f['time_role']=='PRIOR_SESSION_WINDOW' else target
            if 'producer_lineage' in f:f['producer_lineage'].update(numerator_trade_date=target,prior_window_end=envelope['previous_market_session'])
        # Negative/unknown facts are frozen scenario inputs, not new thresholds.
        if not choice.get('confirmation',False):row['facts']['actual_bar'].update(value=False)
        if choice.get('unknown',False):row['facts']['normal_universe'].update(value=None,quality='UNKNOWN',reason='EXPLICIT_SYNTHETIC_VECTOR')
    if _edge_prepared is not None:
        facts=_edge_prepared['F0']['output']['seed_facts'];seed=_edge_prepared['A']['output'];prewatch=_edge_prepared['C']['output'];cp=_edge_prepared['D0']['input']['projection'];rotation=_edge_prepared['B1']['output']
    confirmation=synthetic_confirmation(seal(cp));cr=confirmation['rows'][0]
    from .v4_12_structure_io import FrozenContracts
    from .v4_12_structure_engine import SessionLedger
    from .v4_12_anchor_runtime import create_anchor,create_event
    c12=FrozenContracts(root);sb=c12.config['machine_vectors'];sv=next(v for v in sb['vectors'] if v['vector_id']==choice.get('structure_vector','S01'))
    anchor=previous['output']['anchor'] if previous else create_anchor(c12,'BULLISH_IMPULSE_LOW','SYNTHETIC',target,envelope['cutoff'],dict(price_basis='SYNTHETIC_QFQ',adjustment_source_revision='r1'),'SYNTHETIC_SUPPORT_EVENT',digest(dict(source='FROZEN_OWNER_STRUCTURE_BOOK')), (10,10),dict(scope='ENGINEERING_SYNTHETIC',source=ref(root,'config/v4_12_machine_vectors_v1.json')),dict(mul='1',add='0',scope='ENGINEERING_SYNTHETIC'))
    history_d1=previous['output']['structure_history'] if previous else {}
    ledger=SessionLedger(c12,anchor['available_date'],[s['trade_date'] for s in calendar(authority)['sessions']],anchor['anchor_id'],history_d1)
    structural_inputs={**sb['defaults'],**sv['inputs']}
    structural_inputs['prior_separated_sessions']=previous['output']['structure_ledger']['separated_sessions'] if previous else 0
    observation=ledger.observe(target,envelope['target_revision'],not choice.get('unknown',False),structural_inputs)
    observation=json.loads(json.dumps(observation,default=str));ledger.history=json.loads(json.dumps(ledger.history,default=str))
    structure=observation['support']
    sources=dict(SEED=seed,PREWATCH=prewatch,CONFIRMED=confirmation,structure=structure,rotation=rotation)
    vals=dict(SEED=seed['base_seed_state'],PREWATCH=prewatch['raw_qualification'],CONFIRMED=cr['confirmation_status'],scenario=cr['primary_scenario'] or 'UNKNOWN')
    if choice.get('unknown'):vals.update(SEED='UNKNOWN',PREWATCH='UNKNOWN',CONFIRMED='UNKNOWN')
    vals.update(core_price_damage='TRUE' if choice.get('damage') else 'FALSE',delta3=choice.get('delta3',0),dq5=0)
    x=state_input(authority,envelope,prior,vals,sources);d2=engineering_d2_publication([x]);history=previous['output']['episode_history']+[previous['output']['d2']] if previous else []
    events=[]
    if previous:
        frozen=freeze_prior_session(target_date=target,prior_date=envelope['previous_market_session'],calendar_publication_id=x['calendar_publication_id'],rows=previous['output']['d2']['rows'],source_binding=previous['output']['d2'],scope='SYNTHETIC_ENGINEERING_ONLY',calendar_manifest=x['synthetic_calendar_manifest'],episode_history=history)
        events=state_events(d2,frozen)
    contracts=AcceptedContracts(root);selection=dict(quality='UNKNOWN',membership_basis='UNKNOWN')
    context=sector_snapshot(selection,None,contracts,[authority.owners['v4_08']]);copied=copy_structure(None,contracts,authority.owners['v4_12'])
    if _edge_prepared is not None:context=_edge_prepared['D3_CONTEXT']['output']
    enrichment=dual_enrichment(field(rotation, 'KNOWN',None),field(copied,'UNKNOWN',None),contracts)
    if _edge_prepared is not None:enrichment=dual_enrichment(field(None,'UNKNOWN',rotation.get('reason_codes')),field(copied,'UNKNOWN',None),contracts)
    trace=[dict(node='Accepted Source Binding',owner_ref=authority.data_ref,input_digest=digest(envelope['source_refs']),output_digest=digest(dict(classification='ENGINEERING_SYNTHETIC',calendar=authority.calendar_ref)),output=dict(classification='ENGINEERING_SYNTHETIC',calendar=authority.calendar_ref))]
    for node,owner,inputs,out in [('Seed','v4_07',facts,seed),('Sector/Rotation','v4_08',dict(fixture='R1B'),rotation),('PREWATCH','v4_09',seed,prewatch),('Confirmation','v4_11',seal(cp),confirmation),('Structure','v4_12',dict(frozen_vector=choice.get('structure_vector','S01')),structure),('State Reducer','v4_10',x,d2),('Event Diff','v4_11',dict(prior=envelope['previous_state_publication'],current=d2['publication_id']),events),('Profile/Context','v4_13',dict(structure=copied,rotation=rotation),dict(context=context,enrichment=enrichment))]:
        trace.append(dict(node=node,owner_ref=authority.owners[owner],input_digest=digest(inputs),output_digest=digest(out),output=out))
    trace.append(dict(node='Gate-B Observation',owner_ref=authority.refs[0],input_digest=digest(trace),output_digest=digest(dict(state=d2['rows'][0],events=events))))
    logical=[]
    for event in events:
        for event_type in event['event_types']:
            r=d2['rows'][0];logical.append(dict(model_namespace='ENGINEERING_SYNTHETIC',model_contract_id=r['model_contract_id'],parameter_set_id=r['parameter_set_id'],entity_type=r['entity_type'],entity_id=r['entity_id'],episode_id=r['episode_id'],event_type=event_type,signal_market_date=target))
    return dict(quality='DEGRADED',scope='ENGINEERING_SYNTHETIC',trace=trace,d2=d2,events=events,logical_events=logical,episode_history=history,structure_observation=structure,structure_ledger=observation,structure_history=ledger.history,anchor=anchor,anchor_event=create_event(c12,anchor,envelope['target_revision']),previous_D1_publication=envelope['previous_state_publication'],context=context,enrichment=enrichment,dimension_results=[],raw_provider_fallback=False)
