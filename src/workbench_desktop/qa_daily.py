"""Actual archived-input full daily pipeline under an explicit replay contract."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import sys
import time
from .storage import atomic, WorkspaceLease, verify_resources, frozen_module_evidence
from .engine import EngineController


def run(root):
    root=Path(root).resolve()
    prefix=Path('G:/codex_tmp/test_temp').resolve()
    request=json.loads((root/'ISOLATED_PACKAGE_QA.json').read_bytes())
    if root==prefix or not root.is_relative_to(prefix) or request.get('evidence_kind')!='ARCHIVED_SOURCE_REPLAY':
        raise ValueError('ISOLATED_ARCHIVE_REPLAY_REQUIRED')
    if not getattr(sys,'frozen',False):
        raise ValueError('ACTUAL_FROZEN_EXECUTABLE_REQUIRED')
    from workbench_analysis.r43_owner_replay import checked
    from workbench_analysis.tdx_official_daily_source import sha256_file
    from workbench_analysis import operational_daily_executor_v1 as daily
    from workbench_analysis.operational_owner_adapter_v1 import private_scope
    original=json.loads(checked(root,request['source_freeze']).read_bytes())
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    original_head=head.read_bytes()
    stages=[]
    faults=[]
    started=datetime.now(timezone.utc).isoformat()
    controller=EngineController(root,port=0)
    progress_path=root/'QA_DAILY_PROGRESS.json'
    def progress(day,stage,detail):
        stages.append(dict(stage=stage,observed_at=datetime.now(timezone.utc).isoformat()))
        atomic(progress_path,dict(stage=stage,detail=detail,stages=stages,started_at=started,
                                  evidence_kind='ARCHIVED_SOURCE_REPLAY', first_capture_claim=False))
    def capture(*,snapshot_root,**kwargs):
        if injection['mode']=='TIMEOUT':
            raise TimeoutError('EXPLICIT_REPLAY_SOURCE_TIMEOUT')
        package=copy.deepcopy(original['effective_package'])
        source_root=Path(request['source_workspace']).resolve()
        archive=Path(package['download']['path'])
        relative=archive.relative_to(source_root)
        source=root/relative
        expected='0'*64 if injection['mode']=='BAD_SHA' else package['download']['sha256']
        if sha256_file(source)!=expected:
            raise ValueError('ARCHIVE_SOURCE_SHA_MISMATCH')
        destination=Path(snapshot_root)/'package_replay_capture'/str(time.time_ns())/'hsjday.zip'
        destination.parent.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(source,destination)
        if sha256_file(destination)!=package['download']['sha256']:
            raise ValueError('REPLAY_CAPTURE_OUTPUT_SHA_MISMATCH')
        package['download']['path']=str(destination)
        package['observed_at']=datetime.now(timezone.utc).isoformat()
        package['downloaded_at']=package['observed_at']
        package['replay_evidence']=dict(contract_id='V4_EXPLICIT_ARCHIVE_CAPTURE_REPLAY_V1',
            original_source_freeze=request['source_freeze'], original_observed_at=request['original_observed_at'],
            replay_captured_at=package['observed_at'], first_capture_claim=False,
            transport='LOCAL_IMMUTABLE_ARCHIVE_COPY_SHA_VERIFIED_NO_NETWORK')
        progress(request['target_session'],'ARCHIVE_CAPTURED',package['replay_evidence'])
        return package
    scope=None
    injection=dict(mode='NONE')
    checkpoint=root/'QA_DAILY_SEALED_CANDIDATE.json'
    result=None
    with WorkspaceLease(root):
        try:
            controller.settings(False)
            controller.perform('start')
            from v4 import confirmation_d2_candidate_r5 as d2,confirmation as d0
            from v4.stock_prewatch import load_package as prewatch_package
            # Front-load every original Focus prerequisite before the costly
            # full rebuild. These are the original SHA/AST/package validators.
            d2.adapter_ast_evidence();d0.package();prewatch_package(root)
            from urllib.request import urlopen
            with urlopen(f'http://127.0.0.1:{controller.port}/v4',timeout=10) as response:html=response.read()
            with urlopen(f'http://127.0.0.1:{controller.port}/v4/assets/desktop_status.js',timeout=10) as response:banner=response.read()
            if b'/v4/assets/desktop_status.js' not in html or b'CAPTURE_REQUIRES_APP_RUNNING' not in banner or controller.status()['auto_daily_enabled'] is not False:
                raise ValueError('REAL_PACKAGED_PAGE_CAPTURE_CONDITION_OR_PAUSE_STATUS_MISSING')
            from .source_adapter import executor
            packaged_executor=executor(root)
            scope=private_scope(daily,dict(capture_latest_tdx_package=capture,
                __builtins__=packaged_executor.__globals__['__builtins__']))
            from workbench_analysis import operational_successor_release_v1 as release
            from workbench_analysis.operational_daily_http_readback_v1 import readback
            if checkpoint.exists():
                saved=json.loads(checkpoint.read_bytes())
                if saved['executable_sha256']!=sha256_file(Path(sys.executable)):
                    raise ValueError('REPLAY_RESUME_EXE_IDENTITY_CHANGED')
                if sha256_file(head)!=saved['predecessor_sha256']:
                    raise ValueError('CRASH_RECOVERY_DID_NOT_RESTORE_PREDECESSOR')
                original_head=head.read_bytes()
                faults=saved['faults']+[dict(name='ACTUAL_PROCESS_CRASH_PENDING_AND_NEXT_EXE_RECOVER',status='PASS')]
                stages=saved['stages'];started=saved['started_at']
                result=saved['result']
                candidate=json.loads(checked(root,saved['candidate']).read_bytes())
                progress(request['target_session'],'CRASH_RECOVERED',dict(head_sha256=sha256_file(head)))
            else:
                # Durable original retry classifier/limit; only source transport
                # and clock are controlled. The main head is checked throughout.
                from workbench_analysis import operational_daily_jobs_v1 as jobs_module
                target_day=datetime.fromisoformat(str(request['target_session'])).date()
                predecessor_day=json.loads(original_head).get('accepted_trade_date')
                if not predecessor_day:raise ValueError('REPLAY_PREDECESSOR_TRADE_DATE_REQUIRED')
                plan=dict(status='TIME_ELIGIBLE',requested_through_date=request['target_session'],
                    missing_sessions=[request['target_session']],eligible_sessions=[request['target_session']],
                    last_good_trade_date=str(predecessor_day))
                Job=private_scope(jobs_module,dict(gap_plan=lambda *a,**k:dict(plan)))['DailyJobs']
                now=[datetime.fromisoformat(f"{target_day.isoformat()}T22:10:00+08:00")]
                injection['mode']='TIMEOUT'
                worker=Job(root/'fault_source_timeout',executor=lambda *_:scope['execute_sources'](root,request['target_session'],'CATCH_UP',capture_only=True),clock=lambda:now[0])
                worker.settings(False);job=worker.enqueue()
                for attempt in range(8):
                    worker.tick();record=worker.job(job)
                    if record['days'][0]['next_retry_at']:
                        now[0]=datetime.fromisoformat(record['days'][0]['next_retry_at'])+timedelta(seconds=1)
                if record['status']!='FAILED_TERMINAL' or record['days'][0]['attempt_count']!=8 or head.read_bytes()!=original_head:
                    raise ValueError('BOUNDED_SOURCE_RETRY_PROOF_FAILED')
                faults.append(dict(name='SOURCE_TIMEOUT_BOUNDED_EIGHT_ATTEMPTS',status='PASS',job=record))
                injection['mode']='BAD_SHA'
                worker=Job(root/'fault_source_sha',executor=lambda *_:scope['execute_sources'](root,request['target_session'],'CATCH_UP',capture_only=True),clock=lambda:now[0])
                worker.settings(False);job=worker.enqueue();worker.tick();record=worker.job(job)
                if record['status']!='QA_BLOCKED' or record['days'][0]['next_retry_at'] or head.read_bytes()!=original_head:
                    raise ValueError('DETERMINISTIC_SOURCE_FAILURE_PROOF_FAILED')
                faults.append(dict(name='SOURCE_SHA_BLOCK_NO_BLIND_RETRY',status='PASS',job=record))
                injection['mode']='NONE'
                result=scope['execute_sources'](root,request['target_session'],'CATCH_UP',capture_only=True,progress=progress)
                progress(request['target_session'],'CAPTURE_AND_READINESS_RESULT',result)
                if not result.get('source_ready'):
                    raise ValueError('REPLAY_SOURCE_READINESS_NOT_READY:'+result.get('reason',result.get('status','UNKNOWN')))
                # Derive once using the original numeric/period gates, stopping
                # at the existing no-readback boundary to test the sealed CAS.
                result=daily.derive_ready_sources(root,request['target_session'],result,progress=progress)
                if result.get('reason')!='LIVE_SERVICE_READBACK_ENDPOINT_REQUIRED':
                    raise ValueError('REPLAY_DERIVE_DID_NOT_REACH_SEALED_CANDIDATE')
                candidate=json.loads(checked(root,result['candidate']).read_bytes())
                try:
                    release.promote(root,candidate,'0'*64,lambda _:None)
                except ValueError as exc:
                    if 'STALE_OPERATIONAL' not in str(exc) or head.read_bytes()!=original_head:raise
                else:raise ValueError('REAL_CANDIDATE_STALE_CAS_ACCEPTED')
                faults.append(dict(name='REAL_NUMERIC_CANDIDATE_CAS_CONFLICT_NO_WRITE',status='PASS'))
                try:
                    release.promote(root,candidate,sha256_file(head),lambda _:dict(status='PASS',context_token='wrong'))
                except ValueError as exc:
                    if 'HTTP_SAME_TOKEN' not in str(exc) or head.read_bytes()!=original_head:raise
                else:raise ValueError('BAD_READBACK_ACCEPTED')
                faults.append(dict(name='REAL_CANDIDATE_READBACK_FAILURE_EXACT_ROLLBACK',status='PASS'))
                saved=dict(result=result,candidate=result['candidate'],faults=faults,stages=stages,started_at=started,
                    predecessor_sha256=sha256_file(head),executable_sha256=sha256_file(Path(sys.executable)))
                atomic(checkpoint,saved)
                def crash_after_cas(_):
                    progress(request['target_session'],'CRASH_PENDING',dict(expected_exit_code=70))
                    os._exit(70)
                release.promote(root,candidate,sha256_file(head),crash_after_cas)
                raise ValueError('INTENTIONAL_CRASH_DID_NOT_EXIT')
            publication=release.promote(root,candidate,sha256_file(head),
                lambda value:readback(f'http://127.0.0.1:{controller.port}',value))
            result=dict(result,**publication,source_ready=True,derived_ready=True,published=True)
            transaction=json.loads((root/'runtime/dynamic_daily/publication_transaction.json').read_bytes())
            if result.get('status')!='PUBLISHED' or transaction['state']!='COMMITTED':
                raise ValueError('REPLAY_NOT_COMMITTED')
            from workbench_analysis.operational_successor_release_v1 import recover
            committed=head.read_bytes();recover(root)
            if head.read_bytes()!=committed:raise ValueError('COMMITTED_HEAD_CHANGED_ON_RECOVERY')
            progress(request['target_session'],'COMMITTED',dict(head_sha256=sha256_file(head),result=result))
            return dict(status='PASS',contract_id='V4_FROZEN_ARCHIVED_DAILY_PIPELINE_V1',
                evidence_kind='ARCHIVED_SOURCE_REPLAY_ACTUAL_NUMERIC_DERIVE_ORIGINAL_ADMISSION',
                FROZEN_EXE_END_TO_END_PASS=True, failure_matrix_complete=True,failure_matrix=faults,
                executable=sys.executable,executable_sha256=sha256_file(Path(sys.executable)),
                manifest=verify_resources(),workspace=str(root),started_at=started,
                packaged_home_capture_notice_present=True,paused_daily_status_verified=True,
                loaded_local_modules=frozen_module_evidence(),development_module_fallback_used=False,
                approved_original_source_introspection='Manifest-bound package originals supplied to unchanged Rotation evaluator; its existing versioned source transformation remains authoritative',
                finished_at=datetime.now(timezone.utc).isoformat(),stages=stages,
                predecessor_sha256=hashlib.sha256(original_head).hexdigest(),head_sha256=sha256_file(head),
                transaction=transaction,result=result,first_capture_claim=False,production_written=False,
                external_acceptance='NOT_GRANTED')
        except Exception as exc:
            progress(request['target_session'],'FAILED',dict(reason=str(exc),result=result))
            raise
        finally:
            if controller.state!='STOPPED':controller.perform('stop')
