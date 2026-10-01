"""Freeze R3 governance candidates and externally authorized historical metadata."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind
P='reports/audits/A10_A12_R3_'
TASK='V4_A10_A12_R3_PRODUCER_SOURCE_INSTANCE_SCOPE_REPAIR_TASK_20261001.md'
MODE='TARGET_DATE_QUERYABLE_FACT'
POLICY='SOURCE_AUTHORITY_SOURCE_INSTANCE_POLICY_V1'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def write(p,v):atomic_json(ROOT/p,v)
def main():
    taskpath='docs/evidence/source_authority/'+TASK
    atomic_bytes(ROOT/taskpath,(Path('D:/Users/lps/Desktop/阶段任务')/TASK).read_bytes())
    protected=read('reports/audits/A12_R2_STAGE_ENTRY_R1.json')['protected_bindings']
    extras=[p.relative_to(ROOT).as_posix() for p in (ROOT/'reports/audits').glob('A12_R2_*.json')]
    extras+=['reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R5.json']
    existing={b['path'] for b in protected}
    protected+= [bind(p) for p in extras if p not in existing]
    write(P+'STAGE_ENTRY_R1.json',dict(contract_id='WP-A10-A12-R3-PRODUCER-SOURCE-INSTANCE',
        baseline_commit='a43d663a0cc62d48f65a1160fae9c50874d86548',task=bind(taskpath),
        stage_contract='ACCEPT_PRODUCER_ONCE_VERIFY_SOURCE_EVERY_TARGET',protected_bindings=protected,
        phase0_status='FULL_PASS',phase0_evidence=bind('reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'),
        next_stage='Independent R3 reaudit; A13 separately authorized; DM01 all-nine blocked'))
    stamp=datetime.now(timezone.utc).isoformat()
    authority=dict(document=bind(taskpath),section='1 / 9 / 10',scope='HISTORICAL_PATH_B_AND_NEGATIVE_SCOPE_CENSUS_ONLY',recorded_at=stamp)
    write(P+'EXTERNAL_DISPOSITION_R1.json',dict(external_authority=authority,historical_scope={'start_date':'2023-07-04','end_date':'2026-09-24'},historical_path_b='EXTERNALLY_ACCEPTED',observed_daily_producers='NOT_ACCEPTED',dm01_final_all_nine='NOT_ACCEPTED',AS_RECORDED=False))
    schema_path='config/source_authority_daily_schema_r3.json'
    capturebase='reports/dm01/a01_r2/20261001T033251758661Z/normalized_schema_v2_1/'
    sample=read(capturebase+'TARGET_DATE_CAPTURE_normalized_receipt.json')['responses']['query_daily_history_k_AStock']
    write(schema_path,dict(contract_id='BAOSTOCK_DAILY_FIELDS_SDK_0_9_3_V1',fields=sample['fields'],max_rows=20000,max_pages=1,adjustflag='3',empty='UNKNOWN_BLOCK',local_TDX_actual_precedence=True,isST='BINARY_ST_OR_STAR_ST_NOT_FULL_LEGAL_RISK_TAXONOMY'))
    config=read('config/source_authority_governance_r2.json')
    config.update(contract_id='V4_SOURCE_AUTHORITY_GOVERNANCE_R3',version='3.0.0',supersedes=bind('config/source_authority_governance_r2.json'),status='CANDIDATE_PENDING_EXTERNAL_REAUDIT',owner_runtime=bind('src/workbench_analysis/source_authority_producers_r3.py'),runtime=bind('src/workbench_analysis/source_authority_governance_r1.py'),task=bind(taskpath),required_owner_registry_contract='SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V2')
    identity_head=bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json')
    calendar_head=bind('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json')
    producer_paths={}
    for field in ('TRADING_STATUS','ISST'):
        rule=next(r for r in config['field_rules'] if r['field_id']==field)
        rule.update(owner_contract_id='BAOSTOCK_DATED_'+('TRADING_STATUS' if field=='TRADING_STATUS' else 'ISST')+'_PROVIDER_AUTHORITY_V4',source_family='BAOSTOCK_DATED_FIELD_PROVIDER',source_instance_policy_id=POLICY,role_binding_id='SOURCE_AUTHORITY_ROLE_R3:'+field)
        path=P+'PRODUCER_'+field+'_CANDIDATE_R1.json';producer_paths[field]=path
        write(path,dict(contract_id=rule['owner_contract_id'],field_id=field,external_acceptance=None,
            formal_consumer_authorization=False,allowed_consumers=rule['allowed_consumers'],historical_modes=[MODE],
            source_instance_policy_id=POLICY,role_binding=rule,accepted_at=None,schema_contract=bind(schema_path),
            identity_head=identity_head,calendar_head=calendar_head,knowledge_lineage='RECONSTRUCTED_CORRECTED',
            local_TDX_actual_precedence=True,empty_malformed='UNKNOWN_BLOCK',substantive_change_requires_new_acceptance=True,
            routine_daily_revision_requires_human_acceptance=False,OHLC_authority=False,adjustment_authority=False))
    write('config/source_authority_governance_r3.json',config)
    iddoc=read(read(identity_head['path'])['identity_revision']['path'])
    sessions=read(read(calendar_head['path'])['accepted_extension']['path'])['sessions']
    instances={}
    for purpose in ('TARGET_DATE_CAPTURE','CAPABILITY_SMOKE'):
        receiptpath=capturebase+purpose+'_normalized_receipt.json';receipt=read(receiptpath)
        response=receipt['responses']['query_daily_history_k_AStock'];target=response['target_trade_date']
        raw=read(response['raw_response_binding']['path'])
        records={r['source_security_key']:r for r in iddoc['records'] if r['list_date']<=target and (not r.get('symbol_effective_from') or r['symbol_effective_from']<=target) and (not r.get('symbol_effective_to') or r['symbol_effective_to']>=target)}
        keys=sorted(r['code'].upper() for r in raw['rows'])
        assert len(keys)==len(set(keys)) and all(k in records for k in keys)
        ip=P+'IDENTITY_INSTANCE_'+target+'_R1.json';cp=P+'CALENDAR_INSTANCE_'+target+'_R1.json'
        write(ip,dict(contract_id='SOURCE_INSTANCE_DATED_IDENTITY_UNIVERSE_V1',target_trade_date=target,accepted_head=identity_head,members=[dict(source_security_key=k,security_id=records[k]['security_id']) for k in keys],scope='SOURCE_ROSTER_JOIN_TO_ACCEPTED_DATED_IDENTITY_NOT_BUSINESS_HEAD_PROMOTION'))
        write(cp,dict(contract_id='SOURCE_INSTANCE_DATED_CALENDAR_V1',target_trade_date=target,accepted_head=calendar_head,sessions=[s for s in sessions if s['trade_date']==target]))
        instances[target]={}
        for field in producer_paths:
            path=P+'INSTANCE_'+target+'_'+field+'_R1.json'
            write(path,dict(contract_id=POLICY,field_id=field,source_family='BAOSTOCK_DATED_FIELD_PROVIDER',target_trade_date=target,provider_date=response['provider_date'],raw_artifact=response['raw_response_binding'],capture_receipt=bind(receiptpath),observed_at=response['observed_at'],received_at=response['received_at'],source_revision='sha256:'+response['raw_response_binding']['sha256'],schema_contract=bind(schema_path),identity_binding=bind(ip),calendar_binding=bind(cp),query_status='PASS_NONEMPTY_BOUNDED_EXACT_DATE',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False))
            instances[target][field]=bind(path)
    write(P+'SOURCE_INSTANCE_MANIFEST_R1.json',dict(contract_id='SOURCE_AUTHORITY_DAILY_INSTANCE_INDEX_V1',instances=instances,missing_target_dates=['2026-09-29'],machine_verified_not_human_owner_registration=True,producer_candidates={f:bind(p) for f,p in producer_paths.items()}))
    # Historical acceptance is independent of the unaccepted new daily producers.
    owners=[]
    historical_inputs=[
        'data/v4/source_evidence/a12_r2/PROVIDER_DOCUMENTATION_CAPTURE_R1.json',
        'data/v4/source_evidence/a12_r2/stockKData.md','data/v4/source_evidence/a12_r2/DailyUpdates.md',
        'reports/v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.json',
        'reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json',
        'reports/v4_02/V4_02_DATED_ST_STATUS_BOUNDED_RECOVERY_R1_20260926.json',
        'data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926_RECOVERED_R1.jsonl.gz',
        'reports/audits/A12_R2_INDEPENDENT_REAL_SOURCE_ORACLE_R1.json',
        'reports/audits/A12_R2_SOURCE_REVISION_RECOVERY_BINDING_R1.json']
    # Original pre-R7 normalized status source is bound, not merely the R7 output.
    original=ROOT/'data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.jsonl.gz'
    assert original.is_file()
    historical_inputs.append(original.relative_to(ROOT).as_posix())
    config['historical_field_rules']=[]
    for field in producer_paths:
        oldpath='reports/audits/A12_R2_OWNER_'+field+'_CANDIDATE_R1.json'
        owner=read(oldpath);rule=copy.deepcopy(owner['role_binding'])
        rule.update(authority_status='EXTERNALLY_ACCEPTED',enabled_for_formal_consumer=True,source_instance_policy_id=POLICY)
        owner.update(external_acceptance='EXTERNALLY_ACCEPTED',formal_consumer_authorization=True,accepted_at=stamp,
            historical_modes=[MODE],source_instance_policy_id=POLICY,role_binding=rule,
            external_authority=authority,supersedes=bind(oldpath),source_bindings=[bind(p) for p in historical_inputs],
            source_instance_representation='HISTORICAL_NORMALIZED_ARCHIVE',first_available_at_target_proven=False,AS_RECORDED=False)
        primary='reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json'
        recovery='reports/v4_02/V4_02_DATED_ST_STATUS_BOUNDED_RECOVERY_R1_20260926.json'
        receipts=read(primary)['query_receipts']+read(recovery)['retry_receipts']
        revisions={r['trade_date']:'sha256:'+r['normalized_full_market_status_sha256'] for r in receipts if r.get('normalized_full_market_status_sha256')}
        assert len(revisions)==786
        archivepath=P+'HISTORICAL_'+field+'_SOURCE_INSTANCE_ARCHIVE_R1.json'
        write(archivepath,dict(contract_id=POLICY,field_id=field,rows=4035729,
            source_revisions_by_target_date=revisions,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
            primary_query_receipts=bind(primary),bounded_recovery=bind(recovery),
            independent_oracle=bind('reports/audits/A12_R2_INDEPENDENT_REAL_SOURCE_ORACLE_R1.json'),
            trading_status_revision_basis='Same-date full-market status/ST tuple query revision; range-status receipts also bound; original normalized status facts retained',
            receipt_census_not_raw_network_payload=True))
        owner['historical_source_instance_archive']=bind(archivepath)
        path=P+'HISTORICAL_'+field+'_ACCEPTED_AMENDMENT_R1.json';write(path,owner)
        config['historical_field_rules'].append(rule)
        owners.append(dict(owner_contract_id=owner['contract_id'],field_id=field,producer_contract=bind(path),
            **{k:owner[k] for k in ('external_acceptance','formal_consumer_authorization','allowed_consumers','historical_modes','source_instance_policy_id','role_binding','accepted_at')},registration_scope='HISTORICAL_PATH_B_ONLY',effective_scope=owner['effective_scope']))
    write('config/source_authority_governance_r3.json',config)
    registry_path='data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json'
    write(registry_path,dict(contract_id='SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V2',version=2,
        supersedes=bind('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json'),owners=owners,
        pending_daily_producers={f:bind(p) for f,p in producer_paths.items()},external_authority=authority))
    write('data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json',dict(contract_id='SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V2',registry=bind(registry_path),supersedes=bind('data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R1.json'),business_promotion=False,dm01_final_all_nine_accepted=False))
    ledger=copy.deepcopy(read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R5.json'))
    ledger.update(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R6',extends=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R5.json'),authority=bind(taskpath))
    for e in ledger['entries']:
        if e.get('audit_id') in ('A12_R2_INTERIOR_DATA_GAP_SCOPE','A12_R2_POSITIVE_ST_CODE_CHANGE_SCOPE'):
            e.update(status='ACCEPTED_NEGATIVE_SCOPE_CENSUS',external_acceptance='ACCEPTED_NEGATIVE_SCOPE_CENSUS',formal_consumer_authorization=False,external_authority=authority,next_step='Append future real positive cases; no fabricated example; does not block historical Path B')
        if e.get('work_package')=='WP-A12-V4-02-STATUS-ST-AUTHORITY':
            e.update(status='OPEN',historical_path_b_acceptance='EXTERNALLY_ACCEPTED',observed_daily_producer_acceptance='PENDING',evidence=e['evidence']+[bind(P+'EXTERNAL_DISPOSITION_R1.json')])
    ledger['entries'].append(dict(audit_id='A10_A12_R3_PRODUCER_SOURCE_INSTANCE',work_package='WP-A10-A12-R3-PRODUCER-SOURCE-INSTANCE',status='OPEN',implementation_status='CANDIDATE_PENDING_CLEAN_AND_EXTERNAL_REAUDIT',external_acceptance='PENDING',formal_consumer_authorization=False,evidence=[bind(P+'SOURCE_INSTANCE_MANIFEST_R1.json')],next_step='Independent producer/source-instance reaudit; DM01 final blocked'))
    ledger['audit_count']=len(ledger['entries']);ledger['dependency_graph']={e['work_package']:e.get('depends_on',[]) for e in ledger['entries']}
    write('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R6.json',ledger)
    write(P+'ENGINEERING_GATES_R1.json',dict(allowed_candidate_status='A10_A12_R3_PRODUCER_SOURCE_INSTANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',gates={'GLOBAL_INSTANCE_GATE':'PENDING_CLEAN_DETACHED','REAL_SOURCE_VECTORS':'PENDING_CLEAN_DETACHED','HISTORICAL_LINEAGE':'PASS_ENGINEERING','EXTERNAL_DAILY_PRODUCER_ACCEPTANCE':'PENDING_INDEPENDENT_EXTERNAL_AUDIT'},next_stage='Independent R3 reaudit; A13 authorized; no DM01 all-nine or business head promotion'))
    print('R3 candidates and historical disposition frozen')
if __name__=='__main__':main()
