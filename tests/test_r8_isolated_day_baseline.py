import json
import pytest
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis import operational_revision_guard_r1 as guard


def fixture(tmp_path,monkeypatch):
    policy_binding=dict(path='policy.json',sha256='a'*64)
    parent=dict(accepted_trade_date='2026-10-14',release_policy=policy_binding,accepted_algorithm_bindings=[])
    original=tmp_path/'candidate.json';original.write_text(json.dumps(parent))
    proof=tmp_path/'acceptance.json'
    record=dict(contract_id='R8_ISOLATED_DAY_NUMERIC_ACCEPTANCE_R1',scope='ISOLATED_CANDIDATE_HEAD_ONLY',
        acceptance='PASS_NUMERIC_DAY_QA',production_admitted=False,trade_date='2026-10-14',candidate=ref(tmp_path,original))
    proof.write_text(json.dumps(record));parent['r8_isolated_day_acceptance']=ref(tmp_path,proof)
    checked=[]
    def verify(*args,**kwargs):
        assert kwargs==dict(candidate_only=True);checked.append('policy')
        return dict(publication_ready=False,accepted_algorithm_bindings=[]),policy_binding
    monkeypatch.setattr('workbench_analysis.operational_daily_exact_policy_v2.verify',verify)
    monkeypatch.setattr('workbench_analysis.operational_successor_v1.validate',lambda *args:checked.append('full numeric day'))
    return parent,dict(adjustment_contract=dict(policy=policy_binding)),proof,record,checked


def test_next_candidate_day_rechecks_complete_numeric_day_and_candidate_policy(tmp_path,monkeypatch):
    parent,generation,*rest=fixture(tmp_path,monkeypatch)
    assert guard.isolated_day_baseline(tmp_path,parent,generation)==([],parent['release_policy'],True)
    assert rest[-1]==['policy','full numeric day']


@pytest.mark.parametrize('kind',['changed-parent','production-claim','wrong-date','wrong-policy'])
def test_isolated_receipt_cannot_admit_changed_or_unproved_day(tmp_path,monkeypatch,kind):
    parent,generation,proof,record,checked=fixture(tmp_path,monkeypatch)
    if kind=='changed-parent':parent['extra']='changed after QA'
    elif kind=='wrong-policy':generation['adjustment_contract']['policy']={}
    else:
        if kind=='production-claim':record['production_admitted']=True
        else:record['trade_date']='2026-10-15'
        proof.write_text(json.dumps(record));parent['r8_isolated_day_acceptance']=ref(tmp_path,proof)
    with pytest.raises(ValueError):guard.isolated_day_baseline(tmp_path,parent,generation)
    assert not checked
