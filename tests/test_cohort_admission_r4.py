"""Synthetic receipts verify isolated wiring; never evidence real enrollment."""
import json
import hashlib
import copy
import pytest
from workbench_analysis.validation_cohort_read_contract_r3 import (
    CONTRACT, read_authorized_statistics, publish_isolated_candidate,
    validate_frozen, maturity_schedule)
from workbench_analysis.v4_15_forward_r2 import price_path

def frozen():
    return dict(model_contract_id='M1',state_lineage_id='L1',entity_type='STOCK',entity_id='S1',episode_id='E1',event_type='NEW_CONFIRMED',T0='2026-09-30',publication_id='P1',frozen_signal_version='V1',frozen_at_T0='2026-09-30T16:00:00+08:00',eligible_at_T0=True,asof_first_available='2026-09-30T15:01:00+08:00',benchmark={'id':'B1'},no_lookahead=True,evidence_class='PIT_OBSERVED',cohort_namespace='SHADOW')

def setup(root,patch=None):
    def write(name,value):
        p=root/name;p.write_text(json.dumps(value),encoding='utf8')
        return dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    row=frozen();events=write('events.json',dict(events=[row]))
    manifest=dict(contract_id='COHORT_T0_SOURCE_RECEIPT_R4_V1',publication_id='P1',T0=row['T0'],evidence_class='PIT_OBSERVED',first_available=row['asof_first_available'],accepted_at='2026-09-30T15:30:00+08:00',published_at='2026-09-30T15:30:00+08:00',membership_asof=row['T0'],membership_basis='AS_RECORDED',model_contract_id='M1',events=events)
    manifest.update(patch or {});source=write('source.json',manifest)
    owner=write('owner.json',dict(contract_id=CONTRACT,trade_date=row['T0'],authorized_read=True,enrollments=[row]))
    grant=write('grant.json',dict(contract_id='VALIDATION_COHORT_READ_GRANT_R4_V1',capability='READ_STATISTICS',authorized=True,owner=owner,trade_date=row['T0'],read_cutoff=row['frozen_at_T0'],benchmark_id='B1',frozen_signal_version='V1',source_manifest=source))
    calendar=write('calendar.json',dict(session_dates=['2026-09-30','2026-10-08','2026-10-09','2026-10-12','2026-10-13','2026-10-14']))
    head=write('head.json',dict(owners={row['T0']:{'validation_cohort':owner}},cohort_read_grants={row['T0']:grant},cohort_source_manifests={row['T0']:source},cohort_calendar=calendar))
    return dict(root=root,accepted_head=head,owner_binding=owner,trade_date=row['T0'])

@pytest.mark.parametrize('patch',[
    {'publication_id':'OLD'}, {'first_available':'2026-10-08T15:00:00+08:00'},
    {'published_at':'2026-10-08T15:00:00+08:00'}, {'accepted_at':'2026-09-30T15:30:00'},
    {'membership_asof':'2026-10-09'}, {'membership_basis':'TDX_LATEST_MEMBER_RETRO_V1'},
    {'evidence_class':'RECONSTRUCTED_ASOF'}, {'model_contract_id':'M2'}, {'events':None}])
def test_source_denial(tmp_path,patch):
    with pytest.raises(ValueError):read_authorized_statistics(**setup(tmp_path,patch))

@pytest.mark.parametrize('name',['events.json','owner.json','grant.json','head.json','source.json'])
def test_changed_sha_and_stale_token(tmp_path,name):
    args=setup(tmp_path);(tmp_path/name).write_text('{}',encoding='utf8')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):read_authorized_statistics(**args)

def test_isolated_idempotent_publisher_and_no_head_change(tmp_path):
    args=setup(tmp_path);before=(tmp_path/'head.json').read_bytes()
    sessions=['2026-09-30','2026-10-08','2026-10-09','2026-10-12','2026-10-13','2026-10-14']
    args.update(candidate_directory='docs/evidence/candidates',sessions=sessions)
    a=publish_isolated_candidate(**args);b=publish_isolated_candidate(**args)
    assert a==b and (tmp_path/'head.json').read_bytes()==before
    payload=json.loads((tmp_path/a['path']).read_bytes())
    assert payload['production'] is False and payload['matured_count'] is None
    assert payload['due_plans'][0]['plans'][0]['due_date']=='2026-10-08'
    assert payload['due_plans'][0]['plans'][2]['due_date']=='2026-10-14'
    (tmp_path/a['path']).write_text('{}',encoding='utf8')
    with pytest.raises(ValueError,match='OVERWRITE_FORBIDDEN'):publish_isolated_candidate(**args)

def test_production_directory_denied_before_write(tmp_path):
    args=setup(tmp_path);args.update(candidate_directory='data/v4',sessions=['2026-09-30'])
    with pytest.raises(ValueError,match='ISOLATED'):publish_isolated_candidate(**args)
    assert not (tmp_path/'data').exists()

def test_caller_calendar_cannot_change_due_plan(tmp_path):
    args=setup(tmp_path);args.update(candidate_directory='docs/evidence/candidates',sessions=['2026-09-30','2026-10-01'])
    with pytest.raises(ValueError,match='CALENDAR_IDENTITY'):publish_isolated_candidate(**args)

def test_timezone_same_instant_and_distinct_anchors():
    a=frozen();a['frozen_at_T0']='2026-09-30T08:00:00Z';a['asof_first_available']='2026-09-30T07:01:00Z'
    first=validate_frozen(a,cutoff='2026-09-30T16:00:00+08:00',trade_date=a['T0'])
    b=copy.deepcopy(a);b['episode_id']='SECOND_ANCHOR'
    assert first!=validate_frozen(b,cutoff='2026-09-30T16:00:00+08:00',trade_date=b['T0'])

def test_weekend_due_and_unknown_horizon():
    result=maturity_schedule('2026-10-09',['2026-10-09','2026-10-12'],'2026-10-10')
    assert result[1]['due_date']=='2026-10-12' and result[1]['status']=='PENDING'
    assert result[3]['status']=='CALENDAR_HORIZON_UNAVAILABLE'

@pytest.mark.parametrize('status',['CONFIRMED_SUSPENSION','DELISTED'])
def test_missing_suspension_delisting_keeps_unknown_return(status):
    result=price_path(10,[dict(status=status,verified_identity=True,verified_adjustment=True,evaluation_basis_date='2026-10-08',T0_basis_verified=True,transform_coefficients={'alpha':1,'beta':0},terminal_value=None)],'2026-10-08')
    assert result['R_N'] is None
