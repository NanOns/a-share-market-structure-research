import copy,hashlib,json,shutil
from pathlib import Path
import pytest
from src.v4.stock_prewatch import load_package,load_accepted,build,immutable_gzip_bytes,digest
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def frozen_root(tmp_path):
    freeze=json.loads((ROOT/'reports/v4_09/V4_09_CONTRACT_FREEZE.json').read_text(encoding='utf8'))
    repair=json.loads((ROOT/'reports/v4_09/V4_09_R1_1_REPAIR_CONTRACT_FREEZE.json').read_text(encoding='utf8'))
    paths={'reports/v4_09/V4_09_CONTRACT_FREEZE.json','reports/v4_09/V4_09_R1_1_REPAIR_CONTRACT_FREEZE.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_09_ACCEPTED_HEAD.json','data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json','data/v4/V4_08_ACCEPTED_HEAD.json'}
    bindings=freeze['frozen_bindings']+repair['new_bindings']+[v for v in freeze['authority'].values() if isinstance(v,dict) and 'path' in v]+[repair[k] for k in ['authority','migration_semantics_preserved','protected_original_artifact']]
    paths.update(b['path'] for b in bindings)
    for p in paths:
        dest=tmp_path/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
    assert load_package(tmp_path)==load_package(ROOT)
    return tmp_path

@pytest.mark.parametrize('mode',['status','identity','authority','missing','extra','wrong_file','consumer','original_parent','receipt_extension'])
def test_self_consistent_wrong_repair_rejected(frozen_root,mode):
    path=frozen_root/'reports/v4_09/V4_09_R1_1_REPAIR_CONTRACT_FREEZE.json';repair=json.loads(path.read_text(encoding='utf8'))
    if mode=='status':repair['status']='SELF_ACCEPTED'
    if mode=='identity':repair['contract_id']='OTHER_REPAIR_SAME_FORMAT'
    if mode=='authority':repair['authority']=copy.deepcopy(repair['new_bindings'][0])
    if mode=='missing':repair['new_bindings'].pop()
    if mode=='extra':repair['new_bindings'].append(copy.deepcopy(repair['new_bindings'][0]))
    if mode=='wrong_file':repair['new_bindings'][0]['sha256']=repair['new_bindings'][1]['sha256']
    if mode=='consumer':repair['immutable_writer_contract']['consumer_contract_id']='OTHER_CONSUMER'
    if mode=='original_parent':repair['original_frozen_bindings']=repair['original_frozen_bindings'][:-1]
    if mode=='receipt_extension':repair['self_consistent_unaccepted_extension']='changed receipt'
    path.write_text(json.dumps(repair),encoding='utf8')
    with pytest.raises(ValueError):load_package(frozen_root)

def test_hash_valid_wrong_amended_parent_rejected(frozen_root):
    path=frozen_root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json';head=json.loads(path.read_text(encoding='utf8'))
    other=frozen_root/'data/v4/V4_08_ACCEPTED_HEAD.json'
    head['v4_08_binding']=dict(path=other.relative_to(frozen_root).as_posix(),sha256=hashlib.sha256(other.read_bytes()).hexdigest(),byte_count=other.stat().st_size)
    path.write_text(json.dumps(head),encoding='utf8')
    with pytest.raises(ValueError,match='REPAIR_AMENDED_PARENT_MISMATCH'):load_package(frozen_root)

def test_accepted_full_market_replay_has_identical_bytes_and_logical_digest():
    head=json.loads((ROOT/'data/v4/V4_09_ACCEPTED_HEAD.json').read_text(encoding='utf8'));binding=head['artifact']
    context,cores,factors,seeds,package=load_accepted(ROOT);records=build(cores,factors,seeds,context,package)
    assert len(records)==5222
    assert immutable_gzip_bytes(records)==(ROOT/binding['path']).read_bytes()
    assert digest(records)==binding['logical_digest']

def test_historical_archive_does_not_accept_current_runtime_for_new_promotion():
    from scripts.promote_v4_09_accepted_head import source_checks,validate
    result=validate()
    assert result['status']=='PASS' and result['validation_scope']=='ACCEPTED_PUBLICATION_HISTORY_ONLY'
    assert result['current_runtime_matches_accepted_implementation'] is False
    assert result['current_runtime_external_acceptance']=='PENDING_INDEPENDENT_EXTERNAL_AUDIT'
    assert not all(source_checks().values())

def test_self_consistent_wrong_archive_cannot_replace_accepted_source(monkeypatch):
    from scripts import promote_v4_09_accepted_head as validator
    original_read=validator.read
    archive=copy.deepcopy(original_read('config/v4_09_historical_runtime_archive_r1.json'))
    current=validator.bind('src/v4/stock_prewatch.py')
    archive['bindings']['src/v4/stock_prewatch.py'].update(accepted_source=current,archive=current)
    monkeypatch.setattr(validator,'read',lambda p:archive if p=='config/v4_09_historical_runtime_archive_r1.json' else original_read(p))
    assert validator.validate()['status']=='FAIL'
