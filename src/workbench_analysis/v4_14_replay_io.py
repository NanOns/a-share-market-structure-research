"""Canonical replay artifacts with atomic no-clobber publication."""
import hashlib,json,os,tempfile
from functools import lru_cache
from pathlib import Path
def path_in(root,path):
    root=Path(root).resolve();relative=Path(path)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('REPLAY_PATH_ESCAPE')
    # Resolve directories, preserving the requested final hard-link name on
    # Windows. GetFinalPathNameByHandle can report another link to that file.
    p=root/relative;parent=p.parent.resolve()
    if not parent.is_relative_to(root) or p.is_symlink():raise ValueError('REPLAY_PATH_ESCAPE')
    return root,parent/p.name
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
@lru_cache(maxsize=2)
def _artifact_store(root):
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    project=Path(root).resolve()
    return ForwardFactStore(project,project/'data/v4/v4_replay_artifacts_pg_r1')
def ref(root,path):
    root=Path(root).resolve();relative=Path(path).as_posix()
    if Path(path).is_absolute() or '..' in Path(path).parts:raise ValueError('REPLAY_PATH_ESCAPE')
    key=hashlib.sha256(relative.encode('utf-8')).hexdigest()
    try:return _artifact_store(str(root)).binding('v4_replay_artifact',key)
    except ValueError as error:
        if str(error)!='FORWARD_PG_FACT_NOT_FOUND':raise
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path
    source=read_path(root,relative)
    return dict(path=source['record']['source_path'],sha256=source['record']['source_sha256'],bytes=source['record']['source_bytes'])
def exact(root,binding):
    if isinstance(binding.get('pg_descriptor'),dict):
        value=_artifact_store(str(Path(root).resolve())).read(binding)
        raw=canonical(value)
        if hashlib.sha256(raw).hexdigest()!=binding['pg_descriptor']['payload_sha256']:
            raise ValueError('REPLAY_PG_ARTIFACT_DIGEST_MISMATCH')
        return raw
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
    source=read_bound(root,binding['path'],binding['sha256']);raw=source['raw']
    if len(raw)!=binding.get('bytes',binding.get('byte_count')):
        raise ValueError('REPLAY_EXACT_REF_MISMATCH')
    return raw
def publish(root,path,value):
    root=Path(root).resolve();relative=Path(path).as_posix()
    if Path(path).is_absolute() or '..' in Path(path).parts:raise ValueError('REPLAY_PATH_ESCAPE')
    key=hashlib.sha256(relative.encode('utf-8')).hexdigest()
    return _artifact_store(str(root)).append('v4_replay_artifact',key,value,migration_timeout_seconds=120)
