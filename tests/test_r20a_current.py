import json
from copy import deepcopy
from pathlib import Path
import pytest
from scripts import validate_r20a_current as oracle
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_14_authority import ReplayAuthority
ROOT=Path(__file__).resolve().parents[1]
def test_current_reader_injected_without_historical_validator(monkeypatch):
    import scripts.validate_r17r1_active_closure as historical
    monkeypatch.setattr(historical,'validate',lambda *a:(_ for _ in ()).throw(AssertionError('HISTORICAL_CALLED')))
    a=CurrentStageAuthority(ROOT);r=ReplayAuthority(ROOT,a)
    assert r.head_ref['path']=='data/v4/V4_14_ACCEPTED_HEAD.json'
    assert len(a.owners)==8 and r.previous('2026-09-28')=='2026-09-24'
    assert a.head['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED'
def test_independent_gate():assert oracle.validate()['R20A_CURRENT_STAGE_AUTHORITY']=='PASS_LOCAL'
@pytest.mark.parametrize('change',['range','entry','binding','digest','data','production','shadow','focus','pit'])
def test_independent_current_negatives(change):
    s=deepcopy(oracle.read(oracle.STAGE));h=deepcopy(oracle.read('data/v4/V4_14_ACCEPTED_HEAD.json'))
    if change=='range':s['accepted_stage_range']='V4_00_TO_V4_13_ACCEPTED'
    elif change=='entry':s['v4_14_entry']='CONTRACT_FREEZE_ONLY_NOT_REPLAY_PASS'
    elif change=='binding':s.pop('v4_14_binding')
    elif change=='digest':s['v4_14_binding']['sha256']='0'*64
    elif change=='data':h['bindings']['data_head']['sha256']='0'*64
    elif change=='pit':h['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    else:h[change]=True
    with pytest.raises(ValueError):oracle.validate(s,h)
def test_reader_no_latest_resolution():
    text=(ROOT/'src/workbench_analysis/v4_current_stage_authority.py').read_text()
    assert 'glob(' not in text and 'listdir(' not in text and 'validate_r17r1' not in text
