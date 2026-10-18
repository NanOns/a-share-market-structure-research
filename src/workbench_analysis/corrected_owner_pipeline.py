"""Resumable corrected-owner branch of the same DM01 daily entry."""
import json
from pathlib import Path
from .corrected_owner_replay import load, checked, ref, OUT, CONTRACT, materialize_core
from .market_source_acquisition import write, official_sessions, load_json_source_pg, load_json_binding_pg


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
    root=Path(root).resolve();out=root/OUT;policy=load(root/CONTRACT)
    seal=out/'OWNER_STAGE_SEAL_V1.json'
    if seal.exists():
        bound=load(seal)
        if bound.get('production_admission') is not False:raise ValueError('CORRECTED_SEAL_PERMISSION_OVERCLAIM')
        for binding in bound['bindings']:checked(root,binding)
    if target_date not in policy['target_sessions'] or target_date not in official_sessions(root):
        raise ValueError('CORRECTED_SESSION_OUTSIDE_VERSIONED_CONTRACT')
    if (out/'CORE_REPLAY.json').exists():
        core=load(out/'CORE_REPLAY.json')
        current=load_json_source_pg(root,'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json',
                                    source_origin='V4_CORRECTED_OWNER_CANDIDATE')
        capture=load_json_binding_pg(root,current['capture_receipt'],
                                     source_origin='V4_CORRECTED_OWNER_CANDIDATE')
        if capture['package']['sha256']!=core['owners'][0]['sources']['package']['sha256']:
            raise ValueError('NEW_SOURCE_REVISION_REQUIRES_SEPARATE_CORRECTED_OWNER_NAMESPACE')
        for owner in core['owners']:
            for key in ('core','prior_core','history','raw','adjusted'):checked(root,owner[key])
    else:materialize_core(root)
    if stage=='core':return dict(status='CORRECTED_CORE_READY',receipt=str(out/'CORE_REPLAY.json'),calendar_authority=calendar_authority)
    if not (out/'PROFILE_STRUCTURE_REPLAY.json').exists():
        from .corrected_structure_replay import materialize_profiles_structure
        materialize_profiles_structure(root)
    profiles=load(out/'PROFILE_STRUCTURE_REPLAY.json')
    for owner in profiles['owners']:
        for key in ('profiles','status'):checked(root,owner['owner'][key])
        checked(root,owner['structure_manifest']);checked(root,owner['snapshot'])
    if stage=='profile':return dict(status='CORRECTED_PROFILE_STRUCTURE_READY',receipt=str(out/'PROFILE_STRUCTURE_REPLAY.json'),calendar_authority=calendar_authority)
    if not (out/'SECTOR_REPLAY.json').exists():
        from .corrected_sector_replay import materialize_sectors
        materialize_sectors(root)
    sectors=load(out/'SECTOR_REPLAY.json')
    for owner in sectors['owners']:
        for key in ('membership','native','seed','relative_sector'):checked(root,owner[key])
    if not (out/'HEALTH_PROJECTION_REPLAY.json').exists():
        from .corrected_health_projection import materialize_health
        materialize_health(root)
    if not (out/'FOCUS_FORWARD_REPLAY.json').exists():
        from .corrected_focus_replay import materialize_focus
        materialize_focus(root)
    if not (out/'MARKET_ROTATION_REPLAY.json').exists():
        from .corrected_market_rotation import materialize_market_rotation
        materialize_market_rotation(root)
    for name in ('HEALTH_PROJECTION_REPLAY','MARKET_ROTATION_REPLAY'):
        for owner in load(out/(name+'.json'))['owners']:
            for key in ('projection','market','rotation'):
                if key in owner:checked(root,owner[key])
    focus=load(out/'FOCUS_FORWARD_REPLAY.json');checked(root,focus['focus'])
    for owner in focus['owners']:
        for key in ('D2','facts','calculations'):checked(root,owner[key])
    qa_path=out/'INDEPENDENT_QA_AND_SAFE_RELEASE_READBACK.json'
    qa=load(qa_path) if qa_path.exists() else None
    if qa and (qa['errors'] or qa['acceptance']!='PASS_CORRECTED_CANDIDATE_SCOPE'):
        raise ValueError('CORRECTED_OWNER_INDEPENDENT_QA_FAILED')
    result=dict(status='CORRECTED_OWNER_QA_PASS_PENDING_SCOPED_ADMISSION' if qa else 'CORRECTED_OWNER_CANDIDATE_READY_PENDING_RELEASE_QA',target_date=target_date,
                contract=ref(root,root/CONTRACT),core=ref(root,out/'CORE_REPLAY.json'),
                profile_structure=ref(root,out/'PROFILE_STRUCTURE_REPLAY.json'),sector=ref(root,out/'SECTOR_REPLAY.json'),
                health=ref(root,out/'HEALTH_PROJECTION_REPLAY.json'),focus_forward=ref(root,out/'FOCUS_FORWARD_REPLAY.json'),
                market_rotation=ref(root,out/'MARKET_ROTATION_REPLAY.json'),
                calendar_authority=calendar_authority,
                source_requests_this_run=0,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
                data_head_moved=False,production_admission=False,
                next_stage='INDEPENDENT_EXTERNAL_SCOPED_OWNER_REVIEW' if qa else 'FOCUS_FORWARD_AND_SCOPED_RELEASE_QA')
    write(out/'DM01_CORRECTED_OWNER_RECEIPT.json',result)
    return dict(result,receipt=str(out/'DM01_CORRECTED_OWNER_RECEIPT.json'))
