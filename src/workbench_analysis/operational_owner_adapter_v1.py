"""Private IO scopes over frozen reconstructed producer implementations.

Frozen source files and their globals are never edited. Mapped reads redirect
dated source receipts and output roots; numeric kernels remain the same code.
The adapter is an explicit versioned producer, not dynamic plugin discovery.
"""
from pathlib import Path
from types import FunctionType,SimpleNamespace,ModuleType
import builtins
from . import r43_owner_replay as core
from . import r43_structure_replay as structure
from . import r43_daily_price_limits as limits
from . import r43_market_replay as market
from . import r43_focus_replay as focus
from . import tdx_sector_retro_r43 as sector


def private_scope(module, replacements):
    scope=dict(vars(module));scope.update(replacements)
    for name,original in vars(module).items():
        if isinstance(original,FunctionType) and original.__module__==module.__name__:
            function=FunctionType(original.__code__,scope,name,original.__defaults__,original.__closure__)
            function.__kwdefaults__=original.__kwdefaults__;scope[name]=function
    for name,original in vars(module).items():
        if isinstance(original,type) and original.__module__==module.__name__:
            attrs={}
            for key,value in vars(original).items():
                if key in ('__dict__','__weakref__'):continue
                if isinstance(value,FunctionType):
                    value=FunctionType(value.__code__,scope,value.__name__,value.__defaults__,value.__closure__)
                attrs[key]=value
            scope[name]=type(name,original.__bases__,attrs)
    scope.update(replacements)
    return scope


def replay(root,folder,dates,read_mappings,*,membership_snapshot,seed_registry,observed_at,exact_adjustment=False):
    root=Path(root).resolve();folder=Path(folder).resolve()
    if exact_adjustment:
        import os
        if os.environ.get('R4_NATIVE_ISOLATION')!='1' or not root.is_relative_to(Path('G:/codex_tmp').resolve()):
            raise ValueError('ISOLATED_EXACT_CORE_CANDIDATE_REQUIRED')
    def immutable_source_write(path,blob,**kwargs):
        path=Path(path)
        if path.exists():
            if path.read_bytes()!=blob:raise ValueError('FROZEN_OWNER_SOURCE_CONTENT_CONFLICT')
            return
        return core._atomic_write(path,blob,**kwargs)
    if not folder.is_relative_to(root) or folder==root:
        raise ValueError('SUCCESSOR_OUTPUT_ROOT_REQUIRED')
    def mapped(path):
        path=Path(path).resolve()
        return Path(read_mappings.get(str(path),path))
    def load(path):return core.load(mapped(path))
    def ref(base,path):
        target=mapped(path)
        if exact_adjustment and target==root/'src/adjustment/tdx_adjustment.py':
            target=Path(__file__).resolve().parents[2]/'src/adjustment/tdx_adjustment_v0_3.py'
        if not target.is_relative_to(root):
            # Record the bytes of the code actually executed, separately from
            # the accepted source copies inside the isolated workspace.
            repository=Path(__file__).resolve().parents[2]
            if not target.is_relative_to(repository/'src') or target.suffix!='.py':
                raise ValueError('EXTERNAL_OWNER_BINDING_OUTSIDE_EXECUTED_SOURCE')
            blob=target.read_bytes()
            import hashlib
            destination=folder/'executed_sources'/hashlib.sha256(blob).hexdigest()/target.relative_to(repository)
            destination.parent.mkdir(parents=True,exist_ok=True)
            immutable_source_write(destination,blob,tdx_root=Path('D:/new_tdx'))
            return core.ref(base,destination)
        return core.ref(base,target)
    output=(folder/'owner_v3').relative_to(root).as_posix()
    from datetime import datetime as real_datetime
    class FrozenDatetime(real_datetime):
        @classmethod
        def now(cls,tz=None):
            value=real_datetime.fromisoformat(observed_at)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    common=dict(OUT=output,load=load,ref=ref,now=lambda:observed_at,datetime=FrozenDatetime,
                _atomic_write=immutable_source_write)
    c=private_scope(core,common)
    if exact_adjustment:
        from . import exact_operational_core_candidate_r3 as exact
        c.update(transform_window=exact.transform_window,independent_affine=exact.independent_affine)
    core_path=folder/'owner_v3/CORE_REPLAY.json'
    if exact_adjustment and core_path.exists():
        source=load(folder/'owner_v3/SOURCE_BINDINGS.json')['sources']['adjustment_kernel']
        expected=Path(__file__).resolve().parents[2]/'src/adjustment/tdx_adjustment_v0_3.py'
        from .tdx_official_daily_source import sha256_file
        if source['sha256']!=sha256_file(expected):raise ValueError('EXACT_CORE_CACHED_SOURCE_MISMATCH')
    owners=load(core_path)['owners'] if core_path.exists() else c['materialize_core'](root,dates,
        basis_namespace='TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE' if exact_adjustment else 'TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE')
    from scripts import run_v4_04_full_market_candidate_r4 as original_builder
    builder=ModuleType(original_builder.__name__)
    vars(builder).update(vars(original_builder))
    for name,function in vars(original_builder).items():
        if isinstance(function,FunctionType) and function.__module__==original_builder.__name__:
            clone=FunctionType(function.__code__,vars(builder),name,function.__defaults__,function.__closure__)
            clone.__kwdefaults__=function.__kwdefaults__;setattr(builder,name,clone)
    real_import=builtins.__import__
    def structure_import(name,globals=None,locals=None,fromlist=(),level=0):
        if name=='scripts.run_v4_04_full_market_candidate_r4':return builder
        if name=='scripts' and 'run_v4_04_full_market_candidate_r4' in fromlist:
            return SimpleNamespace(run_v4_04_full_market_candidate_r4=builder)
        return real_import(name,globals,locals,fromlist,level)
    s=private_scope(structure,dict(common,__builtins__=dict(vars(builtins),__import__=structure_import)))
    profile_path=folder/'owner_v3/PROFILE_STRUCTURE_REPLAY.json'
    profiles=load(profile_path)['owners'] if profile_path.exists() else s['materialize_profiles_structure'](root)
    sec=private_scope(sector,dict(load=load,ref=ref,EVIDENCE=folder.relative_to(root).as_posix(),
                               capture=lambda base:membership_snapshot,
                               validate_snapshot=lambda snapshot,base:core.gzrows(core.checked(base,snapshot['memberships']))))
    # The comparator is explicitly an UNKNOWN bootstrap for new dates. The
    # unchanged producer computes every stock Seed from real Core/Profile.
    seed_path=root/sector.OUT/'SECTOR_REPLAY.json'
    old_load=sec['load']
    sec['load']=lambda path: seed_registry if Path(path).resolve()==seed_path.resolve() else old_load(path)
    sector_path=folder/'sector_v3/SECTOR_REPLAY.json'
    sectors=load(sector_path) if sector_path.exists() else sec['run'](root)
    l=private_scope(limits,common)
    original_import=builtins.__import__
    def imports(name,globals=None,locals=None,fromlist=(),level=0):
        if name=='r43_daily_price_limits' and level==1:
            return SimpleNamespace(materialize_daily_limits=l['materialize_daily_limits'])
        return original_import(name,globals,locals,fromlist,level)
    m=private_scope(market,dict(common,__builtins__=dict(vars(builtins),__import__=imports)))
    market_path=folder/'owner_v3/MARKET_REPLAY.json'
    markets=load(market_path)['owners'] if market_path.exists() else m['materialize_market'](root)
    f=private_scope(focus,common)
    focus_path=folder/'owner_v3/FOCUS_FORWARD_REPLAY.json'
    forwards=load(focus_path) if focus_path.exists() else f['materialize_focus'](root)
    return dict(core=owners,profiles=profiles,sectors=sectors,market=markets,focus=forwards)
