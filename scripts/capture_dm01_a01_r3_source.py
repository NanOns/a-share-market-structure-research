"""Bounded actual dated provider retrieval; immutable evidence, no OHLC authority."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.baostock_supplemental import BaoStockClient,RequestBudget,package_metadata
from workbench_analysis.dm01_incremental_component_builders import digest
from workbench_analysis.source_authority_producers_r4 import require_formal_source

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--target-date',required=True);args=parser.parse_args()
    target=args.target_date
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'data/v4/source_evidence/dm01_a01_r3'/target/run
    folder.mkdir(parents=True,exist_ok=False)
    ledger=folder/'request_ledger.json'
    registry='data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json'
    before=bind(registry)
    schema_path='config/source_authority_daily_schema_r3.json'
    schema=json.loads((ROOT/schema_path).read_text(encoding='utf8'))
    capability_path='reports/dm01/a01_r2/20261001T033251758661Z/normalized_schema_v2_1/runtime_capability_v2.json'
    from workbench_analysis.baostock_dm01_capability_v2 import require_capability
    capability=json.loads((ROOT/capability_path).read_text(encoding='utf8'))
    require_capability(capability,package_metadata(),target)
    observed=datetime.now(timezone.utc).isoformat()
    with BaoStockClient(RequestBudget(ledger,hard_limit=4,soft_limit=4),auth_mode='PUBLIC_ANONYMOUS',timeout=30,
                        allow_unaccepted_runtime_smoke=True) as client:
        rows,meta=client.query_rows('dm01_r3_dated_field_capture','query_daily_history_k_AStock',date=target,max_rows=20000,max_pages=1)
        received=datetime.now(timezone.utc).isoformat()
        endpoint=dict(client.runtime_endpoint)
    assert meta['error_code']=='0' and meta['page_count']==1 and meta['fields']==schema['fields'] and rows
    assert all(set(r)==set(schema['fields']) and r['date']==target and r['adjustflag']=='3' and
               r['tradestatus'] in ('0','1') and r['isST'] in ('0','1') for r in rows)
    raw=folder/'daily_response.json';atomic_json(raw,dict(rows=rows,provider_metadata=meta,actual_capture_envelope=dict(observed_at=observed,received_at=received,method='query_daily_history_k_AStock',target_trade_date=target)))
    rawref=bind(raw.relative_to(ROOT).as_posix())
    response=dict(method='query_daily_history_k_AStock',target_trade_date=target,provider_date=target,
        observed_at=observed,received_at=received,request_count=1,max_rows=20000,max_pages=1,page_count=1,
        row_count=len(rows),fields=schema['fields'],raw_response_binding=rawref,error_code='0',
        provider_date_basis='EVERY_RESPONSE_ROW_EXACT_DATE_NOT_INFERRED_FROM_REQUEST')
    receipt=folder/'capture_receipt.json'
    atomic_json(receipt,dict(contract_id='DM01_A01_R3_ACTUAL_BOUNDED_SOURCE_CAPTURE_V1',
        responses={'query_daily_history_k_AStock':response},request_ledger=bind(ledger.relative_to(ROOT).as_posix()),
        sdk=package_metadata(),endpoint=endpoint,runtime_capability=bind(capability_path),executed_source=bind('scripts/capture_dm01_a01_r3_source.py'),origin='DELAYED_HISTORICAL_RETRIEVAL',
        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False,
        OHLC_authority=False,adjustment_authority=False))
    ih='data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'
    ch='data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json'
    idhead=json.loads((ROOT/ih).read_text(encoding='utf8'));calhead=json.loads((ROOT/ch).read_text(encoding='utf8'))
    records=json.loads((ROOT/idhead['identity_revision']['path']).read_text(encoding='utf8'))['records']
    eligible={r['source_security_key']:r['security_id'] for r in records if r['source_security_key'].split('.')[0] in ('SH','SZ')
        and r['list_date']<=target and (not r.get('delist_date') or r['delist_date']>=target)
        and r.get('symbol_effective_from',r['list_date'])<=target and (not r.get('symbol_effective_to') or r['symbol_effective_to']>=target)}
    assert set(eligible)=={r['code'].upper() for r in rows}
    ip=folder/'identity_instance.json';cp=folder/'calendar_instance.json'
    atomic_json(ip,dict(contract_id='SOURCE_INSTANCE_DATED_IDENTITY_UNIVERSE_V1',target_trade_date=target,
        accepted_head=bind(ih),members=[dict(source_security_key=k,security_id=v) for k,v in sorted(eligible.items())]))
    sessions=json.loads((ROOT/calhead['accepted_extension']['path']).read_text(encoding='utf8'))['sessions']
    atomic_json(cp,dict(contract_id='SOURCE_INSTANCE_DATED_CALENDAR_V1',target_trade_date=target,
        accepted_head=bind(ch),sessions=[r for r in sessions if r['trade_date']==target]))
    config=json.loads((ROOT/'config/source_authority_governance_r4.json').read_text(encoding='utf8'))
    instances={};proofs={}
    for field in ('TRADING_STATUS','ISST'):
        path=folder/('instance_'+field+'.json')
        atomic_json(path,dict(contract_id='SOURCE_AUTHORITY_SOURCE_INSTANCE_POLICY_V1',field_id=field,
            source_family='BAOSTOCK_DATED_FIELD_PROVIDER',target_trade_date=target,provider_date=target,
            raw_artifact=rawref,capture_receipt=bind(receipt.relative_to(ROOT).as_posix()),observed_at=observed,
            received_at=received,source_revision='sha256:'+rawref['sha256'],schema_contract=bind(schema_path),
            identity_binding=bind(ip.relative_to(ROOT).as_posix()),calendar_binding=bind(cp.relative_to(ROOT).as_posix()),
            query_status='PASS_NONEMPTY_BOUNDED_EXACT_DATE',origin='DELAYED_HISTORICAL_RETRIEVAL',
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False))
        instances[field]=bind(path.relative_to(ROOT).as_posix())
        rule=next(r for r in config['field_rules'] if r['field_id']==field)
        proofs[field]=require_formal_source(ROOT,rule,consumer_contract_id='DM01_FINAL_ALL_NINE',
            target_trade_date=target,instance_binding=instances[field])['instance']
    assert bind(registry)==before
    result=dict(status='PASS',target_trade_date=target,raw_response=rawref,capture_receipt=bind(receipt.relative_to(ROOT).as_posix()),
        instances=instances,actual_global_gate_readback=proofs,producer_registry_before=before,producer_registry_after=bind(registry),
        same_accepted_producer_and_registry_unchanged=True,human_producer_reacceptance_required=False,
        origin='DELAYED_HISTORICAL_RETRIEVAL',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
        first_available_at_target_proven=False,request_count=sum(v['count'] for v in json.loads(ledger.read_text(encoding='utf8'))['by_shanghai_date'].values()),row_count=len(rows))
    atomic_json(ROOT/('reports/audits/DM01_A01_R3_'+target.replace('-','')+'_SOURCE_CAPTURE_R1.json'),result)
    print(json.dumps(dict(status='PASS',target=target,rows=len(rows),instances=instances)))
if __name__=='__main__':main()
