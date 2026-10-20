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


def test_readback_failure_exact_rollback(simulated,monkeypatch):
    root,head,candidate=simulated;before=head.read_bytes()
    calls=[]
    def cas(_root,value,expected):
        calls.append((value,expected))
        if len(calls)==1:
            return dict(candidate=value,head_sha256=digest(value),generation=2,
                predecessor=json.loads(before),predecessor_sha256=expected)
        return dict(candidate=value,head_sha256=digest(value),generation=3,
            predecessor=candidate,predecessor_sha256=expected)
    from workbench_db import v4_operational_live_head_pg_r1 as live_head
    monkeypatch.setattr(live_head,'compare_and_swap',cas)
    with pytest.raises(ValueError,match='HTTP_SAME_TOKEN'):
        release.promote(root,candidate,sha256_file(head),lambda _:dict(status='PASS',context_token='wrong'))
    assert head.read_bytes()==before
    assert len(calls)==2 and calls[1][0]==json.loads(before)


def test_stale_cas_rejected_without_write(simulated):
    root,head,candidate=simulated;before=head.read_bytes()
    with pytest.raises(ValueError,match='STALE_OPERATIONAL'):
        release.promote(root,candidate,'0'*64,lambda _:None)
    assert head.read_bytes()==before


def test_success_and_restart_transaction(simulated,monkeypatch):
    root,head,candidate=simulated
    from workbench_db import v4_operational_live_head_pg_r1 as live_head
    monkeypatch.setattr(live_head,'compare_and_swap',lambda _root,value,expected:dict(candidate=value,head_sha256=digest(value),
        generation=2,predecessor=json.loads(head.read_bytes()),predecessor_sha256=expected))
    result=release.promote(root,candidate,sha256_file(head),lambda c:dict(status='PASS',context_token=digest(c),accepted_trade_date=c['accepted_trade_date']))
    assert result['status']=='PUBLISHED'
    before=head.read_bytes();assert release.recover(root)['status']=='PG_ATOMIC_HEAD_NO_FILE_RECOVERY';assert head.read_bytes()==before


def test_exact_candidate_prepares_remaining_pg_authorities_before_validation(simulated,monkeypatch):
    from workbench_db import v4_successor_pg_authority_preparation_v1 as preparation
    from workbench_service import native_current_snapshot_v3
    root,head,candidate=simulated;candidate['exact_daily_adjustment_contract']='exact-r1'
    events=[]
    monkeypatch.setattr(preparation,'prepare_remaining',lambda r,c:events.append('prepare'))
    monkeypatch.setattr(release,'validate',lambda *a:events.append('validate'))
    from workbench_db import v4_operational_live_head_pg_r1 as live_head
    monkeypatch.setattr(live_head,'compare_and_swap',lambda r,c,e:events.append('commit') or dict(
        candidate=c,head_sha256=digest(c),generation=2,predecessor={},predecessor_sha256=e))
    release.promote(root,candidate,sha256_file(head),lambda c:dict(status='PASS',context_token=digest(c),accepted_trade_date=c['accepted_trade_date']))
    assert events==['prepare','validate','commit']


def test_recovery_never_reads_or_restores_a_workspace_head_file(simulated):
    root,head,candidate=simulated
    atomic_json(root,root/'runtime/dynamic_daily/publication_transaction.json',
                dict(state='CAS_COMPLETE_READBACK_PENDING',predecessor=candidate['predecessor'],candidate_token=digest(candidate)))
    atomic_json(root,head,candidate);after=head.read_bytes()
    assert release.recover(root)['status']=='PG_ATOMIC_HEAD_NO_FILE_RECOVERY'
    assert head.read_bytes()==after
