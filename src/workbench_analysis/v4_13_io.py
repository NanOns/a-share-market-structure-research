"""Exact immutable contract/source IO for scoped V4-13 engineering."""
import gzip
import hashlib
import json
import os
import tempfile
import re
from pathlib import Path
from datetime import datetime


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_ref(root, path):
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path
    payload=read_path(Path(root).resolve(),path)['raw']
    return dict(path=path, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))


def exact(root, binding):
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
    b=read_bound(Path(root).resolve(),binding['path'],binding['sha256'])['raw']
    if hashlib.sha256(b).hexdigest()!=binding['sha256']:raise ValueError('ACCEPTED_SOURCE_DIGEST_MISMATCH')
    size=binding.get('bytes',binding.get('byte_count',binding.get('actual_byte_count')))
    if size is not None and len(b)!=size:raise ValueError('ACCEPTED_SOURCE_BYTES_MISMATCH')
    return b


def available(value, cutoff):
    return datetime.fromisoformat(value.replace('Z','+00:00'))<=datetime.fromisoformat(cutoff.replace('Z','+00:00'))


def rows(root, binding):
    exact(root,binding)
    from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_bound
    path=materialize_bound(Path(root).resolve(),binding)
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf8') as stream:
        for line in stream:
            if line.strip():yield json.loads(line)


def atomic(root,path,payload,append_only=False):
    target=(Path(root)/path).resolve()
    if not target.is_relative_to(Path(root).resolve()):raise ValueError('WRITE_PATH_OUTSIDE_REPOSITORY')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()==payload:return file_ref(root,path)
        if append_only:raise ValueError('APPEND_ONLY_REVISION_CONFLICT')
    fd,tmp=tempfile.mkstemp(dir=target.parent,prefix='.v4-13-')
    try:
        with os.fdopen(fd,'wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        if append_only:
            try:os.link(tmp,target)
            except FileExistsError:
                if target.read_bytes()!=payload:raise ValueError('APPEND_ONLY_REVISION_CONFLICT')
        else:os.replace(tmp,target)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return file_ref(root,path)


class FrozenContracts:
    def __init__(self, root):
        self.root=Path(root)
        from workbench_db.v4_historical_source_ingress_pg_r1 import read_source
        package=read_source(self.root,'a3f1c1082580e1a2cdda395ef10089f5bc93c4b1bd8c9259de1ec30232b9bfb3')['value']
        if not isinstance(package,dict):raise ValueError('V4_13_CONTRACT_PACKAGE_NOT_REGISTERED_IN_PG')
        self.refs=package['contracts']
        self.config={}
        for r in self.refs:
            name=Path(r['path']).stem.removeprefix('v4_13_').removesuffix('_v1_1')
            self.config[name]=json.loads(exact(self.root,r))
        try:
            decision=read_source(self.root,'68655f6ef966294ab81f470cd39ca56d909d6cde67fced202e72734e929b8b13')['value']
        except ValueError as error:
            if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':raise
            decision=None
        if decision is not None:
            amendment=decision['amendment']
            projection=json.loads(exact(self.root,amendment))
            previous=next(r for r in self.refs if r['path']=='config/v4_13_projection_v1_1.json')
            if projection['contract_id']!=self.config['projection']['contract_id'] or projection['version']!='1.2.0' or projection['supersedes']!=previous:raise ValueError('PROJECTION_SAME_FAMILY_LINEAGE_REQUIRED')
            self.refs=[amendment if r==previous else r for r in self.refs]
            self.config['projection']=projection
        self.digest=digest(self.refs)
        self.owners={k:json.loads(exact(self.root,r)) for k,r in self.config['loo_context']['accepted_owner_bindings'].items()}
        self.owner_refs=self.config['loo_context']['accepted_owner_bindings']
        self.dependencies={k:json.loads(exact(self.root,r)) for k,r in self.config['loo_context']['accepted_sector_dependencies'].items()}
        sector=self.owners['V4_08']
        for k in ['native_producer','rotation_producer','b2_producer']:exact(self.root,sector[k])
        exact(self.root,self.config['loo_context']['relative_state']['owner'])


def envelope(value=None,quality='UNKNOWN',reason='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE',refs=(),**identity):
    return dict(value=value,quality=quality,reason=reason,source_identity=list(refs),**identity)


def revision_ordinal(revision):
    if not isinstance(revision,str) or not re.fullmatch(r'r[1-9][0-9]*',revision):raise ValueError('INVALID_REVISION')
    return int(revision[1:])
