"""Resumable corrected-owner branch of the same DM01 daily entry."""
import json
from pathlib import Path
from .corrected_owner_replay import load, checked, OUT, CONTRACT, materialize_core, pg_json_source
from .r43_owner_replay import historical_source, pg_source_binding, write_candidate_json
from .market_source_acquisition import official_sessions


def _candidate_json(root, relative_path):
    try:
        return pg_json_source(root,relative_path)
    except ValueError as error:
        if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':raise
        if (Path(root)/relative_path).exists():
            raise ValueError('UNINGRESSED_WORKSPACE_CANDIDATE_NOT_CONSUMABLE:'+relative_path) from error
        return None


def run_corrected_owner_pipeline(root, *, target_date='2026-10-08', stage='all',
                                calendar_source='pg_publication_head'):
    root=Path(root).resolve()
    if calendar_source=='accepted_dm01_data_head_candidate':
        from .dm01_runtime_r4 import calendar
        from .market_source_acquisition import bind_dm01_calendar_for_diagnostic_candidate,digest
        from workbench_db.dm01_data_accepted_head_pg_r1 import read_current
        from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
        accepted_head=read_current(root)
        accepted_calendar_binding=accepted_head['candidate'].get('calendar')
        if not isinstance(accepted_calendar_binding,dict):
            raise ValueError('DM01_ACCEPTED_DATA_HEAD_CALENDAR_BINDING_MISSING')
        accepted_calendar=read_bound(root,accepted_calendar_binding['path'],accepted_calendar_binding['sha256'])
        accepted_calendar_value=accepted_calendar.get('value')
        accepted_sessions=(accepted_calendar_value.get('session_dates') or
                           accepted_calendar_value.get('sessions')) if isinstance(accepted_calendar_value,dict) else accepted_calendar_value
        extension=calendar(root)
        if (not isinstance(accepted_sessions,list)
                or accepted_calendar_binding.get('bytes')!=len(accepted_calendar['raw'])
                or accepted_sessions!=sorted(set(accepted_sessions))):
            raise ValueError('DM01_ACCEPTED_DATA_HEAD_CALENDAR_INVALID')
        sessions=sorted(set(accepted_sessions)|set(extension['session_dates']))
        source_bindings=[
            dict(role='accepted_data_head',path='data/v4/V4_DATA_ACCEPTED_HEAD.json',
                 sha256=accepted_head['head_sha256'],bytes=accepted_head['head_bytes']),
            dict(role='accepted_data_head_calendar',**accepted_calendar_binding),
            dict(role='r4_calendar_head',**extension['head_binding']),
            dict(role='r4_calendar_payload',**extension['binding']),
        ]
        snapshot=dict(status='DM01_ACCEPTED_BASE_PLUS_R4_CALENDAR_DIAGNOSTIC_CANDIDATE',
            source_bindings=source_bindings,session_dates=sessions,
            payload_digest=digest(json.dumps(dict(source_bindings=source_bindings,sessions=sessions),
                sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()),
            production_admission=False)
        with bind_dm01_calendar_for_diagnostic_candidate(root,snapshot) as authority:
            return _run_corrected_owner_pipeline(root,target_date=target_date,stage=stage,
                                                 calendar_authority=authority)
    if calendar_source!='pg_publication_head':
        raise ValueError('CORRECTED_CALENDAR_SOURCE_INVALID')
    return _run_corrected_owner_pipeline(root,target_date=target_date,stage=stage,
        calendar_authority=dict(contract_id='V4_PG_MARKET_CALENDAR_READER_R1',
                                status='ACCEPTED_PUBLICATION_HEAD'))


def _run_corrected_owner_pipeline(root, *, target_date, stage, calendar_authority):
    root=Path(root).resolve();out=root/OUT;policy=pg_json_source(root,CONTRACT)
    seal_path=OUT+'/OWNER_STAGE_SEAL_V1.json';bound=_candidate_json(root,seal_path)
    if bound is not None:
        if bound.get('production_admission') is not False:raise ValueError('CORRECTED_SEAL_PERMISSION_OVERCLAIM')
        for binding in bound['bindings']:checked(root,binding)
    if target_date not in policy['target_sessions'] or target_date not in official_sessions(root):
        raise ValueError('CORRECTED_SESSION_OUTSIDE_VERSIONED_CONTRACT')
    core_path=OUT+'/CORE_REPLAY.json';core=_candidate_json(root,core_path)
    if core is not None:
        current=historical_source(root,'capture_audit')['value']
        capture=load(checked(root,current['capture_receipt']))
        if capture['package']['sha256']!=core['owners'][0]['sources']['package']['sha256']:
            raise ValueError('NEW_SOURCE_REVISION_REQUIRES_SEPARATE_CORRECTED_OWNER_NAMESPACE')
        for owner in core['owners']:
            for key in ('core','prior_core','history','raw','adjusted'):checked(root,owner[key])
    else:materialize_core(root)
    if stage=='core':return dict(status='CORRECTED_CORE_READY',receipt=pg_source_binding(root,core_path),calendar_authority=calendar_authority)
    profile_path=OUT+'/PROFILE_STRUCTURE_REPLAY.json';profiles=_candidate_json(root,profile_path)
    if profiles is None:
        from .corrected_structure_replay import materialize_profiles_structure
        materialize_profiles_structure(root)
        profiles=_candidate_json(root,profile_path)
    for owner in profiles['owners']:
        for key in ('profiles','status'):checked(root,owner['owner'][key])
        checked(root,owner['structure_manifest']);checked(root,owner['snapshot'])
    if stage=='profile':return dict(status='CORRECTED_PROFILE_STRUCTURE_READY',receipt=pg_source_binding(root,profile_path),calendar_authority=calendar_authority)
    sector_path=OUT+'/SECTOR_REPLAY.json';sectors=_candidate_json(root,sector_path)
    if sectors is None:
        from .corrected_sector_replay import materialize_sectors
        materialize_sectors(root)
        sectors=_candidate_json(root,sector_path)
    for owner in sectors['owners']:
        for key in ('membership','native','seed','relative_sector'):checked(root,owner[key])
    health_path=OUT+'/HEALTH_PROJECTION_REPLAY.json';health=_candidate_json(root,health_path)
    if health is None:
        from .corrected_health_projection import materialize_health
        materialize_health(root)
        health=_candidate_json(root,health_path)
    focus_path=OUT+'/FOCUS_FORWARD_REPLAY.json';focus=_candidate_json(root,focus_path)
    if focus is None:
        from .corrected_focus_replay import materialize_focus
        materialize_focus(root)
        focus=_candidate_json(root,focus_path)
    market_path=OUT+'/MARKET_ROTATION_REPLAY.json';market_rotation=_candidate_json(root,market_path)
    if market_rotation is None:
        from .corrected_market_rotation import materialize_market_rotation
        materialize_market_rotation(root)
        market_rotation=_candidate_json(root,market_path)
    for name in ('HEALTH_PROJECTION_REPLAY','MARKET_ROTATION_REPLAY'):
        manifest=health if name=='HEALTH_PROJECTION_REPLAY' else market_rotation
        for owner in manifest['owners']:
            for key in ('projection','market','rotation'):
                if key in owner:checked(root,owner[key])
    checked(root,focus['focus'])
    for owner in focus['owners']:
        for key in ('D2','facts','calculations'):checked(root,owner[key])
    qa=_candidate_json(root,OUT+'/INDEPENDENT_QA_AND_SAFE_RELEASE_READBACK.json')
    if qa and (qa['errors'] or qa['acceptance']!='PASS_CORRECTED_CANDIDATE_SCOPE'):
        raise ValueError('CORRECTED_OWNER_INDEPENDENT_QA_FAILED')
    result=dict(status='CORRECTED_OWNER_QA_PASS_PENDING_SCOPED_ADMISSION' if qa else 'CORRECTED_OWNER_CANDIDATE_READY_PENDING_RELEASE_QA',target_date=target_date,
                contract=pg_source_binding(root,CONTRACT),core=pg_source_binding(root,core_path),
                profile_structure=pg_source_binding(root,profile_path),sector=pg_source_binding(root,sector_path),
                health=pg_source_binding(root,health_path),focus_forward=pg_source_binding(root,focus_path),
                market_rotation=pg_source_binding(root,market_path),
                calendar_authority=calendar_authority,
                source_requests_this_run=0,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
                data_head_moved=False,production_admission=False,
                next_stage='INDEPENDENT_EXTERNAL_SCOPED_OWNER_REVIEW' if qa else 'FOCUS_FORWARD_AND_SCOPED_RELEASE_QA')
    receipt_path=OUT+'/DM01_CORRECTED_OWNER_RECEIPT.json'
    write_candidate_json(root,out/'DM01_CORRECTED_OWNER_RECEIPT.json',result)
    return dict(result,receipt=pg_source_binding(root,receipt_path))
