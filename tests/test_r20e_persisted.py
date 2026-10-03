"""Independent persisted oracle adversarial suite, against exact disk artifacts."""
import copy,json
from pathlib import Path
import pytest
from scripts import validate_r20e_oracle as oracle
from scripts import validate_r20a_current as authority_oracle
ROOT=Path(__file__).resolve().parents[1]

def receipts():
    p=json.loads((ROOT/'reports/r20e/PRODUCER_RECEIPT.json').read_bytes())
    t=json.loads((ROOT/'reports/r20e/SETTLEMENT_RECEIPT.json').read_bytes())
    return p,t
def load(r):return json.loads((ROOT/r['path']).read_bytes())

def test_full_independent_disk_oracle():
    result=oracle.validate()
    assert result['R20E_INDEPENDENT_ORACLE']=='PASS_LOCAL'
    assert result['absolute_settlements_verified']>=20

@pytest.mark.parametrize('attack',['stage_pointer_reverted_to_v4_13','stale_v4_14_entry','v4_14_head_digest_mutated'])
def test_current_authority_negatives(attack):
    stage=authority_oracle.read(authority_oracle.STAGE)
    if attack=='stage_pointer_reverted_to_v4_13':stage['accepted_stage_range']='V4_00_TO_V4_13_ACCEPTED'
    elif attack=='stale_v4_14_entry':stage['v4_14_entry']='CONTRACT_FREEZE_ONLY_NOT_REPLAY_PASS'
    else:stage['v4_14_binding']['sha256']='0'*64
    with pytest.raises(ValueError):authority_oracle.validate(stage=stage)

@pytest.mark.parametrize('attack',[
    'future_source_before_T0_freeze','Focus_filters_enrollment','UI_filters_enrollment',
    'same_day_revision_new_logical_event','source_correction_resets_T0',
    'source_correction_redraws_controls','benchmark_reweights_missing_member',
    'marked_threshold_invented','control_future_refill','control_assignment_changed_after_crossing',
    'same_source_creates_duplicate_revision','corrected_source_overwrites_first_observed',
    'mixed_adjustment_basis','unregistered_CRLF_normalization','binary_normalization',
    'FEP_feedback','raw_provider_fallback'])
def test_persisted_semantic_negatives(attack):
    p,t=receipts();objects={}
    def changed(r):
        if r['path'] not in objects:objects[r['path']]=load(r)
        return objects[r['path']]
    firstmanifest=load(p['publications'][0]);fr=p['freezes'][0]
    observed=next(r for r in t['outcomes'] if load(r)['outcome_status']=='OBSERVED')
    if attack=='future_source_before_T0_freeze':t['first_future_source_open_at']=p['start']
    elif attack=='Focus_filters_enrollment':p['first_enrollments']=p['first_enrollments'][:1]
    elif attack=='UI_filters_enrollment':changed(firstmanifest['daily_ledger'][0])['display_rank']=1
    elif attack=='same_day_revision_new_logical_event':changed(p['publications'][1])['logical_events'].append({'path':'fake','sha256':'0'*64,'bytes':0})
    elif attack=='source_correction_resets_T0':changed(p['first_enrollments'][0])['T0']='2026-09-01'
    elif attack in ('source_correction_redraws_controls','control_future_refill'):changed(fr)['controls']['C']['control_entity_ids']=['FUTURE_ONLY']
    elif attack=='benchmark_reweights_missing_member':changed(fr)['market']['members'][0]['weight']=1
    elif attack=='marked_threshold_invented':changed(observed)['market_benchmark']['marked_permission']=True
    elif attack=='control_assignment_changed_after_crossing':changed(p['crossed'])['assignment_digest']='0'*64
    elif attack=='same_source_creates_duplicate_revision':
        r=t['corrected_outcomes'][0];o=changed(r);o['evaluation_source']=t['future_sources'][0]
    elif attack=='corrected_source_overwrites_first_observed':
        r=next(r for r in t['readbacks'] if any(load(x)['frozen_t0']==load(r)['frozen_t0'] for x in t['corrected_outcomes']))
        view=changed(r);view['FIRST_OBSERVED']=copy.deepcopy(view['LATEST_CORRECTED'])
    elif attack=='mixed_adjustment_basis':changed(observed)['price_path'][0]['evaluation_basis_date']='2099-01-01'
    elif attack in ('unregistered_CRLF_normalization','binary_normalization'):
        receipt=p['portability_receipts'][0];receipt['normalization_applied']=True
        receipt['authority_mode']='LFS_OBJECT_EXACT' if attack=='binary_normalization' else 'UNREGISTERED_TEXT_NORMALIZE'
    elif attack=='FEP_feedback':p['input_channels'].append('FEP_PREDICTION')
    else:t['raw_provider_fallback']=True
    with pytest.raises((ValueError,KeyError,FileNotFoundError)):oracle.validate(p,t,objects)

def test_changed_byte_overwrite_fails_closed(tmp_path):
    from workbench_analysis.v4_15_persistence import Store
    store=Store(tmp_path,'reports/v4_15_runtime_r20/negative')
    first=store.append('outcomes','stable',{'value':1})
    assert store.append('outcomes','stable',{'value':1})==first
    with pytest.raises(ValueError):store.append('outcomes','stable',{'value':2})

def test_oracle_does_not_import_evaluators_or_resolver():
    source=(ROOT/'scripts/validate_r20e_oracle.py').read_text()
    for prohibited in ['v4_15_radar_cohort','v4_15_settlement','v4_portable_exact']:
        assert prohibited not in source
