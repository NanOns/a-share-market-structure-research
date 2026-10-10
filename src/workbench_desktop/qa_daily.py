"""Actual archived-input full daily pipeline under an explicit replay contract."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import shutil
import sys
import time
from .storage import atomic, WorkspaceLease, verify_resources
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
    started=datetime.now(timezone.utc).isoformat()
    controller=EngineController(root,port=0)
    progress_path=root/'QA_DAILY_PROGRESS.json'
    def progress(day,stage,detail):
        stages.append(dict(stage=stage,observed_at=datetime.now(timezone.utc).isoformat()))
        atomic(progress_path,dict(stage=stage,detail=detail,stages=stages,started_at=started,
                                  evidence_kind='ARCHIVED_SOURCE_REPLAY', first_capture_claim=False))
    def capture(*,snapshot_root,**kwargs):
        package=copy.deepcopy(original['effective_package'])
        source_root=Path(request['source_workspace']).resolve()
        archive=Path(package['download']['path'])
        relative=archive.relative_to(source_root)
        source=root/relative
        if sha256_file(source)!=package['download']['sha256']:
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
    scope=private_scope(daily,dict(capture_latest_tdx_package=capture))
    result=None
    with WorkspaceLease(root):
        try:
            controller.settings(False)
            controller.perform('start')
            result=scope['execute_sources'](root,request['target_session'],'CATCH_UP',capture_only=True,progress=progress)
            progress(request['target_session'],'CAPTURE_AND_READINESS_RESULT',result)
            if not result.get('source_ready'):
                raise ValueError('REPLAY_SOURCE_READINESS_NOT_READY:'+result.get('reason',result.get('status','UNKNOWN')))
            result=daily.derive_ready_sources(root,request['target_session'],result,
                                             readback_url=f'http://127.0.0.1:{controller.port}',progress=progress)
            transaction=json.loads((root/'runtime/dynamic_daily/publication_transaction.json').read_bytes())
            if result.get('status')!='PUBLISHED' or transaction['state']!='COMMITTED':
                raise ValueError('REPLAY_NOT_COMMITTED')
            from workbench_analysis.operational_successor_release_v1 import recover
            committed=head.read_bytes();recover(root)
            if head.read_bytes()!=committed:raise ValueError('COMMITTED_HEAD_CHANGED_ON_RECOVERY')
            progress(request['target_session'],'COMMITTED',dict(head_sha256=sha256_file(head),result=result))
            return dict(status='PASS',contract_id='V4_FROZEN_ARCHIVED_DAILY_PIPELINE_V1',
                evidence_kind='ARCHIVED_SOURCE_REPLAY_ACTUAL_NUMERIC_DERIVE_ORIGINAL_ADMISSION',
                FROZEN_EXE_END_TO_END_PASS=True, failure_matrix_complete=False,
                executable=sys.executable,executable_sha256=sha256_file(Path(sys.executable)),
                manifest=verify_resources(),workspace=str(root),started_at=started,
                finished_at=datetime.now(timezone.utc).isoformat(),stages=stages,
                predecessor_sha256=hashlib.sha256(original_head).hexdigest(),head_sha256=sha256_file(head),
                transaction=transaction,result=result,first_capture_claim=False,production_written=False,
                external_acceptance='NOT_GRANTED')
        except Exception as exc:
            progress(request['target_session'],'FAILED',dict(reason=str(exc),result=result))
            raise
        finally:
            if controller.state!='STOPPED':controller.perform('stop')
