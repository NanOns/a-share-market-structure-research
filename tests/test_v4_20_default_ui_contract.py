"""Independent synthetic design vectors; no live router or browser changes."""
import json
from pathlib import Path
import pytest
from reports.r29.design_resolver import CAPS,DEPS,MODULES,affected,digest,fixture,focus_write,open_deep_link,page_context,resolve,stale,vector_result

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'config/v4_20_default_ui_cutover_contract_v1.json').read_text(encoding='utf8'))


@pytest.mark.parametrize('i',range(1,21),ids=lambda i:f'U20-{i:02}')
def test_twenty_design_vectors(i):
    result=vector_result(i); rows=result['modules']; mode=lambda m:rows[m]['mode']
    assert not result['actual_default_cutover'] and not result['production_grant'] and result['actual_route_changes']==[]
    if i==1: assert all(r['mode']=='LEGACY_PRODUCTION' for r in rows.values())
    if i==2: assert mode('stock_research')=='PRODUCTION_V4' and mode('sector_research')=='LEGACY_PRODUCTION'
    if i==3: assert mode('sector_research')=='PRODUCTION_V4' and mode('stock_research')=='LEGACY_PRODUCTION'
    if i==4: assert mode('stock_sector_dependent')=='LEGACY_PRODUCTION'
    if i==5: assert mode('sector_research')=='PRODUCTION_V4' and mode('rotation')=='LEGACY_PRODUCTION'
    if i==6: assert all(r['mode']=='SHADOW_V4' and r['label']=='SHADOW' for r in rows.values())
    if i==7: assert mode('stock_research')=='LEGACY_PRODUCTION' and rows['stock_research']['reason']=='NO_PERMISSION'
    if i==8: assert mode('stock_research')=='UNKNOWN' and rows['stock_research']['reason']=='EXACT_V4_BINDING_CONFLICT'
    if i in (9,16): assert result['stale'] and not result['session_write_allowed'] and result['cache_action']=='INVALIDATE_AFFECTED_BINDING_NO_SILENT_REBASE'
    if i==10: assert result['deep_link']['status']=='HISTORICAL_EXACT_READ_ONLY' and digest(result['deep_link']['context'])==result['original_context_digest'] and not result['deep_link']['write_allowed']
    if i==11: assert all(r['reason']=='IMPLICIT_SOURCE_FORBIDDEN' for r in rows.values())
    if i==12: assert result['page']['manifest']['stock_research']['label']=='PRODUCTION_V4_PROVISIONAL' and result['page']['manifest']['sector_research']['label']=='LEGACY_PRODUCTION'
    if i==13: assert result['page']['status']=='REJECTED_GLOBAL_LABEL'
    if i==14: assert not result['focus_write_allowed']
    if i==15: assert result['user_pins_preserved'] and mode('stock_research')=='PRODUCTION_V4'
    if i==17: assert result['rollback_affected']==['ROTATION'] and mode('stock_research')==mode('sector_research')=='PRODUCTION_V4' and mode('rotation')=='LEGACY_PRODUCTION'
    if i in (18,19):
        assert result['rollback_affected']==['ROTATION','SECTOR_RISK_CHANGE','SECTOR_STAGE','STOCK_SECTOR_DEPENDENT']
        assert all(mode(m)=='LEGACY_PRODUCTION' for m in ('rotation','sector_research','sector_risk_change','stock_sector_dependent'))
        assert mode('stock_research')=='PRODUCTION_V4' and result['historical_context_preserved'] and result['user_pins_preserved']
    if i==20: assert mode('stock_research')=='LEGACY_PRODUCTION' and rows['stock_research']['reason']=='NO_PERMISSION'


def test_current_all_legacy_and_authorities_unchanged():
    assert not any(C['current_state']['production_permission'].values())
    assert set(C['current_state']['default_modules'].values())=={'LEGACY_PRODUCTION'}
    assert not C['current_state']['DEFAULT_UI_CUTOVER'] and C['current_state']['V4_20_ACCEPTED_HEAD']=='NOT_CREATED'
    assert C['implementation_entry']['receipts']==[None]*4
    assert C['implementation_entry']['status']=='BLOCKED_WAIT_PRODUCTION_PERMISSION'
    assert not C['source_resolution']['implemented_in_router'] and not C['focus_write']['implemented']


def test_module_capability_registry_and_native_context_identity():
    assert C['dependency_graph']==DEPS and set(C['module_registry'])==set(MODULES)
    for m,(required,optional) in MODULES.items():
        row=C['module_registry'][m]
        assert row['required_capabilities']==required and row['optional_capabilities']==optional
        for field in ('fallback_source','default_source','shadow_only_subcomponents','write_permissions','context_identity_fields'): assert field in row
    assert len(C['context_composition']['native_shadow_fields'])==11
    assert C['context_composition']['native_legacy_fields']==['run_id','publication_id','local_date','mode','snapshot_id','algorithm_version']
    assert not C['aggregate_v4_production_label']


def test_write_requires_current_route_permission_and_endpoint_agreement():
    state=fixture(['STOCK_CORE']); row=resolve('stock_research',state)
    endpoint=dict(accepted=True,source_mode='PRODUCTION_V4',context_digest=row['context_digest'],capability_scope=['STOCK_CORE'],route_heads=dict(row['context']['route_heads']),permission_receipt_digests=dict(row['context']['permission_receipt_digests']))
    endpoint.update({k:row['context'][k] for k in ('model_contract_id','parameter_digest','state_lineage_id')})
    assert focus_write(row,state,endpoint)
    state['focus_routes']['STOCK_CORE']['accepted']=False
    assert not focus_write(row,state,endpoint)
    state['focus_routes']['STOCK_CORE']['accepted']=True
    endpoint['context_digest']='wrong'; assert not focus_write(row,state,endpoint)
    endpoint['context_digest']=row['context_digest']; state['route_heads']['STOCK_CORE']='other'; assert not focus_write(row,state,endpoint)
    legacy=resolve('sector_research',fixture())
    assert focus_write(legacy,fixture(),dict(legacy_authority=True,legacy_route_head='SIM_LEGACY_HEAD'))
    assert not focus_write(legacy,fixture(),dict(legacy_authority=True,legacy_route_head='wrong'))


def test_deep_link_tampering_and_missing_context_never_discovers_latest():
    row=resolve('stock_research',fixture(['STOCK_CORE']))
    link=dict(context=row['context'],context_digest=row['context_digest'])
    link['context']['publication_revision']=2
    assert open_deep_link(link)['status']=='EXACT_CONTEXT_UNAVAILABLE'
    link['context_digest']=digest(link['context']); del link['context']['module']
    assert open_deep_link(link)['status']=='EXACT_CONTEXT_UNAVAILABLE'


def test_forbidden_source_discovery_and_empty_capability_not_v4():
    for source in ('latest','mtime','browser','page_local','global_flag'):
        state=fixture(CAPS); state['discovery']=source
        assert resolve('stock_research',state)['mode']=='UNKNOWN'
    assert resolve('today_overview',fixture(CAPS))['mode']=='LEGACY_PRODUCTION'
    assert resolve('data_diagnostics',fixture(CAPS))['mode']=='LEGACY_PRODUCTION'
    state=fixture(); del state['bindings']['stock_research','LEGACY_PRODUCTION']
    assert resolve('stock_research',state)['mode']=='UNKNOWN'


def test_r28_p2_transitive_rollback_independent_stock_preserved():
    assert affected('SECTOR_STAGE')==['ROTATION','SECTOR_RISK_CHANGE','SECTOR_STAGE','STOCK_SECTOR_DEPENDENT']
    result=vector_result(18)
    assert result['modules']['stock_research']['mode']=='PRODUCTION_V4'
    assert result['modules']['sector_risk_change']['mode']=='LEGACY_PRODUCTION'
    assert len(C['vectors'])==20 and C['vectors'][17]['id']=='U20-18'
