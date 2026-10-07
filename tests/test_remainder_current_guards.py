"""Current full-regression protection and current R25 fail-closed boundary."""
import os
from pathlib import Path
import pytest,psycopg
from scripts.full_chain_repair_io import ROOT

def test_unknown_pg_endpoint_rejected_before_connect():
    with pytest.raises(ValueError,match='DISPOSABLE_PG_CLUSTER_REQUIRED'):
        psycopg.connect('host=127.0.0.1 port=5432 dbname=market_research connect_timeout=1')

@pytest.mark.parametrize('operation',['open','mkdir','rename'])
def test_protected_filesystem_mutation_rejected(operation,tmp_path):
    target=ROOT/'data'/'REMAINDER_GUARD_NEGATIVE_MUST_NOT_EXIST'
    assert not target.exists()
    with pytest.raises(ValueError,match='PROTECTED_FILESYSTEM_WRITE_FORBIDDEN'):
        if operation=='open':target.write_bytes(b'forbidden')
        elif operation=='mkdir':target.mkdir()
        else:
            source=tmp_path/'source';source.write_bytes(b'isolated');os.rename(source,target)
    assert not target.exists()

def test_current_r25_keeps_historical_source_freeze_closed():
    from scripts.validate_r25_preflight import selection
    from scripts.validate_r25_preflight_v6 import selection as successor
    for gate in (selection,successor):
        with pytest.raises(ValueError,match='HISTORICAL_PROTECTED_BYTES_CHANGED'):gate(ROOT)
    # This task formally supersedes tests; admission and R25 rebuild stay gated.


@pytest.mark.parametrize('rel',['D:/new_tdx/x.day','D:\\new_tdx\\x.day','../outside.json','/absolute.json','E:/codex work/大A交易/data/v4/V4_DATA_ACCEPTED_HEAD.json'])
def test_profile_copy_rejects_nonrelative_references_before_io(rel,tmp_path):
    from scripts.forward_remainder_profiles import relative_reference
    assert relative_reference(tmp_path,rel) is None


def test_frozen_profile_reads_exact_git_and_tracks_mutations(tmp_path,monkeypatch):
    import subprocess
    from tests.remainder_historical_profiles import install
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    subprocess.run(['git','config','core.autocrlf','false'],cwd=tmp_path,check=True)
    target=tmp_path/'frozen.txt';target.write_bytes(b'exact historical bytes\n')
    subprocess.run(['git','add','frozen.txt'],cwd=tmp_path,check=True)
    oid=subprocess.check_output(['git','rev-parse',':frozen.txt'],cwd=tmp_path,text=True).strip()
    subprocess.run(['git','update-index','--skip-worktree','frozen.txt'],cwd=tmp_path,check=True)
    target.unlink()
    install(monkeypatch,tmp_path,{'frozen.txt':oid})
    assert target.exists() and target.read_bytes()==b'exact historical bytes\n'
    assert list(tmp_path.glob('*.txt'))==[target]
    assert list(Path(__file__).parent.glob('test_remainder_current_guards.py'))
    with pytest.raises(ValueError,match='PINNED_HISTORICAL_TRACKED_FILE_WRITE_FORBIDDEN'):target.write_bytes(b'forbidden')
    with pytest.raises(ValueError,match='PINNED_HISTORICAL_TRACKED_FILE_WRITE_FORBIDDEN'):
        with open(target,'wb') as stream:stream.write(b'forbidden')
    import os
    descriptor=os.open(target,os.O_WRONLY|os.O_TRUNC)
    try:os.write(descriptor,b'changed\n')
    finally:os.close(descriptor)
    assert subprocess.check_output(['git','diff','--name-only'],cwd=tmp_path,text=True).strip()=='frozen.txt'
def test_g_storage_child_keeps_protected_root_rejection():
    import subprocess,sys,uuid
    from pathlib import Path
    from tests.runtime_isolation import REPOSITORY
    root=Path('G:/codex_tmp/test_temp')/('remainder_storage_guard_'+uuid.uuid4().hex)
    code="""from tests.remainder_storage import configure
from tests.runtime_isolation import create,guard
import sys
configure('G:/codex_tmp/test_temp')
root=create(sys.argv[1]);guard(root,root/'test.db')
for root,database in [('D:/new_tdx','D:/new_tdx/test.db'),(sys.argv[2],sys.argv[2]+'/data/database/market_research.duckdb')]:
 try:guard(root,database)
 except ValueError:pass
 else:raise AssertionError('PROTECTED_ROOT_ACCEPTED')
try:configure('D:/new_tdx')
except ValueError:pass
else:raise AssertionError('UNREGISTERED_STORAGE_ACCEPTED')
print('G_DISPOSABLE_ONLY_PASS')
"""
    result=subprocess.run([sys.executable,'-c',code,str(root),str(REPOSITORY)],cwd=REPOSITORY,text=True,capture_output=True,check=True)
    assert result.stdout.strip()=='G_DISPOSABLE_ONLY_PASS'
