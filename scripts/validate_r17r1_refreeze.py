"""Independent contract completeness gate; intentionally no replay engine."""
from pathlib import Path
from copy import deepcopy
import json,hashlib
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
NAMES=['replay_gate_b_contract_v1_1','replay_case_registry_v1_1','temporal_non_edge_registry_v1_1','quality_degradation_v1_1','machine_vectors_v1_1']
REQUIRED=['same_day_feedback','state_transition_legality','hysteresis','expiry','direct_prewatch_confirmed','rotation_pulse_accepted_failed','support_reclaim_retest_break','confirmation_persistent_suppression','multi_sector_dedup','unknown_propagation','no_duplicate_event_episode','same_day_revision_predecessor','cross_process_previous_session','future_publication_leakage','revision_append_only','deterministic_replay','historical_pit_evidence']
REQUIRED_NON_EDGES=[['D3','A','T'],['D3','B0','T'],['D3','B1','T'],['D3','C','T'],['D1','C','T'],['D2','D1','T'],['D2','C','T'],['FUTURE_PUBLICATION','T0','ANY'],['T_PLUS_1','T0','ANY'],['SAME_DAY_REVISION_PARENT','PREVIOUS_SESSION','ANY'],['EVENT_DIFF','D0','T']]
CLASSES={'ENGINEERING_SYNTHETIC','REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','HISTORICAL_PIT_EFFECTIVENESS'}
REFERENCE_SCHEMA=dict(type='object',required=['path','sha256','bytes'],properties=dict(path=dict(type='string',minLength=1),sha256=dict(type='string',pattern='^[0-9a-f]{64}$'),bytes=dict(type='integer',minimum=1)))
SCHEMA=dict(type='object',required=['contract_id','version','status','source_bindings','time_role','required_history','unknown_semantics','negative_cases','acceptance_criteria','runtime_implemented','production','shadow','focus','global_mandatory_adoption','ALGORITHM_STATE_REPLAY_PASS'],properties=dict(contract_id=dict(type='string',minLength=1),version=dict(const='1.1.0'),status=dict(const='CONTRACT_FREEZE_ONLY'),source_bindings=dict(type='array',minItems=20,items=REFERENCE_SCHEMA),time_role=dict(type='string',minLength=1),required_history=dict(type='string',minLength=1),unknown_semantics=dict(type='string',minLength=1),negative_cases=dict(type='array',minItems=11,items=dict(type='string')),acceptance_criteria=dict(type='string',minLength=1),runtime_implemented=dict(const=False),production=dict(const=False),shadow=dict(const=False),focus=dict(const=False),global_mandatory_adoption=dict(const=False),ALGORITHM_STATE_REPLAY_PASS=dict(const='NOT_GRANTED')))
LITERAL_BEHAVIOR={
 'same_day_feedback':dict(raw_after='TRUE'),
 'state_transition_legality':dict(maturity='CONFIRMED',episode='E1'),
 'hysteresis':dict(maturity='PREWATCH',downgrade_count=1),
 'expiry':dict(maturity='NONE',tracking='FOLLOWUP',expiry_count=10),
 'direct_prewatch_confirmed':dict(maturity='CONFIRMED',mandatory_wait_sessions=0),
 'rotation_pulse_accepted_failed':dict(accepted_branch='ROTATION_ACCEPTED',failed_branch='ROTATION_FAILED',branches_mutually_exclusive=True),
 'support_reclaim_retest_break':dict(trace=['TESTING','RECLAIMED','HELD_TENTATIVE','RETESTING','HELD_CONFIRMED','BROKEN'],anchor='A1'),
 'confirmation_persistent_suppression':dict(event_class='PERSISTENT_CONFIRMED',new_actionable_event=False,new_episode=False),
 'multi_sector_dedup':dict(logical_security_event_count=1,sector_context_count=3),
 'unknown_propagation':dict(final_eligibility='UNKNOWN',maturity='PREWATCH',expiry_count=9,unaffected_relation_quality='KNOWN'),
 'no_duplicate_event_episode':dict(logical_event_count=1,episode_count=1,episode_id='E1'),
 'same_day_revision_predecessor':dict(previous_dates=['2026-09-29','2026-09-29'],previous_manifest_digests=['a'*64,'a'*64],event_classes=['NEW_CONFIRMED','NEW_CONFIRMED']),
 'cross_process_previous_session':dict(readback='EXACT_PERSISTED_PREVIOUS_SESSION',memory_prior_used=False),
 'future_publication_leakage':dict(temporal_admission='ALLOW'),
 'revision_append_only':dict(old_revision_immutable=True,new_revision_separate=True),
 'deterministic_replay':dict(output_digest_equal=True,duplicate_side_effects=0),
 'historical_pit_evidence':dict(evidence_class='ENGINEERING_SYNTHETIC',historical_effectiveness='NOT_VERIFIABLE',affected_quality='DEGRADED')}
def exact(ref):
    p=(ROOT/ref['path']).resolve();assert p.is_relative_to(ROOT)
    raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref.get('bytes',ref.get('byte_count')),ref['path'];return raw
def load():return {n:json.loads((ROOT/('config/v4_14_'+n+'.json')).read_bytes()) for n in NAMES}
def preserve_authority_only(bundle):
    from scripts.validate_r17r1_active_closure import read
    new_head=read('data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json',ROOT)
    old_head=read('data/v4/V4_13_ACCEPTED_HEAD.json',ROOT)
    reverse={b['path']:a for a,b in zip(old_head['contract_refs'],new_head['contract_refs']) if a!=b}
    def reference(path):
        raw=(ROOT/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    reverse['data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json']=reference('data/v4/V4_13_ACCEPTED_HEAD.json')
    reverse['reports/r17r1b/owner_oracle_witnesses_v1_1.json']=reference('reports/r17c/owner_oracle_witnesses.json')
    reverse['reports/r17r1a/completion_gate.json']=reference('reports/r17b/completion_gate.json')
    for name in NAMES:reverse['config/v4_14_'+name+'.json']=reference('config/v4_14_'+name.removesuffix('_1')+'.json')
    def normalize(x,lineage=False):
        if isinstance(x,list):return [normalize(v,lineage) for v in x]
        if isinstance(x,dict):
            if {'path','sha256','bytes'}<=x.keys():return deepcopy(reverse.get(x['path'],x)) if not lineage else deepcopy(x)
            return {k:normalize(v,lineage or k in ['supersedes','derived_from','historical_lineage']) for k,v in x.items()}
        return x
    for name,obj in bundle.items():
        prior=read('config/v4_14_'+name.removesuffix('_1')+'.json',ROOT)
        new=normalize(deepcopy(obj))
        for k in ['supersedes','active_family_closure','accepted_v4_13_authority']:new.pop(k)
        new['version']=prior['version']
        new['source_bindings']=[r for r in new['source_bindings'] if r['path']!='config/v4_13_rotation_structure_enrichment_schema_v1_1.json']
        if name=='temporal_non_edge_registry_v1_1':
            for row,old in zip(new['owner_edges'],prior['owner_edges']):
                if old['field']=='structure_projection':row['contract_binding']=old['contract_binding']
                if old['field'] in ['structure_projection','rotation_structure_enrichment']:row['version']=old['version']
        assert new==prior,'REPLAY_SEMANTICS_CHANGED: '+name
def validate_bundle(bundle):
    assert set(bundle)==set(NAMES)
    for obj in bundle.values():
        Draft202012Validator(SCHEMA).validate(obj)
        for ref in obj['source_bindings']:exact(ref)
        assert 'UNKNOWN_NEVER_FALSE' in obj['unknown_semantics']
    from scripts.validate_r17r1_active_closure import read as closure_read, walk
    families=deepcopy(closure_read('config/v4_13_active_contract_family_closure_r17r1.json',ROOT)['families'])
    for name,obj in bundle.items():
        raw=(ROOT/('config/v4_14_'+name+'.json')).read_bytes()
        families[obj['contract_id']]=dict(active=dict(path='config/v4_14_'+name+'.json',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    for name,obj in bundle.items():
        previous=json.loads(exact(obj['supersedes']));assert previous['contract_id']==obj['contract_id'] and previous['version']=='1.0.0'
        assert obj['accepted_v4_13_authority']['path']=='data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'
        walk(obj,families,ROOT)
    gate=bundle[NAMES[0]];cases=bundle[NAMES[1]];dag=bundle[NAMES[2]];quality=bundle[NAMES[3]];book=bundle[NAMES[4]]
    assert gate['required_dimensions']==cases['dimensions']==REQUIRED
    assert gate['runtime_authorization']=='NOT_GRANTED_THIS_ROUND' and gate['local_completion_claim']=='PASS_READY_FOR_EXTERNAL_AUDIT_ONLY' and gate['V4_14_ACCEPTED_HEAD']=='FORBIDDEN' and gate['NEXT']=='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'
    assert set(gate['baseline_sections'])=={'53','54','78','80','81'}
    for n,section in gate['baseline_sections'].items():
        text=exact(section['authority']).decode('utf8');start=text.index('# '+n+'.');end=text.index('# '+str(int(n)+1)+'.',start)
        assert section['read'] and hashlib.sha256(text[start:end].replace('\r\n','\n').encode()).hexdigest()==section['normalized_excerpt_sha256']
    ids=[v['id'] for v in book['vectors']];assert len(ids)==len(set(ids))>=52
    by_id={v['id']:v for v in book['vectors']}
    for v in book['vectors']:
        assert v['dimension'] in REQUIRED and v['polarity'] in ['positive','negative'] and v['evidence_class']=='ENGINEERING_SYNTHETIC'
        assert isinstance(v['input'],dict) and v['input'] and v['expected_origin'].startswith('HAND_AUTHORED')
        if v['polarity']=='positive':assert v['expected']['verdict']=='ADMIT_CONTRACT_CASE' and v['expected']['required_behavior']
        else:assert v['expected']['verdict']=='REJECT_CONTRACT_VIOLATION' and v['expected']['reason']
    assert book['expected_generation']=='LITERAL_BEFORE_RUNTIME'
    for ref in book['owner_oracle_books']:exact(ref)
    assert len(cases['cases'])==len(REQUIRED) and {c['case_id'] for c in cases['cases']}==set(REQUIRED)
    for case in cases['cases']:
        d=case['case_id'];assert case['positive']==d+'_positive' and case['negative']==d+'_negative'
        assert by_id[case['positive']]['expected']['required_behavior']==LITERAL_BEHAVIOR[d]
        assert by_id[case['negative']]['polarity']=='negative'
        assert set(case['vector_ids'])=={v['id'] for v in book['vectors'] if v['dimension']==d}
        assert case['acceptance_scope']=='CONTRACT_FROZEN_NOT_RUNTIME_PASS' and case['failure_scope']=='AFFECTED_COMPONENT_ONLY'
    owner=json.loads(exact(dag['owner_dag']));assert dag['owner_edges']==owner['edges']
    for edge in REQUIRED_NON_EDGES:assert edge in dag['forbidden_edges']
    for edge in owner['forbidden_edges']:assert edge in dag['forbidden_edges']
    edges=dag['owner_edges']+dag['replay_required_edges'];graph={}
    assert dag['canonical_nodes']==dict(PROFILE='D3',CONTEXT='D3_CONTEXT',CORE_V4_04='F0',NATIVE_V4_05='F0',BASE_SEED_V4_07='A')
    def canonical_node(n):return dag['canonical_nodes'].get(n,n)
    for e in edges:
        assert e['time_role'] in ['T','T_MINUS_1'] and e['producer'] and e['consumer'] and e['field']
        for key in ['contract_binding','source_owner_binding','owner']:
            if key in e:exact(e[key])
        if e['time_role']=='T':graph.setdefault(canonical_node(e['producer']),set()).add(canonical_node(e['consumer']))
    def visit(node,stack):
        assert node not in stack,'SAME_DAY_DAG_CYCLE'
        for child in graph.get(node,[]):visit(child,stack|{node})
    for node in graph:visit(node,set())
    for source,target,role in dag['forbidden_edges']:
        if role=='T':
            seen=set();todo=list(graph.get(canonical_node(source),set()))
            while todo:
                child=todo.pop()
                if child not in seen:seen.add(child);todo.extend(graph.get(child,set()))
            assert canonical_node(target) not in seen,'FORBIDDEN_FEEDBACK_PATH_PRESENT'
    for node in ['F0','A','B0','B1','B2','C','D0','D1','D2','D3']:assert any(node in [e['producer'],e['consumer']] for e in edges)
    cross=dag['cross_day'];assert cross['required_sequence']==['T_MINUS_1_PERSISTED_PUBLICATION','PRODUCER_PROCESS_EXIT','T_FRESH_PROCESS_START','EXACT_T_MINUS_1_READBACK','T_STATE_TRANSITION'] and cross['memory_prior_is_proof'] is False
    assert set(['producer_pid','consumer_pid','producer_exit_at','consumer_start_at','publication_sha256','publication_bytes','previous_market_session','readback_sha256','calendar_binding']).issubset(cross['must_record'])
    revisions=cross['same_day_revisions'];assert revisions['revisions']==['r1','r2'] and all(revisions[k] is True for k in ['same_exact_previous_date','same_exact_previous_manifest','no_r1_to_r2_prior','new_stays_new'])
    assert cross['missing_previous_state']=='UNKNOWN_NOT_FABRICATED_NONE' and cross['wrong_hash_or_date']=='REJECT'
    assert set(quality['evidence_classes'])==CLASSES
    historical=quality['evidence_classes']['HISTORICAL_PIT_EFFECTIVENESS'];assert historical['current_membership_backfill_allowed'] is False and historical['all_prerequisites_must_be_proven'] is True
    assert set(historical['required'])=={'price_PIT','universe_PIT','membership_PIT','source_identity','availability_cutoff','AS_RECORDED_adjustment_revision'}
    assert quality['evidence_classes']['REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED']['historical_effectiveness_implied'] is False
    policy=quality['failure_policy'];assert policy['unknown_to_false'] is False and policy['unaffected_components']=='REMAIN_INDEPENDENTLY_TESTABLE' and policy['missing_availability']=='NOT_VERIFIABLE'
    assert quality['real_current_scope']['AS_RECORDED'] is False and quality['real_current_scope']['historical_pit_effectiveness']=='NOT_GRANTED' and quality['real_current_scope']['historical_LOO']=='NOT_VERIFIABLE' and quality['real_current_scope']['legacy_B2']=='NOT_IMPLEMENTED'
    assert gate['identity_rules']['old_revisions']=='APPEND_ONLY_BYTE_IMMUTABLE' and gate['identity_rules']['episode_continuation']=='SAME_ID_UNTIL_FORMAL_EXIT'
    assert gate['identity_rules']['event_logical_key']==['model_namespace','model_contract_id','parameter_set_id','entity_type','entity_id','episode_id','event_type','signal_market_date']
    assert gate['identity_rules']['event_revision_key']==['logical_event_id','observation_revision']
    assert gate['identity_rules']['new_episode']=='ONLY_FROZEN_OWNER_REENTRY_OR_AUTHORIZED_MODEL_BOUNDARY; LINK_PARENT_EPISODE'
    assert len(gate['field_registry'])>=11 and all(set(['field','producer','time_role','source_binding','quality']).issubset(r) for r in gate['field_registry'])
    assert len({r['field'] for r in gate['field_registry']})==len(gate['field_registry'])
    for row in gate['field_registry']:exact(row['source_binding']);assert row['producer'] and row['time_role'] and row['quality']=='OWNER_EXACT_NO_COERCION'
    witnesses=json.loads(exact(gate['owner_oracle_witnesses']));Draft202012Validator(SCHEMA).validate(witnesses)
    assert witnesses['expectation_origin']=='PREEXISTING_INDEPENDENT_OWNER_BOOKS_EXACT_COPY_NO_RUNTIME_EVALUATOR' and len(witnesses['records'])>=40
    for record in witnesses['records']:
        book_at_source=json.loads(exact(record['source']));idx=int(record['pointer'].split('/')[-1])
        frozen=book_at_source['vectors'][idx];assert record['independent_frozen_record']==frozen and record['vector_id']==frozen.get('id',frozen.get('vector_id'))
    for ref in gate['contract_package']:assert json.loads(exact(ref))==bundle[Path(ref['path']).stem.removeprefix('v4_14_')]
    return dict(status='PASS_READY_FOR_EXTERNAL_AUDIT',dimensions=len(REQUIRED),vectors=len(ids),runtime_executed=False,ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED')
def validate():
    from scripts.validate_r17r1_active_closure import validate as validate_active
    assert validate_active(ROOT)['ACTIVE_CONTRACT_FAMILY_CLOSURE']=='PASS'
    bundle=load();result=validate_bundle(bundle);preserve_authority_only(bundle)
    stage=json.loads((ROOT/'reports/r17r1b/stage_contract.json').read_bytes())
    for ref in stage['protected'].values():exact(ref)
    entry=json.loads(exact(stage['entry_gate']));assert entry['R17R1A_V4_13_ACTIVE_BINDING_REPAIR']=='PASS'
    assert not (ROOT/'data/v4/V4_14_ACCEPTED_HEAD.json').exists()
    if (ROOT/'src/workbench_analysis/v4_14_replay_runtime.py').exists():
        audit=dict(path='docs/evidence/r18/V4_R17R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md',sha256='9a8cc8c92599d6aa843e1fdb9eefe498361ba37b55dd2091c13c6eb75f403d43',bytes=3583)
        assert 'AUTHORIZED_NEXT_SCOPED_ENGINEERING' in exact(audit).decode('utf8')
    manifest=json.loads((ROOT/'reports/r17r1b/contract_freeze_manifest.json').read_bytes())
    for ref in manifest['contracts']:exact(ref)
    assert manifest['vector_count']==result['vectors'] and manifest['dimensions']==result['dimensions']
    return dict(result,R17R1B_V4_14_CONTRACT_REFREEZE='PASS_LOCAL',ACTIVE_CONTRACT_FAMILY_CLOSURE='PASS',V4_14_CONTRACT_COMPLETENESS='PASS_READY_FOR_EXTERNAL_AUDIT',V4_14_RUNTIME='NOT_IMPLEMENTED',protected_byte_identical=True,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':print(json.dumps(validate()))
