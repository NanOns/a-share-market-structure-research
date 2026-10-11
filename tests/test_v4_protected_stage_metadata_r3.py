"""Original historical bytes and permission separation under an upgraded V4 head."""
from pathlib import Path
import hashlib,json,shutil
import pytest
from workbench_analysis import protected_stage_metadata_r3 as reader

ROOT=Path(__file__).resolve().parents[1]
OLD=dict(path='data/v4/V4_STAGE_ACCEPTED_HEAD.json',sha256='529c532bd5553ace00fa4813aef07979cfce4e1f18fa5ea66f38fcddd8ed16cb',bytes=8574)

def test_real_current_stage_keeps_exact_historical_metadata_without_permission():
    path,receipt=reader.resolve(ROOT,OLD)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==OLD['sha256']
    assert len(path.read_bytes())==8574
    assert json.loads(path.read_bytes())['accepted_stage_range']=='V4_00_TO_V4_10_ACCEPTED'
    assert json.loads((ROOT/reader.STAGE).read_bytes())['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED'
    assert receipt['grants_current_permission'] is False
    assert receipt['current_bytes_substituted'] is False

@pytest.mark.parametrize('change',[{'path':'src/workbench_analysis/r43_owner_replay.py'}, {'sha256':'0'*64},{'bytes':8573}])
def test_wrong_metadata_identity_never_resolves(change):
    with pytest.raises(ValueError):reader.resolve(ROOT,dict(OLD,**change))

def test_archived_bytes_tamper_is_rejected_before_current_admission(tmp_path):
    book=reader.registry(ROOT)
    row=next(row for row in book['entries'] if row['original_namespace']['sha256']==OLD['sha256'])
    registry_path=tmp_path/'config/v4_historical_moving_head_registry_r17_v1.json'
    registry_path.parent.mkdir(parents=True);shutil.copyfile(ROOT/registry_path.relative_to(tmp_path),registry_path)
    target=tmp_path/row['archive']['path'];target.parent.mkdir(parents=True)
    target.write_bytes((ROOT/row['archive']['path']).read_bytes()+b' ')
    with pytest.raises(ValueError,match='EXACT_ARCHIVE_SHA_OR_BYTES_INVALID'):reader.resolve(tmp_path,OLD)

READER=dict(path='src/workbench_analysis/dm01_publication_history_reader_v1.py',sha256='51729be1ad211080a73f9c071a9142370e3ba281eadc3c1eb4d7969a7cd7572d',bytes=2138)

def test_recorded_reader_verifies_archived_git_bytes_without_executing_source():
    path=reader.resolve_recorded_reader_source(ROOT,READER)
    assert path.relative_to(ROOT).as_posix().startswith('reports/r17a/source_archive/')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==READER['sha256']
    assert len(path.read_bytes())==READER['bytes']
    assert hashlib.sha256((ROOT/READER['path']).read_bytes()).hexdigest()!=READER['sha256']

@pytest.mark.parametrize('change',[{'path':'src/workbench_analysis/r43_owner_replay.py'},{'sha256':'0'*64},{'bytes':2137}])
def test_recorded_reader_rejects_wrong_identity(change):
    with pytest.raises(ValueError,match='RECORDED_READER_SOURCE_IDENTITY_REQUIRED'):
        reader.resolve_recorded_reader_source(ROOT,dict(READER,**change))
