"""Positive exact-authority reachability and independent adversarial debt coverage."""
import copy,json
from pathlib import Path
import pytest
from scripts.r20r1r1_fixture import build,put
from scripts.r20r1r1_io import ROOT,exact,ref
from scripts.r20r1r1_packet_validation import validate_packet
from scripts.r20r1r1_maturity_debt import refresh
from scripts.validate_r20r1r1_oracle import packet_oracle,state_oracle,validate
def read(root,path):return json.loads((Path(root)/path).read_bytes())
def replace(root,b,change):
    obj=exact(b,root);change(obj);return put(root,b['path'],obj)
def current_state():return read(ROOT,'reports/r20r1r1/MATURITY_DEBT_READBACK.json')
def test_current_exact_authority_no_real_maturity():
    result=validate();assert result['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE'
    s=current_state();assert s['proved_horizons']==[] and s['unproved_horizons']==[1,3,5,10,20]
    assert s['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']=='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'
def test_positive_reconstructed_t1_is_reachable(tmp_path):
    p=build(tmp_path)[0];proof=validate_packet(p,tmp_path)
    assert proof['T0_OBSERVATION_SCOPE']=='RECONSTRUCTED_ASOF'
    assert proof['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED'
    assert packet_oracle(p,tmp_path)==1
    s=exact(refresh([p],tmp_path),tmp_path)
    assert s['status']=='PARTIAL_MATURITY_EVIDENCE' and s['proved_horizons']==[1] and s['unproved_horizons']==[3,5,10,20]
    assert s['capability_by_horizon']['1']=='PASS_CAPABILITY_SCOPED'
    assert s['blocks_unqualified_matured_real_claims'] and not s['stage_promotion_authorized']
    assert s['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED'
    assert state_oracle(tmp_path)['proved_horizons']==[1]
    assert current_state()['proved_horizons']==[]
def test_incremental_all_horizons_and_old_snapshots_revalidate(tmp_path):
    packets=build(tmp_path,(1,3,5,10,20));assert exact(refresh([],tmp_path),tmp_path)['status']=='OPEN'
    for i,p in enumerate(packets):
        s=exact(refresh([p],tmp_path),tmp_path)
        assert s['proved_horizons']==[1,3,5,10,20][:i+1]
        assert state_oracle(tmp_path)['aggregate_state']==('FULL_REQUIRED_HORIZONS_PROVEN' if i==4 else 'PARTIAL_MATURITY_EVIDENCE')
    assert s['unproved_horizons']==[] and s['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED'
    assert s['blocks_unqualified_matured_real_claims'] # Isolated evidence cannot grant actual real capability.
def test_duplicate_exact_packet_is_idempotent(tmp_path):
    p=build(tmp_path)[0];first=refresh([p],tmp_path)
    assert refresh([p],tmp_path)==first
    view=read(tmp_path,'reports/r20r1r1/MATURITY_DEBT_READBACK.json')
    assert len(next(iter(view['proofs_by_enrollment_horizon'].values()))['receipt_history'])==1
@pytest.mark.parametrize('attack',['synthetic_owner','unsealed_owner','enrollment_mismatch','freeze_mismatch','raw_provider','prices_only','unaccepted_endpoint','before_freeze','wrong_horizon','wrong_due','corrupted_outcome','boolean_proof','PIT_upgrade','realtime_upgrade','incomplete_path','T0_in_path','corrupt_exact_bytes','unknown_data_snapshot','nonfinite_outcome'])
def test_negative_packets_fail_closed(tmp_path,attack):
    p=build(tmp_path)[0]
    if attack=='synthetic_owner':
        reg=read(tmp_path,'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json');head=exact(reg['accepted_head'],tmp_path);seal=exact(head['bindings']['runtime_seal'],tmp_path);b=seal['replay_publications'][0]
        put(tmp_path,b['path'],raw=(ROOT/b['path']).read_bytes());p['owner_publication']=b;reg['owner_publication']=b;put(tmp_path,'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json',reg)
    elif attack=='unsealed_owner':p['owner_publication']=p['enrollment']
    elif attack=='enrollment_mismatch':p['enrollment']=p['freeze']
    elif attack=='freeze_mismatch':p['freeze']=p['enrollment']
    elif attack=='raw_provider':p['raw_provider_fallback']=True
    elif attack=='prices_only':p['historical_prices_only']=True
    elif attack=='unaccepted_endpoint':p['accepted_endpoints']=[p['outcome']]
    elif attack=='before_freeze':
        p['first_future_endpoint_open_at']='2026-09-30T00:00:00+00:00';p['endpoint_read_receipt']=replace(tmp_path,p['endpoint_read_receipt'],lambda o:o.update(first_future_endpoint_open_at=p['first_future_endpoint_open_at']))
    elif attack=='wrong_horizon':p['horizon']=3
    elif attack=='wrong_due':p['outcome']=replace(tmp_path,p['outcome'],lambda o:o.update(due_date='2026-10-09'))
    elif attack=='corrupted_outcome':p['outcome']=replace(tmp_path,p['outcome'],lambda o:o.update(R_N=99))
    elif attack=='boolean_proof':p={'independent_exact_maturity_proof':True,'REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME':'PASS'}
    elif attack=='PIT_upgrade':p['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    elif attack=='realtime_upgrade':p['REALTIME_ACCEPTED_COHORT_MATURITY']='PASS'
    elif attack=='incomplete_path':p['accepted_endpoints']=[]
    elif attack=='T0_in_path':p['outcome']=replace(tmp_path,p['outcome'],lambda o:o['price_path'].insert(0,dict(o['price_path'][0],trade_date='2026-09-30')))
    elif attack=='corrupt_exact_bytes':put(tmp_path,p['outcome']['path'],dict(exact(p['outcome'],tmp_path),R_N=99))
    elif attack=='unknown_data_snapshot':p['data_head']=p['outcome']
    else:p['outcome']=replace(tmp_path,p['outcome'],lambda o:o.update(MFE_N=float('nan')))
    with pytest.raises((ValueError,KeyError)):validate_packet(p,tmp_path)
def test_mixed_accepted_basis_rejected_even_after_exact_rebinding(tmp_path):
    p=build(tmp_path)[0];old=p['accepted_endpoints'][0]
    new=replace(tmp_path,old,lambda a:a['rows'][0].update(evaluation_basis_date='2026-09-30'))
    p['accepted_endpoints']=[new]
    p['data_head']=replace(tmp_path,p['data_head'],lambda d:d['component_artifacts'].update(FORWARD_EVALUATION_INPUTS=[new]))
    put(tmp_path,'data/v4/V4_DATA_ACCEPTED_HEAD.json',exact(p['data_head'],tmp_path))
    p['endpoint_read_receipt']=replace(tmp_path,p['endpoint_read_receipt'],lambda d:d.update(accepted_endpoints=[new]))
    with pytest.raises(ValueError,match='EVALUATION_BASIS'):validate_packet(p,tmp_path)
@pytest.mark.parametrize('attack',['full_after_t1','global_unblock_after_t1','invent_horizon','PIT_upgrade','stage_authorized'])
def test_independent_coverage_oracle_rejects_overclaims(tmp_path,attack):
    p=build(tmp_path)[0];s=exact(refresh([p],tmp_path),tmp_path)
    if attack=='full_after_t1':s['aggregate_state']=s['status']='FULL_REQUIRED_HORIZONS_PROVEN'
    elif attack=='global_unblock_after_t1':s['blocks_unqualified_matured_real_claims']=s['blocks_matured_real_claims']=False
    elif attack=='invent_horizon':s['proved_horizons']=[1,3]
    elif attack=='PIT_upgrade':s['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    else:s['stage_promotion_authorized']=True
    with pytest.raises(ValueError):state_oracle(tmp_path,s)
def test_readback_tamper_cannot_invent_coverage(tmp_path):
    p=build(tmp_path)[0];refresh([p],tmp_path);view=read(tmp_path,'reports/r20r1r1/MATURITY_DEBT_READBACK.json');view['proved_horizons']=[1,20]
    put(tmp_path,'reports/r20r1r1/MATURITY_DEBT_READBACK.json',view)
    with pytest.raises(ValueError,match='IMMUTABLE_REVISION'):refresh([],tmp_path)
def corrected_packet(root,p):
    p=copy.deepcopy(p);olddata=exact(p['data_head'],root);parent=put(root,'fixtures/data_before_correction.json',olddata)
    source=exact(p['accepted_endpoints'][0],root);row=source['rows'][0];row.update(close=3,high=3.1,low=2.7)
    endpoint=put(root,'fixtures/corrected_endpoint_r2.json',source)
    d=copy.deepcopy(olddata);d.update(parent_archive=parent,component_artifacts=dict(FORWARD_EVALUATION_INPUTS=[endpoint]));p['data_head']=put(root,'fixtures/data_corrected_r2.json',d);put(root,'data/v4/V4_DATA_ACCEPTED_HEAD.json',d)
    p['accepted_endpoints']=[endpoint];old=p['outcome'];out=exact(old,root);reference=exact(p['freeze'],root)['comparison_reference'];out.update(price_path=[row],R_N=3/reference-1,MFE_N=3.1/reference-1,MAE_N=0,PATH_MDD_CLOSE_N=0,revision_sequence=2,supersedes=old)
    p['outcome']=put(root,'fixtures/outcome_n1_r2.json',out)
    log=exact(p['endpoint_read_receipt'],root);log['accepted_endpoints']=[endpoint];p['endpoint_read_receipt']=put(root,'fixtures/read_receipt_n1_r2.json',log);return p
def test_corrected_source_appends_and_preserves_first_observed(tmp_path):
    p=build(tmp_path)[0];refresh([p],tmp_path);before=read(tmp_path,'reports/r20r1r1/MATURITY_DEBT_READBACK.json');old=next(iter(before['proofs_by_enrollment_horizon'].values()));old_bytes=(tmp_path/old['FIRST_OBSERVED']['path']).read_bytes()
    correction=corrected_packet(tmp_path,p);refresh([correction],tmp_path);after=read(tmp_path,'reports/r20r1r1/MATURITY_DEBT_READBACK.json');now=next(iter(after['proofs_by_enrollment_horizon'].values()))
    assert now['FIRST_OBSERVED']==old['FIRST_OBSERVED'] and now['LATEST_VALIDATED']!=old['LATEST_VALIDATED']
    assert len(now['receipt_history'])==2 and (tmp_path/old['FIRST_OBSERVED']['path']).read_bytes()==old_bytes
    assert now['horizon']==1 and after['proved_horizons']==[1]
    assert state_oracle(tmp_path)['aggregate_state']=='PARTIAL_MATURITY_EVIDENCE'
def test_duplicate_packet_cannot_change_existing_receipt(tmp_path):
    p=build(tmp_path)[0];refresh([p],tmp_path);before=(tmp_path/'reports/r20r1r1/MATURITY_DEBT_READBACK.json').read_bytes()
    receipt=exact(p['endpoint_read_receipt'],tmp_path)
    p['first_future_endpoint_open_at']='2026-10-09T16:30:00+00:00'
    receipt['first_future_endpoint_open_at']=p['first_future_endpoint_open_at']
    p['endpoint_read_receipt']=put(tmp_path,'fixtures/duplicate_read_receipt.json',receipt)
    with pytest.raises(ValueError,match='NEXT_REVISION'):refresh([p],tmp_path)
    assert (tmp_path/'reports/r20r1r1/MATURITY_DEBT_READBACK.json').read_bytes()==before
def test_corrected_source_cannot_overwrite_first_observation(tmp_path):
    p=build(tmp_path)[0];refresh([p],tmp_path);view=read(tmp_path,'reports/r20r1r1/MATURITY_DEBT_READBACK.json');b=next(iter(view['proofs_by_enrollment_horizon'].values()))['FIRST_OBSERVED'];proof=exact(b,tmp_path);proof['packet']['horizon']=20;put(tmp_path,b['path'],proof)
    with pytest.raises(ValueError,match='EXACT_BINDING'):refresh([],tmp_path)
def test_fixture_cannot_write_current_repository():
    with pytest.raises(ValueError):build(ROOT)
def test_independent_oracle_has_no_writer_or_evaluator_imports():
    source=(ROOT/'scripts/validate_r20r1r1_oracle.py').read_text()
    for forbidden in ['r20r1r1_maturity_debt','r20r1r1_packet_validation','v4_15_settlement','v4_15_radar_cohort','r20r1r1_fixture']:assert forbidden not in source
