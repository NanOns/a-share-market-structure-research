"""Prepare a new immutable R6 native Joint; do not move the active pointer."""
import hashlib,json,os,psutil,sys
from pathlib import Path

ROOT=Path(r'G:\codex work\v4-production-20261012')
SOURCE=Path(__file__).resolve().parents[1]

def inherit_live_environment():
    for process in psutil.process_iter(['pid','name','cmdline']):
        try:
            argv=process.info.get('cmdline') or []
            if (process.info.get('name') or '').lower()=='daav4.exe' and '--port' in argv and argv[argv.index('--port')+1]=='28765':
                env=process.environ()
                for key in ('V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN'):os.environ[key]=env[key]
                return process.info['pid']
        except (psutil.Error,ValueError,IndexError,KeyError):pass
    raise RuntimeError('LIVE_28765_CONTROLLED_PG_ENVIRONMENT_UNAVAILABLE')

def main():
    pid=inherit_live_environment();sys.path[:0]=[str(SOURCE/'src'),str(SOURCE),str(ROOT/'src'),str(ROOT)]
    from workbench_analysis.r43_owner_replay import ref,checked
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_service.native_current_snapshot_v3 import prepare_joint,validate_joint
    head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    reader=OperationalSuccessorReaderV1(ROOT,head);candidate=reader.candidate
    source_map={
      'api.js':SOURCE/'src/workbench_service/static/core-product-r1/api.js',
      'app.js':SOURCE/'src/workbench_service/static/core-product-r1/app.js',
      'components.js':SOURCE/'src/workbench_service/static/core-product-r1/components.js',
      'index.html':SOURCE/'src/workbench_service/static/research/index.html',
      'labels.js':SOURCE/'src/workbench_service/static/core-product-r1/labels.js',
      'replay.js':SOURCE/'src/workbench_service/static/core-product-r1/replay.js',
      'stock.js':SOURCE/'src/workbench_service/static/core-product-r1/stock.js',
      'style.css':SOURCE/'src/workbench_service/static/research/style.css'}
    assets={};payload={}
    for name,path in source_map.items():
        raw=path.read_bytes();payload[name]=raw
        assets[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    release_id=hashlib.sha256(json.dumps(assets,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    from workbench_service.v4_daily_refresh import atomic_bytes
    for name,raw in payload.items():
        target=ROOT/'data/v4/ui_releases_r6'/release_id/name
        if target.exists() and target.read_bytes()!=raw:raise ValueError('R6_UI_RELEASE_IMMUTABLE_CONFLICT:'+name)
        if not target.exists():atomic_bytes(target,raw)
        assets[name].update(path=target.relative_to(ROOT).as_posix())
    reconciliation=ROOT/'data/v4/engineering_series_source_reconciliations_r1/eec0177b3e932eab553cc16383d24b9f98b5e0629cfcc583dca2f64326723694/SOURCE_RECONCILIATION.json'
    record=json.loads(reconciliation.read_bytes())
    if record.get('contract_id')!='V4_ENGINEERING_SERIES_SOURCE_RECONCILIATION_R1':raise ValueError('R6_SERIES_RECONCILIATION_REQUIRED')
    binding=ref(ROOT,reconciliation)
    joint_binding=prepare_joint(ROOT,candidate,ui_assets=assets,source_reconciliation=binding,verify_loaded=False)
    joint=json.loads(checked(ROOT,joint_binding).read_bytes());validate_joint(ROOT,joint,candidate,verify_loaded=False)
    active=ROOT/'config/v4_current_native_joint_authority_v3.json'
    active_before=active.read_bytes()
    report=dict(contract_id='V4_R6_NATIVE_JOINT_CANDIDATE_R1',acceptance='PASS_NEW_CURRENT_TOKEN_JOINT_CANDIDATE',
      production_root=str(ROOT),live_service_pid=pid,T0=joint['T0'],business_token=joint['business_token'],
      active_joint_before_sha256=hashlib.sha256(active_before).hexdigest(),active_pointer_changed=False,
      candidate_joint=joint_binding,ui_release_id=release_id,ui_assets=assets,source_reconciliation=binding,
      snapshot=joint['snapshot'],full_joint_validation='PASS_SOURCE_AND_PG',frozen_runtime_loaded_source_check='DEFERRED_TO_BUILT_EXE_STARTUP',head_changed=False,auto_daily_changed=False)
    out=SOURCE/'reports/audits/v4_r6_closeout_20261014/NATIVE_JOINT_CANDIDATE.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'acceptance':report['acceptance'],'T0':report['T0'],'token':report['business_token'],
      'candidate_joint':joint_binding['path'],'ui_release_id':release_id,'active_pointer_changed':False},ensure_ascii=False))

if __name__=='__main__':main()
