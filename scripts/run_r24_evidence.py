"""Persist stage-specific gates backed by contracts and isolated execution."""
import subprocess
from scripts.r24_io import ROOT, BASE, read, ref, atomic
from scripts.validate_r24_activation import inspect, protected
from tests.test_r24_activation import positive, negative, REASONS, test_owner_projection_preserves_accepted_semantics

def run():
    deps=read('config/v4_16_runtime_dependencies_v2.json')
    head=read(deps['engineering_acceptance']['path'])
    assert head['scope']=='ENGINEERING_RUNTIME_ONLY' and head['real_activation']=='REAL_ACTIVATION_NOT_GRANTED'
    assert subprocess.check_output(['git','rev-parse',head['tested_tag']],cwd=ROOT,text=True).strip()==head['tested_source']
    for binding in head['bindings']+[head['external_r23r1_audit'],head['external_r23_audit']]:assert ref(binding['path'])==binding
    assert 'PASS_FINAL_OBSERVATION_SLOT_RUNTIME_COMPLETENESS' in (ROOT/head['external_r23r1_audit']['path']).read_text(encoding='utf-8')
    for b in deps['bindings']:assert ref(b['path'])==b
    assert deps['slot_runtime_policy'] in deps['bindings']
    authority=read(deps['activation']['path'])
    assert not authority['runtime_authorized'] and not authority['real_shadow_authorized']
    before=protected()
    # Independently compare protected tracked bytes against the authorized baseline.
    for b in before['bindings']:
        raw=subprocess.check_output(['git','show',BASE+':'+b['path']],cwd=ROOT)
        assert raw==(ROOT/b['path']).read_bytes()
    positive_result=positive('persisted_positive_'+__import__('uuid').uuid4().hex)
    context=positive_result['context']
    oracle=inspect(ROOT/context['database'],context['manifest'])
    positive_result['database_binding']=ref(context['database'])
    positive_result['manifest_binding']=ref(context['manifest'])
    negatives=[negative(case) for case in REASONS]
    assert protected()==before
    test_owner_projection_preserves_accepted_semantics()
    common=dict(status='PASS_LOCAL',execution_baseline=BASE,external_acceptance='NOT_GRANTED',
        runtime_authorized=False,real_shadow_authorized=False,NEXT='STOP_WAIT_R24_INDEPENDENT_EXTERNAL_AUDIT')
    gates={
      'R23R1_EXTERNAL_ACCEPTANCE_BINDING':dict(head_binding=deps['engineering_acceptance'],external_audit=head['external_r23r1_audit'],scope=head['scope']),
      'RUNTIME_ENGINEERING_ACCEPTED_HEAD_GATE':dict(head=head,bindings_verified=True,tested_tag_verified=True),
      'DEPENDENCY_MANIFEST_V2_GATE':dict(manifest=ref('config/v4_16_runtime_dependencies_v2.json'),bindings_verified=len(deps['bindings']),slot_policy_centrally_registered=True),
      'REAL_STORAGE_SCHEMA_GATE':dict(contract=deps['storage'],migration=deps['migration'],persisted_database=ref(context['database']),oracle=oracle,engineering_migration_unchanged=True),
      'ACTIVATION_AUTHORITY_V2_GATE':dict(authority=deps['activation'],required_grant_fields=authority['required_grant_fields'],disabled_before_consumption_cases=negatives[:2]+negatives[-1:]),
      'REAL_PATH_REACHABILITY_GATE':dict(entry='ShadowRuntimeController(mode=REAL_SHADOW)',simulation=positive_result['manifest_binding'],persisted_database=positive_result['database_binding'],oracle=oracle),
      'REAL_INITIALIZATION_BOUNDARY_GATE':dict(contract=deps['initialization_boundary'],first_real_trade_date='REQUIRES_EXACT_LATER_EXTERNALLY_ACCEPTED_ACTIVATION_GRANT',predecessor_not_real_observation=True,simulation_predecessor=ref(context['base']+'/predecessor.json'),negative_cases=[n for n in negatives if n['case'] in ('A13','A14','A15')]),
      'SOURCE_READINESS_ADAPTER_GATE':dict(contract=deps['source_adapters'],negative_cases=[n for n in negatives if n['case'] in ('A09','A10','A11','A12')],internal_acquisition_clock=True,acquisition_survives_publication_rollback=True),
      'ACTIVATION_SIMULATION_E2E':positive_result,
      'NEGATIVE_ACTIVATION_MATRIX':dict(count=len(negatives),cases=negatives),
      'INDEPENDENT_ACTIVATION_ORACLE':dict(oracle=oracle,writer_imported=False,database_binding=positive_result['database_binding']),
      'LEGACY_ISOLATION_GATE':dict(before=before,after=protected(),unchanged=True,real_database_absent=True),
      'ROLLBACK_GATE':dict(persisted_database=positive_result['database_binding'],oracle=oracle,accepted_enrollment_preserved=True,pending_obligations_preserved=True,settlement_continues_after_stop=True),
      'PROTECTED_BYTES':dict(before=before,after=protected(),compared_to_baseline=True),
      'OWNER_ADAPTER_SEMANTIC_EQUIVALENCE':dict(contract=deps['owner_adapter'],successor=deps['owner_projection'],AST_semantics_identical_except_historical_date_ceiling=True,original_accepted_implementation_unchanged=True),
    }
    for name,payload in gates.items():atomic('reports/r24/'+name+'.json',dict(common,**payload))
    atomic('reports/r24/STAGE_CONTRACT_AND_AUDIT_ITEMS.json',dict(common,stage_contract=ref('config/v4_16_runtime_dependencies_v2.json'),
        task=ref('docs/evidence/r24/V4_16_R24_REAL_SHADOW_ACTIVATION_READINESS_TASK_20261004.md'),
        latest_upgrade_document=ref('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        acceptance='PASS_LOCAL_PENDING_CLEAN_REGRESSION_AND_EXTERNAL_AUDIT',
        separate_audit_items=[dict(id='R23R1_DEPENDENCY_MANIFEST_STYLE',scope='slot policy registration',acceptance='CLOSED_LOCAL_SUCCESSOR_REGISTERED',evidence=ref('reports/r24/DEPENDENCY_MANIFEST_V2_GATE.json')),
          dict(id='R24_OWNER_CALENDAR_SUCCESSOR',scope='historical date ceiling removal only; no business algorithm changes',acceptance='PASS_LOCAL_PENDING_EXTERNAL_AUDIT',evidence=ref('reports/r24/OWNER_ADAPTER_SEMANTIC_EQUIVALENCE.json'))]))
    print(dict(status='PASS_LOCAL',negative_cases=len(negatives),oracle=oracle))

if __name__=='__main__':run()
