"""Isolated publication IO controls; no production mutation or numeric admission."""
import json
import pytest
from workbench_analysis import operational_successor_release_v1 as release
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import digest
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.tdx_official_daily_source import sha256_file
from workbench_service import native_current_snapshot_v3 as snapshot


@pytest.fixture
def coordinated(tmp_path,monkeypatch):
    head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    joint=tmp_path/snapshot.AUTHORITY
    atomic_json(tmp_path,head,{'accepted_trade_date':'2026-10-09'})
    before=head.read_bytes(); predecessor=tmp_path/'predecessor.json'
    predecessor.write_bytes(before)
    candidate={'accepted_trade_date':'2026-10-12','predecessor':ref(tmp_path,predecessor),'exact_daily_adjustment_contract':'simulation'}
    atomic_json(tmp_path,joint,{'business_token':'previous','T0':'2026-10-09'})
    old_joint=joint.read_bytes()
    prepared=tmp_path/'prepared_joint.json'
    atomic_json(tmp_path,prepared,{'business_token':digest(candidate),'T0':'2026-10-12'})
    monkeypatch.setattr(release,'validate',lambda *a:None)
    monkeypatch.setattr(release,'verify_policy',lambda *a:None)
    monkeypatch.setattr(snapshot,'prepare_joint',lambda *a:ref(tmp_path,prepared))
    return tmp_path,head,joint,candidate,before,old_joint,prepared


def test_readback_observes_both_current_authorities(coordinated):
    root,head,joint,candidate,_,_,prepared=coordinated
    def readback(c):
        assert json.loads(head.read_bytes())==c
        assert joint.read_bytes()==prepared.read_bytes()
        return {'status':'PASS','context_token':digest(c),'accepted_trade_date':c['accepted_trade_date']}
    assert release.promote(root,candidate,sha256_file(head),readback)['status']=='PUBLISHED'
    record=json.loads((root/'runtime/dynamic_daily/publication_transaction.json').read_bytes())
    assert record['state']=='COMMITTED' and record['current_joint_predecessor']


def test_failed_readback_restores_both_exact_bytes(coordinated):
    root,head,joint,candidate,before,old_joint,_=coordinated
    with pytest.raises(ValueError,match='HTTP_SAME_TOKEN'):
        release.promote(root,candidate,sha256_file(head),lambda _: {'status':'FAIL'})
    assert head.read_bytes()==before and joint.read_bytes()==old_joint


@pytest.mark.parametrize('joint_written',[False,True])
def test_incomplete_coordinated_write_recovers_exact_predecessors(coordinated,joint_written):
    root,head,joint,candidate,before,old_joint,prepared=coordinated
    previous=root/'previous_joint.json';previous.write_bytes(old_joint)
    atomic_json(root,root/'runtime/dynamic_daily/publication_transaction.json',dict(state='PREPARED',predecessor=candidate['predecessor'],candidate_token=digest(candidate),current_joint=ref(root,prepared),current_joint_predecessor=ref(root,previous)))
    atomic_json(root,head,candidate)
    if joint_written:joint.write_bytes(prepared.read_bytes())
    release.recover(root)
    assert head.read_bytes()==before and joint.read_bytes()==old_joint


def test_recovery_rejects_a_third_party_joint_without_head_mutation(coordinated):
    root,head,joint,candidate,_,old_joint,prepared=coordinated
    previous=root/'previous_joint.json';previous.write_bytes(old_joint)
    atomic_json(root,root/'runtime/dynamic_daily/publication_transaction.json',dict(state='PREPARED',predecessor=candidate['predecessor'],candidate_token=digest(candidate),current_joint=ref(root,prepared),current_joint_predecessor=ref(root,previous)))
    atomic_json(root,head,candidate);current_head=head.read_bytes()
    atomic_json(root,joint,{'business_token':'unrelated'});current_joint=joint.read_bytes()
    with pytest.raises(ValueError,match='JOINT_MOVED_FAIL_CLOSED'):release.recover(root)
    assert head.read_bytes()==current_head and joint.read_bytes()==current_joint
