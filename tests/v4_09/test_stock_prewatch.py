from copy import deepcopy
from pathlib import Path
import pytest
from src.v4.stock_prewatch import build, digest, evaluate, load_package, project

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=load_package(ROOT)
VECTORS=PACKAGE['machine_vectors']['vectors']

def fixture_context(date='2030-01-02', count=2):
    context=dict(context_id='SYNTHETIC_CONTRACT_VECTOR:'+date,trade_date=date,knowledge_cutoff=date+'T23:59:59+08:00',
        source_publication_id='synthetic-source:'+date,profile_row_publication_id='synthetic-profile:'+date,
        core_logical_digest=digest(date),expected_identity_count=count,expected_board_counts={'SYNTHETIC_BOARD':count},
        identity_ids=[f'SYNTHETIC-ENTITY-{i}' for i in range(count)],source_bindings={'synthetic_input_revision':digest(date)})
    cores=[]; factors=[]; seeds=[]
    for security in context['identity_ids']:
        meta=dict(security_id=security,trade_date=date,formal_publication_at=date+'T08:00:00+08:00',
                  coordinate_basis='T0_CURRENT_COORDINATE',historical_as_recorded_claim=False,max_source_trade_date=date)
        cores.append(dict(meta,board='SYNTHETIC_BOARD',publication_id=context['profile_row_publication_id'],
            states={k:dict(value=v,unknown_reason=None) for k,v in dict(compression_state='COMPRESSING_STRONG',
                ma_structure_state='BULL_ALIGNED',core_extension_risk='LOW').items()}))
        factors.append(dict(meta,fields={k:dict(value=v,quality_state='OBSERVED',unknown_reason=None,
            target_trade_date=date,source_asof=date,max_source_trade_date=date,available_at=date+'T08:00:00+08:00',
            contract_id='CORE_FACTOR_V1') for k,v in dict(core_price_damage=False,rps5_delta3=10).items()}))
        seeds.append(dict(security_id=security,trade_date=date,publication_id=context['source_publication_id'],
            source_publication_id=context['profile_row_publication_id'],source_core_logical_digest=context['core_logical_digest'],
            base_seed_state='TRUE',quality='READY',model_contract_id='BASE_SEED_V1'))
    return context,cores,factors,seeds

@pytest.mark.parametrize('vector',VECTORS,ids=[v['id'] for v in VECTORS])
def test_independent_frozen_vector(vector):
    result=evaluate(vector['facts'],PACKAGE)
    assert {k:result[k] for k in vector['expected']}==vector['expected']

@pytest.mark.parametrize('unknown', ['damage','seed','source_date','availability','basis','publication','identity'])
def test_required_unknown_dominates_false_seed(unknown):
    context,cores,factors,seeds=fixture_context(count=1)
    seeds[0]['base_seed_state']='FALSE'
    if unknown=='damage': factors[0]['fields']['core_price_damage']['quality_state']='UNKNOWN'
    if unknown=='seed': seeds[0]['base_seed_state']='UNKNOWN'
    if unknown=='source_date': cores[0]['max_source_trade_date']='2031-01-01'
    if unknown=='availability': factors[0]['formal_publication_at']='2031-01-01T08:00:00+08:00'
    if unknown=='basis': factors[0]['coordinate_basis']='OTHER'
    if unknown=='publication': seeds[0]['publication_id']='wrong'
    if unknown=='identity': factors[0]['security_id']='wrong'
    facts,reasons,_=project(cores[0],factors[0],seeds[0],context,PACKAGE)
    assert reasons and evaluate(facts,PACKAGE)['raw_qualification']=='UNKNOWN'

def test_priority_unknown_does_not_gate_true_seed():
    context,cores,factors,seeds=fixture_context(count=1)
    factors[0]['fields']['rps5_delta3']['quality_state']='UNKNOWN'
    cores[0]['states']['core_extension_risk']['unknown_reason']='MISSING'
    row=build(cores,factors,seeds,context,PACKAGE)[0]
    assert row['raw_qualification']=='TRUE' and row['priority_bucket']=='UNKNOWN_BUCKET'

def test_partial_seed_does_not_require_all_profile_fields():
    context,cores,factors,seeds=fixture_context(count=1)
    seeds[0]['quality']='PARTIAL_UNKNOWN'
    cores[0]['profile_quality']='UNKNOWN'
    assert build(cores,factors,seeds,context,PACKAGE)[0]['raw_qualification']=='TRUE'

@pytest.mark.parametrize('field',['sector_prewatch','rotation_core_state','B2','state_reducer','final_eligibility',
    'confirmation','anchor','support','radar','focus','ui','future_outcome','forward_return','turnover'])
def test_forbidden_fields_do_not_change_any_result_bytes(field):
    context,cores,factors,seeds=fixture_context()
    baseline=build(cores,factors,seeds,context,PACKAGE)
    for value in [True,False,'UNKNOWN',{'future_date':'2099-12-31','value':999}]:
        changed=deepcopy([cores,factors,seeds])
        for group in changed:
            for row in group: row[field]=value
        assert build(*changed,context,PACKAGE)==baseline

def test_parameter_instance_and_numeric_enum_order():
    facts=VECTORS[0]['facts']; changed=deepcopy(PACKAGE)
    changed['parameter_set']['parameters'][1]['value']=11
    assert evaluate(facts,changed)['priority_bucket']=='C'
    assert evaluate(facts,PACKAGE)['priority_bucket']=='A'
    changed['parameter_set']['parameters'][0]['unit']='ratio'
    with pytest.raises(ValueError): evaluate(facts,changed)
    assert PACKAGE['machine_ast']['enum_order']['risk_axis']==['LOW','MEDIUM','HIGH','EXTREME']

@pytest.mark.parametrize('date,count',[('2030-01-02',1),('2030-02-04',3),('2031-03-05',4)])
def test_context_drives_dates_publications_counts(date,count):
    context,cores,factors,seeds=fixture_context(date,count)
    rows=build(cores,factors,seeds,context,PACKAGE)
    assert len(rows)==count and {r['trade_date'] for r in rows}=={date}
    assert rows==build(cores,factors,seeds,deepcopy(context),PACKAGE)

def test_duplicate_missing_and_board_scope_rejected():
    context,cores,factors,seeds=fixture_context()
    with pytest.raises(ValueError): build(cores+cores,factors,seeds,context,PACKAGE)
    with pytest.raises(ValueError): build(cores,factors,seeds[:-1],context,PACKAGE)
    context['expected_board_counts']={'OTHER':2}
    with pytest.raises(ValueError): build(cores,factors,seeds,context,PACKAGE)

def test_production_and_v4_09_acceptance_stay_disabled():
    from scripts.promote_v4_08_accepted_head import validate
    assert validate()['status']=='PASS'
    assert not (ROOT/'data/v4/V4_09_ACCEPTED_HEAD.json').exists()
