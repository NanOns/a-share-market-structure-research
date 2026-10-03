"""Externally authorized engineering-only promotion of the exact audited r6."""
import json,subprocess
from scripts.prepare_r17_governance import ROOT,bind,put
from src.workbench_analysis.v4_13_io import atomic,canonical,digest
BASE='f12315bf8e3142aa44e9068c5895004c35c4e23c'
TESTED='d370788688c7e1be0fe2e3c9b0b160d93374b4ee'
HEAD='data/v4/V4_13_ACCEPTED_HEAD.json'
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
MANIFEST='reports/v4_13_runtime_r16/real/2026-09-30/r6/manifest.json'
MANIFEST_SHA='a02e7918826627c2b496d89e546d3f5a408e4c68a1a89bc93946e152e7ca42ec'
AUDIT='docs/evidence/r17/V4_R16R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md'
ENTRY='config/v4_13_accepted_entry_contract_v1.json'
CAPABILITIES=dict(V4_13_PROFILE_ADVANCED_PROJECTION='ENGINEERING_ACCEPTED',V4_13_CURRENT_MEMBERSHIP_RELATION='ENGINEERING_ACCEPTED_PIT_20260930',V4_13_TARGET_EXCLUDED_LOO_CORE='ENGINEERING_ACCEPTED_CAPABILITY_SCOPED',V4_13_STRUCTURE_READ_ONLY_PROJECTION='ENGINEERING_ACCEPTED',V4_13_COMPONENT_PROVENANCE='ENGINEERING_ACCEPTED',V4_13_REVISION_PUBLICATION='ENGINEERING_ACCEPTED',V4_13_REAL_SIGNAL_CAPABILITY='DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY',algorithmic_support_sector='UNKNOWN_REAL_ACCEPTED_CAPABILITY',relative_sector_state='UNKNOWN_REAL_ACCEPTED_CAPABILITY',historical_LOO='NOT_VERIFIABLE',legacy_B2='NOT_IMPLEMENTED')
def promote():
    from scripts.validate_r17b_promotion import validate
    if (ROOT/HEAD).exists():
        result=validate();assert result['status']=='PASS';return result
    gate=json.loads((ROOT/'reports/r17a/completion_gate.json').read_bytes())
    assert gate['R17A_CROSS_STAGE_GOVERNANCE_REPAIR']=='PASS'
    clean=json.loads((ROOT/gate['clean_detached']['path']).read_bytes());assert clean['status']=='PASS' and clean['git_clean_before'] and clean['git_clean_after']
    assert bind(MANIFEST)['sha256']==MANIFEST_SHA
    manifest=json.loads((ROOT/MANIFEST).read_bytes());parent=bind(STAGE);g=json.loads((ROOT/STAGE).read_bytes())
    assert g['accepted_stage_range']=='V4_00_TO_V4_12_ACCEPTED' and parent['sha256']=='b0e1c2402efdd71d706a87f45280206a87fbe9e637a4168255b7ff4c036520f7'
    archive='reports/r17b/PARENT_STAGE_HEAD.json';atomic(ROOT,archive,(ROOT/STAGE).read_bytes(),append_only=True)
    put(ENTRY,dict(contract_id='V4_13_ACCEPTED_CONTRACT_PACKAGE_ENTRY_V1',version='1.0.0',authority_namespace=HEAD,authority_resolution='EXACT_CURRENT_STAGE_HEAD_BINDING_THEN_ACCEPTED_HEAD_CONTRACT_REFS',candidate=bind(MANIFEST),contract_refs=manifest['contract_refs'],contract_digest=manifest['contract_digest'],amendment_receipt_presence_is_authority=False,time_role='ACCEPTED_PUBLICATION_READ_ONLY',unknown_semantics='PRESERVE_COMPONENT_UNKNOWN_AND_UPSTREAM_DEGRADATION',required_history='NO_HISTORICAL_LOO_ACCEPTANCE',negative_cases=['wrong_head','wrong_candidate','wrong_package','informal_receipt_substitution'],acceptance_criteria='EXACT_EXTERNALLY_AUTHORIZED_ENGINEERING_HEAD_ONLY'))
    contract=dict(contract_id='R17B_V4_13_ENGINEERING_PROMOTION_V1',baseline=BASE,task=bind('docs/evidence/r17/V4_R17B_V4_13_ACCEPTED_HEAD_PROMOTION_TASK_20261003.md'),master=bind('docs/evidence/r17/V4_NEXT_ROUND_EXECUTION_MASTER_R17_20261003.md'),external_audit=bind(AUDIT),entry_gate=bind('reports/r17a/completion_gate.json'),parent_stage=parent,protected={p:bind(p) for p in ['AGENTS.md','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json']},scope='ENGINEERING_ACCEPTANCE_ONLY',next='R17C_AFTER_PROMOTION_PASS')
    put('reports/r17b/stage_contract.json',contract)
    h=dict(contract_id='V4_13_ACCEPTED_HEAD_V1',version='1.0.0',stage='V4-13',status='ENGINEERING_PASS_CAPABILITY_SCOPED',external_acceptance='EXTERNALLY_ACCEPTED_ENGINEERING_SCOPE',external_acceptance_decision='R16R1_EXTERNAL_AUDIT_PASS_SCOPED_ENGINEERING_AFTER_R17A_PASS',external_authority=bind(AUDIT),audited_sealed_head=BASE,tested_runtime_source=TESTED,r17a_gate=bind('reports/r17a/completion_gate.json'),candidate=bind(MANIFEST),artifact_refs=manifest['artifacts'],contract_refs=manifest['contract_refs'],contract_digest=manifest['contract_digest'],formal_entry_contract=bind(ENTRY),runtime_source_bindings=manifest['runtime_source_refs'],input_accepted_head_refs=manifest['input_accepted_head_refs'],global_head_parent=parent,global_head_parent_archive=bind(archive),protected_head_bindings=contract['protected'],capabilities=CAPABILITIES,production=False,shadow=False,focus=False,global_mandatory_adoption=False,ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED',knowledge_lineage=manifest['knowledge_lineage'],AS_RECORDED=False,accepted_trade_date='2026-09-30',accepted_at='2026-10-03',permission_scope='ENGINEERING_ONLY_NO_V4_14_REPLAY_RUNTIME_AUTHORIZATION',next='V4_14_CONTRACT_FREEZE_ENTRY_ONLY')
    atomic(ROOT,HEAD,canonical(h)+b'\n',append_only=True)
    g.update(accepted_stage_range='V4_00_TO_V4_13_ACCEPTED',v4_13_binding=bind(HEAD),v4_13_external_acceptance=h['external_acceptance_decision'],v4_13_status=h['status'],v4_13_capabilities=CAPABILITIES,v4_14_entry='CONTRACT_FREEZE_ONLY_NOT_REPLAY_PASS',v4_13_promotion_parent_archive=bind(archive))
    atomic(ROOT,STAGE,canonical(g)+b'\n')
    result=validate();put('reports/r17b/promotion_gate.json',result);assert result['status']=='PASS';return result
if __name__=='__main__':print(json.dumps(promote()))
