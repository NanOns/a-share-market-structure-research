"""Persistent paths, atomic writes and whole-workspace ownership."""
from pathlib import Path
from contextlib import contextmanager
import hashlib
import json
import os
import tempfile
import uuid

_OWNED = set()


def require_owned(root):
    if str(Path(root).resolve()) not in _OWNED:
        raise ValueError('WORKSPACE_LEASE_REQUIRED')


def g_path(path):
    path = Path(path).resolve()
    if os.name == 'nt' and path.drive.upper() != 'G:':
        raise ValueError('G_DRIVE_REQUIRED')
    from workbench_analysis.daily_source_freeze import ensure_outside_tdx
    ensure_outside_tdx(path, Path('D:/new_tdx'))
    return path


def atomic(path, payload):
    path = g_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8')
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class WorkspaceLease:
    """Shared by packaged and source launchers; held even with engine stopped."""
    def __init__(self, root):
        self.root = g_path(root)
        if not self.root.is_dir():
            raise ValueError('WORKSPACE_MISSING')
        self.path = self.root/'runtime/desktop/app.lock'
        self.owner = self.path.with_name('instance.json')
        self.stream = None
        import psutil
        self.identity = dict(instance_id=uuid.uuid4().hex, pid=os.getpid(),
                             workspace=str(self.root), process_created_at=psutil.Process().create_time(),
                             executable=str(Path(__import__('sys').executable).resolve()),
                             build_release_id=verify_resources()['build_release_id'])

    def acquire(self):
        from workbench_analysis.operational_daily_storage_v1 import output_path
        output_path(self.root, self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open('a+b')
        if stream.seek(0, 2) == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            raise ValueError('WORKSPACE_ALREADY_OWNED') from None
        self.stream = stream
        _OWNED.add(str(self.root))
        try:
            atomic(self.owner, self.identity)
        except Exception:
            self.close()
            raise
        return self

    def close(self):
        if self.stream:
            stream, self.stream = self.stream, None
            _OWNED.discard(str(self.root))
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)
            stream.close()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.close()


def resource_root():
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)/'resources'
    return Path(__file__).resolve().parents[2]


def verified_existing_owner(root):
    import psutil
    owner = json.loads((Path(root)/'runtime/desktop/instance.json').read_bytes())
    process = psutil.Process(owner['pid'])
    if (process.create_time() != owner['process_created_at'] or
            Path(process.exe()).resolve() != Path(owner['executable']).resolve() or
            Path(owner['workspace']).resolve() != Path(root).resolve()):
        raise ValueError('EXISTING_INSTANCE_IDENTITY_UNCONFIRMED')
    return owner


def verify_resources():
    root = resource_root()
    manifest_path = root/'package_manifest.json'
    if not manifest_path.exists():
        import sys
        if getattr(sys, 'frozen', False):
            raise ValueError('RESOURCE_MANIFEST_MISSING')
        return dict(build_release_id='DEVELOPMENT', source_sha='DEVELOPMENT',
                    resource_manifest_sha=None, workspace_schema_version=1)
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    for entry in manifest['resources']:
        path = (root/entry['path']).resolve()
        if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('PACKAGE_RESOURCE_SHA_MISMATCH')
    manifest['resource_manifest_sha'] = hashlib.sha256(raw).hexdigest()
    return manifest
