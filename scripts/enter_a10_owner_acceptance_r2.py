"""Freeze the A10 R2 entry and empty owner registry; no owner promotion."""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.formalize_source_authority_registry_r3 import protected_bindings,PERMISSIONS
from workbench_analysis.source_authority_accepted_owners_v1 import HEAD_PATH,REGISTRY_PATH,HEAD_CONTRACT,REGISTRY_CONTRACT

TASK='V4_A10_R2_OWNER_ACCEPTANCE_BINDING_HARDENING_TASK_20261001.md'

def main():
    taskpath='docs/evidence/source_authority/'+TASK
    atomic_bytes(ROOT/taskpath,(Path('D:/Users/lps/Desktop/阶段任务')/TASK).read_bytes())
    r1=json.loads((ROOT/'config/source_authority_governance_r1.json').read_text(encoding='utf8'))
    contract=copy.deepcopy(r1)
    contract.update(contract_id='V4_SOURCE_AUTHORITY_GOVERNANCE_R2',version='2.0.0',
        supersedes=bind('config/source_authority_governance_r1.json'),task=bind(taskpath),
        runtime=bind('src/workbench_analysis/source_authority_governance_r1.py'),
        owner_runtime=bind('src/workbench_analysis/source_authority_accepted_owners_v1.py'),
        required_owner_registry_contract=REGISTRY_CONTRACT,formal_use_defaults_to_true=True,
        failure_taxonomy=[*r1['failure_taxonomy'],'AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED'],
        production_permission=False,external_acceptance=None,
        supplemental_promotion_requires=['New versioned owner contract','Independent external acceptance',
            'Exact accepted owner registry entry','New accepted role binding'])
    pending=[]
    for rule in contract['field_rules']:
        rule['role_binding_id']='SOURCE_AUTHORITY_ROLE_R2:'+rule['field_id']
        if rule['role'] in ('CORE_AUTHORITY','FIELD_AUTHORITY'):
            rule.update(authority_status='PENDING_EXTERNAL_ACCEPTANCE',enabled_for_formal_consumer=False)
            pending.append(dict(owner_contract_id=rule['owner_contract_id'],field_id=rule['field_id'],
                authority_status='PENDING_EXTERNAL_ACCEPTANCE',formal_consumer_authorization=False,
                reason='NO_OWNER_REGISTRATION_AUTHORIZED_BY_THIS_TASK'))
        if rule['field_id'] in ('TRADING_STATUS','ISST'):
            rule['allowed_consumers'].append('DM01_FINAL_ALL_NINE')
    atomic_json(ROOT/'config/source_authority_governance_r2.json',contract)
    assert not (ROOT/REGISTRY_PATH).exists() and not (ROOT/HEAD_PATH).exists()
    atomic_json(ROOT/REGISTRY_PATH,dict(contract_id=REGISTRY_CONTRACT,version=1,owners=[],pending_owners=pending,
        scope='OWNER_REGISTRATION_INFRASTRUCTURE_ONLY_NO_REAL_OWNER_PROMOTION',external_acceptance=None,
        permissions=PERMISSIONS,next_registration_gate='A10-R2_AND_A12-R2_EXTERNAL_ACCEPTANCE_AND_NEW_AUTHORIZED_TASK'))
    binding=bind(REGISTRY_PATH);binding['version']=1
    atomic_json(ROOT/HEAD_PATH,dict(contract_id=HEAD_CONTRACT,registry={k:binding[k] for k in ('path','sha256','version')},
        scope='INDEPENDENT_SOURCE_AUTHORITY_METADATA_NAMESPACE',business_head_promotion=False,permissions=PERMISSIONS))
    protected=protected_bindings()
    protected.extend(bind(p) for p in [
        'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json',
        'config/V4_01_HISTORICAL_IDENTITY_AUTHORITY_AMENDMENT_R1.json',
        'reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json',
        'reports/audits/V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json',
        'config/dm01_incremental_builders_contract_r1.json',
        'src/workbench_analysis/dm01_incremental_component_builders.py',
        'src/workbench_analysis/dm01_accepted_builder_registry.py'])
    atomic_json(ROOT/'reports/audits/A10_R2_STAGE_ENTRY_R1.json',dict(
        contract_id='WP-A10-R2-OWNER-ACCEPTANCE-BINDING',baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        task=bind(taskpath),contract=bind('config/source_authority_governance_r2.json'),
        registry=bind(REGISTRY_PATH),global_authority_head=bind(HEAD_PATH),protected_bindings=protected,
        phase0_evidence=bind('reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'),
        phase0_status='FULL_PASS',permissions=PERMISSIONS,
        next_stage='Independent A10 R2 reaudit; A12 R2 not authorized by this task; DM01 final remains blocked'))
    print('A10 R2 entry frozen; zero accepted owner registrations')

if __name__=='__main__':main()
