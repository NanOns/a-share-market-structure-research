from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.v4.research_state import reduce_state
from src.v4.state_identity import digest,canonical,state_id
from src.v4.state_provenance import PostgresEngineeringLedger,validate_output
from scripts.v4_10_r1_2_fixtures import synthetic_input,accepted_bundle,publish_setup,refresh,setup_vector
from scripts.verify_v4_10_r1_2 import direct_sql_probes,independent_input_audit,sql_digest
ROOT=Path(__file__).resolve().parents[2]
VECTORS=json.loads((ROOT/'config/v4_10_machine_vectors_r1_2.json').read_text(encoding='utf8'))['vectors'][98:]

@pytest.mark.parametrize('v',[v for v in VECTORS if v['kind']=='API'],ids=[v['id'] for v in VECTORS if v['kind']=='API'])
def test_r1_1_adversarial_api_vector(v,pg):
    setup=v.get('ledger_setup')
    setup_vector(pg,setup)
    audit=independent_input_audit(v['input'],pg)
    if v['expected_error']:
        with pytest.raises(ValueError,match=v['expected_error']):reduce_state(v['input'],ledger=PostgresEngineeringLedger(pg))
        assert not audit['valid']
    else:
        r=reduce_state(v['input'],ledger=PostgresEngineeringLedger(pg))
        assert {k:r[k] for k in v['expected']}==v['expected'] and audit['valid']
        if r['boundary_event']:assert 'REENTERED' not in r['transition_reasons']

def test_direct_sql_forgery_gate_has_exact_rejection_reasons(pg):
    checks,errors=direct_sql_probes(pg)
    assert checks and all(checks.values()),errors

@pytest.mark.parametrize('mode',['SYNTHETIC_CONTRACT_VECTOR','ACCEPTED_FACT_INTERFACE'])
@pytest.mark.parametrize('bad',['PUB',[],[''],['PUB','PUB'],[['PUB']],[1],[None]])
def test_publication_manifest_shape_both_modes(mode,bad):
    x=synthetic_input() if mode=='SYNTHETIC_CONTRACT_VECTOR' else accepted_bundle()[0]
    x['input_publication_ids']=bad
    with pytest.raises(ValueError,match='INPUT_PUBLICATION_MANIFEST_SHAPE_INVALID'):reduce_state(x)

def test_accepted_interface_never_accepts_a_caller_supplied_fake_resolver():
    x=accepted_bundle()[0]
    with pytest.raises(ValueError,match='TRUSTED_ENGINEERING_LEDGER_REQUIRED'):reduce_state(x,ledger={'prior':'self-consistent'})

@pytest.mark.parametrize('value',[0,-0.0,1.0,1e-7,1.2e12,-3.01,{'中文':'你好\n世界','é':True,'items':[None,0.10,-0.0]}])
def test_independent_python_and_sql_canonical_numeric_unicode_identity(pg,value):
    assert digest(value)==sql_digest(pg,value)

def test_future_published_fact_not_available_by_cutoff_is_rejected(pg):
    x,manifests=accepted_bundle()
    # The trusted issuer publishes the future timestamp; the caller cannot make it usable at T.
    m=manifests[1]
    for f in m['fields'].values():f['system_available_at']='2026-09-29T01:00:00Z'
    pub='V4_10_INPUT:'+digest(m)
    for f in x['input_provenance'].values():
        if f['status']=='IMPLEMENTED':f.update(publication_id=pub,system_available_at='2026-09-29T01:00:00Z')
    x['input_publication_ids']=[pub];refresh(x);publish_setup(pg,manifests)
    with pytest.raises(ValueError,match='FIELD_TIME_AVAILABILITY_MISMATCH'):reduce_state(x,ledger=PostgresEngineeringLedger(pg))
    assert not independent_input_audit(x,pg)['valid']

def test_output_schema_rejects_complete_but_wrong_counter_type():
    r=reduce_state(synthetic_input());r['expiry_count']=True;r['publication_id']=state_id(r)
    with pytest.raises(ValueError,match='PRIOR_SCHEMA_COUNTER_INVALID'):validate_output(r)
