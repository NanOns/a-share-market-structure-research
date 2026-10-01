"""Resolve the accepted calendar and inspect real source readiness, or execute a frozen context.

No head promotion and no retrospective recreation of a missed request-time source capture.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from workbench_analysis.dm01_incremental_component_builders import sha,load,digest,resolve_target_session
from workbench_analysis.dm01_accepted_builder_registry import validate_incremental_registry
from workbench_analysis.dm01_candidate_orchestrator_r1 import build_candidate
from workbench_analysis.gbbq_source_revision_probe import probe_gbbq_source_revision
from scripts.run_v4_dm01_daily_increment import _runtime_acceptance

def bind(p):
    p=Path(p);return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)

def real_probe():
    protected_paths=[ROOT/'data/v4'/n for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_STAGE_ACCEPTED_HEAD.json','V4_DEV_BASELINE_HEAD.json')]
    protected_before={p:sha(p) for p in protected_paths}
    parent_path=ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json';parent=json.loads(parent_path.read_text(encoding='utf8'))
    cal_head_path=ROOT/'data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json'
    head=json.loads(cal_head_path.read_text(encoding='utf8'))
    if head['status']!='ACCEPTED':raise ValueError('CALENDAR_EXTENSION_NOT_ACCEPTED')
    extension=load(head['accepted_extension']); sessions_by={m:sorted(r['trade_date'] for r in extension['sessions'] if r['market']==m) for m in ('SSE','SZSE')}
    if sessions_by['SSE']!=sessions_by['SZSE']:raise ValueError('ACCEPTED_CALENDAR_MARKET_MISMATCH')
    now=datetime.now(timezone.utc).isoformat()
    calendar=dict(session_dates=sessions_by['SSE'],coverage_end=head['coverage_end'])
    target=resolve_target_session(parent['accepted_trade_date'],calendar,now)
    report=ROOT/'reports/dm01'
    resolution=dict(contract_id='DM01_A01_TARGET_SESSION_RESOLUTION_R1',status='PASS',parent_data_head=bind(parent_path),
        parent_trade_date=parent['accepted_trade_date'],accepted_calendar_head=bind(cal_head_path),
        accepted_calendar_extension=head['accepted_extension'],candidate_sessions=sessions_by['SSE'],
        next_completed_required_session=target,observed_at=now,selection='MIN_ACCEPTED_SESSION_STRICTLY_AFTER_PARENT',
        no_hardcoded_target_date=True,later_sessions_cannot_leap_over_missing_target=True)
    atomic_json(report/'DM01_A01_TARGET_SESSION_RESOLUTION_R1.json',resolution)
    gbbq_root=ROOT/'data/v4/source_snapshot_store/gbbq/sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e'
    gbbq=probe_gbbq_source_revision(target_date=target,current_source_root=Path('D:/new_tdx/vipdoc/cw'),
        accepted_snapshot_root=gbbq_root,output_snapshot_root=ROOT/'data/v4/source_snapshot_store',
        observed_at=now,official_sessions_after_target=[d for d in calendar['session_dates'] if d>target],tdx_root=Path('D:/new_tdx'))
    runtime,error=_runtime_acceptance(target)
    captures=[]
    folder=ROOT/'data/v4/source_snapshots/tdx'/target.replace('-','')
    for p in folder.glob('*/capture_receipt.json'):
        value=json.loads(p.read_text(encoding='utf8'))
        if value.get('target_date')==target and value.get('update_date')==target and value.get('status') in ('TDX_PACKAGE_READY','NOOP_SOURCE_ALREADY_FROZEN'):
            download=value.get('download') or {};package=p.parent/'hsjday.zip'
            if package.exists() and sha(package)==download.get('sha256'):
                captures.append(dict(receipt=bind(p),package=bind(package),status='PASS_FROZEN_OFFICIAL_PACKAGE_EXACT',
                                     snapshot_id=value.get('snapshot_id')))
        elif value.get('contract_id')=='V4_02_GO_FORWARD_TDX_CAPTURE_R2' and value.get('target_trade_date')==target and value.get('status')=='TDX_PACKAGE_READY':
            go_head_path=ROOT/'data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json'
            go=json.loads(go_head_path.read_text(encoding='utf8'));ref=go['evidence_bindings']['official_tdx_package']
            package=ROOT/ref['path']
            if go['external_acceptance']=='EXTERNALLY_ACCEPTED' and ref['sha256']==value['package_sha256'] and sha(package)==ref['sha256']:
                captures.append(dict(receipt=bind(p),package=ref,status='PASS_EXTERNALLY_ACCEPTED_FROZEN_R2_PACKAGE_EXACT',
                    snapshot_id='sha256-'+ref['sha256'],accepted_go_forward_head=bind(go_head_path)))
    bao_folder=ROOT/'data/v4/source_snapshots/baostock'/target.replace('-','')
    bao_files=list(bao_folder.glob('*/daily_update.json'))
    problems=[]
    if not captures:problems.append('REQUIRED_TARGET_OFFICIAL_TDX_CAPTURE_MISSING')
    if runtime is None:problems.append('BAOSTOCK_EXACT_TARGET_RUNTIME_ACCEPTANCE_MISSING:'+str(error))
    if not bao_files:problems.append('BAOSTOCK_TARGET_DAILY_ROSTER_STATUS_ST_AND_FACTOR_FREEZE_MISSING')
    go_head_path=ROOT/'data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json'
    go=json.loads(go_head_path.read_text(encoding='utf8'));gbbq_ref=go['evidence_bindings']['gbbq_snapshot']
    frozen_gbbq=load(gbbq_ref)
    frozen_gbbq_ok=go['external_acceptance']=='EXTERNALLY_ACCEPTED' and frozen_gbbq['first_eligible_formal_trade_date']<=target
    frozen_gbbq_ok=frozen_gbbq_ok and all(sha(gbbq_root/name)==ref['sha256'] for name,ref in frozen_gbbq['files'].items())
    if not frozen_gbbq_ok:problems.append('ACCEPTED_DATED_GBBQ_SNAPSHOT_NOT_VERIFIED')
    status='BLOCKED_MISSING_INTERMEDIATE_SESSION' if problems else 'SOURCE_SET_PRESENT_REQUIRES_FROZEN_CONTEXT'
    result=dict(contract_id='DM01_A01_REAL_NEXT_SESSION_CANDIDATE_R1',status=status,target_trade_date=target,
        source_readiness_problems=problems,target_resolution=bind(report/'DM01_A01_TARGET_SESSION_RESOLUTION_R1.json'),
        frozen_TDX_packages=captures,baostock_runtime_acceptance=runtime,baostock_runtime_error=error,
        baostock_daily_artifacts=[bind(p) for p in bao_files],gbbq_current_read_only_probe=gbbq,
        accepted_dated_gbbq_snapshot=dict(binding=gbbq_ref,status='PASS_EXACT_TARGET_ELIGIBLE_FROZEN_SNAPSHOT' if frozen_gbbq_ok else 'BLOCKED',
            current_source_probe_is_diagnostic_for_already_frozen_target=True),
        runtime_live_smoke_request_count=0,retrospective_source_capture_forbidden=True,
        note='Existing DailyUpdates contract accepts live smoke only on the target date after close. A missed dated freeze cannot be relabeled from a later date.',
        real_market_component_builds=[],real_market_candidate_written=False,
        engineering_fixture_results_are_not_market_evidence=True,
        protected_heads_unchanged=all(sha(p)==s for p,s in protected_before.items()),
        data_head_moved=False,stage_head_moved=False,dev_head_moved=False,tdx_root_write_count=0,
        external_acceptance='PENDING',next_stage='SUPPLY_EXACT_DATED_ACCEPTED_SOURCE_FREEZE_OR_INDEPENDENTLY_AUTHORIZE_A_SOURCE_REMEDIATION_CONTRACT')
    atomic_json(report/'DM01_A01_REAL_NEXT_SESSION_CANDIDATE_R1.json',result)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--context',type=Path);p.add_argument('--staging-root',type=Path,default=ROOT/'data/v4/dm01_candidate_staging_r1');a=p.parse_args()
    registry=validate_incremental_registry(project_root=ROOT)
    if registry['status']!='PASS_ENGINEERING_EXPORTS':raise ValueError(registry)
    if a.context:
        c=json.loads(a.context.read_text(encoding='utf8'))
        result=build_candidate(parent_data_head=c['parent_data_head'],source_freeze=c['source_freeze'],calendar_binding=c['calendar_binding'],
            identity_binding=c['identity_binding'],staging_root=a.staging_root,head_paths=[ROOT/'data/v4'/n for n in
                ('V4_DATA_ACCEPTED_HEAD.json','V4_STAGE_ACCEPTED_HEAD.json','V4_DEV_BASELINE_HEAD.json')])
    else:result=real_probe()
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status'].startswith(('DM01_A01','NOOP_')) else 2

if __name__=='__main__':raise SystemExit(main())
