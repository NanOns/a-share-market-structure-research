"""Scoped additive governance propagation. Never rewrites V3/V5 or business logic."""
import copy,json
from scripts.full_chain_repair_io import ROOT,write,binding
from scripts.v4_16_capability_resolution import FIELDS
from scripts.v4_16_capability_resolution_v2 import resolve

PREFIX='reports/a08_current_runtime_propagation_20261006/'
DOCS='docs/evidence/a08_current_runtime_propagation_20261006/'
HEAD='data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json'
AUTH='config/v4_cross_stage_current_audit_authority_v4.json'
CAP='config/v4_16_runtime_capability_resolution_v2.json'
DEPS='config/v4_16_runtime_dependencies_v6.json'

def load(p):return json.loads((ROOT/p).read_bytes())

def build():
    entry=load(PREFIX+'ENTRY_BASELINE.json')
    for ref in entry['frozen']+entry['protected']:assert binding(ref['path'])==ref,ref['path']
    a08=binding(DOCS+'V4_A08_CURRENT_RUNTIME_INDEPENDENT_EXTERNAL_REAUDIT_R1_20261006.md')
    p002=binding(DOCS+'V4_FULL_CHAIN_R1R1_P0_02_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md')
    assert 'PASS_CURRENT_RUNTIME_ENGINEERING_SHADOW_DEPENDENCY_SCOPE' in (ROOT/a08['path']).read_text(encoding='utf8')
    assert 'P0_02_R1R1_FINAL_EXTERNAL_AUDIT = PASS' in (ROOT/p002['path']).read_text(encoding='utf8')
    assert binding('src/v4/stock_prewatch.py')['sha256']=='a57a4413b56cd81f43a06611f4dec328ef6ac35486f4a4b56e5b5938e2db60ce'
    old_head=load('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json');head=copy.deepcopy(old_head)
    head.update(contract_id='V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4',version='4.0.0',
        supersedes_current_head=binding('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json'),
        execution_baseline=entry['baseline_commit'],status='GOVERNANCE_PROPAGATION_CANDIDATE',
        normalization_status='A08_CURRENT_RUNTIME_SCOPED_EXTERNAL_PASS_PROPAGATED',a08_external_acceptance=a08)
    head['pre16_external_acceptance']=head['external_acceptance'];head['external_acceptance']=a08
    head['descriptive_normalization_predecessor']=binding('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json')
    issue=head['entries']['A08_CURRENT_RUNTIME']
    issue.update(current_state='ACCEPTED_SCOPED',blocks_affected_capability_in_shadow=False,blocks_shadow_entry=False)
    issue['current_authority']['current_runtime_external_acceptance']=a08
    issue['evidence_bindings'].append(a08)
    issue['current_runtime_acceptance_scope']='ENGINEERING_SHADOW_DEPENDENCY_ONLY; NO_RUNTIME_OR_PRODUCTION_PERMISSION'
    head_ref=write(HEAD,head)
    auth=load('config/v4_cross_stage_current_audit_authority_v3.json')
    auth.update(contract_id='V4_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_V4',version='4.0.0',current_head=head_ref,
        predecessor=binding('config/v4_cross_stage_current_audit_authority_v3.json'),a08_external_acceptance=a08,
        p0_02_external_acceptance=p002,execution_baseline=entry['baseline_commit'],normalization_status='GOVERNANCE_PROPAGATION_CANDIDATE',
        historical_predecessor_semantics='V1/V2/V3 IMMUTABLE; V4 PROPAGATES ONLY A08 CURRENT RUNTIME SCOPED ACCEPTANCE')
    auth['blocking_schema']['runtime_activation_dependency']='A08 current runtime dependency externally accepted; A04 capability blockers remain. No runtime permission.'
    auth['pre16_external_acceptance']=auth['external_acceptance'];auth['external_acceptance']=a08
    auth['supersedes_current_config']=auth['predecessor']
    auth_ref=write(AUTH,auth)
    cap=load('config/v4_16_runtime_capability_resolution_v1.json')
    cap.update(contract_id='V4_16_RUNTIME_CAPABILITY_RESOLUTION_V2',version='2.0.0',
        predecessor=binding('config/v4_16_runtime_capability_resolution_v1.json'),current_audit_head=head_ref,
        current_audit_authority=auth_ref,external_acceptance_bindings=[a08,p002],permission_granted=False)
    cap['current_producer_bindings']=[binding(p) for p in ('src/v4/stock_prewatch.py','reports/v4_09/V4_09_R1_1_REPAIR_CONTRACT_FREEZE.json','config/v4_09_priority_provenance_contract_r1_1.json','config/v4_09_priority_producer_vectors_r1_1.json')]
    ids=sorted(k for k,v in head['entries'].items() if not v.get('alias_of') and (v.get('blocks_affected_capability_in_shadow') or v.get('blocks_v4_16_runtime_activation')))
    cap['blocked_issue_ids']=ids
    cap['current_audit_issue_resolution']={k:{f:head['entries'][k].get(f,False) for f in FIELDS} for k in ids}
    cap['effective_blocked_runtime_capabilities']=resolve(cap,head,['PURE_CORE_STOCK'])['effective_blocked_runtime_capabilities']
    cap_ref=write(CAP,cap)
    activation=load('config/v4_16_runtime_activation_authority_v4.json')
    activation.update(contract_id='V4_16_RUNTIME_ACTIVATION_AUTHORITY_V5',authority_id='V4_16_DISABLED_V6_A08_SCOPE_V1',
        predecessor=binding('config/v4_16_runtime_activation_authority_v4.json'),capability_resolution=cap_ref,blocked_issue_ids=ids)
    activation_ref=write('config/v4_16_runtime_activation_authority_v5.json',activation)
    packet=load('config/v4_16_r25_packet_preflight_v3.json')
    packet.update(contract_id='V4_16_R25_PACKET_PREFLIGHT_V4',predecessor=binding('config/v4_16_r25_packet_preflight_v3.json'),
        capability_resolution=cap_ref,blocked_issue_ids=ids,runtime_dependency_contract_id='V4_16_RUNTIME_DEPENDENCIES_V6',
        builder=binding('scripts/build_r25_packet_r4r4.py'),validator=binding('scripts/validate_r25_preflight_v6.py'))
    packet_ref=write('config/v4_16_r25_packet_preflight_v4.json',packet)
    worker=load('config/v4_16_settlement_worker_contract_v2.json')
    worker.update(contract_id='V4_16_SETTLEMENT_WORKER_RUNTIME_V3',version='3.0.0',
        predecessor=binding('config/v4_16_settlement_worker_contract_v2.json'),external_engineering_acceptance=p002,
        dependency_contract_id='V4_16_RUNTIME_DEPENDENCIES_V6',current_audit_head=head_ref,
        entrypoint=binding('scripts/run_v4_16_settlement_v3.py'),
        historical_v5_entrypoint=binding('scripts/run_v4_16_settlement_v2.py'),historical_v5_runtime=binding('scripts/v4_16_go_forward_shadow_runtime_r4r3.py'),
        delivery_implementation=binding('scripts/v4_16_settlement_worker_v2.py'),
        compatibility='EXPLICIT_V5_OR_V6_GENERATION; NEVER_REBIND_ACCEPTED_OBLIGATIONS')
    worker_ref=write('config/v4_16_settlement_worker_contract_v3.json',worker)
    old=load('config/v4_16_runtime_dependencies_v5.json');deps=copy.deepcopy(old)
    changes=dict(current_audit_head=head_ref,capability_resolution=cap_ref,activation=activation_ref,
        packet_contract=packet_ref,settlement_worker=worker_ref,runtime_writer=binding('scripts/v4_16_go_forward_shadow_runtime_r4r4.py'))
    mapping={old[k]['path']:v for k,v in changes.items()}
    deps['bindings']=[mapping.get(b['path'],b) for b in old['bindings']]
    additions=[auth_ref,a08,p002,binding('config/v4_16_runtime_dependencies_v5.json'),binding('config/v4_16_settlement_worker_contract_v2.json'),
        binding('scripts/v4_16_capability_resolution_v2.py'),binding('scripts/v4_16_shadow_runtime_v6.py'),
        binding('scripts/run_v4_16_settlement_v3.py'),binding('scripts/build_r25_packet_r4r4.py'),binding('scripts/validate_r25_preflight_v6.py'),
        binding('docs/evidence/r25/V4_R24R1_GO_FORWARD_INPUT_AUTHORITY_COHORT_IDENTITY_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md')]
    additions+=cap['current_producer_bindings']+[auth['stage_current_authority_unchanged']]
    for ref in additions:
        if ref not in deps['bindings']:deps['bindings'].append(ref)
    deps.update(changes,contract_id='V4_16_RUNTIME_DEPENDENCIES_V6',version='6.0.0',execution_baseline=entry['baseline_commit'],
        predecessor=binding('config/v4_16_runtime_dependencies_v5.json'),current_audit_authority=auth_ref,blocked_issue_ids=ids,
        p0_02_external_acceptance=p002,historical_v5_settlement_runtime=worker['historical_v5_runtime'],runtime_authorized=False)
    deps_ref=write(DEPS,deps)
    write('config/v4_16_current_runtime_entrypoints_v1.json',dict(contract_id='V4_16_CURRENT_RUNTIME_ENTRYPOINTS_V1',version='1.0.0',
        runtime_dependencies=deps_ref,runtime=binding('scripts/v4_16_shadow_runtime_v6.py'),
        settlement=worker['entrypoint'],historical_v5_settlement=worker['historical_v5_entrypoint'],
        r25_builder=packet['builder'],r25_validator=packet['validator'],
        entry_policy='EXPLICIT_VERSIONED_V6_ONLY; LEGACY_DEFAULT_DISPATCH_IS_HISTORICAL',
        runtime_authorized=False,first_real_shadow_authorized=False,external_acceptance=False))
    diff={k:dict(before=old_head['entries'][k],after=head['entries'][k]) for k in head['entries'] if old_head['entries'][k]!=head['entries'][k]}
    assert set(diff)=={'A08_CURRENT_RUNTIME'}
    write(PREFIX+'A08_HEAD_SUCCESSOR_DIFF.json',dict(canonical_issue_diff=diff,external_acceptance=a08,predecessor=binding('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json'),successor=head_ref))
    unchanged={k:v for k,v in old.items() if k not in set(changes)|{'bindings','contract_id','version','execution_baseline','predecessor','blocked_issue_ids'}}
    assert all(deps[k]==v for k,v in unchanged.items())
    write(PREFIX+'DEPENDENCY_SUCCESSOR_PROOF.json',dict(predecessor=deps['predecessor'],successor=deps_ref,
        unchanged_fields=unchanged,unchanged_binding_entries=[b for b in old['bindings'] if b['path'] not in mapping],
        replacements=mapping,all_old_bytes_preserved=True))

if __name__=='__main__':build()
