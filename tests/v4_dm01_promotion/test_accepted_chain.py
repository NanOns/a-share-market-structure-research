"""Exact accepted-market readback and fail-closed promotion contract probes."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from workbench_analysis.dm01_accepted_chain_v1 import (
    binding,load,require_audit,validate_chain,validate_head_v2,validate_registry_r10,
    resolve_frozen_binding,validate_historical_incremental_registry,
    HEAD_PATH,ANCHOR_SHA,AUDIT_SHA,AcceptedChainError)

ROOT=Path(__file__).resolve().parents[2]
CANDIDATE='data/v4/data_head_promotion/DM01_A01_R3_DATA_HEAD_CANDIDATE_V2_R1.json'
def read(path):return json.loads((ROOT/path).read_bytes())
@pytest.fixture(scope='module')
def head():return read(CANDIDATE)
@pytest.fixture(scope='module')
def chain(head):return load(ROOT,head['accepted_chain'])

def test_exact_real_chain_and_final_permissions(head):
    result=validate_head_v2(ROOT,head)
    assert result['status']=='PASS' and result['accepted_trade_date']=='2026-09-30'
    assert [n['trade_date'] for n in result['nodes']]==['2026-09-28','2026-09-29','2026-09-30']
    assert all(n['components']==9 for n in result['nodes'])
    degraded={c for c,p in head['component_permissions'].items() if p['status']=='DEGRADED_PASS'}
    assert degraded=={'ADJUSTED_DAILY','PERIOD_ADJUSTED','PRICE_LIMIT'}
    assert all(p['quality_counts'].get('READY')==p['row_count'] for c,p in head['component_permissions'].items() if c in degraded)
    assert not any(head['permissions'].values())

@pytest.mark.parametrize('mutation',['task_card','hash','audited_commit'])
def test_only_actual_independent_audit_is_authority(head,mutation):
    a=deepcopy(load(ROOT,head['external_acceptance_record'])['external_authority'])
    if mutation=='task_card':a['document']=binding(ROOT,'docs/evidence/source_authority/V4_DM01_A01_R3_EXTERNAL_ACCEPTANCE_AND_DATA_HEAD_PROMOTION_TASK_20261001.md')
    elif mutation=='hash':a['document']['sha256']='0'*64
    else:a['audited_head']='0'*40
    with pytest.raises(AcceptedChainError,match='INVALID_EXTERNAL_AUTHORITY_BINDING'):require_audit(ROOT,a)

@pytest.mark.parametrize('key',['production','shadow','focus'])
def test_production_permissions_stay_closed(head,key):
    bad=deepcopy(head);bad['permissions'][key]=True
    with pytest.raises(AcceptedChainError,match='PERMISSION_OR_TEMPORAL_OVERCLAIM'):validate_head_v2(ROOT,bad)

@pytest.mark.parametrize('key',['AS_RECORDED','first_available_at_target_proven'])
def test_reconstruction_does_not_grant_temporal_claims(head,key):
    bad=deepcopy(head);bad[key]=True
    with pytest.raises(AcceptedChainError,match='PERMISSION_OR_TEMPORAL_OVERCLAIM'):validate_head_v2(ROOT,bad)

def test_unknown_head_schema_field_rejected(head):
    bad=deepcopy(head);bad['ungoverned_field']=True
    with pytest.raises(AcceptedChainError,match='SCHEMA_FIELDS_INVALID'):validate_head_v2(ROOT,bad)

@pytest.mark.parametrize('mutation',['omit_session','wrong_parent','wrong_session','omit_component','wrong_source_instance'])
def test_chain_cannot_skip_or_substitute_accepted_nodes(chain,mutation):
    bad=deepcopy(chain)
    if mutation=='omit_session':bad['nodes'].pop(1)
    elif mutation=='wrong_parent':bad['nodes'][0]['parent']['sha256']='0'*64
    elif mutation=='wrong_session':bad['nodes'][0]['trade_date']='2026-09-29'
    elif mutation=='omit_component':bad['nodes'][0]['components'].pop('ISST')
    else:bad['nodes'][0]['source_instances']['ISST']['sha256']='0'*64
    with pytest.raises(AcceptedChainError):validate_chain(ROOT,bad)

@pytest.mark.parametrize('key',['observed_daily_producer_acceptance','capability_limitations','transition'])
def test_registry_rejects_stale_a12_current_fields(head,key):
    bad=deepcopy(load(ROOT,head['audit_registry']))
    a=next(e for e in bad['entries'] if e['audit_id']=='V4_02_STATUS_ST_SOURCE_AUTHORITY_DIVERGENCE')
    a[key]={'status':'OPEN'} if key=='transition' else 'PENDING'
    with pytest.raises(AcceptedChainError):validate_registry_r10(ROOT,bad)

def test_registry_keeps_bootstrap_open_and_history(head):
    registry=load(ROOT,head['audit_registry']);assert validate_registry_r10(ROOT,registry)
    entries={e['audit_id']:e for e in registry['entries']}
    assert entries['V4_02_STATUS_ST_SOURCE_AUTHORITY_DIVERGENCE']['history'][0]['prior_entry']['acceptance_scope']=='NO_FUNCTIONAL_CLOSURE'
    assert entries['OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS']['status']=='OPEN'
    assert entries['DM01_REAL_INCREMENTAL_BUILDERS']['production_gate'] is True
    assert entries['OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS']['formal_consumer_authorization'] is False

def test_anchor_is_exact_bytes_and_wrong_hash_never_redirects(head):
    archive=load(ROOT,head['parent_archive']);assert archive['accepted_trade_date']=='2026-09-24'
    p=resolve_frozen_binding(ROOT,dict(path=HEAD_PATH,sha256=ANCHOR_SHA,bytes=2478))
    assert binding(ROOT,p.relative_to(ROOT).as_posix())['sha256']==ANCHOR_SHA
    with pytest.raises(AcceptedChainError):resolve_frozen_binding(ROOT,dict(path=HEAD_PATH,sha256='0'*64))
    assert validate_historical_incremental_registry(ROOT)['status']=='PASS_ENGINEERING_EXPORTS'

@pytest.mark.parametrize('cap',['ADJUSTED_DAILY','PERIOD_ADJUSTED','PRICE_LIMIT'])
def test_ready_rows_cannot_upgrade_degraded_capability(head,cap):
    bad=deepcopy(head);bad['component_permissions'][cap]['status']='FULL_PASS'
    with pytest.raises(AcceptedChainError,match='CAPABILITY_PERMISSION_UPGRADE_OR_RECEIPT_MISMATCH'):validate_head_v2(ROOT,bad)

def test_current_pointer_is_audited_anchor_or_exact_promoted_v2(head):
    current=read(HEAD_PATH)
    if current['accepted_trade_date']=='2026-09-24':assert binding(ROOT,HEAD_PATH)['sha256']==ANCHOR_SHA
    else:
        assert current==head and current['accepted_trade_date']=='2026-09-30'
        receipt=read('reports/v4_joint/DM01_A01_R3_DATA_HEAD_PROMOTION_RECEIPT_R1.json')
        assert receipt['new_data_head']==binding(ROOT,HEAD_PATH)
        assert receipt['stage_head_before']==receipt['stage_head_after']==head['stage_head']
        assert not receipt['stage_head_moved'] and not any(receipt['permissions_after'].values())

def test_business_publication_history_has_explicit_archive_scope(head):
    from workbench_analysis.dm01_publication_history_reader_v1 import validate_v4_09_history,validate_v4_10_history
    from scripts import validate_v4_10_promotion_r1 as original
    saved_root=original.ROOT
    for reader in (validate_v4_09_history,validate_v4_10_history):
        result=reader()
        assert result['status']=='PASS' and result['validation_scope']=='ACCEPTED_PUBLICATION_HISTORY_ONLY'
        assert not result['business_reacceptance_performed'] and not result['production_authorization']
    assert original.ROOT is saved_root
    if read(HEAD_PATH)['accepted_trade_date']=='2026-09-30':
        assert original.validate()['checks']['P19_protected']=='FAIL'
