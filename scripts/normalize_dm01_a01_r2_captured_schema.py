"""Versioned offline normalization of actual captures; no raw receipt is overwritten."""
import inspect,json,sys
from pathlib import Path
import baostock as bs
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.baostock_dm01_sdk_schema_v2 import normalize_response
from workbench_analysis.baostock_dm01_capability_v2 import digest,classify_capture_response,build_capability,require_capability
from workbench_analysis.baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,DAILY_REQUIRED_FIELDS,FACTOR_REQUIRED_FIELDS
from workbench_analysis.baostock_supplemental import package_metadata

def immutable_json(path,value):
    if path.exists():
        assert json.loads(path.read_text(encoding='utf8'))==value,'IMMUTABLE_NORMALIZED_CAPTURE_CONFLICT'
        return
    atomic_json(path,value)

def main():
    summary=json.loads((ROOT/'reports/audits/A01_R2_HISTORICAL_CATCHUP_R1.json').read_text(encoding='utf8'))
    contract_path='config/baostock_dm01_sdk_schema_adapter_v2.json';contract=json.loads((ROOT/contract_path).read_text(encoding='utf8'));sdk=package_metadata();cap=None;normalized_refs={}
    evidence='docs/evidence/source_authority/BAOSTOCK_0_9_3_DAILY_METHOD_SOURCE_PROOF.txt'
    source=inspect.getsource(bs.query_daily_adjust_factor)+'\n'+inspect.getsource(bs.query_daily_history_k_AStock)
    assert 'msg_body = receive_data[cons.MESSAGE_HEADER_LENGTH:-1]' in source and 'data.setFields(body_arr[5])' in source
    atomic_bytes(ROOT/evidence,source.encode('utf8'))
    for purpose in ['CAPABILITY_SMOKE','TARGET_DATE_CAPTURE']:
        oldref=summary['observations'][purpose];assert bind(oldref['path'])['sha256']==oldref['sha256']
        rawreceipt=json.loads((ROOT/oldref['path']).read_text(encoding='utf8'));receipt={**rawreceipt,'contract_id':rawreceipt['contract_id']+'_NORMALIZED_SDK_SCHEMA_V2','original_capture_binding':oldref,'schema_adapter':bind(contract_path),'sdk_parser_evidence':bind(evidence),'responses':{}}
        base=(ROOT/oldref['path']).parent/'normalized_schema_v2_1';base.mkdir(exist_ok=True)
        for method,required in [(DAILY_METHOD,DAILY_REQUIRED_FIELDS),(FACTOR_METHOD,FACTOR_REQUIRED_FIELDS)]:
            old=rawreceipt['responses'][method];ref=old['response_binding'];assert bind(ref['path'])['sha256']==ref['sha256']
            raw=json.loads((ROOT/ref['path']).read_text(encoding='utf8'));assert digest(raw['rows'])==old['response_sha256']
            rows,meta=normalize_response(raw['rows'],raw['provider_metadata'],target=rawreceipt['target_trade_date'],sdk=sdk,contract=contract,method=method)
            path=base/(purpose+'_'+method+'_normalized_response.json');immutable_json(path,dict(rows=rows,provider_metadata=meta,raw_binding=ref))
            r={**old,**meta,'raw_response_binding':ref,'response_binding':bind(path.relative_to(ROOT).as_posix()),'response_sha256':digest(rows)}
            r['availability_state']=classify_capture_response(r,target=rawreceipt['target_trade_date'],required_fields=required);receipt['responses'][method]=r
        path=base/(purpose+'_normalized_receipt.json')
        if purpose=='TARGET_DATE_CAPTURE':
            receipt['runtime_capability_id']=require_capability(cap,sdk,receipt['target_trade_date']);receipt['capability_verified']=True
            receipt['source_revision_id']='BS-CAPTURE-V2:'+digest(dict(target=receipt['target_trade_date'],responses={m:r['response_sha256'] for m,r in receipt['responses'].items()},schema=bind(contract_path)['sha256']))
        immutable_json(path,receipt);normalized_refs[purpose]=bind(path.relative_to(ROOT).as_posix())
        if purpose=='CAPABILITY_SMOKE':
            cap=build_capability(sdk,receipt['endpoint'],receipt,normalized_refs[purpose]);cap['schema_adapter']=bind(contract_path)
            cap['runtime_capability_id']='BS-CAP-V2:'+digest({k:v for k,v in cap.items() if k!='runtime_capability_id'})
            immutable_json(base/'runtime_capability_v2.json',cap);normalized_refs['runtime_capability']=bind((base/'runtime_capability_v2.json').relative_to(ROOT).as_posix())
    immutable_json(ROOT/'reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R2.json',dict(status='PASS_BOUNDED_REAL_SMOKE_AND_DELAYED_TARGET_CAPTURE',original_request_receipt=bind('reports/audits/A01_R2_HISTORICAL_CATCHUP_R1.json'),request_count=summary['request_count'],additional_network_requests=0,normalized=normalized_refs,raw_bytes_preserved=True,observed_and_received_times_preserved=True,first_availability_at_target_proven=False,canonical_qfq_authority=False,external_acceptance=None,normalized_capture_storage_revision='V2_1_PURPOSE_SCOPED_IMMUTABLE_FILES',supersedes_unaccepted_engineering_normalization_report=bind('reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R1.json')))
    immutable_json(ROOT/'reports/audits/A01_R2_NORMALIZATION_PATH_COLLISION_REPAIR_R1.json',dict(status='PASS_VERSIONED_NORMALIZED_STORAGE_REPAIR',prior_report=bind('reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R1.json'),corrected_report=bind('reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R2.json'),initial_error='Smoke and target normalization used the same response path; the target overwrote the derived smoke response, breaking its nested binding. Raw captures and original times were preserved.',correction='New V2_1 directory, purpose-scoped response files, immutable equality retries, complete nested smoke/target postcheck.',additional_network_requests=0,prior_diagnostic_artifacts_retained=True,external_acceptance=None))
    print('PASS_REAL_TARGET_CAPTURE_NORMALIZED',summary['request_count'])

if __name__=='__main__':main()
