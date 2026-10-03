from copy import deepcopy
from pathlib import Path
import pytest
from workbench_analysis.v4_13_io import envelope
from workbench_analysis.v4_13_accepted_contract_package import current_contracts as FrozenContracts
from workbench_analysis.v4_13_profile_runtime import fold_quality,copy_structure,dual_enrichment,sector_snapshot
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def contracts():return FrozenContracts(ROOT)
# Independent hand-authored metadata oracle; no runtime helper builds expected.
@pytest.mark.parametrize('qualities,expected',[
(['KNOWN','UNKNOWN'],'DEGRADED'),(['KNOWN','NOT_IMPLEMENTED'],'DEGRADED'),(['UNKNOWN','NOT_IMPLEMENTED'],'UNKNOWN'),(['NOT_APPLICABLE','NOT_APPLICABLE'],'NOT_APPLICABLE'),(['KNOWN','KNOWN'],'KNOWN')])
def test_B01_B02_B10_literal_quality(contracts,qualities,expected):
    assert fold_quality(qualities,contracts.config['quality_map']['component_pair_table'])==expected

def test_B03_no_eligible(contracts):
    assert sector_snapshot(envelope(None,'NOT_APPLICABLE',None),None,contracts)['quality']=='NOT_APPLICABLE'
def test_B04_uncertain_selection(contracts):
    r=sector_snapshot(envelope(),None,contracts)
    assert r['value']['selected_sector_id'] is None
    assert r['value']['loo_confirmed_raw']['quality']=='NOT_IMPLEMENTED'
    assert r['quality']=='UNKNOWN'
def test_B05_structure_unavailable(contracts):
    r=copy_structure(None,contracts);assert len(r)==10 and all(v['quality']=='UNKNOWN' for v in r.values())
@pytest.mark.parametrize('anchor',['A','B'])
def test_B06_B07_exact_copy_no_anchor_reselection(contracts,anchor):
    row=dict(active_selection={'active_anchor_id':anchor,'quality':'KNOWN'},active_projection={'support_state':'HELD','retest_count':3},anchor_states=[dict(anchor_id=anchor,output_envelope={'anchor_view_asof_t':{'value':{'coordinate':100},'quality':'KNOWN','reason':None},'structure_health':{'value':'HEALTHY','quality':'KNOWN','reason':None}})],basic_breakout_state='BREAKOUT_TENTATIVE',events=[{'id':'E'}])
    before=deepcopy(row);r=copy_structure(row,contracts,{'path':'fixture'})
    assert r['active_anchor_id']['value']==anchor;assert r['retest_count']['value']==3
    assert r['anchor_view_asof_t']['value']=={'coordinate':100};assert r['support_state']['value']=='HELD';assert row==before
@pytest.mark.parametrize('rq,sq,expected',[('KNOWN','UNKNOWN','DEGRADED'),('UNKNOWN','KNOWN','DEGRADED')])
def test_B08_B09_independent_dual_sources(contracts,rq,sq,expected):
    r=dual_enrichment(envelope('STABLE' if rq=='KNOWN' else None,rq,None),envelope({'support':'HELD'} if sq=='KNOWN' else None,sq,None),contracts)
    assert r['rotation_core_state']==('STABLE' if rq=='KNOWN' else None)
    assert r['structure_component']==({'support':'HELD'} if sq=='KNOWN' else None);assert r['combined_quality']==expected
@pytest.mark.parametrize('perturb',['context','D1'])
def test_B11_B12_no_input_writeback(contracts,perturb):
    raw={'A':True,'C':False,'B0':False,'B1':'NONE','B2':None};before=deepcopy(raw)
    dual_enrichment(envelope('STABLE','KNOWN',None),envelope({'anchor_id':perturb},'KNOWN',None),contracts)
    sector_snapshot(envelope(),None,contracts);assert raw==before

def test_selected_context_lossless_component_independence(contracts):
    context=dict(sector_id='I',sector_type='INDUSTRY',membership_basis='PIT_OBSERVED',b0={'output_state':'TRUE','reason_codes':[]},b2={'confirmed_reason':'NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE','warm_reason':'AUD_AMOUNT_A_06_OPEN'},native_fields={'base_seed_width_adjusted':{'value':0.25,'quality':'ACCEPTED','reason_code':None}},rotation={'output_state':'ROTATION_ACCEPTED','reason_codes':[]},relative_sector_state={'value':'LEADING_STABLE','quality':'KNOWN','reason':None})
    result=sector_snapshot(envelope('I','KNOWN',None),context,contracts)
    assert result['value']['loo_b0_raw']['value'] is True
    assert result['value']['rotation_core_state']['value']=='ROTATION_ACCEPTED'
    assert result['value']['adjusted_seed_width']['value']==0.25
    assert result['value']['loo_confirmed_raw']['quality']=='NOT_IMPLEMENTED'
    assert result['value']['emergence']['quality']=='UNKNOWN'
    assert result['quality']=='DEGRADED'
def test_source_known_null_and_unknown_reason_are_not_reclassified(contracts):
    row={'active_selection':{'active_anchor_id':None,'quality':'KNOWN','reason':'NO_ACTIVE_ANCHOR'},'active_projection':{},'anchor_states':[],'basic_breakout_state':'UNKNOWN','breakout_projection_quality':'UNKNOWN','breakout_projection_reason':['MISSING_ACCEPTED_ATR'],'events':[]}
    result=copy_structure(row,contracts,{'path':'fixture'})
    assert result['active_anchor_id']['quality']=='KNOWN' and result['active_anchor_id']['value'] is None
    assert result['basic_breakout_state']['value']=='UNKNOWN' and result['basic_breakout_state']['reason']==['MISSING_ACCEPTED_ATR']
