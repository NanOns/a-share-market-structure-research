"""Field-precise, persisted pre-call envelopes around unchanged owner logic."""
import json
from copy import deepcopy
from pathlib import Path
from .v4_14_replay_io import exact,publish,digest,ref

def pointer(value,path):
    for part in path.split('/')[1:]:value=value[int(part)] if isinstance(value,list) else value[part]
    return value

class Invocations:
    def __init__(self,a,e,previous):
        self.a=a;self.e=e;self.previous=previous;self.nodes={};self.receipts=[];self.sequence=0
        self.mapping_ref=e['owner_inputs']['consumption_mapping_ref'];self.mapping=json.loads(exact(a.root,self.mapping_ref));self.edges=self.mapping['mappings']
        if self.mapping['frozen_dag']!=a.refs[2]:raise ValueError('PRECALL_FROZEN_DAG_MISMATCH')
        for r in self.mapping['owner_interfaces']:exact(a.root,r)
        self.storage=Path(e['owner_inputs']['invocation_storage']['artifact_root']);self.namespace=e['owner_inputs']['invocation_storage']['namespace']
    def incoming(self,node):return [e for e in self.edges if e['consumer']==node]
    def source(self,edge):
        prior=edge['time_role']=='T_MINUS_1';p=edge['producer'];projection=edge['producer_projection']
        if prior and not self.previous:return None,dict(scope='CURRENT_OUTPUT',publication=None,pointer='/missing_sources/'+edge['edge_id'])
        value=(self.previous['output']['node_records'] if prior else self.nodes)[p]['output']
        return deepcopy(pointer(value,projection)),dict(scope='PREVIOUS_PUBLICATION' if prior else 'CURRENT_OUTPUT',publication=self.e['previous_state_publication'] if prior else None,pointer=('/output' if prior else '')+'/node_records/'+p+'/output'+projection)
    def call(self,node,args,fn,owner_ref):
        args=deepcopy(args);bindings=[]
        for edge in self.incoming(node):
            source,source_ref=self.source(edge);mode=edge['binding_mode'];prior_missing=edge['time_role']=='T_MINUS_1' and self.previous is None
            degraded=mode=='ACCEPTED_CAPABILITY_GATE' or prior_missing
            if degraded:
                reason='NO_EXACT_PREVIOUS_ENGINEERING_PUBLICATION' if prior_missing else 'ACCEPTED_OWNER_INTERFACE_OR_NATIVE_HISTORY_CAPABILITY_UNAVAILABLE'
                if edge['consumer']=='D2' and edge['producer']=='D1':reason=json.loads(exact(self.a.root,self.a.owners['v4_11']))['capabilities']['V4_12_STRUCTURE_SUPPORT']
                gate=dict(value=None,quality='UNKNOWN',reason=reason,owner_head_ref=edge['owner_head_ref'],upstream_ref=source_ref,upstream_digest=digest(source))
                args.setdefault('capabilities',{})[edge['edge_id']]=gate
                path='/capabilities/'+edge['edge_id'];status='DEGRADED_ACCEPTED_CAPABILITY'
            else:
                path=edge['consumer_argument_path'];status='EXECUTED';reason=None
                if pointer(args,path)!=source:raise ValueError('PRECALL_EXACT_FIELD_ARGUMENT_MISMATCH:'+edge['field'])
            bindings.append(dict(edge_id=edge['edge_id'],producer=edge['producer'],consumer=node,field=edge['field'],time_role=edge['time_role'],producer_payload_ref=source_ref,producer_payload_digest=digest(source),consumer_argument_path=path,consumer_argument_digest=digest(pointer(args,path)),binding_mode=mode,status=status,reason=reason))
        self.sequence+=1;prepared=self.sequence
        invocation=dict(node_id=node,owner_authority=owner_ref,mapping_ref=self.mapping_ref,execution_context=dict(target_trade_date=self.e['target_trade_date'],target_revision=self.e['target_revision'],previous_market_session=self.e['previous_market_session'],cutoff=self.e['cutoff'],calendar_binding=self.a.calendar_ref,contract_package_digest=self.a.package_digest),invocation_input=args,edge_bindings=bindings,invocation_input_digest=digest(args),prepared_sequence=prepared,phase='PRECALL_FROZEN')
        path=self.namespace+'/invocations/'+self.e['target_trade_date']+'/'+self.e['target_revision']+'/'+node+'.json'
        stored=publish(self.storage,path,invocation)
        # The callable receives a deserialized exact persisted envelope, not the
        # mutable builder or a receipt ledger. This write completes BEFORE fn.
        loaded=json.loads(exact(self.storage,stored));call_args=deepcopy(loaded['invocation_input'])
        for gate in call_args.get('capabilities',{}).values():
            if gate['value'] is not None or gate['quality']!='UNKNOWN' or not gate['reason']:raise ValueError('DEGRADED_CAPABILITY_KNOWN_FORBIDDEN')
        self.sequence+=1;started=self.sequence
        output=fn(call_args)
        if digest(call_args)!=loaded['invocation_input_digest']:raise ValueError('OWNER_MUTATED_FROZEN_INVOCATION_ARGUMENT')
        self.sequence+=1;finished=self.sequence
        record=dict(invocation=loaded,invocation_ref=stored,call_started_sequence=started,output_sequence=finished,output=output)
        self.nodes[node]=record
        for edge,binding in zip(self.incoming(node),loaded['edge_bindings']):
            self.receipts.append(dict(edge,producer_payload_ref=binding['producer_payload_ref'],producer_payload_digest=binding['producer_payload_digest'],consumer_argument_path=binding['consumer_argument_path'],consumer_argument_digest=binding['consumer_argument_digest'],binding_mode=binding['binding_mode'],status=binding['status'],reason=binding['reason'],quality='KNOWN' if binding['status']=='EXECUTED' else 'UNKNOWN',execution_mode=binding['binding_mode'],target_trade_date=self.e['target_trade_date'],previous_market_session=self.e['previous_market_session'],source_trade_date=self.e['previous_market_session'] if edge['time_role']=='T_MINUS_1' else self.e['target_trade_date'],available_at=None if edge['time_role']=='T_MINUS_1' and not self.previous else (self.e['previous_market_session'] if edge['time_role']=='T_MINUS_1' else self.e['target_trade_date'])+'T01:00:00+00:00',input_ref=binding['producer_payload_ref'],input_digest=binding['producer_payload_digest'],consumer_input_ref=dict(scope='CURRENT_OUTPUT',publication=None,pointer='/node_records/'+node+'/invocation/invocation_input'+binding['consumer_argument_path']),consumer_input_digest=binding['consumer_argument_digest'],output_ref=dict(scope='CURRENT_OUTPUT',publication=None,pointer='/node_records/'+node+'/output'),output_digest=digest(output),invocation_ref=stored,invocation_input_digest=loaded['invocation_input_digest'],precall_prepared_sequence=prepared,call_started_sequence=started,output_sequence=finished))
        return output

def replay(a,e,previous):
    from src.v4.base_seed import evaluate_facts
    from src.v4.stock_prewatch import evaluate,load_package
    from scripts.v4_11_candidate_inputs_r2 import projection,seal
    from sector.rotation_r5 import evaluate_b0,advance_rotation,resolve_package
    from sector.legacy_b2_r5 import evaluate_b2
    from .v4_13_accepted_contract_package import AcceptedContracts
    from .v4_13_profile_runtime import sector_snapshot,copy_structure,dual_enrichment,envelope as field
    from .v4_14_owner_adapters import synthetic_confirmation
    from .v4_14_full_dag import calendar,state_input
    from .v4_12_structure_io import FrozenContracts
    from .v4_12_structure_engine import SessionLedger
    from .v4_12_anchor_runtime import create_anchor,create_event
    from src.v4.confirmation_d2_bridge import engineering_d2_publication,verify_d2_publication
    from src.v4.confirmation_events import freeze_prior_session,state_events
    root=a.root;target=e['target_trade_date'];choice=e['owner_inputs'];calls=Invocations(a,e,previous)
    fixture=json.loads(exact(root,calls.mapping['fixture_package']));contracts=AcceptedContracts(root);dep=contracts.dependencies
    seedbook=json.loads(exact(root,fixture['seed']['source']));cbook=json.loads(exact(root,fixture['prewatch']['source']))
    seedfacts={k:dict(value=True if v=='TRUE' else False if v=='FALSE' else v,reason=None) for k,v in seedbook['base_input'].items()};seedfacts['severe_extension']['value']=choice.get('severe_extension',False)
    if choice.get('unknown'):seedfacts['price_identity_READY'].update(value=None,reason='EXPLICIT_SYNTHETIC_UNKNOWN')
    stock=deepcopy(next(v['facts'] for v in cbook['vectors'] if v['id']==fixture['prewatch']['vector_id']));stock.pop('base_seed_state')
    c12=FrozenContracts(root);sb=c12.config['machine_vectors'];sv=next(v for v in sb['vectors'] if v['vector_id']==choice.get('structure_vector','S01'))
    corefacts={**sb['defaults'],**sv['inputs']};corefacts['prior_separated_sessions']=previous['output']['structure_ledger']['separated_sessions'] if previous else 0
    native=dict(fields={f['field_id']:dict(value=None,quality='UNKNOWN',reason_code='ACCEPTED_CORE_OR_PRIOR_HISTORY_UNAVAILABLE') for f in dep['field_registry']['fields']},target_trade_date=target,sector_id='SYNTHETIC_SCOPE',sector_type='INDUSTRY',membership_snapshot_id='ENGINEERING:'+digest(fixture),member_ids=[],rank_eligible=False,common_member_quality={})
    f0=calls.call('F0',dict(fixture_package_ref=calls.mapping['fixture_package'],structure_fixture_source=fixture['structure']['source'],structure_vector=choice.get('structure_vector','S01')),lambda _:dict(base_seed_primitives=seedfacts,stock_core=stock,core_facts=corefacts,sector_native=native,d0_facts=deepcopy(fixture['confirmation']['values'])),a.data_ref)
    seed=calls.call('A',dict(seed_facts=f0['base_seed_primitives']),lambda x:evaluate_facts(x['seed_facts'],json.loads((root/'config/v4_07_parameter_set_v1.json').read_bytes())),a.owners['v4_07'])
    params,registry=resolve_package(dep['rotation_contract'],dep['parameter_set'],exact(root,contracts.config['loo_context']['accepted_sector_dependencies']['parameter_set']),dep['field_registry'])
    b0=calls.call('B0',dict(native=f0['sector_native']),lambda x:evaluate_b0(x['native'],dep['b0_contract'],params),a.owners['v4_08'])
    b1=calls.call('B1',dict(native=native),lambda x:advance_rotation(x['native'],{},prior_publication=None,prior_members=None,prior_core=None,calendar_sessions=a.calendar['session_dates'],contract=dep['rotation_contract'],registry=dep['field_registry'],parameters=params,seed_truth={},seed_capability=False),a.owners['v4_08'])
    b2ast=dep['b2_contract'];b2=calls.call('B2',dict(values={}),lambda x:evaluate_b2(x['values'],b2ast,source_sha256=b2ast['source_sha256'],source_parameter_sha256=b2ast['source_parameter_sha256'],parameter_set_sha256=b2ast['parameter_set_sha256']),a.owners['v4_08'])
    prewatch=calls.call('C',dict(stock_core=f0['stock_core'],base_seed_raw=seed['base_seed_state']),lambda x:evaluate(dict(x['stock_core'],base_seed_state=x['base_seed_raw']),load_package(root)),a.owners['v4_09'])
    cp=projection(f0['d0_facts'],cutoff=e['cutoff']);cp['trade_date']=target
    for row in cp['rows']:
        row['trade_date']=target
        for fact in row['facts'].values():
            fact['trade_date']=e['previous_market_session'] if fact['time_role']=='PRIOR_SESSION_WINDOW' else target
            if 'producer_lineage' in fact:fact['producer_lineage'].update(numerator_trade_date=target,prior_window_end=e['previous_market_session'])
        if not choice.get('confirmation'):row['facts']['actual_bar']['value']=False
        if choice.get('unknown'):row['facts']['normal_universe'].update(value=None,quality='UNKNOWN',reason='EXPLICIT_SYNTHETIC_VECTOR')
    cp['replay_prewatch_lineage']=dict(producer='C',field='stock_prewatch_raw',value=prewatch['raw_qualification'],producer_output_digest=digest(prewatch),fixture_package_ref=calls.mapping['fixture_package'],adapter_mapping=fixture['transport']['C_to_D0'])
    confirmation=calls.call('D0',dict(projection=cp),lambda x:synthetic_confirmation(seal(x['projection'])),a.owners['v4_11']);cr=confirmation['rows'][0]
    def structure(x):
        anchor=x['anchor']
        if x['prior_anchor_event'] is not None and (x['prior_anchor_event']['anchor_id']!=anchor['anchor_id']):raise ValueError('PRECALL_FROZEN_ANCHOR_EVENT_MISMATCH')
        ledger=SessionLedger(c12,anchor['available_date'],[s['trade_date'] for s in calendar(a)['sessions']],anchor['anchor_id'],deepcopy(x['history']))
        observation=ledger.observe(target,e['target_revision'],not choice.get('unknown',False),x['core_facts'])
        return json.loads(json.dumps(dict(observation=observation,history=ledger.history,anchor=anchor,event=create_event(c12,anchor,e['target_revision'])),default=str))
    anchor=previous['output']['anchor'] if previous else create_anchor(c12,'BULLISH_IMPULSE_LOW','SYNTHETIC',target,e['cutoff'],dict(price_basis='SYNTHETIC_QFQ',adjustment_source_revision='r1'),'SYNTHETIC_SUPPORT_EVENT',digest(dict(source='FROZEN_OWNER_STRUCTURE_BOOK')),(10,10),dict(scope='ENGINEERING_SYNTHETIC',source=fixture['structure']['source']),dict(mul='1',add='0',scope='ENGINEERING_SYNTHETIC'))
    d1=calls.call('D1',dict(core_facts=f0['core_facts'],anchor=anchor,prior_anchor_event=previous['output']['node_records']['D1']['output']['event'] if previous else None,history=deepcopy(previous['output']['structure_history']) if previous else {}),structure,a.owners['v4_12'])
    vals=dict(SEED=seed['base_seed_state'],PREWATCH=prewatch['raw_qualification'],CONFIRMED=cr['confirmation_status'],scenario=cr['primary_scenario'] or 'UNKNOWN',core_price_damage='TRUE' if choice.get('damage') else 'FALSE',delta3=choice.get('delta3',0),dq5=0)
    sources=dict(SEED=seed,PREWATCH=prewatch,CONFIRMED=confirmation,structure=d1['observation']['support'],rotation=b1)
    prior=previous['output']['d2']['rows'][0] if previous else None
    def reducer(x):return engineering_d2_publication([state_input(a,e,x['prior_state'],x['values'],x['source_outputs'])])
    d2=calls.call('D2',dict(values=vals,prior_state=prior,source_outputs=sources),reducer,a.owners['v4_10']);state_args=d2['inputs'][0]
    history=previous['output']['episode_history']+[previous['output']['d2']] if previous else []
    def event_diff(x):
        # Resolve the frozen DAG's direct D0 edge through read-only provenance
        # validation. The accepted event owner then re-executes these D2 inputs.
        row=x['confirmation_facts'];facts=x['d2_publication']['inputs'][0]['input_provenance']
        if facts['CONFIRMED']['value']!=row['confirmation_status'] or facts['scenario']['value']!=(row['primary_scenario'] or 'UNKNOWN'):raise ValueError('PRECALL_D0_EVENT_PROVENANCE_MISMATCH')
        verify_d2_publication(x['d2_publication'])
        if x['prior_d2_publication'] is None:return []
        frozen=freeze_prior_session(target_date=target,prior_date=e['previous_market_session'],calendar_publication_id=state_args['calendar_publication_id'],rows=x['prior_d2_publication']['rows'],source_binding=x['prior_d2_publication'],scope='SYNTHETIC_ENGINEERING_ONLY',calendar_manifest=x['calendar_manifest'],episode_history=x['episode_history'])
        return state_events(x['d2_publication'],frozen)
    events=calls.call('EVENT_DIFF',dict(confirmation_facts=cr,d2_publication=d2,prior_d2_publication=previous['output']['d2'] if previous else None,calendar_manifest=state_args['synthetic_calendar_manifest'],episode_history=history),event_diff,a.owners['v4_11'])
    membership=calls.call('MEMBERSHIP',dict(fixture_package_ref=calls.mapping['fixture_package']),lambda _:dict(snapshot_id=native['membership_snapshot_id'],target_trade_date=target,membership_basis='ENGINEERING_SYNTHETIC',members=[],historical_PIT=False),a.membership_ref)
    def context_owner(x):
        if any(c['quality']!='UNKNOWN' for c in x['capabilities'].values()):raise ValueError('CONTEXT_DEGRADED_KNOWN')
        return sector_snapshot(x['selection'],x['item'],contracts,x['source_bindings'])
    item=dict(security_id='fixture-entity',sector_id=native['sector_id'],sector_type='INDUSTRY',membership_basis='UNKNOWN',native_fields=native['fields'],b0=b0,b2=b2,rotation=b1,relative_sector_state=dict(value=None,quality='UNKNOWN',reason='ACCEPTED_CORE_UNAVAILABLE'))
    context=calls.call('D3_CONTEXT',dict(capabilities={},selection=dict(quality='UNKNOWN',membership_basis='UNKNOWN'),item=item,source_bindings=[a.owners['v4_08'],a.membership_ref]),context_owner,a.owners['v4_13'])
    def profile_owner(x):
        copied=copy_structure(None,contracts,a.owners['v4_12'])
        return dict(context=x['context'],enrichment=dual_enrichment(field(None,'UNKNOWN',b1.get('reason_codes')),field(copied,'UNKNOWN',None),contracts))
    profile=calls.call('D3',dict(context=context),profile_owner,a.owners['v4_13'])
    observation=calls.call('GATE_B_OBSERVATION',dict(state=d2,profile=profile),lambda x:dict(state_digest=digest(x['state']),profile_digest=digest(x['profile'])),a.refs[0])
    trace=[dict(node='Accepted Source Binding',owner_ref=a.data_ref,input_digest=digest(e['source_refs']),output_digest=digest(dict(classification='ENGINEERING_SYNTHETIC',calendar=a.calendar_ref)),output=dict(classification='ENGINEERING_SYNTHETIC',calendar=a.calendar_ref))]
    for label,node in [('Seed','A'),('Sector/Rotation','B1'),('PREWATCH','C'),('Confirmation','D0'),('Structure','D1'),('State Reducer','D2'),('Event Diff','EVENT_DIFF'),('Profile/Context','D3'),('Gate-B Observation','GATE_B_OBSERVATION')]:
        n=calls.nodes[node];trace.append(dict(node=label,owner_ref=n['invocation']['owner_authority'],input_digest=n['invocation']['invocation_input_digest'],output_digest=digest(n['output']),output=n['output']))
    logical=[]
    for event in events:
        for event_type in event['event_types']:
            r=d2['rows'][0];logical.append(dict(model_namespace='ENGINEERING_SYNTHETIC',model_contract_id=r['model_contract_id'],parameter_set_id=r['parameter_set_id'],entity_type=r['entity_type'],entity_id=r['entity_id'],episode_id=r['episode_id'],event_type=event_type,signal_market_date=target))
    statuses={s:sorted(r['edge_id'] for r in calls.receipts if r['status']==s) for s in ['EXECUTED','DEGRADED_ACCEPTED_CAPABILITY','NOT_APPLICABLE_BY_FROZEN_CONTRACT']}
    empty=dict(missing_edges=[],unexpected_edges=[],false_executed_edges=[],unbound_consumer_arguments=[],post_hoc_only_edges=[])
    return dict(quality='DEGRADED',scope='ENGINEERING_SYNTHETIC',trace=trace,d2=d2,events=events,logical_events=logical,episode_history=history,structure_observation=d1['observation']['support'],structure_ledger=d1['observation'],structure_history=d1['history'],anchor=d1['anchor'],anchor_event=d1['event'],previous_D1_publication=e['previous_state_publication'],context=context,enrichment=profile['enrichment'],dimension_results=[],raw_provider_fallback=False,node_records=calls.nodes,edge_receipts=calls.receipts,consumption_mapping_ref=calls.mapping_ref,missing_sources={r['edge_id']:None for r in calls.receipts if r['producer_payload_ref']['pointer'].startswith('/missing_sources/')},edge_completeness=dict(expected_active_edges=sorted(r['edge_id'] for r in calls.receipts),executed_edges=statuses['EXECUTED'],degraded_edges=statuses['DEGRADED_ACCEPTED_CAPABILITY'],not_applicable_edges=statuses['NOT_APPLICABLE_BY_FROZEN_CONTRACT'],status='PASS',**empty))
