"""Explicit historical exact bytes; current authority never falls back to history."""
import hashlib,json,subprocess
from pathlib import Path,PureWindowsPath
REGISTRY='config/v4_historical_binding_routing_remainder_v1.json'
REGISTRY_SHA='a2ce904ff7665c42e53e9f36becdd9bcd629a7b5f86138e4974a4a07433131ef'

def identity(raw):return hashlib.sha256(raw).hexdigest(),len(raw)
def safe(root,name):
    w=PureWindowsPath(name)
    if w.drive or w.root or '..' in w.parts:raise ValueError('PATH_ESCAPE')
    p=Path(root).joinpath(*w.parts).resolve()
    if not p.is_relative_to(Path(root).resolve()):raise ValueError('PATH_ESCAPE')
    return p

class HistoricalExactReader:
    grants_current_permission=False
    def __init__(self,root):
        self.root=Path(root).resolve();raw=safe(root,REGISTRY).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=REGISTRY_SHA:raise ValueError('HISTORICAL_REGISTRY_TAMPERED')
        self.registry=json.loads(raw)
    def read(self,binding):
        row=next((r for r in self.registry['entries'] if binding['path'] in (r['historical_path'],r['windows_path_alias']) and binding['sha256']==r['accepted_sha'] and binding.get('bytes',binding.get('byte_count'))==r['accepted_bytes']),None)
        if row is None:raise ValueError('UNKNOWN_HISTORICAL_BINDING')
        safe(self.root,binding['path'])
        raw=safe(self.root,row['archive']['path']).read_bytes()
        if identity(raw)!=(row['accepted_sha'],row['accepted_bytes']):raise ValueError('HISTORICAL_ARCHIVE_IDENTITY_INVALID')
        oid=subprocess.check_output(['git','rev-parse',row['source_commit']+':'+row['historical_path']],cwd=self.root,text=True).strip()
        if oid!=row['git_blob_oid']:raise ValueError('HISTORICAL_BLOB_OID_INVALID')
        blob=subprocess.check_output(['git','cat-file','blob',oid],cwd=self.root)
        if identity(blob)!=(row['git_blob_sha256'],row['git_blob_bytes']):raise ValueError('HISTORICAL_BLOB_IDENTITY_INVALID')
        if row['reader_mode']=='GIT_BLOB_EXACT':equivalent=raw==blob
        elif row['reader_mode']=='AUDITED_CRLF_LF_EQUIVALENT_TEXT':
            equivalent=raw==blob.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        else:raise ValueError('UNSUPPORTED_REGISTERED_MODE')
        if not equivalent:raise ValueError('HISTORICAL_REPRESENTATION_INVALID')
        return raw,dict(mode=row['reader_mode'],source_commit=row['source_commit'],git_blob_oid=oid,grants_current_permission=False,current_fallback_used=False)

class CurrentExactReader:
    def __init__(self,root):
        from .v4_current_stage_authority import CurrentStageAuthority
        self.authority=CurrentStageAuthority(root);self.root=Path(root).resolve()
    def read(self,binding):
        raw=safe(self.root,binding['path']).read_bytes()
        if identity(raw)!=(binding['sha256'],binding.get('bytes',binding.get('byte_count'))):raise ValueError('CURRENT_BYTES_REQUIRED_NO_HISTORICAL_FALLBACK')
        return self.authority.read(binding)
