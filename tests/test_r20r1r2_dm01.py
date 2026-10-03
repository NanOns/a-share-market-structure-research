import copy,json
from pathlib import Path
import pytest
from scripts.r20r1r2_io import ROOT,ref,exact,digest,atomic
from scripts.r20r1r2_fixture import build,put
from scripts.r20r1r2_dm01_resolver import resolve_accepted_adjusted_daily_path
from scripts.r20r1r2_forward_projection import project,persist
from scripts.r20r1r2_packet_validation import validate_packet
from scripts.r20r1r2_maturity_debt import refresh
from scripts.validate_r20r1r2_oracle import packet_oracle,state_oracle

def read(root,path):return json.loads((root/path).read_bytes())

def rebuild(root,mutate):
    """Rebind a single-date exact graph so semantic negatives reach the resolver."""
    h=read(root,'data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=exact(h['accepted_chain'],root);node=chain['nodes'][0];candidate=exact(node['candidate'],root);rr=candidate['components']['ADJUSTED_DAILY'];a=exact(dict(path=rr['artifact_path'],sha256=rr['artifact_sha256'],bytes=rr['artifact_bytes']),root)
    mutate(h,chain,node,candidate,rr,a)
    ab=put(root,rr['artifact_path'],a);rr.update(artifact_sha256=ab['sha256'],artifact_bytes=ab['bytes'],logical_digest=digest(a['rows']),row_count=len(a['rows']))
    rb=put(root,(Path(rr['artifact_path']).parent/'receipt.json').as_posix(),rr);candidate['components']['ADJUSTED_DAILY']=rr;node['components']=candidate['components'];node['candidate']=put(root,node['candidate']['path'],candidate)
    record=exact(h['external_acceptance_record'],root);record['candidate_bindings']=[n['candidate'] for n in chain['nodes']];record['accepted_scope']['sessions']=[n['trade_date'] for n in chain['nodes']];h['external_acceptance_record']=put(root,h['external_acceptance_record']['path'],record);chain['external_acceptance_record']=h['external_acceptance_record'];h['accepted_chain']=put(root,h['accepted_chain']['path'],chain)
    h['final_candidate']=node['candidate'];h['component_artifacts']['ADJUSTED_DAILY']=ab;h['component_permissions']['ADJUSTED_DAILY'].update(artifact=ab,receipt=rb)
    put(root,'data/v4/V4_DATA_ACCEPTED_HEAD.json',h)
    return h

@pytest.mark.parametrize('n',[1,3,5,10,20])
def test_production_shaped_batch_positive(tmp_path,n):
    p=build(tmp_path,(n,))[0];before=(ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes()
    proof=validate_packet(p,tmp_path);assert proof['horizon']==n and packet_oracle(p,tmp_path)==n
    h=read(tmp_path,'data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=exact(h['accepted_chain'],tmp_path);assert len(chain['nodes'])==n
    assert set(h['component_artifacts'])=={'ADJUSTED_DAILY','RAW_DAILY','TRADING_STATUS','IDENTITY_UNIVERSE','ISST','PERIOD_ADJUSTED','PERIOD_RAW','PRICE_LIMIT','SPECIAL_PHASE'}
    assert all(isinstance(b,dict) and set(b)=={'path','sha256','bytes'} for b in h['component_artifacts'].values())
    refresh([p],tmp_path);view=read(tmp_path,'reports/r20r1r2/MATURITY_DEBT_READBACK.json');assert view['proved_horizons']==[n] and view['HISTORICAL_PIT_EFFECTIVENESS']==view['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED'
    assert view['aggregate_state']=='PARTIAL_MATURITY_EVIDENCE' and view['blocks_unqualified_matured_real_claims'] is True
    assert state_oracle(tmp_path)['proved_horizons']==[n] and (ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes()==before

def test_incremental_coverage_and_duplicate_preserve_pass_keep(tmp_path):
    ps=build(tmp_path);refresh([],tmp_path);assert state_oracle(tmp_path)['aggregate_state']=='OPEN'
    refresh(ps[:1],tmp_path);v=read(tmp_path,'reports/r20r1r2/MATURITY_DEBT_READBACK.json');first=v['FIRST_OBSERVED'];bytes_before=(tmp_path/'reports/r20r1r2/MATURITY_DEBT_READBACK.json').read_bytes();refresh(ps[:1],tmp_path);assert bytes_before==(tmp_path/'reports/r20r1r2/MATURITY_DEBT_READBACK.json').read_bytes()
    refresh(ps[1:2],tmp_path);assert state_oracle(tmp_path)['proved_horizons']==[1,3]
    refresh(ps[2:],tmp_path);v=read(tmp_path,'reports/r20r1r2/MATURITY_DEBT_READBACK.json');assert v['FIRST_OBSERVED']==first and state_oracle(tmp_path)['aggregate_state']=='FULL_REQUIRED_HORIZONS_PROVEN' and v['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']=='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'

@pytest.mark.parametrize('bad',['invented_source_fields','unknown_adjustment','missing_qfq','ambiguous_identity','wrong_artifact_date','receipt_date','parent_component','parent_digest','wrong_target','wrong_source_revision','wrong_source_bar','unbound_source_inputs'])
def test_native_schema_semantic_negatives(tmp_path,bad):
    p=build(tmp_path,(1,))[0]
    def mutate(h,ch,n,c,r,a):
        row=a['rows'][0]
        if bad=='invented_source_fields':row['evaluation_basis_date']=a['trade_date']
        elif bad=='unknown_adjustment':row['adjustment_readiness']='UNKNOWN'
        elif bad=='missing_qfq':row['qfq_mul']=None
        elif bad=='ambiguous_identity':a['rows'].append(copy.deepcopy(row))
        elif bad=='wrong_artifact_date':a['trade_date']='2026-10-09'
        elif bad=='receipt_date':r['trade_date']='2026-10-09'
        elif bad=='parent_component':r['parent_component_bindings']['ADJUSTED_DAILY']=dict(path='fake',sha256='0'*64,bytes=0)
        elif bad=='parent_digest':r['parent_data_head_digest']='0'*64
        elif bad=='wrong_target':c['target_trade_date']='2026-10-09'
        elif bad=='wrong_source_revision':row['adjustment_source_revision']='0'*64
        elif bad=='wrong_source_bar':row['close']='99.99'
        elif bad=='unbound_source_inputs':r['input_publication_ids']=[]
    rebuild(tmp_path,mutate)
    with pytest.raises((ValueError,TypeError,KeyError)):project(p['freeze'],'2026-10-08',tmp_path)

@pytest.mark.parametrize('bad',['missing_receipt','receipt_artifact_bytes','chain_membership','missing_session','chain_parent','incomplete_final_components','invented_head_list'])
def test_production_authority_negatives(tmp_path,bad):
    p=build(tmp_path,(3,))[0];h=read(tmp_path,'data/v4/V4_DATA_ACCEPTED_HEAD.json');ch=exact(h['accepted_chain'],tmp_path)
    if bad=='missing_receipt':(tmp_path/Path(ch['nodes'][0]['components']['ADJUSTED_DAILY']['artifact_path']).parent/'receipt.json').unlink()
    elif bad=='receipt_artifact_bytes':(tmp_path/ch['nodes'][0]['components']['ADJUSTED_DAILY']['artifact_path']).write_bytes(b'{}')
    elif bad in ['chain_membership','missing_session','chain_parent']:
        if bad=='chain_membership':ch['nodes'][0]['candidate']=ch['nodes'][1]['candidate']
        elif bad=='missing_session':ch['nodes'].pop(1)
        else:ch['nodes'][1]['parent']=ch['nodes'][1]['candidate']
        h['accepted_chain']=put(tmp_path,h['accepted_chain']['path'],ch);put(tmp_path,'data/v4/V4_DATA_ACCEPTED_HEAD.json',h)
    elif bad=='incomplete_final_components':h['component_artifacts']['ADJUSTED_DAILY']=ch['nodes'][0]['components']['ADJUSTED_DAILY'];put(tmp_path,'data/v4/V4_DATA_ACCEPTED_HEAD.json',h)
    else:h['component_artifacts']={'FORWARD_EVALUATION_INPUTS':p['accepted_endpoints']};put(tmp_path,'data/v4/V4_DATA_ACCEPTED_HEAD.json',h)
    with pytest.raises((ValueError,KeyError,FileNotFoundError)):resolve_accepted_adjusted_daily_path('2026-09-30','2026-10-12',root=tmp_path)

def test_projection_deterministic_source_immutable_and_t0_mapping(tmp_path):
    p=build(tmp_path,(5,))[0];before={b['path']:(tmp_path/b['path']).read_bytes() for b in p['accepted_endpoints']};value=exact(p['projection'],tmp_path)
    assert project(p['freeze'],value['evaluation_basis_date'],tmp_path,p['data_head'])==value
    assert persist(p['freeze'],value['evaluation_basis_date'],tmp_path)==p['projection']
    assert all((tmp_path/path).read_bytes()==raw for path,raw in before.items())
    assert all(r['evaluation_basis_date']==value['evaluation_basis_date'] and r['T0_transform_coefficients']==value['T0_transform_coefficients'] for r in value['rows'])
    assert value['T0_transform_coefficients']=={'alpha':1.0,'beta':0.0} and packet_oracle(p,tmp_path)==5

def test_projection_digest_tracks_exact_descriptor_changes(tmp_path):
    p=build(tmp_path,(1,))[0];old=p['projection']['sha256']
    def change(h,ch,n,c,r,a):
        r['artifact_path']='fixtures/relocated/ADJUSTED_DAILY/artifact.json'
    rebuild(tmp_path,change)
    assert persist(p['freeze'],'2026-10-08',tmp_path)['sha256']!=old

@pytest.mark.parametrize('bad',['projection_missing','projection_t0_math','outcome_math','pit','one_horizon_full','one_horizon_global_unblock'])
def test_independent_oracle_fail_closed(tmp_path,bad):
    p=build(tmp_path,(1,))[0]
    if bad=='projection_missing':p.pop('projection')
    elif bad=='projection_t0_math':value=exact(p['projection'],tmp_path);value['T0_transform_coefficients']['alpha']=2;put(tmp_path,p['projection']['path'],value)
    elif bad=='outcome_math':value=exact(p['outcome'],tmp_path);value['R_N']=2;put(tmp_path,p['outcome']['path'],value)
    elif bad=='pit':p['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    else:
        refresh([p],tmp_path);value=read(tmp_path,'reports/r20r1r2/MATURITY_DEBT_READBACK.json')
        if bad=='one_horizon_full':value['aggregate_state']=value['status']='FULL_REQUIRED_HORIZONS_PROVEN'
        else:value['blocks_unqualified_matured_real_claims']=False
        with pytest.raises(ValueError):state_oracle(tmp_path,value)
        return
    with pytest.raises((ValueError,KeyError)):packet_oracle(p,tmp_path)

def test_active_admission_rejects_old_fixture_shortcut(tmp_path):
    from scripts.r20r1r1_fixture import build as historical_fixture
    p=historical_fixture(tmp_path)[0]
    with pytest.raises((ValueError,KeyError)):validate_packet(p,tmp_path)

def test_oracle_import_independence():
    source=(ROOT/'scripts/validate_r20r1r2_oracle.py').read_text()
    for forbidden in ['r20r1r2_dm01_resolver','r20r1r2_forward_projection','r20r1r2_maturity_debt','v4_15_settlement','r20r1r2_packet_validation']:assert forbidden not in source

def test_current_real_fail_closed():
    refresh();v=read(ROOT,'reports/r20r1r2/MATURITY_DEBT_READBACK.json')
    assert v['proved_horizons']==[] and v['unproved_horizons']==[1,3,5,10,20] and v['aggregate_state']=='OPEN' and v['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']=='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'

def test_production_same_day_correction_append_only(tmp_path):
    p=build(tmp_path,(1,))[0];refresh([p],tmp_path);old=read(tmp_path,'reports/r20r1r2/MATURITY_DEBT_READBACK.json');entry=next(iter(old['proofs_by_enrollment_horizon'].values()));old_bytes=(tmp_path/entry['FIRST_OBSERVED']['path']).read_bytes()
    corrected=build(tmp_path,(1,),revision=2,prior_accepted_revision=p['data_head'])[0]
    out=exact(corrected['outcome'],tmp_path);out.update(revision_sequence=2,supersedes=p['outcome']);corrected['outcome']=put(tmp_path,'fixtures/r2/outcome_corrected.json',out)
    assert packet_oracle(p,tmp_path)==1 and packet_oracle(corrected,tmp_path)==1
    refresh([corrected],tmp_path);new=read(tmp_path,'reports/r20r1r2/MATURITY_DEBT_READBACK.json');ne=next(iter(new['proofs_by_enrollment_horizon'].values()))
    assert ne['FIRST_OBSERVED']==entry['FIRST_OBSERVED'] and len(ne['receipt_history'])==2 and ne['LATEST_VALIDATED']!=entry['LATEST_VALIDATED'] and (tmp_path/entry['FIRST_OBSERVED']['path']).read_bytes()==old_bytes
    assert state_oracle(tmp_path)['proved_horizons']==[1]

def test_prior_same_day_revision_requires_explicit_accepted_record_binding(tmp_path):
    p=build(tmp_path,(1,))[0];build(tmp_path,(1,),revision=2)
    with pytest.raises(ValueError,match='SNAPSHOT'):validate_packet(p,tmp_path)
    with pytest.raises(ValueError,match='SNAPSHOT'):packet_oracle(p,tmp_path)
