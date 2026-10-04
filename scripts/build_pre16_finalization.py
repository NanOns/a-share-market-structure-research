"""Mechanical governance acceptance only; no business permission transition."""
from copy import deepcopy
from scripts.r22_io import *

def build(root=ROOT):
    old=read(OLD_HEAD,root);h=deepcopy(old)
    audit=ref(AUDIT,root)
    accepted=dict(contract_id='V4_PRE16_GOVERNANCE_ACCEPTED_HEAD_R1',version='1.0.0',status='EXTERNALLY_ACCEPTED_GOVERNANCE_ONLY',execution_baseline=BASE,audited_remote_head=BASE,tested_source='dabb5eb2fcdd4b52cfa4d9d684f9d9a9786c42bf',tested_tag='refs/tags/codex/pre16-gov-r1-1-tested-source-20261004-r1',external_decision='PASS_FINAL_CANONICAL_BLOCK_SCOPE_REPAIR',external_authority=audit,audited_head=ref(OLD_HEAD,root),audited_config=ref(OLD_CONFIG,root),candidate_seal=ref('reports/pre16_governance_r1_1/PRE16_GOV_R1_1_CANDIDATE_SEAL.json',root),closed_findings={'GOV_PRE16_01':'EXTERNALLY_ACCEPTED_CLOSED','GOV_PRE16_02':'EXTERNALLY_ACCEPTED_CLOSED'},production=False,shadow=False,focus=False,V4_16=False,grant='PRE16_GOVERNANCE_ACCEPTANCE_ONLY; R22 CONTRACT ENTRY SUBJECT TO INDEPENDENT FORMALIZATION GATE',Stage='V4_00_TO_V4_15_ACCEPTED',Data='2026-09-30')
    atomic(ACCEPT,accepted,root)
    e=h['entries']['GOV_PRE16_01'];e.update(current_state='EXTERNALLY_ACCEPTED_CLOSED',blocking_scope='NONE',blocks_v4_16_contract_entry=False,blocks_v4_16_runtime_activation=False,blocks_affected_capability_in_shadow=False,blocks_production_cutover_for_scope=False,blocks_engineering_stage=False,blocks_shadow_entry=False,blocks_production_cutover=False)
    e['external_acceptance']=ref(ACCEPT,root)
    h.update(contract_id='V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V2',version='2.0.0',execution_baseline=BASE,status='EXTERNALLY_ACCEPTED_FORMALIZED',supersedes_current_head=ref(OLD_HEAD,root),governance_findings=accepted['closed_findings'],external_acceptance=ref(ACCEPT,root),GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS=[],V4_16_entry='CONTRACT_ENTRY_ONLY_AFTER_FORMALIZATION_GATE; RUNTIME_NOT_AUTHORIZED',NEXT='R22_CONTRACT_FREEZE_ONLY_AFTER_PHASE0_PASS')
    atomic(HEAD,h,root)
    c=deepcopy(read(OLD_CONFIG,root));c.update(contract_id='V4_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_V2',version='2.0.0',execution_baseline=BASE,current_head=ref(HEAD,root),supersedes_current_config=ref(OLD_CONFIG,root),external_acceptance=ref(ACCEPT,root),historical_predecessor_semantics='V1 IS THE IMMUTABLE EXTERNALLY AUDITED R1.1 CANDIDATE; V2 IS THE SOLE FORMALIZED AUTHORITY FOR R22',declared_global_contract_entry_blockers=[])
    atomic(CONFIG,c,root)
    atomic('reports/pre16_finalization/EXTERNAL_AUDIT_BINDING.json',dict(status='EXACT_EXTERNAL_AUTHORITY_BOUND',accepted_head=ref(ACCEPT,root),external_authority=audit),root)
    atomic('reports/pre16_finalization/ACCEPTANCE_DISPOSITION.json',dict(governance_findings=accepted['closed_findings'],capability_only_blocks=['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME'],business_grants_changed=False,GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS=[]),root)
if __name__=='__main__':build()
