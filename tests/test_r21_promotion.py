"""Direct V4-15 governance, explicit replay, fail-closed promotion and rollback."""
from copy import deepcopy
from pathlib import Path
import pytest
from scripts import validate_r21_promotion as oracle
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_14_authority import ReplayAuthority
ROOT=Path(__file__).resolve().parents[1]
def test_independent_promotion():assert oracle.validate()['R21_V4_15_PROMOTION']=='PASS_LOCAL'
def test_current_and_explicit_replay(monkeypatch):
    import scripts.validate_r17r1_active_closure as historical
    monkeypatch.setattr(historical,'validate',lambda *a:(_ for _ in ()).throw(AssertionError('HISTORICAL_CALLED')))
    a=CurrentStageAuthority(ROOT);r=ReplayAuthority(ROOT,a)
    assert a.head['stage']=='V4-15' and a.current_head['path']=='data/v4/V4_15_ACCEPTED_HEAD.json'
    assert r.head['stage']=='V4-14' and r.head_ref==a.contract['predecessor_v4_14']
    assert r.previous('2026-09-28')=='2026-09-24'
    assert a.publication_authority().head['stage']=='V4-14' and a.head['stage']=='V4-15'
def test_exact_rollback_restoration():assert oracle.rollback_validation()['status']=='PASS_LOCAL'
@pytest.mark.parametrize('attack',['stage','entry','head_digest','production','shadow','focus','V4_16','pit','maturity','proved','unproved','real','realtime','audit','seal','tested'])
def test_fail_closed(attack):
    h=deepcopy(oracle.read(oracle.HEAD,ROOT));s=deepcopy(oracle.read(oracle.STAGE,ROOT))
    if attack=='stage':s['accepted_stage_range']='V4_00_TO_V4_14_ACCEPTED'
    elif attack=='entry':s['v4_15_entry']='CONTRACT_FREEZE_ONLY'
    elif attack=='head_digest':s['v4_15_binding']['sha256']='0'*64
    elif attack=='pit':h['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    elif attack=='maturity':h['CURRENT_REAL_MATURITY_EVIDENCE']='REAL'
    elif attack=='proved':h['PROVED_HORIZONS']=[1]
    elif attack=='unproved':h['UNPROVED_HORIZONS']=[]
    elif attack=='real':h['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']='PASS'
    elif attack=='realtime':h['REALTIME_ACCEPTED_COHORT_MATURITY']='PASS'
    elif attack=='audit':h['bindings']['external_audit']['sha256']='0'*64
    elif attack=='seal':h['bindings']['dm01_seal']['sha256']='0'*64
    elif attack=='tested':h['tested_source']='0'*40
    else:h[attack]=True
    with pytest.raises(ValueError):oracle.validate(head=h,stage=s)
    if attack in ['production','shadow','focus','V4_16','pit','maturity','proved','unproved','real','realtime']:
        # Reach independent semantic checks without relying on an earlier hash rejection.
        with pytest.raises(ValueError):oracle.validate_boundary(h)
def test_oracle_never_calls_writer():
    text=(ROOT/'scripts/validate_r21_promotion.py').read_text()
    assert 'promote_r21' not in text and 'glob(' not in text
