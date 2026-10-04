"""Explicit, frozen byte representation authority; never generic normalization."""
import hashlib,json,subprocess
from pathlib import Path,PureWindowsPath
from .v4_14_replay_io import path_in as _path_in

def path_in(root,path):
    win=PureWindowsPath(path)
    if win.drive or win.root or ".." in win.parts:raise ValueError("PORTABLE_PATH_ESCAPE")
    return _path_in(root,path)

def identity(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def lf(raw):
    if raw.startswith((b'\xef\xbb\xbf',b'\xff\xfe',b'\xfe\xff')):raise ValueError('BOM_FORBIDDEN')
    raw.decode('utf-8',errors='strict')
    if b'\r' in raw.replace(b'\r\n',b''):raise ValueError('BARE_CR_FORBIDDEN')
    return raw.replace(b'\r\n',b'\n')

class PortableExact:
    def __init__(self,root,registry_path='data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json',registry_data=None):
        self.root=Path(root).resolve()
        self.registry=registry_data if registry_data is not None else json.loads(path_in(self.root,registry_path)[1].read_bytes())
        self.entries={}
        for e in self.registry['entries']:
            path_in(self.root,e['path'])
            if e['path'] in self.entries:raise ValueError('DUPLICATE_PORTABILITY_PATH')
            if e['mode'] not in ['LITERAL_EXACT_BYTES','GIT_BLOB_EXACT','LFS_OBJECT_EXACT','AUDITED_CRLF_LF_EQUIVALENT_TEXT']:raise ValueError('INVALID_MODE')
            self.entries[e['path']]=e
    def read(self,binding):
        _,p=path_in(self.root,binding['path']);raw=p.read_bytes();observed=identity(raw)
        requested={'sha256':binding['sha256'],'bytes':binding.get('bytes',binding.get('byte_count'))}
        e=self.entries.get(binding['path']);mode=e['mode'] if e else 'LITERAL_EXACT_BYTES'
        usable=raw;applied=False;git_binding=None
        if e:
            accepted=e['accepted_bindings']
            if requested not in accepted:raise ValueError('UNREGISTERED_ACCEPTED_BINDING')
            blob=subprocess.check_output(['git','cat-file','blob',e['git_blob_oid']],cwd=self.root) if e['git_blob_oid'] else raw
            if e['git_blob_oid'] is None and mode!='LITERAL_EXACT_BYTES':raise ValueError('MISSING_GIT_BLOB')
            git_binding=identity(blob)
            if git_binding!=e['git_blob_binding']:raise ValueError('GIT_BLOB_IDENTITY_MISMATCH')
            if mode=='AUDITED_CRLF_LF_EQUIVALENT_TEXT':
                if e['source_kind']!='TEXT' or e.get('lfs_object_identity') or p.suffix.lower() in {'.gz','.parquet','.zip','.bundle','.png','.jpg','.jpeg','.gif','.pdf'}:raise ValueError('BINARY_NORMALIZATION_FORBIDDEN')
                if observed not in e['admitted_representations']:raise ValueError('UNREGISTERED_REPRESENTATION')
                if lf(raw)!=lf(blob):raise ValueError('CONTENT_MUTATION')
                variants=[blob,lf(blob),lf(blob).replace(b'\n',b'\r\n')]
                usable=next((v for v in variants if identity(v)==requested),None)
                if usable is None:raise ValueError('ACCEPTED_REPRESENTATION_MISSING')
                applied=usable!=raw
            elif mode=='LFS_OBJECT_EXACT':
                lfs=e.get('lfs_object_identity')
                if not lfs or observed!={'sha256':lfs['sha256'],'bytes':lfs['bytes']}:raise ValueError('LFS_OBJECT_IDENTITY_MISMATCH')
                if b'oid sha256:'+lfs['sha256'].encode() not in blob or b'size '+str(lfs['bytes']).encode() not in blob:raise ValueError('LFS_POINTER_MISMATCH')
            elif mode=='GIT_BLOB_EXACT' and observed!=git_binding:raise ValueError('GIT_REPRESENTATION_MISMATCH')
        if identity(usable)!=requested:raise ValueError('EXACT_BINDING_MISMATCH')
        receipt=dict(path=binding['path'],requested_binding=requested,observed_binding=observed,authority_mode=mode,git_blob_binding=git_binding,accepted_representation_binding=requested,normalization_applied=applied,normalization_kind='REGISTERED_CRLF_LF_ONLY' if applied else 'NONE',semantic_digest=hashlib.sha256(lf(usable)).hexdigest() if mode=='AUDITED_CRLF_LF_EQUIVALENT_TEXT' else None)
        return usable,receipt


def require_remote_tested_source(root,source,remote_ref):
    """Require a named remotely published ancestry, never a bundle-only identity."""
    if not remote_ref.startswith('refs/remotes/'):
        raise ValueError('REMOTE_IMMUTABLE_ANCESTRY_REQUIRED')
    root=Path(root).resolve()
    resolved=subprocess.check_output(['git','rev-parse',source+'^{commit}'],cwd=root).decode().strip()
    if resolved!=source:raise ValueError('IMMUTABLE_COMMIT_ID_REQUIRED')
    if subprocess.run(['git','merge-base','--is-ancestor',source,remote_ref],cwd=root,capture_output=True).returncode:
        raise ValueError('TESTED_SOURCE_NOT_REMOTE_ADDRESSABLE')
    return dict(tested_source=source,remote_ancestry=remote_ref,status='PASS_LOCAL')
