"""Real accepted envelopes and adversarial engineering owner identity vectors."""
import copy
import json
from pathlib import Path

import pytest

from workbench_analysis.fep_e1 import feature_owner as owner, snapshots

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/fep_e1_r2_final'


def load():
    contract=json.loads((ROOT/'config/fep_feature_owner_contract_v1.json').read_bytes())
    row=json.loads((OUT/'OWNER_ROW_PROJECTION.json').read_bytes())['source_row']
    return contract,row


def test_all_47_accepted_historical_fields_and_seven_relative_rps_are_copied():
    contract,row=load()
    projection=owner.read(ROOT,contract,entity_id=row['security_id'],trade_date=row['trade_date'])
    assert len(projection['values'])==47
    for name in ('rel_market_1','rel_market_3','rel_market_5','rps20','rps20_delta3','rps5','rps5_delta1'):
        assert projection['values'][name]['value']==row['fields'][name]['value']
        assert projection['values'][name]['source_digest']==row['fields'][name]['output_digest']
    assert projection['evidence_origin']=='RECONSTRUCTED_ASOF'
    assert not projection['FIRST_OBSERVED'] and not projection['AS_RECORDED']


@pytest.mark.parametrize('case',['missing_field','wrong_date','nonfinite','wrong_type','unknown_without_reason','missing_window'])
def test_owner_envelope_counterfactuals(case):
    contract,row=load();row=copy.deepcopy(row);name=contract['fields'][0]['field_name'];f=row['fields'][name]
    if case=='missing_field':del row['fields'][name]
    if case=='wrong_date':row['trade_date']='2030-01-01'
    if case=='nonfinite':f['value']=float('nan')
    if case=='wrong_type':f['value']='numeric alias'
    if case=='unknown_without_reason':f.update(value=None,quality_state='UNKNOWN',unknown_reason=None)
    if case=='missing_window':del f['window_identity']
    with pytest.raises(ValueError):owner.project_row(row,contract)


def test_unknown_is_present_and_not_imputed():
    contract,row=load();row=copy.deepcopy(row);name=contract['fields'][0]['field_name']
    row['fields'][name].update(value=None,quality_state='UNKNOWN',unknown_reason='ENGINEERING_MISSING_INPUT_VECTOR')
    p=owner.project_row(row,contract)
    assert len(p['values'])==47 and p['values'][name]['value'] is None
    assert p['values'][name]['quality']=='UNKNOWN'


@pytest.mark.parametrize('case',['guessed_alias','wrong_owner_digest','reduced_fields','pit_overclaim','wrong_calendar_digest'])
def test_owner_contract_counterfactuals(case):
    contract,_=load();c=copy.deepcopy(contract)
    if case=='guessed_alias':c['fields'][0]['value_path']=['guessed_english_alias']
    if case=='wrong_owner_digest':c['owner_artifact']['sha256']='0'*64
    if case=='reduced_fields':c['fields']=c['fields'][:-1]
    if case=='pit_overclaim':c['FIRST_OBSERVED']=True
    if case=='wrong_calendar_digest':c['calendar']['sha256']='0'*64
    with pytest.raises(ValueError):owner.validate_contract(ROOT,c)


def test_engineering_snapshot_same_capture_replay_is_stable_and_rejects_pit():
    obs=json.loads((OUT/'ENGINEERING_OBSERVATION.json').read_bytes())
    snap=json.loads((OUT/'ENGINEERING_SNAPSHOT.json').read_bytes())
    registry=json.loads((OUT/'ENGINEERING_MAPPING_REGISTRY.json').read_bytes())
    result=snapshots.build(ROOT,obs,1,snap['dependency_manifest'],snap['values'],registry,
                           feature_cutoff=snap['feature_cutoff'],created_at=snap['created_at'],
                           evidence_origin='RECONSTRUCTED_ASOF',execution_mode='REPLAY')
    assert result['feature_digest']==snap['feature_digest'] and len(result['values'])==47
    with pytest.raises(ValueError,match='PIT_CAPTURE_NOT_ENABLED'):
        snapshots.build(ROOT,obs,1,snap['dependency_manifest'],snap['values'],registry,
                        feature_cutoff=snap['feature_cutoff'],created_at=snap['created_at'],
                        evidence_origin='PIT_OBSERVED',execution_mode='REPLAY')
