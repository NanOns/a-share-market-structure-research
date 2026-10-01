"""Exact original-byte inputs must remain consumable from the actual clean checkout."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from workbench_analysis.dm01_chain_contract_r3_3 import validate_context
from workbench_analysis import dm01_incremental_component_builders_r3_3 as b
from workbench_analysis.daily_source_freeze import build_source_freeze_manifest_v2
ROOT=Path(__file__).resolve().parents[2]

def context():
    config=json.loads((ROOT/b.CONTRACT_PATH).read_text(encoding='utf8'));ctx=b.load(config['execution_context'])
    target=ctx['sessions'][0];source=ctx['inputs'][target]
    freeze=build_source_freeze_manifest_v2(trade_date=target,sources=source['families'],changed_tdx_files=[],
        observed_at=ctx['observed_at'],ingested_at=ctx['observed_at'],system_available_at=ctx['observed_at'])
    freeze.update(inputs=source['inputs'],parent_data_head_digest=ctx['parent']['binding']['sha256'],
        calendar_publication_id=ctx['calendar']['publication_id'],identity_publication_id=ctx['identity']['publication_id'],
        field_source_instances=source['instances'],tdx_roots=['D:/new_tdx'],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    freeze['manifest_sha256']=b.digest({k:v for k,v in freeze.items() if k!='manifest_sha256'})
    return config,ctx,target,freeze

def test_original_byte_archive_exact_with_declared_Git_plane():
    config,_,_,_=context();ref=config['accepted_go_forward_head'];namespace=config['accepted_go_forward_head_namespace']
    archived=(ROOT/ref['path']).read_bytes();actual=(ROOT/namespace['path']).read_bytes()
    assert hashlib.sha256(archived).hexdigest()==ref['sha256']==namespace['sha256']
    assert hashlib.sha256(actual).hexdigest() in (namespace['sha256'],namespace['git_sha256'])
    assert json.loads(actual)==json.loads(archived)
    assert ref['path']!=namespace['path']

def test_original_tdx_capture_receipt_is_an_exact_archived_input():
    config,ctx,target,_=context()
    page=b.load(ctx['inputs'][target]['families']['TDX_PAGE_CAPTURE'])
    repair=json.loads((ROOT/'reports/audits/DM01_A01_R3_METADATA_DURABILITY_REPAIR_R2.json').read_text(encoding='utf8'))
    archived=repair['exact_original_byte_archive'];original=repair['original_capture_receipt']
    assert page['actual_capture_receipt']==archived
    assert b.sha(ROOT/archived['path'])==archived['sha256']==original['sha256']
    assert b.sha(ROOT/original['path']) in (original['sha256'],original['git_sha256'])
    assert json.loads((ROOT/original['path']).read_bytes())==b.load(archived)

@pytest.mark.parametrize('cap',['RAW_DAILY','TRADING_STATUS','ISST'])
def test_actual_final_contract_context_has_no_checkout_binding_failure(cap):
    _,ctx,target,freeze=context()
    result=validate_context(cap,target,ctx['parent'],freeze,ctx['calendar'],ctx['identity'],
        ROOT/'data/v4/dm01_candidate_staging_r3/durability_context_probe')
    assert result['target']==target and result['contract']['version']=='3.2.0'

def test_archive_does_not_authorize_changed_business_head_namespace(monkeypatch):
    config,ctx,target,freeze=context();original=b.load
    changed=deepcopy(config);changed['accepted_go_forward_head_namespace']['sha256']='0'*64
    changed['accepted_go_forward_head_namespace']['git_sha256']='1'*64
    def altered(ref):
        return changed if ref['path']==b.CONTRACT_PATH else original(ref)
    monkeypatch.setattr(b,'load',altered)
    with pytest.raises(b.ComponentBuildError,match='GO_FORWARD_BUSINESS_HEAD_NAMESPACE_CHANGED'):
        validate_context('RAW_DAILY',target,ctx['parent'],freeze,ctx['calendar'],ctx['identity'],ROOT/'data/v4/dm01_candidate_staging_r3/probe')

def test_final_durable_continuous_chain_preserves_initial_candidates():
    final=json.loads((ROOT/'reports/audits/DM01_A01_R3_CONTINUOUS_CHAIN_POSTCHECK_R3.json').read_text(encoding='utf8'))
    initial=json.loads((ROOT/'reports/audits/DM01_A01_R3_CONTINUOUS_CHAIN_POSTCHECK_R1.json').read_text(encoding='utf8'))
    assert final['status']=='PASS' and final['sessions']==initial['sessions']
    parent=final['accepted_anchor']['sha256']
    for ref in final['candidates']:
        marker=b.load(ref)
        assert marker['contract_id']=='DM01_ATOMIC_CONTINUOUS_CANDIDATE_R3_3'
        assert marker['parent_data_head_digest']==parent and len(marker['components'])==9
        assert b.load(marker['cross_postcheck_binding'])['status']=='PASS'
        parent=ref['sha256']
    for ref in initial['candidates']:
        assert hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest()==ref['sha256']
    prior=json.loads((ROOT/'reports/audits/DM01_A01_R3_CONTINUOUS_CHAIN_POSTCHECK_R2.json').read_text(encoding='utf8'))
    for ref in prior['candidates']:
        assert hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest()==ref['sha256']
