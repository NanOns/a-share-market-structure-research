"""Transaction fault injection; simulation is separate from numeric admission."""
import json
from pathlib import Path
import pytest
from workbench_analysis import operational_successor_release_v1 as release
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.tdx_official_daily_source import sha256_file
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import digest


@pytest.fixture
def simulated(tmp_path,monkeypatch):
    root=tmp_path;head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    monkeypatch.setenv('TDX_ROOT',str(root/'readonly_tdx'))
    atomic_json(root,head,dict(accepted_trade_date='2026-10-08',simulation=True))
    archive=root/'data/v4/predecessors'/ (sha256_file(head)+'.json')
    archive.parent.mkdir(parents=True);archive.write_bytes(head.read_bytes())
    candidate=dict(accepted_trade_date='2026-10-09',predecessor=ref(root,archive),simulation=True)
    monkeypatch.setattr(release,'validate',lambda *a:True)
    monkeypatch.setattr(release,'verify_policy',lambda *a:True)
    return root,head,candidate


def test_readback_failure_exact_rollback(simulated):
    root,head,candidate=simulated;before=head.read_bytes()
    with pytest.raises(ValueError,match='HTTP_SAME_TOKEN'):
        release.promote(root,candidate,sha256_file(head),lambda _:dict(status='PASS',context_token='wrong'))
    assert head.read_bytes()==before


def test_stale_cas_rejected_without_write(simulated):
    root,head,candidate=simulated;before=head.read_bytes()
    with pytest.raises(ValueError,match='STALE_OPERATIONAL'):
        release.promote(root,candidate,'0'*64,lambda _:None)
    assert head.read_bytes()==before


def test_success_and_restart_transaction(simulated):
    root,head,candidate=simulated
    result=release.promote(root,candidate,sha256_file(head),lambda c:dict(status='PASS',context_token=digest(c),accepted_trade_date=c['accepted_trade_date']))
    assert result['status']=='PUBLISHED'
    before=head.read_bytes();release.recover(root);assert head.read_bytes()==before


def test_exact_candidate_prepares_remaining_pg_authorities_before_validation(simulated,monkeypatch):
    from workbench_db import v4_successor_pg_authority_preparation_v1 as preparation
    from workbench_service import native_current_snapshot_v3
    root,head,candidate=simulated;candidate['exact_daily_adjustment_contract']='exact-r1'
    events=[]
    monkeypatch.setattr(preparation,'prepare_remaining',lambda r,c:events.append('prepare'))
    monkeypatch.setattr(release,'validate',lambda *a:events.append('validate'))
    monkeypatch.setattr(native_current_snapshot_v3,'prepare_joint',lambda *a,**k:None)
    monkeypatch.setattr(release,'_commit_pointers',lambda *a:events.append('commit') or {'status':'PUBLISHED'})
    release.promote(root,candidate,sha256_file(head),lambda c:dict(status='PASS',context_token=digest(c),accepted_trade_date=c['accepted_trade_date']))
    assert events==['prepare','validate','commit']


def test_crash_after_cas_recovers_exact_predecessor(simulated):
    root,head,candidate=simulated;before=head.read_bytes()
    atomic_json(root,root/'runtime/dynamic_daily/publication_transaction.json',
                dict(state='CAS_COMPLETE_READBACK_PENDING',predecessor=candidate['predecessor'],candidate_token=digest(candidate)))
    atomic_json(root,head,candidate);release.recover(root)
    assert head.read_bytes()==before
