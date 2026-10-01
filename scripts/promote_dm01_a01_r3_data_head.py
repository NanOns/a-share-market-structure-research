"""Formalize independent acceptance and atomically promote only the V4 Data Head."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import argparse,json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from workbench_analysis.daily_data_head import write_json_atomic,CAPABILITIES
from workbench_analysis.dm01_accepted_chain_v1 import (binding,load,bound_path,sha,require_audit,permission_from_receipt,validate_head_v2,
    validate_registry_r10,HEAD_PATH,HEAD_CONTRACT,AUDITED_HEAD,AUDIT_PATH,ANCHOR_SHA,ACCEPTED_NODE_SHAS)
P='reports/audits/DM01_A01_R3_PROMOTION_'
ARCHIVE='data/v4/data_head_archive/V4_DATA_ACCEPTED_HEAD_20260924_ORIGINAL_BYTES_R1.json'
CHAIN='data/v4/DM01_A01_R3_ACCEPTED_CHAIN_20260924_20260930_R1.json'
RECORD='reports/audits/DM01_A01_R3_EXTERNAL_ACCEPTANCE_RECORD_R1.json'
REGISTRY='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json'
CONTRACT='config/v4_data_accepted_head_v2.json'
CANDIDATE='data/v4/data_head_promotion/DM01_A01_R3_DATA_HEAD_CANDIDATE_V2_R1.json'
RECEIPT='reports/v4_joint/DM01_A01_R3_DATA_HEAD_PROMOTION_RECEIPT_R1.json'
TASK='docs/evidence/source_authority/V4_DM01_A01_R3_EXTERNAL_ACCEPTANCE_AND_DATA_HEAD_PROMOTION_TASK_20261001.md'
def read(path):return json.loads((ROOT/path).read_bytes())
def ref(path):return binding(ROOT,path)
def immutable_bytes(path,data):
    p=ROOT/path
    if p.exists():
        if p.read_bytes()!=data:raise ValueError('IMMUTABLE_ARTIFACT_CHANGED:'+path)
    else:atomic_bytes(p,data)
def immutable_json(path,value):immutable_bytes(path,(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def authority():return dict(authority_kind='INDEPENDENT_EXTERNAL_ACCEPTANCE',document=ref(AUDIT_PATH),audited_head=AUDITED_HEAD)
def check_protected(entry):
    for r in entry['protected_bindings']:
        if sha(ROOT/r['path'])!=r['sha256']:raise ValueError('PROTECTED_NAMESPACE_CHANGED:'+r['path'])

def prepare():
    for name in (Path(AUDIT_PATH).name,Path(TASK).name):
        immutable_bytes('docs/evidence/source_authority/'+name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes())
    a=authority();require_audit(ROOT,a)
    if sha(ROOT/HEAD_PATH)!=ANCHOR_SHA:raise ValueError('OLD_DATA_HEAD_NOT_AUDITED_ANCHOR')
    entry_path=P+'STAGE_ENTRY_R1.json'
    if not (ROOT/entry_path).exists():
        protected=[]
        paths={p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4').glob('*ACCEPTED_HEAD*.json')} - {HEAD_PATH}
        paths.update(['data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DEV_BASELINE_HEAD.json','data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json','data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R3.json','reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R9.json'])
        for path in sorted(paths):
            r=ref(path)
            raw=subprocess.check_output(['git','show',AUDITED_HEAD+':'+path],cwd=ROOT)
            g=hashlib.sha256(raw).hexdigest()
            if g!=r['sha256']:
                if raw.replace(b'\r\n',b'\n')!=(ROOT/path).read_bytes().replace(b'\r\n',b'\n'):raise ValueError('UNDECLARED_BASELINE_DIFFERENCE')
                r.update(git_sha256=g,representation='PRE_EXISTING_CRLF_LF_ONLY')
            protected.append(r)
        immutable_json(entry_path,dict(contract_id='DM01_A01_R3_DATA_HEAD_PROMOTION_STAGE_V1',baseline_commit=AUDITED_HEAD,
            stage_contract=ref(TASK),external_authority=a,observed_at=datetime.now(timezone.utc).isoformat(),
            protected_bindings=protected,authorized_mutable_pointer=ref(HEAD_PATH),data_head_target='2026-09-30',
            acceptance_result='EXTERNALLY_ACCEPTED_SCOPE; PROMOTION_PREFLIGHT_PENDING',
            next_stage='DATA_HEAD_PROMOTION_AND_INDEPENDENT_READBACK_ONLY',permissions=dict(production=False,shadow=False,focus=False)))
    entry=read(entry_path);check_protected(entry)
    immutable_bytes(ARCHIVE,(ROOT/HEAD_PATH).read_bytes());archive=ref(ARCHIVE)
    if archive['sha256']!=ANCHOR_SHA:raise ValueError('OLD_HEAD_ARCHIVE_NOT_EXACT')
    post=read('reports/audits/DM01_A01_R3_CONTINUOUS_CHAIN_POSTCHECK_R3.json')
    candidates=post['candidates']
    if tuple(r['sha256'] for r in candidates)!=ACCEPTED_NODE_SHAS or post['status']!='PASS':raise ValueError('AUDITED_CHAIN_NOT_EXACT')
    required=['A10_A12_R3_EXTERNAL_ACCEPTANCE_FORMALIZATION_R1.json','DM01_A01_R3_CONTINUOUS_CHAIN_POSTCHECK_R3.json','DM01_A01_R3_DETERMINISM_R3.json','DM01_A01_R3_ATOMIC_FAILURE_PROBES_R3.json','DM01_A01_R3_FINAL_VERSION_BUSINESS_PARITY_R1.json','DM01_A01_R3_METADATA_DURABILITY_REPAIR_R2.json','DM01_A01_R3_SOURCE_DEPENDENCY_DURABILITY_R1.json','DM01_A01_R3_CLEAN_CHECKOUT_R1.json','DM01_A01_R3_NO_SYMBOL_SCAN_R1.json','DM01_A01_R3_EXTERNAL_REAUDIT_HANDOFF_R3.json']
    evidence=[ref('reports/audits/'+p) for p in required]+[ref('reports/audits/DM01_A01_R3_'+day+'_CANDIDATE_R3.json') for day in ('20260928','20260929','20260930')]
    source_registry=ref('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json');source_head=ref('data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R3.json')
    builder_contract=read('config/dm01_incremental_builders_contract_r3_3.json')
    immutable_json(RECORD,dict(contract_id='DM01_A01_R3_EXTERNAL_ACCEPTANCE_RECORD_V1',external_authority=a,audited_head=AUDITED_HEAD,
        external_acceptance='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN',accepted_through='2026-09-30',
        accepted_scope=dict(anchor='2026-09-24',sessions=post['sessions'],all_nine_each_day=True,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False),
        candidate_bindings=candidates,evidence_bindings=evidence,source_authority_registry=source_registry,source_authority_governance=source_head,
        recorded_at_utc=entry['observed_at'],permissions=dict(production=False,shadow=False,focus=False),next_stage='DATA_HEAD_PROMOTION_ONLY'))
    nodes=[];parent=ref(HEAD_PATH)
    for r in candidates:
        marker=load(ROOT,r)
        nodes.append(dict(trade_date=marker['target_trade_date'],parent=parent,candidate=r,components=marker['components'],source_instances=marker['source_instance_digests']))
        parent=r
    immutable_json(CHAIN,dict(contract_id='DM01_ACCEPTED_CONTINUOUS_CHAIN_V1',version='1.0.0',
        anchor=dict(trade_date='2026-09-24',original_namespace=ref(HEAD_PATH),archive=archive),nodes=nodes,
        external_authority=a,external_acceptance_record=ref(RECORD),builder_contract=ref('config/dm01_incremental_builders_contract_r3_3.json'),
        source_context=builder_contract['execution_context'],source_authority_governance_config=builder_contract['producer_governance'],
        source_authority_registry=source_registry,source_authority_governance=source_head,accepted_through='2026-09-30',
        historical_binding_resolution='ONLY_EXACT_AUDITED_20260924_MOVABLE_NAMESPACE_TO_EXACT_ORIGINAL_BYTE_ARCHIVE',
        production=False,shadow=False,focus=False))
    a13paths=['data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json','data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_SIDECAR_R1.json',*[f'reports/audits/A13_FORMALIZATION_{n}_R1.json' for n in ('REAL_HEAD_RUNTIME_READBACK','COUNTERFACTUAL_REVALIDATION','CLEAN_CHECKOUT','NO_SYMBOL_SCAN','STAGE_CLOSURE')]]
    confirmation='reports/audits/A13_FORMALIZATION_EXTERNAL_CONFIRMATION_R1.json'
    immutable_json(confirmation,dict(status='EXTERNALLY_CONFIRMED',external_authority=a,formalization_external_reaudit='PASS',
        acceptance_scope='EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT',external_acceptance='PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT',
        evidence_bindings=[ref(p) for p in a13paths],v4_08_head_action='KEEP',formal_consumer_authorization=False,
        positive_trading_event_authority_consumed=False,business_rebuild_required=False))
    previous=read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R9.json');registry=deepcopy(previous)
    registry.update(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10',extends=ref('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R9.json'),
        baseline_commit=AUDITED_HEAD,external_authority=a,status='EXTERNALLY_ACCEPTED_DM01_CHAIN_SCOPED; GLOBAL_AND_PRODUCTION_GATES_REMAIN_CLOSED',
        prior_registry_status=previous.get('status'),permissions=dict(production=False,shadow=False,focus=False),global_mandatory_adoption_authorized=False)
    update_ids={'V4_02_STATUS_ST_SOURCE_AUTHORITY_DIVERGENCE','DM01_REAL_INCREMENTAL_BUILDERS','OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS','A10_A12_R3_PRODUCER_SOURCE_INSTANCE','DM01_R3_ACCEPTED_METADATA_GIT_REPRESENTATION'}
    for e in registry['entries']:
        audit=e['audit_id']
        if audit not in update_ids:continue
        prior=deepcopy(e)
        for key in ('transition','prior_transition_r4'):e.pop(key,None)
        e['history']=[dict(registry=registry['extends'],prior_entry=prior)]
        e.update(external_authority=a,latest_task=ref(TASK),next_step='Consumer stages require their own contracts; production/shadow/focus remain disabled')
        if audit in ('V4_02_STATUS_ST_SOURCE_AUTHORITY_DIVERGENCE','A10_A12_R3_PRODUCER_SOURCE_INSTANCE'):
            e.update(status='ACCEPTED_SOURCE_AUTHORITY_SCOPE',external_acceptance='EXTERNALLY_ACCEPTED',
                acceptance_scope='HISTORICAL_RECONSTRUCTED_AND_DAILY_PRODUCER_SOURCE_INSTANCE_AUTHORITY',
                historical_path_b='EXTERNALLY_ACCEPTED_RECONSTRUCTED_ONLY',daily_producer_authority='EXTERNALLY_ACCEPTED',
                observed_daily_producer_acceptance='EXTERNALLY_ACCEPTED_PRODUCER_SOURCE_INSTANCE_MODEL',capability_limitations=[],
                implementation_status='EXTERNAL_ACCEPTANCE_PASS_SOURCE_AUTHORITY_FORMALIZATION',dm01_all_nine_accepted=True,
                formal_consumer_authorization=True,formal_consumer_scope='ACCEPTED_STATUS_ISST_SOURCE_AUTHORITY_ALLOWLIST_ONLY',status_path=RECORD)
        elif audit=='DM01_REAL_INCREMENTAL_BUILDERS':
            e.update(status='ACCEPTED',implementation_status='EXTERNAL_ACCEPTANCE_PASS_REAL_CONTINUOUS_CHAIN',
                external_acceptance='PASS_REAL_INCREMENTAL_CHAIN_20260928_20260930',acceptance_scope='REAL_CONTINUOUS_ALL_NINE_20260928_20260930_RECONSTRUCTED_ONLY',
                formal_consumer_authorization=True,formal_consumer_scope='EXACT_EXTERNALLY_ACCEPTED_DM01_CHAIN_ONLY',dm01_all_nine_accepted=True,
                accepted_through='2026-09-30',remaining_external_gate=None,depends_on=[],production_gate=True,
                capability_limitations=['INHERITED_DEGRADED_CAPABILITIES_RETAINED_FROM_FINAL_RECEIPTS'],status_path=RECORD,
                acceptance_record=ref(RECORD),accepted_chain=ref(CHAIN))
        elif audit=='OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS':
            e.update(status='ACCEPTED',external_acceptance='PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT',formalization_external_reaudit='PASS',
                implementation_status='EXTERNAL_ACCEPTANCE_PASS_FORMALIZATION_EVIDENCE_GOVERNANCE',v4_08_head_action='KEEP',
                confirmation=ref(confirmation),status_path=confirmation)
        else:
            e.update(status='ACCEPTED_SCOPED',external_acceptance='PASS_EXACT_METADATA_AND_SOURCE_DURABILITY',
                implementation_status='EXTERNAL_ACCEPTANCE_PASS_DURABILITY_REPAIR',acceptance_scope='AUDIT_SECTION_12_METADATA_SOURCE_AND_CHECKOUT_DURABILITY',
                formal_consumer_authorization=False)
    validate_registry_r10(ROOT,registry);immutable_json(REGISTRY,registry)
    final=load(ROOT,candidates[-1]);permissions={cap:permission_from_receipt(ROOT,final,cap) for cap in CAPABILITIES}
    head=dict(contract_id=HEAD_CONTRACT,version='2.0.0',accepted_trade_date=final['target_trade_date'],source_revision=final['source_freeze_digest'],
        canonical_data_revision=final['logical_digest'],manifest_path=CHAIN,manifest_sha256=ref(CHAIN)['sha256'],parent_head_sha256=ANCHOR_SHA,
        stage_accepted_head_sha256=ref('data/v4/V4_STAGE_ACCEPTED_HEAD.json')['sha256'],dev_baseline_sha256=ref('data/v4/V4_DEV_BASELINE_HEAD.json')['sha256'],
        component_permissions=permissions,component_artifacts={k:v['artifact'] for k,v in permissions.items()},accepted_chain=ref(CHAIN),
        final_candidate=candidates[-1],external_acceptance_record=ref(RECORD),source_authority_governance=source_head,source_authority_registry=source_registry,
        calendar=final['calendar_binding'],identity=final['identity_binding'],parent_archive=archive,audit_registry=ref(REGISTRY),
        stage_head=ref('data/v4/V4_STAGE_ACCEPTED_HEAD.json'),dev_baseline=ref('data/v4/V4_DEV_BASELINE_HEAD.json'),
        external_acceptance='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN',permissions=dict(production=False,shadow=False,focus=False),
        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False,promoted_at_utc=entry['observed_at'])
    fields=[*head,'contract']
    contract=dict(contract_id=HEAD_CONTRACT,version='2.0.0',supersedes=ref('config/v4_data_accepted_head_v1.json'),required_fields=fields,
        permission_derivation='EXACT_FINAL_COMPONENT_RECEIPTS',accepted_chain_required=True,old_anchor_resolution='EXACT_ARCHIVE_ONLY',
        raw_or_adjusted_sector_context_authorization='NOT_GRANTED; EACH_CONSUMER_REQUIRES_INDEPENDENT_VERSIONED_CONTRACT',
        runtime_bindings=[ref('src/workbench_analysis/dm01_accepted_chain_v1.py'),ref('scripts/promote_dm01_a01_r3_data_head.py')])
    atomic_json(ROOT/CONTRACT,contract);head['contract']=ref(CONTRACT)
    atomic_json(ROOT/CANDIDATE,head)
    print('PREPARED; OLD_DATA_HEAD_UNCHANGED')

def preflight():
    entry=read(P+'STAGE_ENTRY_R1.json');check_protected(entry)
    if sha(ROOT/HEAD_PATH)!=ANCHOR_SHA or (ROOT/ARCHIVE).read_bytes()!=(ROOT/HEAD_PATH).read_bytes():raise ValueError('PRE_SWAP_OLD_HEAD_CHANGED')
    result=validate_head_v2(ROOT,read(CANDIDATE),source_readback=True)
    atomic_json(ROOT/(P+'PREFLIGHT_R1.json'),dict(status='PASS',validated_candidate=ref(CANDIDATE),old_head=ref(HEAD_PATH),old_archive=ref(ARCHIVE),
        accepted_chain=ref(CHAIN),external_acceptance_record=ref(RECORD),registry_r10=ref(REGISTRY),source_readback=result,
        stage_head_before=ref('data/v4/V4_STAGE_ACCEPTED_HEAD.json'),permissions=entry['permissions'],promotion_permitted=True))
    print('PASS_PROMOTION_PREFLIGHT')

def promote():
    entry=read(P+'STAGE_ENTRY_R1.json');head=read(CANDIDATE)
    if (ROOT/HEAD_PATH).read_bytes()==(ROOT/CANDIDATE).read_bytes():
        if not (ROOT/RECEIPT).exists():raise ValueError('PROMOTED_POINTER_WITHOUT_DURABLE_RECEIPT')
        print('NOOP_ALREADY_PROMOTED');return
    actual=datetime.now(timezone.utc).isoformat();head['promoted_at_utc']=actual
    atomic_json(ROOT/CANDIDATE,head)
    preflight();check_protected(entry)
    # Optimistic parent check immediately before the single atomic replacement.
    if sha(ROOT/HEAD_PATH)!=ANCHOR_SHA:raise ValueError('PROMOTION_PARENT_CHANGED')
    validate_head_v2(ROOT,head)
    stage_before=ref('data/v4/V4_STAGE_ACCEPTED_HEAD.json')
    written=write_json_atomic(ROOT/HEAD_PATH,head,tdx_root=Path('D:/new_tdx'))
    check_protected(entry)
    result=validate_head_v2(ROOT,read(HEAD_PATH),source_readback=True)
    atomic_json(ROOT/RECEIPT,dict(status='PROMOTED_TO_2026_09_30',promotion_timestamp_utc=actual,old_data_head_archive=ref(ARCHIVE),
        new_data_head=ref(HEAD_PATH),written_sha256=written,accepted_chain=ref(CHAIN),external_acceptance_record=ref(RECORD),
        stage_head_before=stage_before,stage_head_after=ref('data/v4/V4_STAGE_ACCEPTED_HEAD.json'),stage_head_moved=False,
        permissions_before=entry['permissions'],permissions_after=head['permissions'],independent_source_readback=result,
        audit_registry_r10=ref(REGISTRY),business_stage_reacceptance_performed=False,next_stage='INDEPENDENT_CONSUMER_STAGE_CONTRACTS; NO_PRODUCTION_ENABLEMENT'))
    print('PROMOTED_TO_2026_09_30; STAGE_HEAD_KEEP')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--action',choices=['prepare','preflight','promote'],required=True);args=parser.parse_args()
    {'prepare':prepare,'preflight':preflight,'promote':promote}[args.action]()
if __name__=='__main__':main()
