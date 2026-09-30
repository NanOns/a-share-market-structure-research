from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import pytest

from src.v4.stock_prewatch import (build,digest,immutable_gzip_bytes,materialize,
    materialize_records,write_immutable_gzip_jsonl)
from tests.v4_09.test_stock_prewatch import PACKAGE,ROOT,fixture_context
from scripts.verify_v4_09_stock_prewatch import producer_vector_case
from scripts.promote_v4_08_accepted_head import b0_semantic_checks,bind,read

PRODUCER_VECTORS=json.loads((ROOT/'config/v4_09_priority_producer_vectors_r1_1.json').read_text(encoding='utf8'))['vectors']

@pytest.mark.parametrize('vector',PRODUCER_VECTORS,ids=[v['id'] for v in PRODUCER_VECTORS])
def test_state_contract_and_parameter_identity_negative_vectors(vector):
    result=producer_vector_case(vector,PACKAGE)
    assert result['passed'] and result['required_quality_unchanged']
    assert result['raw']=='TRUE'
    if vector['mode']!='correct':assert result['bucket']=='UNKNOWN_BUCKET'

def test_priority_failures_never_change_false_or_unknown_raw():
    context,cores,factors,seeds=fixture_context(count=1)
    cores[0]['states']['compression_state']['contract_id']='WRONG_PRODUCER'
    for seed_state in ['FALSE','UNKNOWN']:
        seeds[0]['base_seed_state']=seed_state
        row=build(cores,factors,seeds,context,PACKAGE)[0]
        assert row['raw_qualification']==seed_state
        assert row['structure_quality_axis']=='UNKNOWN'

@pytest.mark.parametrize('field',['b0_contract','b0_producer'])
def test_b0_validator_rejects_self_consistent_wrong_producer_or_contract(field):
    head=deepcopy(read('data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json'))
    assert all(b0_semantic_checks(head).values())
    wrong='src/sector/native_r5.py' if field=='b0_producer' else 'config/v4_08_sector_native_contract_r5.json'
    head[field]=bind(wrong);head['evidence_bindings'][field]=bind(wrong)
    assert not all(b0_semantic_checks(head).values())

def test_immutable_writer_exclusive_create_retry_and_conflict(tmp_path):
    path=tmp_path/'artifact.jsonl.gz'; rows=[{'synthetic_entity':'fixture','value':1}]
    assert write_immutable_gzip_jsonl(path,rows)=='CREATED'
    original=path.read_bytes()
    assert write_immutable_gzip_jsonl(path,rows)=='IDEMPOTENT_PASS'
    with pytest.raises(ValueError,match='APPEND_ONLY_ARTIFACT_CONFLICT'):
        write_immutable_gzip_jsonl(path,[{'synthetic_entity':'fixture','value':2}])
    assert path.read_bytes()==original and not list(tmp_path.glob('*.tmp'))

def test_concurrent_conflicting_creates_preserve_one_complete_payload(tmp_path):
    path=tmp_path/'race.jsonl.gz';versions=[[{'value':1}],[{'value':2}]]
    def write(rows):
        try:return write_immutable_gzip_jsonl(path,rows)
        except ValueError as error:return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(write,versions))
    assert sorted(results)==['APPEND_ONLY_ARTIFACT_CONFLICT','CREATED']
    assert path.read_bytes() in [immutable_gzip_bytes(rows) for rows in versions]
    assert not list(tmp_path.glob('*.tmp'))

def test_materialized_t_next_day_and_same_day_revision_do_not_replace_t(tmp_path):
    context,cores,factors,seeds=fixture_context('2030-01-02',2)
    t=materialize_records(tmp_path,context,cores,factors,seeds,PACKAGE)
    path=tmp_path/t['artifact']['path'];original=path.read_bytes()
    c1,r1,f1,s1=fixture_context('2030-01-03',3)
    next_day=materialize_records(tmp_path,c1,r1,f1,s1,PACKAGE)
    revision_context=deepcopy(context)
    revision_context['source_bindings']['synthetic_input_revision']=digest('revision-2')
    revised=materialize_records(tmp_path,revision_context,cores,factors,seeds,PACKAGE)
    assert len({r['artifact']['path'] for r in [t,next_day,revised]})==3
    assert path.read_bytes()==original
    assert materialize_records(tmp_path,context,cores,factors,seeds,PACKAGE)==t

def test_legacy_fixed_output_is_prohibited_before_loading_inputs(tmp_path):
    with pytest.raises(ValueError,match='FIXED_ARTIFACT_FILENAME_NOT_ALLOWED'):
        materialize(tmp_path,tmp_path/'fixed.jsonl.gz')
