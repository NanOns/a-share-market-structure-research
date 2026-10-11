"""Explicit historical protection metadata, with a separate current authority gate."""
from pathlib import Path
import hashlib,json,os,subprocess
from .historical_stage_governance_r17 import registry,exact,STAGE
from .v4_current_stage_authority import CurrentStageAuthority
from .v4_portable_exact import PortableExact
from types import FunctionType,SimpleNamespace

CONTRACT='R4_R3_PROTECTED_STAGE_METADATA_EXACT_ARCHIVE_V1'

def resolve_recorded_reader_source(root,binding):
    """Verify the recorded historical reader source; never execute or accept it."""
    from . import historical_stage_governance_r17 as historical
    name='src/workbench_analysis/dm01_publication_history_reader_v1.py'
    if binding.get('path')!=name or binding.get('sha256')!='51729be1ad211080a73f9c071a9142370e3ba281eadc3c1eb4d7969a7cd7572d' or binding.get('bytes')!=2138:
        raise ValueError('RECORDED_READER_SOURCE_IDENTITY_REQUIRED')
    root=Path(root).resolve()
    if (root/'.git').exists():return historical.resolve(root,binding,source=True)
    marker=root/'R4_READ_ONLY_METADATA_GIT_SOURCE.json'
    provenance=json.loads(marker.read_bytes())
    git_root=Path(provenance['source_root']).resolve()
    if os.environ.get('R4_NATIVE_ISOLATION')!='1' or not root.is_relative_to(Path('G:/codex_tmp').resolve()) or git_root!=Path(__file__).resolve().parents[2] or provenance.get('grants_current_permission') is not False or provenance.get('contract')!='R4_R3_READ_ONLY_METADATA_GIT_SOURCE_V1':
        raise ValueError('RECORDED_SOURCE_EXPLICIT_GIT_PROVENANCE_REQUIRED')
    def read_only_git(args,**kwargs):
        if len(args)!=3 or args[:2]!=['git','show'] or not args[2].endswith(':'+name):raise ValueError('RECORDED_SOURCE_READ_ONLY_GIT_REQUIRED')
        kwargs['cwd']=git_root;return subprocess.check_output(args,**kwargs)
    scope=dict(historical.resolve.__globals__,subprocess=SimpleNamespace(check_output=read_only_git,DEVNULL=subprocess.DEVNULL))
    function=FunctionType(historical.resolve.__code__,scope,historical.resolve.__name__,historical.resolve.__defaults__,historical.resolve.__closure__)
    function.__kwdefaults__=historical.resolve.__kwdefaults__
    return function(root,binding,source=True)

def resolve(root,binding):
    root=Path(root).resolve()
    if binding.get('path')!=STAGE:raise ValueError('PROTECTION_STAGE_METADATA_ONLY')
    matches=[row for row in registry(root)['entries'] if row['original_namespace']['path']==binding['path']
        and row['original_namespace']['sha256']==binding['sha256']]
    if len(matches)!=1:raise ValueError('PROTECTION_UNREGISTERED_STAGE_IDENTITY')
    row=matches[0];original=row['original_namespace'];archive=row['archive']
    if row['scope']!='EXACT_HISTORICAL_PROMOTION_STATE_ONLY' or any(binding[k]!=original['bytes'] for k in ('bytes','byte_count') if k in binding):
        raise ValueError('PROTECTION_HISTORICAL_SCOPE_INVALID')
    if archive['path']==STAGE or archive['sha256']!=binding['sha256'] or archive['bytes']!=original['bytes']:
        raise ValueError('PROTECTION_ARCHIVE_IDENTITY_INVALID')
    path=exact(root,archive);raw=path.read_bytes()
    if json.loads(raw)['accepted_stage_range']!=row['accepted_stage_range']:
        raise ValueError('PROTECTION_ARCHIVED_STAGE_RANGE_INVALID')
    git_root=root
    if not (root/'.git').exists():
        configured=os.environ.get('R4_ENGINEERING_HISTORICAL_GIT_ROOT')
        marker=root/'R4_READ_ONLY_METADATA_GIT_SOURCE.json'
        if marker.exists():
            provenance=json.loads(marker.read_bytes())
            if provenance.get('contract')!='R4_R3_READ_ONLY_METADATA_GIT_SOURCE_V1' or provenance.get('grants_current_permission') is not False or Path(provenance['source_root']).resolve()!=Path(__file__).resolve().parents[2]:
                raise ValueError('PROTECTION_METADATA_GIT_SOURCE_INVALID')
            configured=provenance['source_root']
        if os.environ.get('R4_NATIVE_ISOLATION')!='1' or not root.is_relative_to(Path('G:/codex_tmp').resolve()) or not configured:
            raise ValueError('PROTECTION_EXPLICIT_ISOLATED_GIT_ROOT_REQUIRED')
        git_root=Path(configured).resolve()
        if not git_root.is_relative_to(Path('G:/codex work').resolve()):raise ValueError('PROTECTION_FOREIGN_GIT_ROOT')
        top=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=git_root,text=True).strip()).resolve()
        if top!=git_root:raise ValueError('PROTECTION_EXACT_GIT_ROOT_REQUIRED')
    committed=subprocess.check_output(['git','show',row['source_commit']+':'+STAGE],cwd=git_root)
    if committed!=raw:raise ValueError('PROTECTION_EXACT_HISTORICAL_GIT_BYTES_REQUIRED')
    exact_reader=None
    if git_root!=root:
        def read_only_git(args,**kwargs):
            if len(args)!=4 or args[:3]!=['git','cat-file','blob'] or len(args[3])!=40 or any(c not in '0123456789abcdef' for c in args[3]):
                raise ValueError('PROTECTION_READ_ONLY_GIT_BLOB_REQUIRED')
            kwargs['cwd']=git_root
            return subprocess.check_output(args,**kwargs)
        scope=dict(PortableExact.read.__globals__,subprocess=SimpleNamespace(check_output=read_only_git))
        scoped_read=FunctionType(PortableExact.read.__code__,scope,PortableExact.read.__name__,PortableExact.read.__defaults__,PortableExact.read.__closure__)
        class ScopedPortable(PortableExact):read=scoped_read
        exact_reader=ScopedPortable(root)
    current=CurrentStageAuthority(root,exact_reader=exact_reader)
    return path,dict(contract=CONTRACT,archived_binding=archive,current_stage_binding=current.stage_ref,
        historical_source_commit=row['source_commit'],grants_current_permission=False,
        current_bytes_substituted=False,archive_sha256=hashlib.sha256(raw).hexdigest())
