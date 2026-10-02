"""Exact contract/source loader and immutable atomic candidate persistence."""
from __future__ import annotations
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from decimal import Decimal

def json_scalar(value):
    if isinstance(value,Decimal):return str(value)
    raise TypeError('UNSUPPORTED_CANDIDATE_VALUE_TYPE')
def canonical(value):return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),default=json_scalar)+'\n').encode('utf-8')
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def file_ref(root,path):
    raw=(Path(root)/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def exact_json(root,ref):
    root=Path(root).resolve();path=(root/ref['path']).resolve()
    if not path.is_relative_to(root):raise ValueError('SOURCE_ESCAPE')
    raw=path.read_bytes()
    if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('EXACT_DIGEST_MISMATCH:'+ref['path'])
    return json.loads(raw)

class FrozenContracts:
    def __init__(self,root,entry_path='reports/v4_12/V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json'):
        self.root=Path(root).resolve();self.entry=json.loads((self.root/entry_path).read_bytes());self.entry_ref=file_ref(self.root,entry_path)
        if self.entry['scope']!='V4_12_D1_ENGINEERING_RUNTIME_R1' or not self.entry['scoped_engineering_implementation_permission']:raise ValueError('RUNTIME_ENTRY_NOT_AUTHORIZED')
        acceptance=exact_json(self.root,self.entry['contract_freeze_acceptance'])
        if acceptance['external_audit_status']!='PASS_V4_12_CONTRACT_FREEZE' or acceptance['frozen_contracts']!=self.entry['frozen_contracts']:raise ValueError('CONTRACT_FREEZE_AUTHORITY_MISMATCH')
        for key in ['production_permission','shadow_production_permission','focus_cutover_permission','global_mandatory_adoption','D2_integration_permission','DB_migration_permission']:
            if self.entry[key] is not False:raise ValueError('FORBIDDEN_PERMISSION')
        self.config={};self.refs={}
        for ref in self.entry['frozen_contracts']:
            name=Path(ref['path']).stem.removeprefix('v4_12_')
            if name.endswith('_v1'):name=name[:-3]
            elif name.endswith('_v2'):name=name[:-3]
            self.config[name]=exact_json(self.root,ref);self.refs[name]=ref
        if self.config['time_counter_contract']['contract_id']!='V4_12_SESSION_COUNTER_V2':raise ValueError('STOP_WITH_CONTRACT_GAP:COUNTER_VERSION')
        self.digest=digest(self.entry['frozen_contracts'])

class CandidateStore:
    def __init__(self,root,directory='reports/v4_12_runtime_r1'):
        self.root=Path(root).resolve();self.directory=self.root/directory
        if not self.directory.resolve().is_relative_to(self.root):raise ValueError('CANDIDATE_PATH_ESCAPE')
        self.directory.mkdir(parents=True,exist_ok=True)
    def write_bytes(self,name,raw):
        path=(self.directory/name).resolve()
        if not path.is_relative_to(self.directory.resolve()):raise ValueError('CANDIDATE_PATH_ESCAPE')
        if path.exists():
            if path.read_bytes()!=raw:raise ValueError('IMMUTABLE_REVISION_CONFLICT:'+name)
        else:
            fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
            try:
                with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
        return file_ref(self.root,path.relative_to(self.root).as_posix())
    def json(self,name,value):return self.write_bytes(name,canonical(value))
    def jsonl(self,name,rows,compress=False):
        raw=b''.join(canonical(r) for r in sorted(rows,key=lambda r:canonical(r.get('identity',r.get('security_id',r)))))
        if compress:raw=gzip.compress(raw,mtime=0)
        return self.write_bytes(name,raw)
