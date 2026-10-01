"""Exact source/parent authority for unaccepted continuous all-nine candidates."""
from pathlib import Path
from .daily_data_head import CAPABILITIES
from .source_authority_producers_r4 import require_formal_source

def validate_parent(parent, contract):
    from .dm01_incremental_component_builders_r3 import ROOT,load,digest,ComponentBuildError,CONTRACT_PATH,sha
    anchor=load(contract['accepted_data_head'])
    if parent.get('kind')=='ACCEPTED_ANCHOR':
        if parent['binding']!=contract['accepted_data_head'] or parent['head']!=anchor:
            raise ComponentBuildError('ACCEPTED_PARENT_ANCHOR_MISMATCH')
        if parent['component_manifest_binding']!=contract['bootstrap_parent_manifest']:
            raise ComponentBuildError('ACCEPTED_PARENT_PROJECTION_NOT_CONTRACT_BOUND')
        manifest=load(parent['component_manifest_binding'])
        if manifest['accepted_data_head']!=contract['accepted_data_head'] or manifest['components']!=parent['components']:
            raise ComponentBuildError('ACCEPTED_COMPONENT_PROJECTION_MISMATCH')
        for source in manifest['accepted_source_bindings']:load_bytes(source)
    elif parent.get('kind')=='CANDIDATE_PARENT':
        marker=load(parent['binding'])
        if marker.get('contract_id')!='DM01_ATOMIC_CONTINUOUS_CANDIDATE_R3' or marker.get('status')!='READY_FOR_EXTERNAL_REAUDIT':
            raise ComponentBuildError('INCOMPLETE_OR_UNACCEPTED_CANDIDATE_PARENT')
        if marker.get('data_head_promotion_permitted') is not False or marker.get('external_acceptance')!='PENDING':
            raise ComponentBuildError('CANDIDATE_CANNOT_MINT_ACCEPTANCE')
        if marker['state_view']!=parent['head'] or set(marker['components'])!=set(CAPABILITIES):
            raise ComponentBuildError('CANDIDATE_PARENT_STATE_MISMATCH')
        refs={k:dict(path=r['artifact_path'],sha256=r['artifact_sha256'],bytes=r['artifact_bytes']) for k,r in marker['components'].items()}
        if refs!=parent['components']:
            raise ComponentBuildError('CANDIDATE_PARENT_COMPONENT_BINDINGS_MISMATCH')
        if marker['accepted_anchor']!=contract['accepted_data_head']:
            raise ComponentBuildError('CANDIDATE_PARENT_NOT_LINKED_TO_ACCEPTED_ANCHOR')
        expected=digest(dict(target=marker['target_trade_date'],parent=marker['parent_data_head_digest'],
            source=marker['source_freeze_digest'],contract=sha(ROOT/CONTRACT_PATH)))
        if expected!=marker['candidate_id']:
            raise ComponentBuildError('CANDIDATE_PARENT_REVISION_MISMATCH')
        previous=load(marker['parent_context_binding'])
        if previous['binding']['sha256']!=marker['parent_data_head_digest']:
            raise ComponentBuildError('CANDIDATE_PARENT_CHAIN_MISMATCH')
        validate_parent(previous,contract)
        post=load(marker['cross_postcheck_binding'])
        if post['status']!='PASS' or digest(post)!=marker['postcheck_digest']:
            raise ComponentBuildError('CANDIDATE_PARENT_POSTCHECK_INVALID')
        for cap,r in marker['components'].items():
            payload=load(refs[cap])
            if digest(payload['rows'])!=r['logical_digest'] or len(payload['rows'])!=r['row_count']:
                raise ComponentBuildError('CANDIDATE_PARENT_LOGICAL_DIGEST_MISMATCH')
    else:
        raise ComponentBuildError('PARENT_KIND_NOT_AUTHORIZED')
    manifest=load(parent['component_manifest_binding'])
    if manifest['parent_data_head_digest']!=parent['binding']['sha256'] or manifest['components']!=parent['components']:
        raise ComponentBuildError('PARENT_COMPONENT_MANIFEST_MISMATCH')
    return True

def load_bytes(ref):
    from .dm01_incremental_component_builders_r3 import bound_path
    return bound_path(ref)

def validate_context(cap,target,parent,freeze,calendar,identity,staging):
    from .dm01_incremental_component_builders_r3 import ROOT,load,digest,bound_path,ComponentBuildError,CONTRACT_PATH,resolve_target_session,sha
    from .daily_source_freeze import ensure_outside_tdx,source_freeze_complete_v2
    contract=load(dict(path=CONTRACT_PATH,sha256=sha(ROOT/CONTRACT_PATH)))
    if freeze.get('fixture_scope'):
        raise ComponentBuildError('REAL_CHAIN_FIXTURES_FORBIDDEN')
    validate_parent(parent,contract)
    if any(parent['head']['component_permissions'][c]['status'] not in ('FULL_PASS','DEGRADED_PASS') for c in CAPABILITIES):
        raise ComponentBuildError('PARENT_COMPONENT_NOT_COMPLETE')
    for ref in contract['runtime_bindings']:bound_path(ref)
    cal=load(calendar['binding']);records=load(identity['binding'])
    if calendar.get('status')!='ACCEPTED' or cal.get('accepted_head_binding')!=contract['accepted_calendar_head'] or digest(cal)!=calendar['payload_digest']:
        raise ComponentBuildError('CALENDAR_ACCEPTED_PUBLICATION_MISMATCH')
    calhead=load(contract['accepted_calendar_head']);extension=load(calhead['accepted_extension'])
    allowed=sorted({s['trade_date'] for s in extension['sessions']})
    base=load(contract['accepted_historical_calendar'])['session_dates']
    if cal['session_dates']!=sorted(set(base+allowed)) or cal['session_dates']!=calendar['session_dates']:
        raise ComponentBuildError('CALENDAR_DATES_NOT_EXACT_ACCEPTED_UNION')
    if target!=resolve_target_session(parent['head']['accepted_trade_date'],calendar,freeze['observed_at'],target):
        raise ComponentBuildError('INTERMEDIATE_SESSION_REQUIRED')
    idhead=load(contract['accepted_identity_head'])
    if records['accepted_head_binding']!=contract['accepted_identity_head'] or records['source_identity_binding']!=idhead['identity_revision'] or records['records']!=identity['records']:
        raise ComponentBuildError('IDENTITY_ACCEPTED_PUBLICATION_MISMATCH')
    original=load(idhead['identity_revision'])['records']
    projected=[dict(r,board_scope=(r['exchange']+'_MAIN' if r['board']=='MAIN' else r['board']),
        system_available_at=records['projection_observed_at']) for r in original]
    if records['records']!=projected:
        raise ComponentBuildError('IDENTITY_PROJECTION_NOT_EXACT')
    if not source_freeze_complete_v2(freeze) or freeze['trade_date']!=target or freeze['parent_data_head_digest']!=parent['binding']['sha256']:
        raise ComponentBuildError('SOURCE_FREEZE_OR_PARENT_INVALID')
    for family,ref in freeze['source_families'].items():
        if bound_path(ref).stat().st_size!=ref['bytes']:
            raise ComponentBuildError('SOURCE_SIZE_MISMATCH:'+family)
    for name in ('TDX_PACKAGE_DELTA','BAOSTOCK_DAILY_UPDATE','GBBQ','SPECIAL_PRICE_PHASE'):
        if freeze['inputs'][name]['sha256']!=freeze['source_families'][name]['sha256']:
            raise ComponentBuildError('INPUT_SOURCE_FAMILY_MISMATCH:'+name)
    if identity['publication_id']!=freeze['identity_publication_id'] or calendar['publication_id']!=freeze['calendar_publication_id']:
        raise ComponentBuildError('SOURCE_PUBLICATION_MISMATCH')
    page=load(freeze['source_families']['TDX_PAGE_CAPTURE']);pkg=freeze['source_families']['TDX_FULL_PACKAGE']
    if page['contract_id']!='DM01_TDX_TARGET_SLICE_V3' or page['target_date']!=target or page['snapshot_id']!=pkg['source_revision'] or page['package_binding']['sha256']!=pkg['sha256']:
        raise ComponentBuildError('OFFICIAL_TDX_TARGET_SLICE_BINDING_INVALID')
    capture=load(page['actual_capture_receipt'])
    if page['capture_kind']=='CURRENT_OFFICIAL_ZIP_RECONSTRUCTED':
        if capture['status']!='PASS_OFFICIAL_ZIP' or capture['package']!=page['package_binding']:
            raise ComponentBuildError('OFFICIAL_TDX_CAPTURE_NOT_VALIDATED')
    elif page['capture_kind']=='EXTERNALLY_ACCEPTED_GO_FORWARD_PACKAGE':
        go=load(contract['accepted_go_forward_head'])
        if page['package_binding']!=go['evidence_bindings']['official_tdx_package'] or capture['status']!='TDX_PACKAGE_READY' or capture['package_sha256']!=pkg['sha256']:
            raise ComponentBuildError('ACCEPTED_OFFICIAL_PACKAGE_MISMATCH')
    else:raise ComponentBuildError('TDX_CAPTURE_KIND_UNAUTHORIZED')
    if page.get('AS_RECORDED') is not False or page.get('future_rows_consumed')!=0:
        raise ComponentBuildError('TDX_SLICE_FUTURE_OR_AS_RECORDED_FORBIDDEN')
    rules=load(contract['producer_governance'])['field_rules']
    for field,binding in freeze['field_source_instances'].items():
        rule=next(r for r in rules if r['field_id']==field)
        proof=require_formal_source(ROOT,rule,consumer_contract_id='DM01_FINAL_ALL_NINE',target_trade_date=target,instance_binding=binding)
        if proof['producer']['owner']['OHLC_authority'] or proof['producer']['owner']['adjustment_authority']:
            raise ComponentBuildError('PROVIDER_SCOPE_ESCALATION')
        provider=load(binding);bao=load(freeze['inputs']['BAOSTOCK_DAILY_UPDATE'])
        raw=load(provider['raw_artifact'])
        if bao['raw_response_binding']!=provider['raw_artifact'] or bao['daily_rows']!=raw['rows']:
            raise ComponentBuildError('STRUCTURED_PROVIDER_SOURCE_NOT_EXACT_INSTANCE')
    if set(freeze['field_source_instances'])!={'TRADING_STATUS','ISST'}:
        raise ComponentBuildError('BOTH_FIELD_INSTANCES_REQUIRED')
    stage=Path(staging).resolve()
    for root in (Path('D:/new_tdx'),*[Path(p) for p in freeze.get('tdx_roots',[])]):ensure_outside_tdx(stage,root)
    if stage.is_relative_to((ROOT/'data/v4/artifact_store').resolve()):
        raise ComponentBuildError('CANDIDATE_IN_ACCEPTED_NAMESPACE')
    return dict(cap=cap,target=target,parent=parent,freeze=freeze,calendar=calendar,identity=identity,staging=stage,contract=contract)
