"""Persistent paths, atomic writes and whole-workspace ownership."""
from pathlib import Path
from contextlib import contextmanager
import hashlib
import json
import os
import tempfile
import uuid

_OWNED = set()
_OWNERS = {}


def legacy_workspace_writers(root):
    """Known pre-lock launchers cannot be evaded by selecting another port."""
    import psutil
    root=Path(root).resolve()
    known={root/'run_workbench_service.py',root/'scripts/start_product_attested_r4.py'}
    matches=[]
    for process in psutil.process_iter(['pid','exe','cmdline']):
        if process.pid==os.getpid():continue
        try:
            info=process.info;argv=info['cmdline'] or []
            if Path(info['exe'] or '').name.lower() not in ('python.exe','pythonw.exe'):continue
            if '--v4-shadow-only' in argv or '--legacy-v3' in argv:continue
            scripts=[word for word in argv[1:] if word.lower().endswith('.py')]
            if not scripts:continue
            script=Path(scripts[0])
            if not script.is_absolute():script=Path(process.cwd())/script
            if script.resolve() in known:matches.append(process.pid)
        except (psutil.NoSuchProcess,psutil.AccessDenied,OSError):
            continue
    return matches


def owned_identity(root):
    return _OWNERS.get(str(Path(root).resolve()))


def require_owned(root):
    if str(Path(root).resolve()) not in _OWNED:
        raise ValueError('WORKSPACE_LEASE_REQUIRED')


def activate_workspace_sources(root):
    """Compiled code stays in the EXE; provenance points to exact workspace originals."""
    import sys
    if not getattr(sys,'frozen',False):return
    require_owned(root)
    manifest=verify_resources()
    identities={row['path']:row['sha256'] for row in manifest['resources']}
    policy=Path(root)/'config/read_only_operational_daily_release_policy_v1_1.json'
    if policy.is_file():
        required=json.loads(policy.read_bytes())['accepted_algorithm_bindings']
        required+= [dict(path=name,sha256=identities[name]) for name in
            ('config/v4_03_parameter_set_v1.json','config/v4_03_parameter_registry_v1.json')]
        for row in required:
            path=Path(root)/row['path']
            if identities.get(row['path'])!=row['sha256'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('WORKSPACE_PACKAGE_ALGORITHM_IDENTITY_MISMATCH')
    os.environ['DAAV4_WORKSPACE_ROOT']=str(Path(root).resolve())
    for row in manifest['module_locations']:
        if row['module'].startswith('workbench_desktop'):continue
        module=sys.modules.get(row['module'])
        if module is None:continue
        candidate=Path(root)/row['path']
        if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest()==identities[row['path']]:
            module.__file__=str(candidate)
            module.__spec__.origin=str(candidate)
            # Modules imported before lease acquisition have already bound ROOT
            # and other Path constants from their initial resource __file__.
            # Rebind layout only, so immutable workspace contract/data refs keep
            # their original namespace; no code or numerical predicate changes.
            for name,value in list(vars(module).items()):
                if isinstance(value,Path) and value.is_absolute() and value.is_relative_to(resource_root()):
                    setattr(module,name,Path(root)/value.relative_to(resource_root()))


def frozen_module_evidence():
    import sys
    if not getattr(sys,'frozen',False):raise ValueError('FROZEN_RUNTIME_REQUIRED')
    result=[]
    for row in verify_resources()['module_locations']:
        module=sys.modules.get(row['module'])
        if module is None:continue
        loader=type(module.__loader__).__name__
        if loader!='PyiFrozenLoader':raise ValueError('DEVELOPMENT_SOURCE_FALLBACK:'+row['module'])
        result.append(dict(module=row['module'],loader=loader,original_identity_path=module.__file__))
    return result


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
        self.previous_source_root = os.environ.get('DAAV4_WORKSPACE_ROOT')
        import psutil
        process=psutil.Process()
        self.identity = dict(instance_id=uuid.uuid4().hex, pid=os.getpid(),
                             workspace=str(self.root), process_created_at=process.create_time(),
                             executable=str(Path(process.exe()).resolve()),
                             launcher_executable=str(Path(__import__('sys').executable).resolve()),
                             build_release_id=verify_resources()['build_release_id'])

    def acquire(self):
        legacy=legacy_workspace_writers(self.root)
        if legacy:raise ValueError('LEGACY_V4_WORKSPACE_WRITER_MUST_EXIT:'+','.join(map(str,legacy)))
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
        _OWNERS[str(self.root)]=self.identity
        try:
            activate_workspace_sources(self.root)
            atomic(self.owner, self.identity)
        except Exception:
            self.close()
            raise
        return self

    def close(self):
        if self.stream:
            stream, self.stream = self.stream, None
            _OWNED.discard(str(self.root))
            _OWNERS.pop(str(self.root),None)
            if self.previous_source_root is None:
                os.environ.pop('DAAV4_WORKSPACE_ROOT',None)
            else:
                os.environ['DAAV4_WORKSPACE_ROOT']=self.previous_source_root
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
    try:
        status=json.loads((Path(root)/'runtime/desktop/status.json').read_bytes())
        if (status['instance_id']!=owner['instance_id'] or status['pid']!=owner['pid'] or
                status['BUILD_RELEASE_ID']!=owner['build_release_id'] or
                Path(status['WORKSPACE_ROOT']).resolve()!=Path(root).resolve()):
            status=dict(engine_state='INITIALIZING')
    except (OSError,ValueError,KeyError):
        status=dict(engine_state='INITIALIZING')
    owner['verified_status']=status
    return owner


def register_tray_window(root, hwnd):
    require_owned(root)
    owner=owned_identity(root)
    owner['tray_hwnd']=int(hwnd)
    atomic(Path(root)/'runtime/desktop/instance.json',owner)


def focus_existing_owner(owner):
    import ctypes
    from ctypes import wintypes
    hwnd=owner.get('tray_hwnd')
    if not hwnd:return False
    user=ctypes.windll.user32
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.SendNotifyMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    pid=wintypes.DWORD()
    if not user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid)) or pid.value!=owner['pid']:
        return False
    return bool(user.SendNotifyMessageW(hwnd,0x8021,0,0))


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
