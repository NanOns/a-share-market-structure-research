"""Resumable corrected-owner branch of the same DM01 daily entry."""
from pathlib import Path
from .corrected_owner_replay import load, checked, ref, OUT, CONTRACT, materialize_core
from .market_source_acquisition import write, official_sessions


def run_corrected_owner_pipeline(root, *, target_date='2026-10-08', stage='all'):
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
        current=load(root/'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json')
        capture=load(checked(root,current['capture_receipt']))
        if capture['package']['sha256']!=core['owners'][0]['sources']['package']['sha256']:
            raise ValueError('NEW_SOURCE_REVISION_REQUIRES_SEPARATE_CORRECTED_OWNER_NAMESPACE')
        for owner in core['owners']:
            for key in ('core','prior_core','history','raw','adjusted'):checked(root,owner[key])
    else:materialize_core(root)
    if stage=='core':return dict(status='CORRECTED_CORE_READY',receipt=str(out/'CORE_REPLAY.json'))
    if not (out/'PROFILE_STRUCTURE_REPLAY.json').exists():
        from .corrected_structure_replay import materialize_profiles_structure
        materialize_profiles_structure(root)
    profiles=load(out/'PROFILE_STRUCTURE_REPLAY.json')
    for owner in profiles['owners']:
        for key in ('profiles','status'):checked(root,owner['owner'][key])
        checked(root,owner['structure_manifest']);checked(root,owner['snapshot'])
    if stage=='profile':return dict(status='CORRECTED_PROFILE_STRUCTURE_READY',receipt=str(out/'PROFILE_STRUCTURE_REPLAY.json'))
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
                source_requests_this_run=0,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
                data_head_moved=False,production_admission=False,
                next_stage='INDEPENDENT_EXTERNAL_SCOPED_OWNER_REVIEW' if qa else 'FOCUS_FORWARD_AND_SCOPED_RELEASE_QA')
    write(out/'DM01_CORRECTED_OWNER_RECEIPT.json',result)
    return dict(result,receipt=str(out/'DM01_CORRECTED_OWNER_RECEIPT.json'))
