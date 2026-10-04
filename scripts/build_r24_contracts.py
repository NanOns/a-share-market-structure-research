"""Build only the disabled R24 successor authority; never acquire live inputs."""
import subprocess
from scripts.r24_io import ROOT, BASE, read, ref, atomic

TASKS = [
 'V4_NEXT_ROUND_EXECUTION_MASTER_R24_20261004.md',
 'V4_16_R24_REAL_SHADOW_ACTIVATION_READINESS_TASK_20261004.md',
 'V4_R23R1_OBSERVATION_SLOT_RUNTIME_COMPLETENESS_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md',
]

def build():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    source = __import__('pathlib').Path('D:/Users/lps/Desktop/阶段任务')
    for name in TASKS:
        atomic('docs/evidence/r24/'+name,(source/name).read_bytes(),raw=True)
    audit = ref('docs/evidence/r24/'+TASKS[2])
    head = dict(contract_id='V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1',version='1.0.0',
                scope='ENGINEERING_RUNTIME_ONLY',real_activation='REAL_ACTIVATION_NOT_GRANTED',
                external_r23r1_audit=audit,
                external_r23_audit=ref('docs/evidence/r23r1/V4_R23_REALTIME_SHADOW_RUNTIME_ENGINEERING_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'),
                tested_source='ee12bb7d0f1c89fe8f32aa55aaa385bcb5438ff4',
                tested_tag='refs/tags/codex/r23r1-slot-tested-source-20261004-r1',
                bindings=[ref(p) for p in ['data/v4/V4_16_CLOCK_GOVERNANCE_ACCEPTED_HEAD_R1.json',
                   'config/v4_16_r23r1_slot_runtime_policy_v1.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json',
                   'data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_15_ACCEPTED_HEAD.json']])
    atomic('data/v4/V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1.json',head)
    contract = dict(contract_id='V4_16_REAL_STORAGE_V1',version='1.0.0',
        real_root='data/v4/shadow_real_v1',simulation_root='reports/r24/activation_simulation',
        real_origin='PIT_OBSERVED',simulation_origin='ACTIVATION_SIMULATION',
        simulation_evidence='NOT_REAL_EVIDENCE',namespace='SHADOW_V4',execution_mode='SHADOW',
        engineering_db_forbidden=True,append_only=True,head_CAS=True,
        original_event_unique=True,correction_policy='PRESERVE_T0_CONTROLS_BENCHMARK_FIRST_OBSERVED')
    atomic('config/v4_16_real_storage_contract_v1.json',contract)
    atomic('config/v4_16_real_owner_adapter_v1.json',dict(
        contract_id='V4_16_REAL_OWNER_ADAPTER_V1',version='1.0.0',
        accepted_predecessor=ref('src/workbench_analysis/v4_15_radar_cohort.py'),
        successor=ref('scripts/v4_16_real_owner_projection_v1.py'),
        sole_projection_change='REMOVE_HISTORICAL_DEMONSTRATION_DATE_CEILING_KEEP_ACCEPTED_CALENDAR_MEMBERSHIP',
        unchanged_semantics='EVENT_IDENTITIES_ELIGIBILITY_REVISION_EXPLANATIONS',
        admission_policy='EXACT_ACCEPTED_REALTIME_BYTES_INTERNAL_TIMESTAMPS_COMPLETE_SET_ON_TIME_SLOT',
        real_cohort_namespace='FIRST_OBSERVED',real_evidence_class='PIT_OBSERVED',
        original_enrollment='UNIQUE_LOGICAL_EVENT_FIRST_COMPLIANT_PUBLICATION',
        correction='APPEND_OBSERVATION_PRESERVE_ENROLLMENT_T0_CONTROLS_BENCHMARK',
        settlement='UNCHANGED_ACCEPTED_V4_15_SETTLEMENT',no_business_threshold_changes=True))
    atomic('config/v4_16_source_readiness_adapters_v1.json',dict(
        contract_id='V4_16_SOURCE_READINESS_ADAPTERS_V1',version='1.0.0',
        mandatory_families=['OWNER_OUTPUT','T0_SNAPSHOT'],
        adapter_id='ACCEPTED_LOCAL_EXACT_BYTES_V1',receipt_kind='ACCEPTED_LOCAL_OBSERVATION_ACQUISITION',
        first_observed_policy='INTERNAL_CLOCK_AT_FIRST_EXACT_READ_NO_CALLER_TIMESTAMP',
        accepted_authority_required=True,raw_provider_fallback=False,
        owner_adapter='V4_15_EXACT_OWNER_PROJECTION_SUCCESSOR_ENROLLMENT_GATE_V1',
        reconstruction_never_upgrades_PIT=True))
    atomic('config/v4_16_real_initialization_boundary_v1.json',dict(
        contract_id='V4_16_REAL_INITIALIZATION_BOUNDARY_V1',version='1.0.0',
        first_trade_date='EXACT_FUTURE_ACTIVATION_GRANT_FIELD_REQUIRED',
        predecessor='EXACT_ACCEPTED_GRANT_BINDING_REQUIRED',
        predecessor_evidence_classes=['RECONSTRUCTED_ASOF'],
        initialization_fields=['model_contract_id','parameter_set_id','state_lineage_id','trade_date','owner_state'],
        unknown_fields=['FIRST_OBSERVED','prior_real_observation_id','prior_real_enrollment_id'],
        counts_as_prior_real_observation=False,subsequent_prior='IMMEDIATELY_PREVIOUS_ACCEPTED_SHADOW_MARKET_SESSION',
        engineering_seed_forbidden=True))
    authority = dict(contract_id='V4_16_RUNTIME_ACTIVATION_AUTHORITY_V2',version='2.0.0',
        authority_id='R24_DISABLED_CANDIDATE',runtime_authorized=False,real_shadow_authorized=False,
        production=False,shadow=False,focus=False,V4_16=False,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,
        status='ACTIVATION_CAPABLE_DISABLED_CANDIDATE',environment_class='REAL',
        grant=None,external_acceptance=None,environment_flags_grant=False,
        required_grant_fields=['authority_id','effective_trade_date','effective_from','model_contract_id',
          'parameter_set_id','state_lineage_id','capability_scope','clock','slot','runtime_dependency_contract_id',
          'dependency_set_digest','storage','storage_identity','source_adapters','source_authority','rollback_identity',
          'expected_prior_activation_head','initialization_boundary','predecessor','first_trade_date'],
        allowed_capabilities=['PURE_CORE_STOCK'],blocked_capabilities=read('config/v4_16_runtime_dependencies_v1.json')['blocked_capabilities'])
    atomic('config/v4_16_runtime_activation_authority_v2.json',authority)
    deps = read('config/v4_16_runtime_dependencies_v1.json')
    deps.update(contract_id='V4_16_RUNTIME_DEPENDENCIES_V2',version='2.0.0',execution_baseline=BASE)
    deps['bindings']=[b for b in deps['bindings'] if b['path'] not in
                      ['config/v4_16_runtime_activation_authority_v1.json','migrations/v4_16_r23_shadow_v1.sql']]
    paths = dict(activation='config/v4_16_runtime_activation_authority_v2.json',
        engineering_acceptance='data/v4/V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1.json',
        slot_runtime_policy='config/v4_16_r23r1_slot_runtime_policy_v1.json',
        storage='config/v4_16_real_storage_contract_v1.json',migration='migrations/v4_16_r24_real_shadow_v1.sql',
        source_adapters='config/v4_16_source_readiness_adapters_v1.json',
        initialization_boundary='config/v4_16_real_initialization_boundary_v1.json')
    paths['owner_adapter']='config/v4_16_real_owner_adapter_v1.json'
    paths['owner_projection']='scripts/v4_16_real_owner_projection_v1.py'
    paths['runtime_writer']='scripts/v4_16_real_shadow_runtime.py'
    for key,path in paths.items():
        deps[key]=ref(path)
        deps['bindings'].append(deps[key])
    deps.pop('fixture_registry')
    atomic('config/v4_16_runtime_dependencies_v2.json',deps)
    atomic('reports/r24/STAGE_CONTRACT_AND_AUDIT_ITEMS.json',dict(baseline=BASE,
        authority=[ref('docs/evidence/r24/'+n) for n in TASKS],
        upgrade_document=ref('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        contract=ref('config/v4_16_runtime_dependencies_v2.json'),acceptance='PENDING_EXECUTION',
        separate_audit_items=[dict(id='R23R1_DEPENDENCY_MANIFEST_STYLE',scope='central registration of slot runtime policy',
          external_classification='P2_NONBLOCKING',acceptance='SUCCESSOR_MANIFEST_REGISTERED',evidence=deps['slot_runtime_policy'])],
        NEXT='R24_ISOLATED_VALIDATION_THEN_EXTERNAL_AUDIT'))

if __name__=='__main__':
    build()
