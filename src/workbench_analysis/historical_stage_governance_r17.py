"""Explicit immutable historical identities plus a separate current-state gate."""
from pathlib import Path
import hashlib,json,subprocess
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
REGISTRY='config/v4_historical_moving_head_registry_r17_v1.json'
REGISTRY_SHA='e1696ce9a5b037fe3b798d069631fafb3621ffa7fa6b51e6e23d577b103c3bef'
class HistoricalBindingError(ValueError):pass
def exact(root,ref):
    root=Path(root).resolve();p=(root/ref['path']).resolve()
    if not p.is_relative_to(root) or not p.is_file():raise HistoricalBindingError('ARCHIVE_MISSING_OR_OUTSIDE_PROJECT')
    raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256'] or any(len(raw)!=ref[k] for k in ('bytes','byte_count') if k in ref):raise HistoricalBindingError('EXACT_ARCHIVE_SHA_OR_BYTES_INVALID')
    return p
def registry(root):
    return json.loads(exact(root,dict(path=REGISTRY,sha256=REGISTRY_SHA,bytes=7249)).read_bytes())
def resolve(root,ref,*,source=False):
    book=registry(root);rows=book['source_archives' if source else 'entries']
    row=next((r for r in rows if r['original_namespace']['path']==ref.get('path') and r['original_namespace']['sha256']==ref.get('sha256')),None)
    if row is None:raise HistoricalBindingError('UNREGISTERED_HISTORICAL_IDENTITY')
    original=row['original_namespace']
    if any(ref[k]!=original['bytes'] for k in ('bytes','byte_count') if k in ref):raise HistoricalBindingError('HISTORICAL_NAMESPACE_BYTES_INVALID')
    archive=row['archive']
    if archive['path']==ref['path'] or archive['sha256']!=original['sha256'] or archive['bytes']!=original['bytes']:raise HistoricalBindingError('CURRENT_NAMESPACE_IS_NOT_AN_ARCHIVE')
    p=exact(root,archive);raw=p.read_bytes()
    git_raw=subprocess.check_output(['git','show',row['source_commit']+':'+original['path']],cwd=Path(root),stderr=subprocess.DEVNULL)
    if raw!=git_raw:raise HistoricalBindingError('ARCHIVE_NOT_EXACT_PROMOTION_TIME_GIT_BYTES')
    if not source and json.loads(raw).get('accepted_stage_range')!=row['accepted_stage_range']:raise HistoricalBindingError('HISTORICAL_STAGE_RANGE_INVALID')
    return p
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
    row=next((r for r in registry(root).get('static_byte_archives',[]) if r['original_namespace']['path']==ref['path']),None)
    if row is None:return exact(root,ref)
    original=row['original_namespace']
    if ref['sha256']!=original['sha256'] or any(ref[k]!=original['bytes'] for k in ('bytes','byte_count') if k in ref):raise HistoricalBindingError('STATIC_ACCEPTED_IDENTITY_CHANGED')
    p=exact(root,row['archive']);archive=p.read_bytes()
    git_raw=subprocess.check_output(['git','show',row['source_commit']+':'+ref['path']],cwd=root)
    if hashlib.sha256(git_raw).hexdigest()!=row['git_blob_sha256'] or len(git_raw)!=row['git_blob_bytes'] or archive.replace(b'\r\n',b'\n')!=git_raw:
        raise HistoricalBindingError('STATIC_ARCHIVE_GIT_REPRESENTATION_INVALID')
    if (Path(root)/ref['path']).read_bytes().replace(b'\r\n',b'\n')!=git_raw:raise HistoricalBindingError('CURRENT_STATIC_HEAD_CONTENT_CHANGED')
    return p
def current_state(root):
    root=Path(root);s=json.loads((root/STAGE).read_bytes());d=json.loads((root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    if s['accepted_stage_range'] not in ('V4_00_TO_V4_12_ACCEPTED','V4_00_TO_V4_13_ACCEPTED'):raise HistoricalBindingError('CURRENT_STAGE_NOT_ACCEPTED')
    if d['accepted_trade_date']!='2026-09-30' or any(d['permissions'].values()):raise HistoricalBindingError('CURRENT_DATA_SCOPE_INVALID')
    if any(s[k] for k in ('production_permission','shadow_production_permission','focus_cutover_permission','global_mandatory_adoption')):raise HistoricalBindingError('CURRENT_PERMISSION_OVERCLAIM')
    for key,value in s.items():
        if key.endswith('_binding') and isinstance(value,dict) and 'sha256' in value:accepted_static_binding(root,value)
    for key,value in s.get('bindings',{}).items():
        if 'accepted_head' in key:exact(root,value)
    exact(root,s['v4_12_binding'])
    if s['accepted_stage_range']=='V4_00_TO_V4_13_ACCEPTED':exact(root,s['v4_13_binding'])
    return dict(status='PASS',stage_range=s['accepted_stage_range'],data_date=d['accepted_trade_date'],production=False,shadow=False,focus=False,global_mandatory_adoption=False,static_byte_representation='EXACT_REGISTERED_ARCHIVE_PLUS_VERIFIED_CURRENT_GIT_CONTENT')
