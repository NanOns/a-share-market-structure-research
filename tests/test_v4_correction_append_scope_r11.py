import json
import pytest
from workbench_db import v4_profile_semantic_corrections_pg_v1 as module

@pytest.fixture
def sample(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'checked',lambda root,binding:root/binding['path'])
    old={'2026-10-12':{'profile':{'path':'profile12'}}}
    binding={'path':'authority.json'}
    prior=dict(owners=old,accepted_trade_date='2026-10-12',**{module.KEY:binding})
    (tmp_path/'prior.json').write_text(json.dumps(prior))
    candidate=dict(owners=dict(old,**{'2026-10-13':{'profile':{'path':'profile13'}}}),accepted_trade_date='2026-10-13',predecessor={'path':'prior.json'},**{module.KEY:binding})
    authority=dict(contract_id=module.CONTRACT,source_profiles={'2026-10-12':old['2026-10-12']['profile']},dates={'2026-10-12':{'original_profile':old['2026-10-12']['profile'],'security_ids':[]}},PIT_ELIGIBLE=False,AS_RECORDED=False)
    (tmp_path/'authority.json').write_text(json.dumps(authority))
    return tmp_path,candidate


def test_single_append_preserves_old_patch_and_new_day_noop(sample):
    root,candidate=sample;original=[{'security_id':'new'}]
    assert set(module.load(root,candidate)['dates'])=={'2026-10-12'}
    assert module.apply(root,candidate,'2026-10-13',original) is original
    assert module.field_binding(root,candidate,'2026-10-13','new') is None
    assert module.attest(root,candidate,'2026-10-13') is None


def test_changed_historical_owner_is_rejected(sample):
    root,candidate=sample;candidate['owners']['2026-10-12']={'profile':{'path':'changed'}}
    with pytest.raises(ValueError,match='PREDECESSOR_OWNER_CHANGED'):module.load(root,candidate)


def test_no_predecessor_subset_is_rejected(sample):
    root,candidate=sample;candidate.pop('predecessor')
    with pytest.raises(ValueError,match='OWNER_CONSERVATION'):module.load(root,candidate)


def test_changed_authority_binding_is_rejected(sample):
    root,candidate=sample;candidate[module.KEY]=dict(candidate[module.KEY],sha256='different')
    with pytest.raises(ValueError,match='INHERITANCE_BINDING'):module.load(root,candidate)


def test_multiple_append_days_keep_original_correction_scope(sample):
    root,candidate=sample
    (root/'day13.json').write_text(json.dumps(candidate))
    later=dict(candidate,owners=dict(candidate['owners'],**{'2026-10-14':{'profile':{'path':'profile14'}}}),accepted_trade_date='2026-10-14',predecessor={'path':'day13.json'})
    assert set(module.load(root,later)['dates'])=={'2026-10-12'}
    rows=[{'security_id':'new'}]
    assert module.apply(root,later,'2026-10-14',rows) is rows


def test_broken_intermediate_append_is_rejected(sample):
    root,candidate=sample
    candidate['owners']['2026-10-12']={'profile':{'path':'changed'}}
    (root/'day13.json').write_text(json.dumps(candidate))
    later=dict(candidate,owners=dict(candidate['owners'],**{'2026-10-14':{'profile':{'path':'profile14'}}}),accepted_trade_date='2026-10-14',predecessor={'path':'day13.json'})
    with pytest.raises(ValueError,match='PREDECESSOR_OWNER_CHANGED'):module.load(root,later)
