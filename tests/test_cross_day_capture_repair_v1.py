"""Synthetic different Heads; no future real session or accepted Head mutation."""
import gzip
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.producer_bootstrap_v1 import capture_daily_sources, optional_step
from workbench_analysis.strict_source_candidate_v2 import freeze_for_review
from workbench_analysis.source_scope_reconciliation_v1 import reconcile


@pytest.fixture
def chain(tmp_path, monkeypatch):
    day = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    previous = (datetime.fromisoformat(day)-timedelta(days=1)).date().isoformat()
    def doc(name, value): return publish(tmp_path, 'inputs/'+name+'.json', value)
    def rows(name, value):
        p=tmp_path/'inputs'/ (name+'.gz');p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(gzip.compress('\n'.join(json.dumps(r) for r in value).encode()))
        return ref(tmp_path,p)
    now=datetime.now(timezone.utc).isoformat()
    member=tmp_path/'inputs/current_members';member.parent.mkdir(parents=True,exist_ok=True)
    member.write_bytes(b'new day actual member bytes')
    mb=ref(tmp_path,member)
    old_members=rows('old_members',[dict(security_id='OLD',sector_id='B0')])
    old_snapshot=doc('old_snapshot',dict(sources=[dict(address=str(member),sha256='0'*64)],memberships=old_members))
    old_life=doc('old_life',dict(active_security_ids=['OLD']))
    old_head=dict(accepted_trade_date=previous,owners={previous:dict(lifecycle=old_life)},membership_snapshot=old_snapshot)
    p=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(old_head))
    native=doc('native',dict(observed_at=now,requested_at=now))
    target=doc('target',dict(source_available_at=now,source_transport_v2=dict(requested_at=now)))
    freeze=doc('freeze',dict(target_session=day,observed_at=now,native_baostock=native,
        tdx=dict(target,path=str(tmp_path/target['path'])),normalized=dict(daily=dict(rows=[dict(code='SH.600001'),dict(code='SZ.000002')]))))
    paths=['src/workbench_analysis/r43_focus_replay.py','config/research_attention_v3.yaml',
        'src/workbench_analysis/strict_source_candidate_v2.py','src/workbench_analysis/full_state_signal_candidate_v1.py']
    for path in paths:
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic identity')
    p=tmp_path/'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json'
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(dict(session_dates=[day])))
    monkeypatch.setattr('workbench_analysis.producer_bootstrap_v1.official_sessions',lambda root:[day])
    def new_head(codes=('SH.600001','SZ.000002'),states=('ACTUAL_TRADED','SUSPENDED'),member_binding=mb):
        ids=['NEW','RENAMED'][:len(codes)]
        life=doc('life_'+str(len(codes))+member_binding['sha256'][:4],dict(active_security_ids=ids,
            source_rows=[dict(security_id=s,source_security_key=c,trade_date=day,status=t) for s,c,t in zip(ids,codes,states)]))
        memberships=rows('members_'+member_binding['sha256'][:4],[dict(security_id=s,sector_id='B1') for s in ids])
        snapshot=doc('snapshot_'+member_binding['sha256'][:4],dict(sources=[dict(member_binding,address=str(member))],memberships=memberships))
        common=[dict(security_id=s,trade_date=day,PIT_ELIGIBLE=True,target_values={},normal_evidence={},
            confirmation=dict(scenario_evidence=[dict(scenario='LAUNCH_CONFIRM',status='FALSE')])) for s in ids]
        owner=dict(lifecycle=life,raw=rows('raw',common),core=rows('core',common),prewatch=rows('prewatch',common))
        return doc('head_'+str(len(codes))+member_binding['sha256'][:4],dict(accepted_trade_date=day,owners={day:owner},membership_snapshot=snapshot))
    return tmp_path,day,freeze,new_head,member


def test_real_capture_and_strict_calls_reconcile_changed_universe(chain):
    root,day,freeze,new_head,member=chain
    original_head=(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    capture=capture_daily_sources(root,day,freeze)
    initial=json.loads((root/capture['path']).read_bytes())
    assert initial['scope_class']=='PRELIMINARY_PREVIOUS_HEAD_SCOPE'
    assert initial['capture_status']=='SOURCE_BYTES_CAPTURED' and initial['security_ids']==['OLD']
    head=new_head()
    strict=freeze_for_review(root,capture_binding=capture,candidate_binding=head,trade_date=day)
    result=json.loads((root/strict['path']).read_bytes())
    receipt=json.loads((root/result['scope_reconciliation']['receipt']['path']).read_bytes())
    assert receipt['status']=='SAME_DAY_SCOPE_RECONCILED'
    assert receipt['added_security_ids']==['NEW','RENAMED'] and receipt['removed_security_ids']==['OLD']
    assert receipt['original_source_receipts']==initial['sources']
    assert receipt['original_captured_at']==initial['captured_at']
    assert result['candidate_status']=='STRICT_SOURCE_CANDIDATE_READY_FOR_REVIEW'
    assert capture_daily_sources(root,day,freeze)==capture
    assert freeze_for_review(root,capture_binding=capture,candidate_binding=head,trade_date=day)==strict
    assert (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()==original_head


@pytest.mark.parametrize('change',['member_after_capture','missing_new_security','wrong_date','interruption'])
def test_changes_gaps_and_nonblocking(chain,change):
    root,day,freeze,new_head,member=chain
    capture=capture_daily_sources(root,day,freeze)
    if change=='member_after_capture':
        member.write_bytes(b'later bytes')
        head=new_head(member_binding=ref(root,member))
    else: head=new_head(codes=('SH.600001',)) if change=='missing_new_security' else new_head()
    if change=='wrong_date':
        with pytest.raises(ValueError,match='SCOPE_TARGET_DATE'):reconcile(root,capture_binding=capture,candidate_binding=head,trade_date='2999-01-01')
        return
    if change=='interruption':
        def fail():raise OSError('WORK_INTERRUPTED')
        assert optional_step(fail)['main_flow_blocked'] is False
        assert capture_daily_sources(root,day,freeze)==capture
        return
    receipt=reconcile(root,capture_binding=capture,candidate_binding=head,trade_date=day)
    result=json.loads((root/receipt['path']).read_bytes())
    assert result['status']=='SOURCE_GAPS'
    assert ('SAME_DAY_MEMBERSHIP_ORIGINAL_BYTES_INCOMPLETE' if change=='member_after_capture' else 'SAME_DAY_UNIVERSE_SOURCE_BYTES_INCOMPLETE') in result['source_gaps']
