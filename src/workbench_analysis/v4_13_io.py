"""Exact immutable contract/source IO for scoped V4-13 engineering."""
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_ref(root, path):
    payload=(Path(root)/path).read_bytes()
    return dict(path=path, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))


def exact(root, binding):
    root=Path(root).resolve();path=(root/binding['path']).resolve()
    if not path.is_relative_to(root):raise ValueError('ACCEPTED_PATH_OUTSIDE_WORKSPACE')
    b=path.read_bytes()
    if hashlib.sha256(b).hexdigest()!=binding['sha256']:raise ValueError('ACCEPTED_SOURCE_DIGEST_MISMATCH')
    size=binding.get('bytes',binding.get('byte_count',binding.get('actual_byte_count')))
    if size is not None and len(b)!=size:raise ValueError('ACCEPTED_SOURCE_BYTES_MISMATCH')
    return b


def available(value, cutoff):
    return datetime.fromisoformat(value.replace('Z','+00:00'))<=datetime.fromisoformat(cutoff.replace('Z','+00:00'))


def rows(root, binding):
    exact(root,binding)
    path=Path(root)/binding['path']
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf8') as stream:
        for line in stream:
            if line.strip():yield json.loads(line)


def atomic(root,path,payload,append_only=False):
    target=(Path(root)/path).resolve();target.parent.mkdir(parents=True,exist_ok=True)
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
        self.root=Path(root);self.refs=json.loads((self.root/'reports/v4_13_r1_1/V4_13_CONTRACT_AMENDMENT_R1_1.json').read_bytes())['contracts']
        self.config={}
        for r in self.refs:
            name=Path(r['path']).stem.removeprefix('v4_13_').removesuffix('_v1_1')
            self.config[name]=json.loads(exact(self.root,r))
        self.digest=digest(self.refs)
        self.owners={k:json.loads(exact(self.root,r)) for k,r in self.config['loo_context']['accepted_owner_bindings'].items()}
        self.owner_refs=self.config['loo_context']['accepted_owner_bindings']
        self.dependencies={k:json.loads(exact(self.root,r)) for k,r in self.config['loo_context']['accepted_sector_dependencies'].items()}
        sector=self.owners['V4_08']
        for k in ['native_producer','rotation_producer','b2_producer']:exact(self.root,sector[k])
        exact(self.root,self.config['loo_context']['relative_state']['owner'])


def envelope(value=None,quality='UNKNOWN',reason='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE',refs=(),**identity):
    return dict(value=value,quality=quality,reason=reason,source_identity=list(refs),**identity)
