import json,subprocess
from pathlib import Path
import pytest
from workbench_analysis.portable_historical_archives_r1 import resolve,PATH,BOOK

@pytest.fixture
def archive(tmp_path):
    repository=Path(__file__).resolve().parents[1]
    manifest=json.loads((repository/PATH).read_bytes())
    row=manifest['entries'][0]
    for name in (PATH,BOOK,row['archive']['path']):
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((repository/name).read_bytes())
    return tmp_path,manifest,row

def test_runtime_exact_archive_verifies_without_git(archive,monkeypatch):
    root,_,row=archive
    monkeypatch.setattr(subprocess,'check_output',lambda *a,**k:pytest.fail('RUNTIME_GIT_DEPENDENCY'))
    path=resolve(root,row['original'])
    assert path==root/row['archive']['path']

@pytest.mark.parametrize('mutation',['archive','commit','registry','unregistered','grant','witness_hash'])
def test_portable_archive_tampering_rejected(archive,mutation):
    root,manifest,row=archive
    binding=dict(row['original'])
    if mutation=='archive':(root/row['archive']['path']).write_bytes(b'CHANGED')
    elif mutation=='commit':manifest['entries'][0]['source_commit']='0'*40
    elif mutation=='registry':(root/BOOK).write_bytes(b'{}')
    elif mutation=='unregistered':binding['sha256']='0'*64
    elif mutation=='grant':manifest['authority_granted']=True
    elif mutation=='witness_hash':manifest['entries'][0]['verified_git_blob_sha256']='0'*64
    (root/PATH).write_text(json.dumps(manifest),encoding='utf8')
    with pytest.raises(ValueError):resolve(root,binding)
