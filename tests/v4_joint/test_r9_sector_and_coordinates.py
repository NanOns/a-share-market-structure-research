"""R9 板块动态总体和两代精确仿射坐标回归。"""
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from sector.candidate_lifecycle_v1 import build_candidate_lifecycle
from sector.lifecycle_reconstructed_v1 import _value
from workbench_service.core_product_bff_r1 import _retained_price_coordinate


@pytest.mark.parametrize('base', ['TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',
                                 'TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE'])
def test_final_presentation_preserves_complete_legal_coordinate(base):
    value=base+':'+'a'*64
    assert _retained_price_coordinate(value)==value
    assert _retained_price_coordinate(base) is None
    assert _retained_price_coordinate(base+':'+'g'*64) is None
    assert _retained_price_coordinate('RAW:'+'a'*64) is None


@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf'),True])
def test_sector_nonfinite_inputs_cannot_be_classified_neutral(value):
    assert _value({'fields':{'sector_rs5':{'value':value,'quality':'KNOWN'}}},'sector_rs5') is None


def test_new_sector_uses_current_scope_and_missing_history_stays_unknown(tmp_path):
    sessions=['2026-03-02','2026-03-03','2026-03-04','2026-03-05','2026-03-06']
    candidate=dict(accepted_trade_date=sessions[-1],published_sessions=sessions,owners={})
    def save(day,domain,rows):
        path=tmp_path/day/(domain+'.gz');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(gzip.compress(('\n'.join(json.dumps(row) for row in rows)+'\n').encode(),mtime=0))
        return dict(path=path.relative_to(tmp_path).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    for day in sessions:
        ids=['SYN-SECTOR-A']+(['SYN-SECTOR-NEW'] if day==sessions[-1] else [])
        rows=[dict(sector_id=sid,trade_date=day,fields={}) for sid in ids]
        rotations=[dict(sector_id=sid,target_trade_date=day,rotation={'output_state':'NONE'}) for sid in ids]
        candidate['owners'][day]={'sector':save(day,'sector',rows),'rotation':save(day,'rotation',rotations)}
    root=Path(__file__).resolve().parents[2]
    result=build_candidate_lifecycle(tmp_path,candidate,root)
    assert set(result['items'])=={'SYN-SECTOR-A','SYN-SECTOR-NEW'}
    assert result['items']['SYN-SECTOR-NEW']['maturity']['current']=='UNKNOWN'
    assert result['items']['SYN-SECTOR-NEW']['input_completeness']['observed_sessions']==1
    # Duplicate input must never disappear through dict construction.
    rows=[dict(sector_id='SYN-SECTOR-A',trade_date=sessions[-1],fields={})]*2
    candidate['owners'][sessions[-1]]['sector']=save(sessions[-1],'sector-duplicate',rows)
    with pytest.raises(ValueError,match='DENOMINATOR_MISMATCH'):
        build_candidate_lifecycle(tmp_path,candidate,root)


def test_market_reprojection_cannot_borrow_a_changed_source_scope(tmp_path,monkeypatch):
    from workbench_analysis import r6_candidate_market_stress as market
    from workbench_analysis.operational_successor_v1 import digest
    original={'accepted_trade_date':'2026-03-03','owners':{'2026-03-03':{'core':{'sha256':'a'*64}}}}
    path=tmp_path/'original.json';path.write_text(json.dumps(original),encoding='utf8')
    binding=dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    scope=dict(contract_id='V4_R9_CANDIDATE_OWNER_SCOPE_V1',T0='2026-03-03',
        market_reprojection_contract='R9_MARKET_CORE_SOURCE_REPROJECTION_V1',production_admission=False,
        source_head=binding,source_context_token=digest(original),source_owners=original['owners']['2026-03-03'])
    candidate=dict(original,r9_derivation_scope=scope)
    monkeypatch.setattr(market,'_stress_window_days',lambda c:[])
    assert market.build_candidate_market_stress(tmp_path,candidate)['production_admission'] is False
    for change in ({'production_admission':True},{'source_context_token':'b'*64},{'T0':'2026-03-04'}):
        with pytest.raises(ValueError,match='REPROJECTION_SCOPE_MISMATCH'):
            market.build_candidate_market_stress(tmp_path,dict(candidate,r9_derivation_scope=dict(scope,**change)))
