"""Freeze the narrow projection amendment before runtime repair/replay."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_13_io import atomic,canonical,file_ref
OUT='reports/v4_13_runtime_r16r1/'

def prepare():
    old=json.loads((ROOT/'config/v4_13_projection_v1_1.json').read_bytes())
    mapping={}
    for name,path in old['source_field_paths'].items():
        metadata={
            'active_anchor_id':'active_selection',
            'anchor_view_asof_t':'selected_anchor_state.output_envelope.anchor_view_asof_t',
            'basic_breakout_state':None,
            'basic_pullback_state':'selected_anchor_state.state_observations.pullback',
            'basic_recovery_state':'selected_anchor_state.state_observations.recovery',
            'support_state':'selected_anchor_state.state_observations.support',
            'acceptance_state':'selected_anchor_state.state_observations.acceptance',
            'retest_count':'selected_anchor_state.facts.prior_test_count',
            'structure_health':'selected_anchor_state.output_envelope.structure_health',
            'structure_events':None,
        }[name]
        mapping[name]=dict(value_source=path,quality_source=metadata+'.quality' if metadata else None,
            reason_source=metadata+'.reason' if metadata else None,
            value_mode='ENVELOPE_VALUE_OR_EXACT_OBJECT' if name in ['anchor_view_asof_t','structure_health'] else 'EXACT',
            producer_identity_source='authorized_manifest.contract_id + runtime_row.identity + exact_source_paths',
            source_ref_identity='authorized_manifest + authorized_manifest.artifacts.runtime_security.jsonl.gz',
            missing_metadata_quality='UNKNOWN',missing_metadata_reason='UNKNOWN_ACCEPTED_SOURCE_METADATA_UNAVAILABLE')
    mapping['basic_breakout_state'].update(quality_source='breakout_projection_quality',reason_source='breakout_projection_reason')
    # Events are a plain list with no collection quality/reason in the owner schema.
    # Health is a plain scalar in some owner publications. Preserve values, fail closed.
    amendment=dict(old,version='1.2.0',supersedes=file_ref(ROOT,'config/v4_13_projection_v1_1.json'),
        reason='R16R1_EXACT_PROJECTION_PROVENANCE_ONLY',projection_mapping=mapping,
        selected_state_lookup='EXACT_ACTIVE_SELECTION_ID_LOOKUP_NO_RESELECTION',
        absent_metadata='PRESERVE_VALUE_UNKNOWN_WITH_EXPLICIT_REASON_NO_VALUE_INFERENCE',
        source_metadata_preservation='COPY_PRESENT_PRODUCER_AND_SOURCE_IDENTITIES_WITHOUT_REPLACEMENT')
    from scripts.validate_v4_13_r1_1 import validate_lineage
    validate_lineage(amendment)
    binding=atomic(ROOT,'config/v4_13_projection_v1_2.json',canonical(amendment))
    atomic(ROOT,OUT+'structure_projection_mapping.json',canonical(mapping))
    atomic(ROOT,OUT+'contract_amendment_decision.json',canonical(dict(CONTRACT_AMENDMENT='REQUIRED_MINIMAL_V1_2',
        evidence=file_ref(ROOT,'config/v4_13_projection_v1_1.json'),
        reason='v1.1 specifies value paths only; machine quality/reason/producer/source paths are not uniquely specified',
        amendment=binding,same_contract_family_lineage='PASS',business_thresholds='UNCHANGED',owner_semantics='UNCHANGED')))
    stage=json.loads((ROOT/'reports/v4_13_runtime_r16/STAGE_CONTRACT.json').read_bytes())
    stage.update(baseline='92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff',order=['A_MAPPING','B_RUNTIME','C_PROVENANCE','D_ORACLE','E_BOUNDARY','F_REAL','G_CLEAN','COMMIT_PUSH','STOP'],
        contract_amendment='REQUIRED_MINIMAL_V1_2',next='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    stage['contracts']=[binding if r['path']=='config/v4_13_projection_v1_1.json' else r for r in stage['contracts']]
    stage['authority']=file_ref(ROOT,'docs/evidence/next_round_r16r1/V4_NEXT_ROUND_EXECUTION_MASTER_R16R1_20261003.md')
    atomic(ROOT,OUT+'STAGE_CONTRACT.json',canonical(stage))

if __name__=='__main__':prepare()
