"""Register five independently accepted narrow scopes and immutable readback."""
import json
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,get_ident
from copy import deepcopy
from scripts.next_round_bundle_r1 import ROOT,write,bind,read,exact
from workbench_analysis.parallel_scoped_acceptance_r1 import (
    AUDITED,AUDIT,DISPOSITIONS,PERMISSIONS,OWNER_PATH,READER_PATH,record_path,
    validate_record,validate_accepted_owner_metadata,validate_reader_manifest,
    accepted_forward_append,accepted_adjusted_lineage,read_accepted_history,
)

PROFILE={
    'A03':dict(evidence=['reports/audits/A03_R2_1_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json','reports/audits/A03_FORWARD_PIT_BUILDER_R2_REAL_OBSERVATION.json','reports/audits/A03_R2_1_PAYLOAD_GOVERNANCE_SUPPLEMENT_R1.json'],runtime=['src/workbench_analysis/forward_pit_ledger_r2.py','src/workbench_analysis/forward_pit_ledger_r2_1.py','scripts/run_a03_forward_pit_daily_r2_1.py'],current_state='ACCUMULATION_CONTINUES',limitations=['FORWARD_ACCUMULATION_CONTINUES','NO_RETROACTIVE_AS_RECORDED_FABRICATION','FUTURE_OBSERVATION_COUNT_IS_NOT_ENGINEERING_OPEN_BLOCKER']),
    'A06':dict(evidence=['reports/audits/A06_R2_CANDIDATE_CLOSURE_R1.json','reports/audits/A06_R2_REAL_REPRESENTATIVE_MATRIX_R2.json','reports/audits/A06_R2_DOCUMENT_FREEZE_R1.json','config/baostock_binding_tolerance_policy_r2_candidate.json'],runtime=['src/workbench_analysis/baostock_tolerance_candidate_r2.py'],current_state='ACCEPTED_SCOPED',limitations=['ALL_UNDOCUMENTED_TOLERANCES_NULL','STRICT_BINDING_FALSE','BAOSTOCK_SUPPLEMENTAL_ONLY','TDX_CORE_NEVER_BLOCKED_BY_SUPPLEMENTAL_MISMATCH']),
    'A07':dict(evidence=['reports/audits/A07_R2_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json','reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_DURABLE_REAL_PROOF_R1.json','config/a07_adjusted_price_lineage_r2.json'],runtime=['src/workbench_analysis/adjusted_price_lineage_r2.py','scripts/capture_a07_adjustment_source_r2.py'],current_state='PERMANENT_CAPABILITY_BLOCK',limitations=['PRE_CAPTURE_AS_RECORDED_PERMANENTLY_BLOCKED','GO_FORWARD_LINEAGE_BEGINS_AT_REAL_CAPTURE_TIME','FORMAL_ADJUSTED_PRICE_CONSUMER_PERMISSIONS_SEPARATE']),
    'OWNER':dict(evidence=['data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json','reports/audits/OWNER_REGISTRY_SCOPED_BOOTSTRAP_CANDIDATE_CLOSURE_R1.json'],runtime=['src/workbench_analysis/source_authority_owner_bootstrap_r1.py'],current_state='INACTIVE_ACCEPTED_METADATA',limitations=['ACTIVE_REGISTRY_R3_UNCHANGED','ALL_SEVEN_FIELD_LIMITATIONS_PRESERVED','FORMAL_GLOBAL_CONSUMER_CUTOVER_FALSE']),
    'READER':dict(evidence=['reports/audits/HISTORICAL_PUBLICATION_READER_DI_CANDIDATE_CLOSURE_R1.json','reports/audits/HISTORICAL_PUBLICATION_READER_DI_READBACK_R1.json'],runtime=['src/workbench_analysis/dm01_publication_history_reader_v2.py','src/workbench_analysis/dm01_publication_history_reader_v1.py','scripts/promote_v4_09_accepted_head.py','scripts/validate_v4_10_promotion_r1.py'],current_state='ACCEPTED_SCOPED',limitations=['HISTORY_ONLY','BUSINESS_REACCEPTANCE_FALSE','V1_RETAINED_IMMUTABLE']),
}


def prepare():
    exact(AUDIT)
    protected=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'data/v4').glob('*HEAD*.json'))]
    protected.extend([bind('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json'),bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json')])
    for package,profile in PROFILE.items():
        if (ROOT/record_path(package)).exists():
            validate_record(ROOT,read(record_path(package)),package)
            continue
        record=dict(contract_id='PARALLEL_SCOPED_EXTERNAL_ACCEPTANCE_RECORD_R1',version=1,package=package,
            audited_head=AUDITED,external_authority=dict(authority_kind='INDEPENDENT_EXTERNAL_ACCEPTANCE',audited_head=AUDITED,document=AUDIT),
            disposition=DISPOSITIONS[package],external_acceptance='EXTERNALLY_ACCEPTED_SCOPED',current_state=profile['current_state'],limitations=profile['limitations'],
            permissions=PERMISSIONS,business_reacceptance=False,head_action=dict(data='KEEP',stage='KEEP',v4_06='KEEP',v4_09='KEEP',v4_10='KEEP'),
            evidence_bindings=[bind(p) for p in profile['evidence']],runtime_bindings=[bind(p) for p in profile['runtime']],protected_heads=protected,
            formalization_contract=bind('docs/evidence/next_round_r2/V4_PARALLEL_SCOPED_ACCEPTANCE_FORMALIZATION_A03_A06_A07_OWNER_READER_TASK_R1_20261001.md'))
        validate_record(ROOT,record,package);write(record_path(package),record)
    source=read('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json')
    metadata=dict(contract_id=DISPOSITIONS['OWNER'],version=1,registration_status='ACCEPTED_SCOPED_INACTIVE_METADATA',
        acceptance_record=bind(record_path('OWNER')),external_authority=read(record_path('OWNER'))['external_authority'],
        accepted_candidate=bind('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json'),
        owners=source['owners'],field_external_dispositions={x['field_id']:'EXTERNALLY_ACCEPTED_SCOPED_INACTIVE_METADATA' for x in source['owners']},
        inherited_pending_fields_preserved_as_historical_candidate_declarations=True,
        active_registry=bind('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json'),active_global_trust_root=False,permissions=PERMISSIONS)
    validate_accepted_owner_metadata(ROOT,metadata);write(OWNER_PATH,metadata)
    reader=dict(contract_id='ACCEPTED_HISTORY_ONLY_PUBLICATION_READER_R1',version=1,accepted_reader_version='v2',acceptance_record=bind(record_path('READER')),
        validation_scope='ACCEPTED_PUBLICATION_HISTORY_ONLY',permissions=PERMISSIONS,business_reacceptance=False,
        reader_and_preserved_validator_bindings=[bind(p) for p in PROFILE['READER']['runtime']],
        v1_preservation='IMMUTABLE_HISTORICAL_VERSION',current_business_gate='DIRECT_ORIGINAL_VALIDATOR_REMAINS_FAIL_ON_MOVED_DATA_HEAD')
    validate_reader_manifest(ROOT,reader);write(READER_PATH,reader)


def readback():
    results={p:validate_record(ROOT,read(record_path(p)),p) for p in PROFILE}
    before=[(r,exact(r).read_bytes()) for r in read(record_path('A03'))['protected_heads']]
    envelope=read('data/v4/a03_forward_pit_r2/accepted_baseline_capture_envelope.json')
    ledger='data/v4/a03_scoped_acceptance_r1/accepted_baseline_replay'
    first=accepted_forward_append(ROOT,ledger,envelope);second=accepted_forward_append(ROOT,ledger,envelope)
    original=read('reports/audits/A03_FORWARD_PIT_BUILDER_R2_REAL_OBSERVATION.json')['publication']
    replay=bind(ledger+'/publications/'+first['publication']['publication_id']+'.json')
    if exact(replay).read_bytes()!=exact(original).read_bytes() or not second['retry']:raise ValueError('A03_APPEND_IMMUTABILITY_READBACK_FAILURE')
    a07=read('reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_DURABLE_REAL_PROOF_R1.json');capture=a07['real_capture']
    before_capture=accepted_adjusted_lineage(ROOT,capture,knowledge_time='2026-09-24T15:00:00+08:00')
    at_capture=accepted_adjusted_lineage(ROOT,capture,knowledge_time=capture['knowledge_time'])
    if before_capture['lineage']!='RECONSTRUCTED_CORRECTED' or before_capture['historical_capability']!='PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED' or at_capture['lineage']!='AS_RECORDED':raise ValueError('A07_CAPTURE_BOUNDARY_FAILURE')
    from workbench_analysis.baostock_tolerance_candidate_r2 import validate_policy,decompose
    policy=read('config/baostock_binding_tolerance_policy_r2_candidate.json');no_tolerance=validate_policy(policy)
    local=dict(source_security_key='SH.600000',trade_date='2026-09-30',close=10,volume=100,amount=1000)
    source=dict(code='sh.600000',date='2026-09-30',close='20',volume='300',amount='9000',tradestatus='1',adjustflag='3')
    mismatch=decompose(local,source)
    if mismatch['tdx_core_blocked'] or mismatch['strict_binding']:raise ValueError('A06_SUPPLEMENTAL_BLOCK_OR_SELF_PROMOTION')
    owner=validate_accepted_owner_metadata(ROOT,read(OWNER_PATH))
    from workbench_analysis import dm01_publication_history_reader_v1 as old
    from scripts import promote_v4_09_accepted_head as v9,validate_v4_10_promotion_r1 as v10
    module_roots=(v9.ROOT,v10.ROOT);expected=[old.validate_v4_09_history(),old.validate_v4_10_history()];barrier=Barrier(3)
    def run(stage):
        barrier.wait()
        result=read_accepted_history(ROOT,stage) if stage!='CURRENT' else v10.validate()
        if (v9.ROOT,v10.ROOT)!=module_roots:raise ValueError('READER_GLOBAL_ROOT_CONTAMINATION')
        return dict(thread_id=get_ident(),stage=stage,result=result)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(run,s) for s in ['V4-09','V4-10','CURRENT']];parallel=[j.result() for j in jobs]
    if [x['result'] for x in parallel[:2]]!=expected or parallel[2]['result']['checks']['P19_protected']!='FAIL':raise ValueError('READER_PARITY_OR_CURRENT_GATE_FAILURE')
    candidate=read(v10.CANDIDATE);candidate['protected_head_bindings']=deepcopy(candidate['protected_head_bindings']);candidate['protected_head_bindings'][0]['sha256']='0'*64
    wrong_old=old.validate_v4_10_history(candidate);wrong_new=read_accepted_history(ROOT,'V4-10',candidate)
    if wrong_old!=wrong_new or wrong_new['status']!='FAIL':raise ValueError('READER_WRONG_HASH_PARITY_FAILURE')
    from workbench_analysis.dm01_publication_history_reader_v2 import HistoricalBindingResolver
    resolver=HistoricalBindingResolver(ROOT);negative=[]
    for p,s in [('data/v4/V4_DATA_ACCEPTED_HEAD.json','0'*64),('../outside',None),('C:/outside',None)]:
        try:resolver.resolve(p,s)
        except ValueError as e:negative.append(dict(path=p,status='REJECTED',reason=str(e)))
        else:raise ValueError('READER_PATH_BOUNDARY_FAILURE')
    if any(exact(ref).read_bytes()!=raw for ref,raw in before):raise ValueError('FORMALIZATION_PROTECTED_HEAD_CHANGE')
    report=dict(contract_id='PARALLEL_SCOPED_FORMALIZATION_READBACK_R2',status='PASS_SCOPED_FORMALIZATION',records=results,
        a03=dict(first_publication=replay,original_accepted_observation=original,exact_original_bytes=True,second_append_retry=True,new_market_observation_claim=False,current_state='FORWARD_ACCUMULATION_CONTINUES'),
        a06=dict(policy=bind('config/baostock_binding_tolerance_policy_r2_candidate.json'),validation=no_tolerance,conflict=mismatch),
        a07=dict(real_capture=capture,pre_capture=before_capture,at_capture=at_capture),owner=owner,
        reader=dict(concurrent_outputs=[dict(stage=x['stage'],result=x['result']) for x in parallel],exact_v1_output_parity=True,distinct_threads=len({x['thread_id'] for x in parallel}),wrong_hash_output=wrong_new,negative_cases=negative,
            current_data_head_date=read('data/v4/V4_DATA_ACCEPTED_HEAD.json')['accepted_trade_date'],module_roots_unchanged=True),
        permissions=PERMISSIONS,protected_heads_unchanged=True,production_authorization=False,business_reacceptance=False,
        prior_independent_readback=bind('reports/next_round_r2/scoped_acceptance/INDEPENDENT_READBACK_R1.json'))
    write('reports/next_round_r2/scoped_acceptance/INDEPENDENT_READBACK_R2.json',report)
    return report['status']


if __name__=='__main__':
    prepare();print(json.dumps(dict(status=readback())))
