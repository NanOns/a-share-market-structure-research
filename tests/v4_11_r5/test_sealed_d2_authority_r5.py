"""Reject self-asserted authority even when serialized digests are recomputed."""
from copy import deepcopy
import pytest
from src.v4.sealed_owner_authority_r5 import verify_manifest_sources
from src.v4.confirmation import digest
from src.v4.confirmation_d2_candidate_r5 import adapter_ast_evidence

@pytest.fixture
def authority_fixture():
    day='2026-09-30';sid='SEC-'+'A'*32
    source=dict(entity_id=sid,trade_date=day,field='SEED',value='UNKNOWN',quality='UNKNOWN',producer_contract_id='BASE_SEED_V1',parameter_set_id='V4_07_BASE_SEED_PARAMETER_SET_V1',publication_id='SEALED_OWNER',source_output_digest='PINNED_OWNER_OUTPUT',publication_binding=dict(path='sealed/owners.json',sha256='a'*64,bytes=1))
    envelope=dict(value='UNKNOWN',quality='UNKNOWN',source_field_payload=dict(authoritative_source=deepcopy(source)))
    return dict(trade_date=day,rows=[dict(entity_id=sid,fields={'SEED':envelope})]),{day:{sid:{'SEED':source}}}

@pytest.mark.parametrize('field,value',[('value','TRUE'),('quality','KNOWN'),('publication_id','RAW_HELPER'),('source_output_digest','RECOMPUTED_SELF_ASSERTED'),('trade_date','2026-09-29'),('producer_contract_id','UNAUTHORIZED'),('parameter_set_id','MODIFIED')])
def test_tampered_authority_rejected_even_with_new_payload_digest(authority_fixture,field,value):
    manifest,authority=authority_fixture;envelope=manifest['rows'][0]['fields']['SEED']
    envelope['source_field_payload']['authoritative_source'][field]=value
    envelope['source_output_digest']=digest(envelope['source_field_payload'])
    with pytest.raises(ValueError,match='D2_INPUT_NOT_FROM_SEALED'):verify_manifest_sources(manifest,authority)

def test_reconstructed_known_cannot_replace_owner_unknown(authority_fixture):
    manifest,authority=authority_fixture;manifest['rows'][0]['fields']['SEED'].update(value='TRUE',quality='KNOWN')
    with pytest.raises(ValueError):verify_manifest_sources(manifest,authority)

def test_missing_entity_not_silently_admitted(authority_fixture):
    manifest,authority=authority_fixture;manifest['rows']=[]
    with pytest.raises(ValueError,match='EXACT_UNIVERSE'):verify_manifest_sources(manifest,authority)

def test_exact_reducer_ast_rule_order_parameters():
    report=adapter_ast_evidence()
    assert report['exact_rule_order'] and report['exact_business_thresholds']
    assert all(v['normalized_business_AST_exact'] for v in report['business_AST_comparisons'].values())
