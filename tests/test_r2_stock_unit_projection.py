import pytest
from workbench_service.stock_unit_projection import project
from workbench_service.current_v4_context import SourceInvalid

def test_units_do_not_scale_values_and_bind_the_owner_parameter_set():
    registry={'fields':[dict(field_id='rel_market_5',parameter_set_id='P',unit='return_fraction',price_basis='verified_affine_adjusted_OHLC')]}
    cell=dict(value=.01,parameter_set_id='P',quality='KNOWN')
    output=project('rel_market_5',cell,[registry],'ACCEPTED_NATIVE_AFFINE')
    assert output['value']==.01 and output['unit']=='return_fraction' and output['coordinate_basis']=='ACCEPTED_NATIVE_AFFINE'
    assert 'unit' not in cell
    with pytest.raises(SourceInvalid,match='PARAMETER_CONTRACT_MISMATCH'):project('rel_market_5',dict(cell,parameter_set_id='OTHER'),[registry],'ACCEPTED_NATIVE_AFFINE')

def test_unregistered_field_does_not_receive_inferred_units():
    assert project('missing',dict(value=1),[{'fields':[]}],'BASIS')==dict(value=1)
    registry={'fields':[dict(field_id='missing_history',parameter_set_id='P',unit='percentage_points')]}
    source=dict(value=None,unknown_reason='HISTORICAL_POOL_NOT_BOUND')
    assert project('missing_history',source,[registry],'BASIS')==source
