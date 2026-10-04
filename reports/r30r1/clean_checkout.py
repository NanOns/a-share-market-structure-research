"""Exact clean source and LFS materialization on user-approved F drive."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from scripts.r25_clean_checkout import ROOT,approved_directory,environment,call


def prepare(source):
    workspace=approved_directory('F:/codex_tmp')
    directory=(workspace/('r30r1-'+source[:12])).resolve()
    assert directory.parent==workspace and directory.drive.upper()=='F:'
    env=dict(environment(),GIT_LFS_SKIP_SMUDGE='1',PYTHONDONTWRITEBYTECODE='1')
    if directory.exists():
        assert call(['git','rev-parse','HEAD'],cwd=directory,text=True).strip()==source
        assert call(['git','status','--porcelain'],cwd=directory)==b''
    else: subprocess.run(['git','-c','core.longpaths=true','worktree','add','--detach',str(directory),source],cwd=ROOT,env=env,check=True)
    common=Path(call(['git','rev-parse','--git-common-dir'],text=True).strip())
    if not common.is_absolute(): common=(ROOT/common).resolve()
    names=call(['git','lfs','ls-files','--name-only'],cwd=directory,text=True,encoding='utf8').splitlines(); proof=[]
    for name in names:
        pointer=call(['git','cat-file','blob',source+':'+name]).decode(); lines=pointer.splitlines()
        assert lines[0]=='version https://git-lfs.github.com/spec/v1'
        oid=next(line.split('sha256:')[1] for line in lines if line.startswith('oid ')); size=int(next(line.split()[1] for line in lines if line.startswith('size ')))
        obj=common/'lfs/objects'/oid[:2]/oid[2:4]/oid; target=(directory/name).resolve()
        assert target.is_relative_to(directory) and obj.stat().st_size==size
        with obj.open('rb') as stream: assert hashlib.file_digest(stream,'sha256').hexdigest()==oid
        if target.stat().st_size!=size:
            assert target.read_text(encoding='utf8')==pointer
            staging=target.with_name(target.name+'.r30r1-lfs-staging'); shutil.copyfile(obj,staging); os.replace(staging,target)
        assert target.stat().st_size==size
        with target.open('rb') as stream: assert hashlib.file_digest(stream,'sha256').hexdigest()==oid
        proof.append(dict(path=name,sha256=oid,bytes=size,mode='EXACT_OBJECT_AND_F_TARGET_VERIFIED'))
    if names: subprocess.run(['git','add','-f','--pathspec-from-file=-','--pathspec-file-nul'],cwd=directory,input=b'\0'.join(n.encode() for n in names)+b'\0',check=True)
    subprocess.run(['git','diff','--cached','--quiet','--exit-code'],cwd=directory,check=True)
    assert call(['git','status','--porcelain'],cwd=directory)==b''
    return directory,proof
