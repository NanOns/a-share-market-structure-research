"""Clean detached regression on user-approved E/F drives, with exact LFS proof."""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from scripts.r25_io import ROOT, read


def call(args, **kwargs):
    return subprocess.check_output(args, cwd=kwargs.pop('cwd', ROOT), **kwargs)


def approved_directory(path):
    directory = Path(path).resolve()
    if directory.drive.upper() not in ('E:', 'F:'):
        raise ValueError('USER_REQUIRES_TEMPORARY_SPACE_ON_E_OR_F')
    if directory == ROOT or directory.is_relative_to(ROOT):
        raise ValueError('REGRESSION_SPACE_MUST_BE_OUTSIDE_MAIN_CHECKOUT')
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def environment(root=ROOT):
    contract = read('config/v4_16_r25_packet_preflight_v1.json', root)
    temporary = approved_directory(contract['test_temporary_root'])
    return dict(os.environ, TMP=str(temporary), TEMP=str(temporary), TMPDIR=str(temporary),
                PYTHONPATH='src'+os.pathsep+'.')


def prepare(source):
    contract = read('config/v4_16_r25_packet_preflight_v1.json')
    workspace = approved_directory(contract['regression_workspace_root'])
    directory = (workspace / ('r25-'+source[:12])).resolve()
    if directory.drive.upper() not in ('E:', 'F:') or directory.parent != workspace:
        raise ValueError('USER_REQUIRES_TEMPORARY_SPACE_ON_E_OR_F')
    env = dict(environment(), GIT_LFS_SKIP_SMUDGE='1')
    if directory.exists():
        assert call(['git', 'rev-parse', 'HEAD'], cwd=directory, text=True).strip() == source
        assert call(['git', 'status', '--porcelain'], cwd=directory) == b''
    else:
        subprocess.run(['git', '-c', 'core.longpaths=true', 'worktree', 'add', '--detach', str(directory), source], cwd=ROOT, env=env, check=True)
    common = Path(call(['git', 'rev-parse', '--git-common-dir'], text=True).strip())
    if not common.is_absolute():
        common = (ROOT/common).resolve()
    names = call(['git', 'lfs', 'ls-files', '--name-only'], cwd=directory, text=True, encoding='utf8').splitlines()
    verified = []
    for name in names:
        pointer = call(['git', 'cat-file', 'blob', source+':'+name]).decode()
        assert pointer.startswith('version https://git-lfs.github.com/spec/v1\n')
        lines = pointer.splitlines()
        oid = next(line.split('sha256:')[1] for line in lines if line.startswith('oid '))
        size = int(next(line.split()[1] for line in lines if line.startswith('size ')))
        source_object = common/'lfs/objects'/oid[:2]/oid[2:4]/oid
        assert source_object.stat().st_size == size
        with source_object.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == oid
        target = (directory/name).resolve()
        assert target.is_relative_to(directory.resolve())
        if target.stat().st_size != size:
            assert target.read_text(encoding='utf8') == pointer
            staging = target.with_name(target.name+'.r25-lfs-staging')
            shutil.copyfile(source_object, staging)
            assert staging.stat().st_size == size
            with staging.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == oid
            os.replace(staging, target)
        with target.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == oid
        verified.append(dict(path=name, sha256=oid, bytes=size, mode='EXACT_OBJECT_AND_TARGET_SHA256_VERIFIED_E_F_ONLY'))
    if names:
        subprocess.run(['git', 'add', '-f', '--pathspec-from-file=-', '--pathspec-file-nul'], cwd=directory,
                       input=b'\0'.join(name.encode('utf8') for name in names)+b'\0', check=True)
    subprocess.run(['git', 'diff', '--cached', '--quiet', '--exit-code'], cwd=directory, check=True)
    assert call(['git', 'status', '--porcelain'], cwd=directory) == b''
    return directory, verified
