"""Revision checks are anchored to the accepted predecessor, never bootstrap."""
from .r43_owner_replay import checked,load
from .tdx_official_daily_source import sha256_file

CONTRACT='V4_ACCEPTED_PREDECESSOR_REVISION_GUARD_R1'
# Driver admission is checked separately by the release policy. These bindings
# are numerical kernels/parameters and may never borrow that driver exception.
KERNEL_PREFIXES=('src/v4/','src/sector/','src/adjustment/','src/tdx/')
PARAMETERS={'config/v4_02_formal_period_contract_v1.json','config/v4_03_parameter_registry_v1.json','config/v4_03_parameter_set_v1.json'}


CORRECTED_MARKET_KEY='market_context_correction_preparation_r1'
MARKET_DRIVERS={'src/workbench_analysis/r43_market_replay.py','src/workbench_analysis/operational_owner_adapter_v1.py'}


def lifecycle_adapter_only(before,after):
    """Recognize exactly the R8 target-lifecycle plumbing; all other AST stays equal."""
    import ast
    old=ast.parse(before);new=ast.parse(after)
    declaration=ast.parse('PROFILE_LIFECYCLE_CONSERVATION_CONTRACT = "DYNAMIC_PROFILE_LIFECYCLE_CONSERVATION_R1"').body[0]
    declarations=[n for n in new.body if ast.dump(n)==ast.dump(declaration)]
    if len(declarations)!=1:return False
    new.body.remove(declarations[0])
    functions=[n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='replay']
    if len(functions)!=1:return False
    replay=functions[0]
    positions=[i for i,arg in enumerate(replay.args.kwonlyargs) if arg.arg=='lifecycle_binding']
    if len(positions)!=1:return False
    index=positions[0]
    default=replay.args.kw_defaults[index]
    if not isinstance(default,ast.Constant) or default.value is not None:return False
    del replay.args.kwonlyargs[index];del replay.args.kw_defaults[index]
    plumbing=ast.parse("""
lifecycle=load(core.checked(root,lifecycle_binding)) if lifecycle_binding else None
identity_binding=lifecycle.get('identity') if lifecycle else None
identity_rows=load(core.checked(root,identity_binding))['rows'] if identity_binding else None
active_security_ids=set(lifecycle.get('active_security_ids',[])) if lifecycle else None
""").body
    matches=[i for i in range(len(replay.body)-3)
             if all(ast.dump(replay.body[i+j])==ast.dump(n) for j,n in enumerate(plumbing))]
    if len(matches)!=1:return False
    del replay.body[matches[0]:matches[0]+4]
    expected=ast.parse("c['materialize_core'](identity_binding=identity_binding,identity_rows=identity_rows,required_active_ids=active_security_ids)").body[0].value
    calls=[n for n in ast.walk(replay) if isinstance(n,ast.Call) and ast.dump(n.func)==ast.dump(expected.func)]
    if len(calls)!=1:return False
    call=calls[0]
    for keyword in expected.keywords:
        matches=[k for k in call.keywords if ast.dump(k)==ast.dump(keyword)]
        if len(matches)!=1:return False
        call.keywords.remove(matches[0])
    return ast.dump(old)==ast.dump(new)

def accepted_baseline(root,parent,generation):
    """Only an independently admitted predecessor may advance driver baseline."""
    original=generation.get('adjustment_contract',{}).get('policy')
    if CORRECTED_MARKET_KEY not in parent:
        if original:return load(checked(root,original))['accepted_algorithm_bindings'],original,False
        return parent.get('accepted_algorithm_bindings',[]),None,False
    from .operational_runtime_acceptance_r1_1 import KEY,verify as verify_runtime
    if KEY not in parent:raise ValueError('RANGE_REPAIR_REQUIRED:MARKET_RUNTIME_ADMISSION_MISSING')
    from .operational_market_context_correction_r1 import verify as verify_market
    policy=load(checked(root,parent['release_policy']))
    if parent.get('accepted_algorithm_bindings')!=policy['accepted_algorithm_bindings']:raise ValueError('RANGE_REPAIR_REQUIRED:ACCEPTED_MARKET_POLICY_BINDING_MISMATCH')
    verify_market(root,parent,policy)
    verify_runtime(root,parent,policy)
    return policy['accepted_algorithm_bindings'],parent['release_policy'],True


def isolated_day_baseline(root,parent,generation):
    """A numerically verified isolated day may precede the next isolated day."""
    from pathlib import Path
    root=Path(root).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp').resolve()):
        raise ValueError('ISOLATED_CANDIDATE_REVISION_SCOPE_REQUIRED')
    proof=load(checked(root,parent['r8_isolated_day_acceptance']))
    if (proof.get('contract_id')!='R8_ISOLATED_DAY_NUMERIC_ACCEPTANCE_R1'
            or proof.get('scope')!='ISOLATED_CANDIDATE_HEAD_ONLY'
            or proof.get('acceptance')!='PASS_NUMERIC_DAY_QA'
            or proof.get('production_admitted') is not False
            or proof.get('trade_date')!=parent['accepted_trade_date']):
        raise ValueError('ISOLATED_DAY_NUMERIC_ACCEPTANCE_REQUIRED')
    original=load(checked(root,proof['candidate']))
    stripped={k:v for k,v in parent.items() if k!='r8_isolated_day_acceptance'}
    if original!=stripped:raise ValueError('ISOLATED_ACCEPTED_CANDIDATE_CHANGED')
    if generation.get('adjustment_contract',{}).get('policy')!=parent['release_policy']:
        raise ValueError('ISOLATED_GENERATION_POLICY_MISMATCH')
    from .operational_daily_exact_policy_v2 import verify
    policy,_=verify(root,parent['release_policy'],candidate_only=True)
    if policy.get('publication_ready') is not False or parent['accepted_algorithm_bindings']!=policy['accepted_algorithm_bindings']:
        raise ValueError('ISOLATED_CANDIDATE_POLICY_REQUIRED')
    from .operational_successor_v1 import validate
    validate(root,parent)
    # Keep both market drivers protected on subsequent candidate days.
    return policy['accepted_algorithm_bindings'],parent['release_policy'],True

def detect(root,parent,gbbq_sha,member_hashes,*,execution_bindings=None,candidate_only=False):
    from pathlib import Path
    root=Path(root);previous=parent['accepted_trade_date']
    if candidate_only and not root.resolve().is_relative_to(Path('G:/codex_tmp').resolve()):
        raise ValueError('ISOLATED_CANDIDATE_REVISION_SCOPE_REQUIRED')
    registry=parent.get('source_registry',{}).get(previous,{})
    if not registry.get('generation'):raise ValueError('RANGE_REPAIR_REQUIRED:ACCEPTED_GENERATION_MISSING')
    generation=load(checked(root,registry['generation']))
    revisions=[]
    if generation.get('gbbq')!=gbbq_sha:revisions.append('GBBQ_REVISION')
    if generation.get('member_sources')!=member_hashes:revisions.append('MEMBERSHIP_REVISION')
    isolated_parent=bool(candidate_only and parent.get('r8_isolated_day_acceptance'))
    baseline,baseline_policy,corrected_market=(isolated_day_baseline(root,parent,generation) if isolated_parent else accepted_baseline(root,parent,generation))
    kernels=[];drivers=[];candidate_admissions=[]
    executed={b.get('module_path',b['path']):b for b in execution_bindings or []}
    for binding in baseline:
        name=binding.get('module_path',binding['path'])
        if name.startswith(KERNEL_PREFIXES) or name in PARAMETERS or corrected_market and name in MARKET_DRIVERS:
            if execution_bindings is not None:
                # Exact successor policies need not repeat every numerical
                # source already bound by their accepted predecessor. When a
                # source is absent from the successor execution set, verify
                # the predecessor's immutable binding directly instead of
                # treating the omission as missing or inferring a replacement.
                executed_binding=executed.get(name,binding)
                if name in executed:
                    actual_path=checked(root,executed_binding)
                    actual=sha256_file(actual_path)
                    actual_bytes=actual_path.stat().st_size
                else:
                    predecessor_path=(root/executed_binding['path']).resolve()
                    predecessor_path.relative_to(root.resolve())
                    actual=sha256_file(predecessor_path)
                    actual_bytes=predecessor_path.stat().st_size
            else:
                executed_binding=binding
                actual_path=(root/binding['path']).resolve()
                actual_path.relative_to(root.resolve())
                actual=sha256_file(actual_path)
                actual_bytes=actual_path.stat().st_size
            unchanged=actual==binding['sha256'] and (actual_bytes is None or actual_bytes==binding.get('bytes'))
            kernels.append(dict(module_path=name,accepted_sha256=binding['sha256'],actual_sha256=actual,
                accepted_bytes=binding.get('bytes'),actual_bytes=actual_bytes,
                executed_binding=executed_binding,execution_binding_source='SUCCESSOR_POLICY' if name in executed else 'PREDECESSOR_HEAD',
                unchanged=unchanged))
            if not unchanged:
                admitted=(candidate_only and name=='src/workbench_analysis/operational_owner_adapter_v1.py'
                    and name in executed and lifecycle_adapter_only(checked(root,binding).read_text(encoding='utf8'),checked(root,executed[name]).read_text(encoding='utf8')))
                if admitted:
                    candidate_admissions.append(dict(contract_id='R8_ISOLATED_LIFECYCLE_DRIVER_ADMISSION_R1',
                        accepted_binding=binding,executed_binding=executed[name],
                        scope='CANDIDATE_COMPUTATION_ONLY_REQUIRES_NUMERIC_QA',production_admitted=False))
                else:revisions.append('NUMERIC_ALGORITHM_REVISION:'+name)
        else:drivers.append(name)
    if not kernels:raise ValueError('RANGE_REPAIR_REQUIRED:ACCEPTED_NUMERIC_BINDINGS_MISSING')
    return dict(contract_id=CONTRACT,status='RANGE_REPAIR_REQUIRED' if revisions else 'APPEND_DAY',
        predecessor_trade_date=previous,predecessor_generation=registry['generation'],
        accepted_source_baseline=baseline_policy,bounded_market_admission_verified=corrected_market,
        baseline_scope='ISOLATED_NUMERIC_QA' if isolated_parent else 'ACCEPTED_PREDECESSOR',
        gbbq=dict(accepted=generation.get('gbbq'),actual=gbbq_sha),
        member_sources_unchanged=generation.get('member_sources')==member_hashes,
        revisions=revisions,numeric_bindings=kernels,driver_bindings_separate_admission=drivers,
        candidate_driver_admissions=candidate_admissions,
        history_overlap='REQUIRES_CORE_HISTORY_OVERLAP_CHECK',head_mutated=False)
