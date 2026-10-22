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
from adjustment import tdx_adjustment_v0_3 as exact_kernel


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


PROFILE_LIFECYCLE_CONSERVATION_CONTRACT = "DYNAMIC_PROFILE_LIFECYCLE_CONSERVATION_R1"


def replay(root,folder,dates,read_mappings,*,membership_snapshot,seed_registry,observed_at,lifecycle_binding=None,exact_adjustment=False,exact_daily_policy=None,candidate_only_exact=False,predecessor=None,progress=None):
    root=Path(root).resolve();folder=Path(folder).resolve()
    if exact_daily_policy:
        from .operational_daily_exact_policy_v2 import verify
        verify(root,exact_daily_policy,candidate_only=candidate_only_exact)
        if not exact_adjustment:raise ValueError('EXACT_DAILY_KERNEL_REQUIRED')
    elif exact_adjustment:
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
            target=Path(exact_kernel.__file__).resolve()
        if not target.is_relative_to(root):
            # Record the bytes of the code actually executed, separately from
            # the accepted source copies inside the isolated workspace.
            origins={Path(module.__file__).resolve():'src/'+module.__name__.replace('.','/')+'.py'
                for module in (core,structure,limits,market,focus,sector,exact_kernel)}
            if target not in origins:
                raise ValueError('EXTERNAL_OWNER_BINDING_OUTSIDE_EXECUTED_SOURCE')
            blob=target.read_bytes()
            import hashlib
            destination=folder/'executed_sources'/hashlib.sha256(blob).hexdigest()/origins[target]
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
    def report(stage,state):
        if progress:progress(dates[-1],stage,dict(stage_state=state,mode='APPEND_DAY' if predecessor else 'FULL_REBUILD',compute_sessions=list(dates)))
    def counter(stage):
        if not progress:return None
        return lambda detail:progress(dates[-1],stage,dict(detail,stage_state='RUNNING',mode='APPEND_DAY' if predecessor else 'FULL_REBUILD',compute_sessions=list(dates)))
    if predecessor:
        from .operational_increment_plan_v1 import predecessor_documents
        previous=predecessor_documents(root,predecessor)
        if len(dates)!=1 or dates[0]<=predecessor['accepted_trade_date']:
            raise ValueError('APPEND_SINGLE_NEW_DAY_REQUIRED')
    else:previous=None
    c=private_scope(core,common)
    if exact_adjustment:
        from . import exact_operational_core_candidate_r3 as exact
        c.update(transform_window=exact.transform_window,independent_affine=exact.independent_affine)
    core_path=folder/'owner_v3/CORE_REPLAY.json'
    if exact_adjustment and core_path.exists():
        source=load(folder/'owner_v3/SOURCE_BINDINGS.json')['sources']['adjustment_kernel']
        expected=Path(exact_kernel.__file__).resolve()
        from .tdx_official_daily_source import sha256_file
        if source['sha256']!=sha256_file(expected):raise ValueError('EXACT_CORE_CACHED_SOURCE_MISMATCH')
    lifecycle=load(core.checked(root,lifecycle_binding)) if lifecycle_binding else None
    identity_binding=lifecycle.get('identity') if lifecycle else None
    identity_rows=load(core.checked(root,identity_binding))['rows'] if identity_binding else None
    active_security_ids=set(lifecycle.get('active_security_ids',[])) if lifecycle else None
    report('CORE','RUNNING')
    owners=load(core_path)['owners'] if core_path.exists() else c['materialize_core'](root,dates,
        basis_namespace='TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE' if exact_adjustment else 'TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',
        identity_binding=identity_binding,identity_rows=identity_rows,required_active_ids=active_security_ids,
        accepted_history=previous['profiles'][-1]['owner']['history'] if previous else None,progress_counter=counter('CORE'))
    if [r['trade_date'] for r in owners]!=list(dates):raise ValueError('COMPUTE_OWNER_DATES_MISMATCH')
    report('CORE','COMPLETED')
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
    report('PROFILE','RUNNING')
    bootstrap={}
    if previous:
        prior=previous['profiles'][-1]
        bootstrap=dict(prior_snapshot={'frozen_manifest_episode':prior['snapshot']},
                       prior_security_ids=[r['security_id'] for r in core.gzrows(core.checked(root,prior['owner']['core']))])
    profiles=load(profile_path)['owners'] if profile_path.exists() else s['materialize_profiles_structure'](
        root,progress_counter=counter('PROFILE'),
        lifecycle_rows=lifecycle.get('source_rows',[]) if lifecycle else None,
        lifecycle_trade_date=lifecycle.get('trade_date') if lifecycle else None,
        **bootstrap)
    report('PROFILE','COMPLETED')
    sec=private_scope(sector,dict(load=load,ref=ref,EVIDENCE=folder.relative_to(root).as_posix(),
                               capture=lambda base:membership_snapshot,
                               validate_snapshot=lambda snapshot,base:core.gzrows(core.checked(base,snapshot['memberships']))))
    # The comparator is explicitly an UNKNOWN bootstrap for new dates. The
    # unchanged producer computes every stock Seed from real Core/Profile.
    seed_path=root/sector.OUT/'SECTOR_REPLAY.json'
    # Every replay date needs a comparator, including previously published
    # successors absent from the original four-date historical registry.
    # Missing comparators stay UNKNOWN; actual Seed is computed from Core/Profile.
    registered={row['trade_date'] for row in seed_registry['owners']}
    additions=[]
    for item in profiles:
        dated=item['owner'];day=dated['trade_date']
        if day in registered:continue
        rows=core.gzrows(core.checked(root,dated['core']))
        comparator=core.gzwrite(root,folder/'sources/unknown_seed_comparators'/ (day+'.jsonl.gz'),[
            dict(security_id=row['security_id'],base_seed_state='UNKNOWN',
                contract_id='EXPLICIT_NO_PRIOR_TARGET_SEED_COMPARATOR_V1') for row in rows])
        additions.append(dict(trade_date=day,seed=comparator))
    seed_registry=dict(seed_registry,owners=seed_registry['owners']+additions)
    old_load=sec['load']
    sec['load']=lambda path: seed_registry if Path(path).resolve()==seed_path.resolve() else old_load(path)
    sector_path=folder/'sector_v3/SECTOR_REPLAY.json'
    report('SECTOR_MARKET','RUNNING')
    sector_bootstrap={}
    if previous:
        from .operational_increment_plan_v1 import sector_history
        from .market_source_acquisition import official_sessions
        sessions=official_sessions(root);index=sessions.index(dates[0])
        sector_bootstrap=dict(predecessor_history=sector_history(root,previous['profiles'],previous['sectors'],
                            {sessions[index-1],sessions[index-3]}))
    sectors=load(sector_path) if sector_path.exists() else sec['run'](root,progress_counter=counter('SECTOR_MARKET'),**sector_bootstrap)
    l=private_scope(limits,common)
    original_import=builtins.__import__
    def imports(name,globals=None,locals=None,fromlist=(),level=0):
        if name=='r43_daily_price_limits' and level==1:
            return SimpleNamespace(materialize_daily_limits=l['materialize_daily_limits'])
        return original_import(name,globals,locals,fromlist,level)
    m=private_scope(market,dict(common,__builtins__=dict(vars(builtins),__import__=imports)))
    market_path=folder/'owner_v3/MARKET_REPLAY.json'
    market_bootstrap={}
    if previous:
        market_bootstrap=dict(predecessor_profiles=previous['profiles'],predecessor_markets=[dict(trade_date=d,market=bindings['market']) for d,bindings in sorted(predecessor['owners'].items())])
    markets=load(market_path)['owners'] if market_path.exists() else m['materialize_market'](root,**market_bootstrap)
    report('SECTOR_MARKET','COMPLETED')
    f=private_scope(focus,common)
    focus_path=folder/'owner_v3/FOCUS_FORWARD_REPLAY.json'
    report('FOCUS_FORWARD','RUNNING')
    focus_bootstrap={}
    if previous:
        from .operational_increment_plan_v1 import focus_predecessor
        focus_bootstrap=dict(predecessor_state=focus_predecessor(root,previous['accepted_days']))
        focus_bootstrap['predecessor_state']['research_mainline_source_bindings']=[r['relative_sector'] for r in previous['sectors']]
    forwards=load(focus_path) if focus_path.exists() else f['materialize_focus'](root,progress_counter=counter('FOCUS_FORWARD'),**focus_bootstrap)
    report('FOCUS_FORWARD','COMPLETED')
    return dict(core=owners,profiles=profiles,sectors=sectors,market=markets,focus=forwards)
