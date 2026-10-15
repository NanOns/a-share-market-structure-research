import json
from pathlib import Path

import pytest

from workbench_analysis import operational_revision_guard_r1 as guard
from workbench_analysis.r43_owner_replay import ref

ROOT=Path(__file__).resolve().parents[1]
BEFORE=(Path(__file__).parent/'fixtures/r8_owner_adapter_before.txt').read_text(encoding='utf8')
AFTER=(ROOT/'src/workbench_analysis/operational_owner_adapter_v1.py').read_text(encoding='utf8')
MODULE='src/workbench_analysis/operational_owner_adapter_v1.py'


def test_real_accepted_adapter_allows_only_r8_lifecycle_plumbing():
    assert guard.lifecycle_adapter_only(BEFORE,AFTER)


@pytest.mark.parametrize('after',[
    AFTER+'\nUNAUTHORIZED = 1\n',
    AFTER.replace('private_scope(market,','private_scope(focus,'),
    AFTER.replace('required_active_ids=active_security_ids','required_active_ids=set()'),
])
def test_market_or_identity_semantic_change_is_not_admitted(after):
    assert after!=AFTER
    assert not guard.lifecycle_adapter_only(BEFORE,after)


def test_candidate_allowance_never_grants_production_or_numeric_kernel_admission(tmp_path,monkeypatch):
    previous=tmp_path/'before.py';previous.write_text(BEFORE,encoding='utf8')
    executed=tmp_path/'after.py';executed.write_text(AFTER,encoding='utf8')
    kernel=tmp_path/'core.py';kernel.write_text('accepted kernel',encoding='utf8')
    old=[dict(ref(tmp_path,previous),module_path=MODULE),dict(ref(tmp_path,kernel),module_path='src/v4/core.py')]
    current=[dict(ref(tmp_path,executed),module_path=MODULE),old[1]]
    generation=tmp_path/'generation.json'
    generation.write_text(json.dumps(dict(gbbq='factor',member_sources={})),encoding='utf8')
    parent=dict(accepted_trade_date='2026-10-13',source_registry={'2026-10-13':dict(generation=ref(tmp_path,generation))})
    monkeypatch.setattr(guard,'accepted_baseline',lambda *args:(old,None,True))
    normal=guard.detect(tmp_path,parent,'factor',{},execution_bindings=current)
    assert normal['revisions']==['NUMERIC_ALGORITHM_REVISION:'+MODULE]
    candidate=guard.detect(tmp_path,parent,'factor',{},execution_bindings=current,candidate_only=True)
    assert candidate['status']=='APPEND_DAY'
    assert candidate['candidate_driver_admissions'][0]['production_admitted'] is False
    assert candidate['numeric_bindings'][0]['unchanged'] is False
    revised=tmp_path/'revised.py';revised.write_text('revised kernel',encoding='utf8')
    result=guard.detect(tmp_path,parent,'factor',{},execution_bindings=[current[0],dict(ref(tmp_path,revised),module_path='src/v4/core.py')],candidate_only=True)
    assert result['revisions']==['NUMERIC_ALGORITHM_REVISION:src/v4/core.py']
