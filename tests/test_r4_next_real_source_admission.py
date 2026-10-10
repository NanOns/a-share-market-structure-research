"""Read-only actual T0 negatives; fixtures never become production owners."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone,timedelta
import pytest
from workbench_analysis.cohort_first_capture_producer_r1 import freeze_source_candidate,extract_candidate
from workbench_analysis.cohort_capture_readiness_r1 import inspect_daily_candidate
from workbench_analysis.v4_14_replay_io import publish
ROOT=Path(__file__).resolve().parents[1]
def bound(path):
    raw=path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def test_real_current_head_has_no_enrollment_or_writer():
    r=inspect_daily_candidate(ROOT,candidate_binding=bound(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),trade_date='2026-10-09',cutoff='2026-10-09T23:59:59+08:00')
    assert r['observed_count'] is None and not r['production_write_authorized']
    assert not r['blocks_local_daily_publication']
    assert 'SEPARATE_FIRST_CAPTURE_WRITE_GRANT' in r['missing_inputs']
@pytest.mark.parametrize('day',['2026-10-08','2026-10-10'])
def test_actual_head_cannot_supply_another_t0(day,tmp_path):
    with pytest.raises(ValueError,match='DAILY_CANDIDATE_DATE_MISMATCH'):
        extract_candidate(ROOT,candidate_binding=bound(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),trade_date=day,cutoff=day+'T23:59:59+08:00',candidate_directory='docs/evidence/forbidden_capture')
@pytest.mark.parametrize('mode',['corrected','before_t0','after_t0','wrong_owner','tampered_manifest'])
def test_real_bound_owner_is_not_a_first_capture_state_source(tmp_path,mode):
    original=(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    p=tmp_path/'actual_head.json';p.write_bytes(original)
    owner=dict(path=p.name,bytes=len(original),sha256=hashlib.sha256(original).hexdigest())
    manifest=dict(contract_id='COHORT_FIRST_CAPTURE_SOURCE_MANIFEST_R1',source_owner=owner,
        T0='2026-10-09',evidence_class='PIT_OBSERVED',membership_basis='AS_RECORDED',
        scope='ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS',revision='r1',membership_version='UNADMITTED',
        publication_id='UNADMITTED',frozen_signal_version='UNADMITTED',parameters_sha256='a'*64,
        first_available='2026-10-09T15:00:00+08:00',accepted_at='2026-10-09T15:30:00+08:00',capture_deadline='2026-10-09T18:00:00+08:00')
    if mode=='corrected':manifest.update(evidence_class='RECONSTRUCTED_CORRECTED',membership_basis='CURRENT')
    if mode=='wrong_owner':manifest['source_owner']={}
    p=tmp_path/'manifest.json';p.write_text(json.dumps(manifest),encoding='utf8')
    binding=dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    if mode=='tampered_manifest':binding['sha256']='0'*64
    clock=datetime(2026,10,9,16,tzinfo=timezone(timedelta(hours=8)))
    if mode=='before_t0':clock-=timedelta(days=1)
    if mode=='after_t0':clock+=timedelta(days=1)
    with pytest.raises(ValueError,match='DIGEST_MISMATCH|REALTIME_FULL_SOURCE_MANIFEST_REQUIRED'):
        freeze_source_candidate(tmp_path,source_owner_binding=owner,source_manifest_binding=binding,candidate_directory='docs/evidence/forbidden_capture',clock=lambda:clock)
    assert not (tmp_path/'docs/evidence/forbidden_capture').exists()
