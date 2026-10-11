from pathlib import Path
import os,subprocess
import pytest
from workbench_analysis.fep_engineering_storage import engineering_directory
from workbench_analysis.fep_e3.protocol import immutable

def directory_link(link,target):
    if os.name=='nt':
        # Windows junctions exercise real resolved reparse points without
        # requiring the separate symbolic-link privilege on this machine.
        subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],check=True,capture_output=True)
    else:
        link.symlink_to(target,target_is_directory=True)

@pytest.mark.parametrize('path',[
    'D:/new_tdx/out','G:/elsewhere','G:/codex_tmp_other/out',
    'G:/codex work/大A交易/data/v4/out','G:/codex work/大A交易/artifacts/out',
    'E:/engineering/out','G:/codex_tmp/../elsewhere',
])
def test_forbidden_roots_rejected_before_any_write(path):
    with pytest.raises(ValueError,match='DENIED'):
        engineering_directory(path,error='DENIED')

def test_resolved_symlink_escape_rejected(tmp_path):
    link=tmp_path/'escape'
    # Creating the link writes only inside the authorized G test directory.
    directory_link(link,Path('G:/codex work/大A交易'))
    with pytest.raises(ValueError,match='DENIED'):
        engineering_directory(link/'data/v4',error='DENIED')

def test_symlink_inside_engineering_root_and_atomic_identity(tmp_path):
    actual=tmp_path/'actual';actual.mkdir()
    link=tmp_path/'inside';directory_link(link,actual)
    assert engineering_directory(link,error='DENIED')==actual
    a,path=immutable(link,'model',dict(value=1,created_at='a',run_id='a'))
    original=path.read_bytes()
    b,same=immutable(link,'model',dict(value=1,created_at='b',run_id='b'))
    assert a['artifact_id']==b['artifact_id'] and path==same and path.read_bytes()==original
    c,other=immutable(link,'model',dict(value=2))
    assert c['artifact_id']!=a['artifact_id'] and other!=path

@pytest.mark.parametrize('kind',['../escape','..\\escape','G:/elsewhere','/absolute','a/b','a\\b',''])
def test_artifact_kind_cannot_escape_admitted_directory(tmp_path,kind):
    before=list(tmp_path.iterdir())
    with pytest.raises(ValueError,match='E3_ARTIFACT_KIND_PATH_REQUIRED'):
        immutable(tmp_path,kind,dict(value=1))
    assert list(tmp_path.iterdir())==before
