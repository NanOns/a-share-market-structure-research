"""Versioned disabled successor contracts and explicit immutable algorithm pins."""
from scripts.r24r1_io import ROOT, read, ref, atomic

def prepare():
    contract=dict(contract_id='V4_16_GO_FORWARD_INPUT_AUTHORITY_V1',version='1.0.0',
        authority_layers=['IMMUTABLE_ALGORITHM_STAGE','EXACT_ACCEPTED_SESSION_INPUT'],
        frozen_data_head_role='HISTORICAL_ACCEPTANCE_ONLY',implicit_resolution='FORBIDDEN',
        mandatory_pure_core_sources=['TDX_RAW_DAILY','ADJUSTED_DAILY','OWNER_OUTPUT','T0_SNAPSHOT'],
        membership_required_capabilities=['SECTOR_ENHANCED'],
        model_identity=dict(model_contract_id='RESEARCH_STATE_V1',parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1'),
        immutable_algorithm_bindings={name:ref(path) for name,path in dict(
            stage='data/v4/V4_STAGE_ACCEPTED_HEAD.json',v4_15='data/v4/V4_15_ACCEPTED_HEAD.json',
            model='config/v4_10_research_state_contract_r1_2.json',parameters='config/v4_10_parameter_set_r1_2.json',
            cohort='config/v4_15_cohort_contract_v1.json').items()},
        required_fields=['daily_input_id','revision','target_trade_date','accepted_at','calendar','previous_trade_date',
            'target_session_confirmed','identity','membership','sources','day_package','snapshot_identity',
            'max_source_trade_date','quality_capability_matrix','source_manifest_digest','daily_input_digest',
            'model_contract_id','parameter_set_id','immutable_algorithm_bindings','environment_class'])
    forward=atomic('config/v4_16_go_forward_input_authority_v1.json',contract)
    admission=atomic('config/v4_16_realtime_admission_contract_v1.json',dict(
        contract_id='V4_16_REALTIME_ADMISSION_V1',version='1.0.0',
        candidate_role='CANDIDATE_ENROLLMENT_TEMPLATE',candidate_acceptance='NOT_COHORT_ACCEPTANCE',
        admitted_namespace='FIRST_OBSERVED',storage_namespace='SHADOW_V4',
        cohort_contract=contract['immutable_algorithm_bindings']['cohort'],
        required_evidence=['accepted_on_time_slot','internal_source_receipts','exact_owner_logical_event','daily_input_authority','atomic_publication'],
        reconstructed_annotation_upgrade=False))
    storage=read('config/v4_16_real_storage_contract_v1.json')
    storage.update(contract_id='V4_16_GO_FORWARD_STORAGE_V1',simulation_root='reports/r24r1/activation_simulation')
    storage_binding=atomic('config/v4_16_go_forward_storage_v1.json',storage)
    authority=read('config/v4_16_runtime_activation_authority_v2.json')
    authority.update(authority_id='V4_16_DISABLED_R24R1_V1',contract_id='V4_16_RUNTIME_ACTIVATION_AUTHORITY_V3',
        runtime_authorized=False,real_shadow_authorized=False,grant=None,external_acceptance=None)
    authority['required_grant_fields']+=['daily_input_authority','daily_input_digest','target_trade_date','daily_input_boundary','minimum_daily_input_revision']
    activation=atomic('config/v4_16_runtime_activation_authority_v3.json',authority)
    deps=read('config/v4_16_runtime_dependencies_v2.json')
    old_activation=deps['activation']; old_storage=deps['storage']; old_writer=deps['runtime_writer']
    deps.update(contract_id='V4_16_RUNTIME_DEPENDENCIES_V3',version='3.0.0',execution_baseline='0c9f59fbe723fe0fb0e9d1a6750c339894bc7a5b',
        activation=activation,storage=storage_binding,go_forward_input=forward,realtime_admission=admission,
        runtime_writer=ref('scripts/v4_16_go_forward_shadow_runtime.py'),
        input_authority_writer=ref('src/workbench_analysis/v4_16_go_forward_authority.py'))
    deps['bindings']=[b for b in deps['bindings'] if b not in [old_activation,old_storage,old_writer]]
    deps['bindings'] += [activation,storage_binding,forward,admission,deps['runtime_writer'],deps['input_authority_writer']]
    atomic('config/v4_16_runtime_dependencies_v3.json',deps)
    return deps

if __name__=='__main__':prepare()
