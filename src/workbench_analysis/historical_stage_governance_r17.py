"""Explicit immutable historical identities plus a separate current-state gate."""
from pathlib import Path
import hashlib,json,subprocess
import re
from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound,read_package_bytes
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
REGISTRY='config/v4_historical_moving_head_registry_r17_v1.json'
REGISTRY_SHA='3926d58b3953597e10c4619f442b910c853d229c61e4b4b65bd58f3c05679e4d'
class HistoricalBindingError(ValueError):pass

class PGBoundBytes:
    """Read-only file-shaped adapter for exact bytes already resident in PG."""
    __slots__=('path','_raw')
    def __init__(self,path,raw):self.path=path;self._raw=raw
    def read_bytes(self):return self._raw
    def read_text(self,encoding='utf-8'):return self._raw.decode(encoding)

def exact(root,ref):
    project=Path(root).resolve()
    try:raw=read_bound(project,ref['path'],ref['sha256'])['raw']
    except ValueError as error:
        if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':
            raise HistoricalBindingError('PG_ARCHIVE_MISSING_OR_INVALID:'+str(ref.get('path'))) from error
        try:raw=read_package_bytes(project,ref['path'],ref['sha256'])['raw']
        except (OSError,KeyError,ValueError) as package_error:
            raise HistoricalBindingError('PG_ARCHIVE_MISSING_OR_INVALID:'+str(ref.get('path'))) from package_error
    except (OSError,KeyError) as error:
        raise HistoricalBindingError('PG_ARCHIVE_MISSING_OR_INVALID:'+str(ref.get('path'))) from error
    if hashlib.sha256(raw).hexdigest()!=ref['sha256'] or any(len(raw)!=ref[k] for k in ('bytes','byte_count') if k in ref):raise HistoricalBindingError('EXACT_ARCHIVE_SHA_OR_BYTES_INVALID')
    return PGBoundBytes(ref['path'],raw)
def registry(root):
    return json.loads(exact(root,dict(path=REGISTRY,sha256=REGISTRY_SHA,bytes=33810)).read_bytes())
def resolve(root,ref,*,source=False):
    book=registry(root);rows=book['source_archives' if source else 'entries']
    row=next((r for r in rows if r['original_namespace']['path']==ref.get('path') and r['original_namespace']['sha256']==ref.get('sha256')),None)
    if row is None:raise HistoricalBindingError('UNREGISTERED_HISTORICAL_IDENTITY')
    original=row['original_namespace']
    if any(ref[k]!=original['bytes'] for k in ('bytes','byte_count') if k in ref):raise HistoricalBindingError('HISTORICAL_NAMESPACE_BYTES_INVALID')
    archive=row['archive']
    if archive['path']==ref['path'] or archive['sha256']!=original['sha256'] or archive['bytes']!=original['bytes']:raise HistoricalBindingError('CURRENT_NAMESPACE_IS_NOT_AN_ARCHIVE')
    raw=exact(root,archive).read_bytes()
    git_raw=subprocess.check_output(['git','show',row['source_commit']+':'+original['path']],cwd=Path(root),stderr=subprocess.DEVNULL)
    if raw!=git_raw:raise HistoricalBindingError('ARCHIVE_NOT_EXACT_PROMOTION_TIME_GIT_BYTES')
    if not source and json.loads(raw).get('accepted_stage_range')!=row['accepted_stage_range']:raise HistoricalBindingError('HISTORICAL_STAGE_RANGE_INVALID')
    return PGBoundBytes(archive['path'],raw)
def protected_bytes(root,path,sha256):
    if path==STAGE:return resolve(root,dict(path=path,sha256=sha256)).read_bytes()
    return exact(root,dict(path=path,sha256=sha256)).read_bytes()
def historical_absence(root,stage_sha,path):
    row=next(r for r in registry(root)['entries'] if r['original_namespace']['sha256']==stage_sha)
    resolve(root,row['original_namespace'])
    if subprocess.run(['git','cat-file','-e',row['source_commit']+':'+path],cwd=root,capture_output=True).returncode==0:
        raise HistoricalBindingError('HISTORICAL_OBJECT_ALREADY_EXISTS')
    return True
def accepted_static_binding(root,ref):
    row=next((r for r in registry(root).get('static_byte_archives',[]) if r['original_namespace']['path']==ref['path'] and r['original_namespace']['sha256']==ref['sha256']),None)
    if row is None:return exact(root,ref)
    original=row['original_namespace']
    if ref['sha256']!=original['sha256'] or any(ref[k]!=original['bytes'] for k in ('bytes','byte_count') if k in ref):raise HistoricalBindingError('STATIC_ACCEPTED_IDENTITY_CHANGED')
    archived=row['archive'];archive_raw=exact(root,archived).read_bytes()
    try:git_raw=subprocess.check_output(['git','show',row['source_commit']+':'+ref['path']],cwd=root,stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:raise HistoricalBindingError('STATIC_ORIGIN_GIT_BLOB_UNAVAILABLE') from exc
    if row.get('representation')=='EXACT_ACCEPTED_GIT_BLOB_ARCHIVE_CURRENT_MAY_EVOLVE':
        if (archive_raw!=git_raw or hashlib.sha256(git_raw).hexdigest()!=row['git_blob_sha256']
                or len(git_raw)!=row['git_blob_bytes']):
            raise HistoricalBindingError('STATIC_ARCHIVE_GIT_BLOB_IDENTITY_INVALID')
        return PGBoundBytes(archived['path'],archive_raw)
    if row.get('representation')=='EXACT_ARCHIVED_ACCEPTED_BYTES_WITH_GIT_LF_ORIGIN_CURRENT_MAY_EVOLVE':
        if (hashlib.sha256(git_raw).hexdigest()!=row['git_blob_sha256'] or len(git_raw)!=row['git_blob_bytes']
                or archive_raw.replace(b'\r\n',b'\n')!=git_raw):
            raise HistoricalBindingError('STATIC_ARCHIVE_GIT_ORIGIN_IDENTITY_INVALID')
        return PGBoundBytes(archived['path'],archive_raw)
    if hashlib.sha256(git_raw).hexdigest()!=row['git_blob_sha256'] or len(git_raw)!=row['git_blob_bytes'] or archive_raw.replace(b'\r\n',b'\n')!=git_raw:
        raise HistoricalBindingError('STATIC_ARCHIVE_GIT_REPRESENTATION_INVALID')
    return PGBoundBytes(archived['path'],archive_raw)
def current_state(root):
    from workbench_db.dm01_data_accepted_head_pg_r1 import read_current
    from .v4_current_stage_authority import CurrentStageAuthority
    root=Path(root).resolve();data_head=read_current(root);d=data_head['candidate']
    # The Data Head's stage_head is its historical promotion-time binding. It
    # must not be mistaken for the live accepted Stage Head. Resolve the latter
    # through its PostgreSQL ingress/Owner/Head chain, then require that its
    # bound Data Head is the same exact row selected in this PG snapshot.
    authority=CurrentStageAuthority(root);s=authority.stage
    if authority.data_ref.get('sha256')!=data_head['head_sha256'] or authority.data!=d:
        raise HistoricalBindingError('CURRENT_STAGE_DATA_HEAD_PG_IDENTITY_MISMATCH')
    match=re.fullmatch(r'V4_00_TO_V4_(\d+)_ACCEPTED',s.get('accepted_stage_range',''))
    if not match or not 12<=int(match[1])<=15:raise HistoricalBindingError('CURRENT_STAGE_NOT_ACCEPTED')
    if d['accepted_trade_date']!='2026-09-30' or any(d['permissions'].values()):raise HistoricalBindingError('CURRENT_DATA_SCOPE_INVALID')
    if any(s[k] for k in ('production_permission','shadow_production_permission','focus_cutover_permission','global_mandatory_adoption')):raise HistoricalBindingError('CURRENT_PERMISSION_OVERCLAIM')
    for key,value in s.items():
        if key.endswith('_binding') and isinstance(value,dict) and 'sha256' in value:accepted_static_binding(root,value)
    for key,value in s.get('bindings',{}).items():
        if 'accepted_head' in key:exact(root,value)
    for stage_no in range(12,int(match[1])+1):
        binding=s.get(f'v4_{stage_no}_binding')
        if not isinstance(binding,dict):raise HistoricalBindingError('CURRENT_STAGE_BINDING_MISSING')
        accepted_static_binding(root,binding)
    return dict(status='PASS',stage_range=s['accepted_stage_range'],data_date=d['accepted_trade_date'],production=False,shadow=False,focus=False,global_mandatory_adoption=False,static_byte_representation='EXACT_REGISTERED_ARCHIVE_PLUS_VERIFIED_SOURCE_COMMIT_GIT_CONTENT')
