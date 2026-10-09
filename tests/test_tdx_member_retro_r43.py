from copy import deepcopy
from pathlib import Path
import pytest
from workbench_analysis.tdx_member_retro_r43 import validate_snapshot, load, EVIDENCE
from workbench_analysis.sector_taxonomy_v2 import loo_medians
from workbench_analysis.rotation_reconstructed_r43 import advance,evaluator


def test_real_frozen_snapshot_namespace_and_falseflags():
    root=Path(__file__).resolve().parents[1]
    s=load(root/EVIDENCE/'MEMBER_SNAPSHOT_S.json')
    rows=validate_snapshot(s,root)
    assert {r['sector_type'] for r in rows}=={'INDUSTRY','THEME'}
    assert any(sum(x['source_security_key']==r['source_security_key'] for x in rows[:100])>1 for r in rows[:100])
    with pytest.raises(ValueError,match='STRICT_PIT'):validate_snapshot(s,root,strict_pit=True)
    for key,value in [('taxonomy','BAOSTOCK_CSRC_INDUSTRY'),('AS_RECORDED',True),('membership_snapshot_id','wrong'),('member_set_asof','2026-09-30')]:
        bad=deepcopy(s);bad[key]=value
        with pytest.raises(ValueError):validate_snapshot(bad,root)
    bad=deepcopy(s);bad['sources'][0]['sha256']='0'*64
    with pytest.raises(ValueError):validate_snapshot(bad,root)


def test_member_move_invalidates_only_related_group():
    rows=[dict(sector_id=s,security_id=i) for s,ids in [('INDUSTRY:A',['x','y','z']),('THEME:B',['x','a','b']),('THEME:C',['c','d','e'])] for i in ids]
    returns={x:float(i) for i,x in enumerate(['x','y','z','a','b','c','d','e'])}
    untouched=loo_medians(rows,returns,'c');before=loo_medians(rows,returns,'x')
    moved=[r for r in rows if not(r['sector_id']=='THEME:B' and r['security_id']=='b')]
    assert loo_medians(moved,returns,'c')==untouched
    assert loo_medians(moved,returns,'x')['INDUSTRY:A']==before['INDUSTRY:A']
    assert loo_medians(moved,returns,'x')['THEME:B']!=before['THEME:B']


def test_operational_episode_cannot_accept_strict_or_csrc_scope():
    for native in (dict(membership_mode='BAOSTOCK_CSRC_INDUSTRY',PIT_ELIGIBLE=False),
                   dict(membership_mode='TDX_LATEST_MEMBER_RETRO_V1',PIT_ELIGIBLE=True)):
        with pytest.raises(ValueError,match='OPERATIONAL_RETRO_ONLY'):
            advance(native,{},previous=None,prior_native=None,prior_members=None,prior_core={},prior_date='2026-09-24',calendar_sessions=[],contract={},registry={},parameters={},seed_truth={})
    function,sha=evaluator()
    assert 'acceptance' not in function.__code__.co_consts
    assert 'episode_contract_id' in function.__code__.co_consts
    assert len(sha)==64
