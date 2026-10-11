"""Current closure cannot borrow old acceptance; frozen validator bodies retained."""
from pathlib import Path
import ast,hashlib
import pytest
from workbench_analysis import dm01_publication_history_reader_v2 as base
from workbench_analysis import dm01_publication_history_reader_v3 as current
from workbench_analysis.protected_stage_metadata_r3 import resolve_recorded_reader_source

ROOT=Path(__file__).resolve().parents[1]
V2=dict(path='src/workbench_analysis/dm01_publication_history_reader_v2.py',sha256='8c4c74c3fa61d1f6c4664fc143afcae07a803345ae5be3536af39b8188ac828c',bytes=4693)

def test_actual_historical_source_and_dependency_function_bodies_are_preserved():
    archive=resolve_recorded_reader_source(ROOT,V2)
    old=ast.parse(archive.read_bytes());new=ast.parse((ROOT/V2['path']).read_bytes())
    for name in ('HistoricalBindingResolver','ProjectView','injected_validators','_scope'):
        pick=lambda t:ast.dump(next(n for n in t.body if getattr(n,'name',None)==name),include_attributes=False)
        assert pick(old)==pick(new)
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==V2['sha256']

@pytest.mark.parametrize('change',[{'path':'src/workbench_analysis/dm01_runtime_r4.py'},{'sha256':'0'*64},{'bytes':4692}])
def test_recorded_v2_source_wrong_identity_is_rejected(change):
    with pytest.raises(ValueError):resolve_recorded_reader_source(ROOT,dict(V2,**change))

def test_v2_source_archive_tamper_rejected_without_git_or_permission(tmp_path):
    target=tmp_path/'data/v4/stage_head_archive/r4_r3_readers/reader_v2_original.py'
    target.parent.mkdir(parents=True);target.write_bytes(resolve_recorded_reader_source(ROOT,V2).read_bytes()+b' ')
    with pytest.raises(ValueError,match='EXACT_ARCHIVE_SHA_OR_BYTES_INVALID'):resolve_recorded_reader_source(tmp_path,V2)

def test_current_authority_and_archived_stage_have_distinct_identities():
    resolver=current.Resolver(ROOT)
    assert resolver.authority.stage['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED'
    path=resolver.resolve(current.STAGE,current.STAGE_SHA)
    assert path!=ROOT/current.STAGE
    assert hashlib.sha256(path.read_bytes()).hexdigest()==current.STAGE_SHA
    with pytest.raises(ValueError,match='PUBLICATION_STAGE_ARCHIVE_HASH_MISMATCH'):
        resolver.resolve(current.STAGE,'0'*64)
    for path in ('../outside.json','C:/outside.json','data/v4/../../outside.json'):
        with pytest.raises(ValueError):resolver.resolve(path)
