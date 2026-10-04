"""Exact detached R31 source checkout; all temporary storage is on F drive."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from reports.r31.build_contract import write


def call(args,cwd=ROOT):
    return subprocess.check_output(args,cwd=cwd)


def prepare(source):
    workspace=Path('F:/codex_tmp').resolve()
    workspace.mkdir(parents=True,exist_ok=True)
    directory=(workspace/('r31-'+source[:12])).resolve()
    assert directory.parent==workspace and directory.drive.upper()=='F:'
    env=dict(os.environ,GIT_LFS_SKIP_SMUDGE='1',PYTHONDONTWRITEBYTECODE='1',TEMP='F:/codex_tmp/test_temp',TMP='F:/codex_tmp/test_temp',TMPDIR='F:/codex_tmp/test_temp')
    if directory.exists():
        assert call(['git','rev-parse','HEAD'],directory).decode().strip()==source
        assert call(['git','status','--porcelain'],directory)==b''
    else:
        subprocess.run(['git','-c','core.longpaths=true','worktree','add','--detach',str(directory),source],cwd=ROOT,env=env,check=True)
    common=Path(call(['git','rev-parse','--git-common-dir']).decode().strip())
    if not common.is_absolute(): common=(ROOT/common).resolve()
    names=call(['git','lfs','ls-files','--name-only'],directory).decode('utf8').splitlines()
    proof=[]
    for name in names:
        pointer=call(['git','cat-file','blob',source+':'+name]).decode()
        lines=pointer.splitlines(); assert lines[0]=='version https://git-lfs.github.com/spec/v1'
        oid=next(line.split('sha256:')[1] for line in lines if line.startswith('oid '))
        size=int(next(line.split()[1] for line in lines if line.startswith('size ')))
        obj=common/'lfs/objects'/oid[:2]/oid[2:4]/oid
        target=(directory/name).resolve(); assert target.is_relative_to(directory)
        assert obj.stat().st_size==size
        with obj.open('rb') as stream: assert hashlib.file_digest(stream,'sha256').hexdigest()==oid
        if target.stat().st_size!=size:
            assert target.read_text(encoding='utf8')==pointer
            staging=target.with_name(target.name+'.r31-lfs-staging'); shutil.copyfile(obj,staging); os.replace(staging,target)
        assert target.stat().st_size==size
        with target.open('rb') as stream: assert hashlib.file_digest(stream,'sha256').hexdigest()==oid
        proof.append(dict(path=name,sha256=oid,bytes=size,mode='EXACT_GIT_LFS_OBJECT_AND_F_TARGET_SHA256_VERIFIED'))
    if names:
        subprocess.run(['git','add','-f','--pathspec-from-file=-','--pathspec-file-nul'],cwd=directory,input=b'\0'.join(n.encode() for n in names)+b'\0',check=True)
    assert call(['git','status','--porcelain'],directory)==b''
    write('reports/r31/CLEAN_CHECKOUT_PROOF.json',dict(source_commit=source,directory=str(directory),clean=True,detached=True,LFS=proof,temporary_drive='F:',actual_real_rows_written=0))
    print(str(directory),flush=True)
    return directory


if __name__=='__main__':
    prepare(sys.argv[1])
