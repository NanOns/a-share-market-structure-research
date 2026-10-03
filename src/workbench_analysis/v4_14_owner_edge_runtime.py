"""Frozen owner-edge accounting over actual owner calls and explicit fixtures."""
import json
from copy import deepcopy
from .v4_14_replay_io import ref,exact,digest

def expected(authority):
    pack=authority.config['temporal_non_edge_registry'];alias=pack['canonical_nodes'];out=[]
    for group in ['owner_edges','replay_required_edges']:
        for e in pack[group]:
            p=alias.get(e['producer'],e['producer']);c=alias.get(e['consumer'],e['consumer']);identity=[p,c,e['field'],e['time_role']]
            head=e.get('source_owner_binding',e.get('owner'));contract=e.get('contract_binding',head)
            contract_id=e['contract_id'] if 'contract_id' in e else json.loads(exact(authority.root,head)).get('contract_id',head['path'])
            out.append(dict(edge_id=digest(identity),producer=p,consumer=c,declared_producer=e['producer'],declared_consumer=e['consumer'],field=e['field'],time_role=e['time_role'],owner_head_ref=head,owner_contract_ref=contract,owner_contract_id=contract_id,group=group))
    if len({e['edge_id'] for e in out})!=len(out):raise ValueError('FROZEN_EDGE_IDENTITY_DUPLICATED')
    return out

def prepare(a,e,previous):
    from src.v4.base_seed import evaluate_facts
    from src.v4.stock_prewatch import evaluate,load_package
    from scripts.v4_11_candidate_inputs_r2 import projection,seal
    from sector.native_r5 import build_native
    from sector.rotation_r5 import evaluate_b0,advance_rotation,resolve_package
    from sector.legacy_b2_r5 import build_b2_inputs,evaluate_b2
    from .v4_13_accepted_contract_package import AcceptedContracts
    from .v4_13_profile_runtime import sector_snapshot
    root=a.root;target=e['target_trade_date'];choice=e['owner_inputs'];fixture_ref=choice['fixture_package_ref'];schema_ref=choice['edge_schema_ref']
    fixture=json.loads(exact(root,fixture_ref));schema=json.loads(exact(root,schema_ref))
    if schema['fixture_package']!=fixture_ref or schema['frozen_dag']!=a.refs[2]:raise ValueError('EDGE_SCHEMA_EXACT_FROZEN_AUTHORITY_REQUIRED')
    for spec in fixture.values():
        if isinstance(spec,dict):
            for r in spec.get('sources',[]):exact(root,r)
            if 'source' in spec:exact(root,spec['source'])
    seed_book=json.loads(exact(root,fixture['seed']['source']));c_book=json.loads(exact(root,fixture['prewatch']['source']))
    seed_facts={k:dict(value=True if v=='TRUE' else False if v=='FALSE' else v,reason=None) for k,v in seed_book['base_input'].items()}
    seed_facts['severe_extension']['value']=choice.get('severe_extension',False)
    if choice.get('unknown'):seed_facts['price_identity_READY'].update(value=None,reason='EXPLICIT_SYNTHETIC_UNKNOWN')
    stock=deepcopy(next(v['facts'] for v in c_book['vectors'] if v['id']==fixture['prewatch']['vector_id']))
    stock.pop('base_seed_state');core=dict(seed_facts=seed_facts,stock_core=stock,d0_facts=deepcopy(fixture['confirmation']['values']),structure_fixture=dict(source=fixture['structure']['source'],vector_id=choice.get('structure_vector','S01')))
    seed=evaluate_facts(core['seed_facts'],json.loads((root/'config/v4_07_parameter_set_v1.json').read_bytes()))
    cf=dict(core['stock_core'],base_seed_state=seed['base_seed_state']);prewatch=evaluate(cf,load_package(root))
    cp=projection(core['d0_facts'],cutoff=e['cutoff']);cp['trade_date']=target
    for row in cp['rows']:
        row['trade_date']=target
        for f in row['facts'].values():
            f['trade_date']=e['previous_market_session'] if f['time_role']=='PRIOR_SESSION_WINDOW' else target
            if 'producer_lineage' in f:f['producer_lineage'].update(numerator_trade_date=target,prior_window_end=e['previous_market_session'])
        if not choice.get('confirmation'):row['facts']['actual_bar']['value']=False
        if choice.get('unknown'):row['facts']['normal_universe'].update(value=None,quality='UNKNOWN',reason='EXPLICIT_SYNTHETIC_VECTOR')
    # Transport the current C result into the owner input digest. It is read-only
    # lineage, not a new scanner predicate or a prewatch eligibility gate.
    cp['replay_prewatch_lineage']=dict(producer='C',field='stock_prewatch_raw',value=prewatch['raw_qualification'],producer_output_digest=digest(prewatch),fixture_package_ref=fixture_ref,adapter_mapping=fixture['transport']['C_to_D0'])
    contracts=AcceptedContracts(root);dep=contracts.dependencies
    params,registry=resolve_package(dep['rotation_contract'],dep['parameter_set'],exact(root,contracts.config['loo_context']['accepted_sector_dependencies']['parameter_set']),dep['field_registry'])
    # Empty accepted primitive coverage is explicit: owners calculate UNKNOWN.
    # Synthetic membership is a frozen engineering scope, never historical PIT.
    membership=dict(snapshot_id='ENGINEERING:'+digest(fixture),target_trade_date=target,membership_basis='ENGINEERING_SYNTHETIC',members=[],excluded_target_id='fixture-entity',fixture_package_ref=fixture_ref)
    native_fields={f['field_id']:dict(value=None,quality='UNKNOWN',reason_code='ACCEPTED_CORE_OR_PRIOR_HISTORY_UNAVAILABLE') for f in dep['field_registry']['fields']}
    native=dict(fields=native_fields,target_trade_date=target,sector_id='SYNTHETIC_SCOPE',sector_type='INDUSTRY',membership_snapshot_id=membership['snapshot_id'],member_ids=[],rank_eligible=False,common_member_quality={})
    b0=evaluate_b0(native,dep['b0_contract'],params)
    b1=advance_rotation(native,{},prior_publication=None,prior_members=None,prior_core=None,calendar_sessions=a.calendar['session_dates'],contract=dep['rotation_contract'],registry=dep['field_registry'],parameters=params,seed_truth={'fixture-entity':seed['base_seed_state']},seed_capability=False)
    b2ast=dep['b2_contract'];b2=evaluate_b2({},b2ast,source_sha256=b2ast['source_sha256'],source_parameter_sha256=b2ast['source_parameter_sha256'],parameter_set_sha256=b2ast['parameter_set_sha256'])
    item=dict(security_id='fixture-entity',sector_id=native['sector_id'],sector_type='INDUSTRY',membership_basis='UNKNOWN',native_fields=native_fields,b0=b0,b2=b2,rotation=b1,relative_sector_state=dict(value=None,quality='UNKNOWN',reason='ACCEPTED_CORE_UNAVAILABLE'))
    context=sector_snapshot(dict(quality='UNKNOWN',membership_basis='UNKNOWN'),item,contracts,[a.owners['v4_08'],a.membership_ref])
    return dict(F0=dict(input=dict(fixture_package_ref=fixture_ref),output=core),A=dict(input=dict(seed_facts=core['seed_facts']),output=seed),B0=dict(input=dict(native=native,seed=seed),output=b0),B1=dict(input=dict(native=native,b0=b0,prior_capability='NO_ACCEPTED_LOO_ROTATION_HISTORY'),output=b1),B2=dict(input=dict(b0=b0,values={},accepted_capability='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE'),output=b2),C=dict(input=cf,output=prewatch),D0=dict(input=dict(projection=cp,prewatch_lineage=cp['replay_prewatch_lineage']),output=None),MEMBERSHIP=dict(input=dict(fixture_package_ref=fixture_ref,accepted_owner=a.membership_ref),output=membership),D3_CONTEXT=dict(input=dict(b0=b0,b1=b1,b2=b2,membership=membership,core=core,seed=seed),output=context))

def replay(a,e,previous):
    from .v4_14_full_dag import replay as legacy
    nodes=prepare(a,e,previous);result=legacy(a,e,previous,_edge_prepared=nodes)
    nodes['D0']['output']=result['trace'][4]['output']
    nodes['D1']=dict(input=dict(structure_fixture=nodes['F0']['output']['structure_fixture'],previous=e['previous_state_publication']),output=dict(observation=result['structure_ledger'],history=result['structure_history'],anchor=result['anchor'],event=result['anchor_event']))
    nodes['D2']=dict(input=result['d2']['inputs'][0],output=result['d2'])
    nodes['EVENT_DIFF']=dict(input=dict(current_d2=result['d2']['publication_id'],previous=e['previous_state_publication']),output=result['events'])
    nodes['D3']=dict(input=dict(context=result['context'],structure=nodes['D1']['output']),output=dict(context=result['context'],enrichment=result['enrichment']))
    nodes['GATE_B_OBSERVATION']=dict(input=dict(state=result['d2'],profile=nodes['D3']['output']),output=dict(state_digest=digest(result['d2']),profile_digest=digest(nodes['D3']['output'])))
    fixture_ref=e['owner_inputs']['fixture_package_ref'];schema_ref=e['owner_inputs']['edge_schema_ref'];head08=json.loads(exact(a.root,a.owners['v4_08']))
    receipts=[]
    for edge in expected(a):
        p=edge['producer'];c=edge['consumer'];prior=edge['time_role']=='T_MINUS_1';source=previous['output']['node_records'][p]['output'] if prior and previous else nodes[p]['output'] if not prior else dict(value=None,quality='UNKNOWN',reason='NO_EXACT_PREVIOUS_ENGINEERING_PUBLICATION')
        consumer=nodes[c];consumer.setdefault('edge_inputs',{})[edge['edge_id']]=deepcopy(source)
        reason=None;status='EXECUTED';quality='KNOWN';mode='EXACT_REPLAY_OWNER_OUTPUT'
        if prior and previous is None:status='DEGRADED_ACCEPTED_CAPABILITY';quality='UNKNOWN';reason='NO_EXACT_PREVIOUS_ENGINEERING_PUBLICATION'
        elif p in ('B0','B1','B2') or c in ('B0','B1','B2'):
            status='DEGRADED_ACCEPTED_CAPABILITY';quality='UNKNOWN';reason=head08['capabilities']['B2_LEGACY_CONFIRMED_WARM'] if p=='B2' or c=='B2' else head08['capabilities']['REAL_SIGNAL_CAPABILITY']
        elif p=='D1' and c=='D2':status='DEGRADED_ACCEPTED_CAPABILITY';quality='UNKNOWN';reason=json.loads(exact(a.root,a.owners['v4_11']))['capabilities']['V4_12_STRUCTURE_SUPPORT'];mode='OWNER_DECLARED_UNAVAILABLE_D1_TO_D2'
        elif p=='D1' and c=='D3':status='DEGRADED_ACCEPTED_CAPABILITY';quality='UNKNOWN';reason='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE';mode='READ_ONLY_OWNER_PROJECTION_WITHOUT_ACCEPTED_FULL_ENVELOPE'
        elif c=='D3_CONTEXT' and p in ('F0','A','MEMBERSHIP'):status='DEGRADED_ACCEPTED_CAPABILITY';quality='UNKNOWN';reason='NO_ACCEPTED_NON_TARGET_CORE_NATIVE_OR_HISTORICAL_MEMBERSHIP';mode='OWNER_CONTEXT_COMPONENT_CAPABILITY_GATE'
        elif p=='C' and c=='D0':mode='OWNER_READ_ONLY_PREWATCH_LINEAGE_TRANSPORT'
        elif p=='F0':mode='EXACT_FROZEN_FIXTURE_PRODUCER'
        input_ref=dict(scope='PREVIOUS_PUBLICATION' if prior and previous else 'CURRENT_OUTPUT',publication=e['previous_state_publication'] if prior and previous else None,pointer='/output/node_records/'+p+'/output' if prior and previous else '/node_records/'+p+'/output')
        if prior and previous is None:input_ref=dict(scope='CURRENT_OUTPUT',publication=None,pointer='/edge_missing_sources/'+edge['edge_id'])
        receipt=dict(edge,target_trade_date=e['target_trade_date'],previous_market_session=e['previous_market_session'],input_ref=input_ref,input_digest=digest(source),output_ref=dict(scope='CURRENT_OUTPUT',publication=None,pointer='/node_records/'+c+'/output'),output_digest=digest(consumer['output']),consumer_input_ref=dict(scope='CURRENT_OUTPUT',publication=None,pointer='/node_records/'+c+'/edge_inputs/'+edge['edge_id']),consumer_input_digest=digest(source),execution_mode=mode,quality=quality,status=status,reason=reason,source_trade_date=e['previous_market_session'] if prior else e['target_trade_date'],available_at=None if prior and previous is None else (e['previous_market_session'] if prior else e['target_trade_date'])+'T01:00:00+00:00',fixture_package_ref=fixture_ref)
        receipts.append(receipt)
    all_ids={r['edge_id'] for r in receipts};sets={s:sorted(r['edge_id'] for r in receipts if r['status']==s) for s in ['EXECUTED','DEGRADED_ACCEPTED_CAPABILITY','NOT_APPLICABLE_BY_FROZEN_CONTRACT']}
    result.update(node_records=nodes,edge_receipts=receipts,edge_schema_ref=schema_ref,fixture_package_ref=fixture_ref,edge_missing_sources={r['edge_id']:nodes[r['consumer']]['edge_inputs'][r['edge_id']] for r in receipts if r['input_ref']['pointer'].startswith('/edge_missing_sources/')},edge_completeness=dict(expected_active_edges=sorted(x['edge_id'] for x in expected(a)),executed_edges=sets['EXECUTED'],degraded_edges=sets['DEGRADED_ACCEPTED_CAPABILITY'],not_applicable_edges=sets['NOT_APPLICABLE_BY_FROZEN_CONTRACT'],missing_edges=[],unexpected_edges=[],status='PASS'))
    return result
