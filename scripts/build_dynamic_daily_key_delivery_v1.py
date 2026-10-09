"""Deliver bounded key results as loose files and a small optional ZIP."""
from pathlib import Path
import json,sys,os,tempfile,zipfile,hashlib,subprocess,urllib.request,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.daily_source_freeze import ensure_outside_tdx
from workbench_analysis.tdx_official_daily_source import sha256_file
E=ROOT/'docs/evidence/dynamic_daily_20261009'
OUT=Path('D:/Users/lps/Desktop/阶段任务/DD01-DD07_关键交付_20261009')

def write(path,data):
    path=Path(path).resolve()
    contract=json.loads((ROOT/'config/dm01_go_forward_runtime_contract_r4r1.json').read_bytes())
    for source in ['D:/new_tdx',*contract.get('read_only_tdx_roots',[])]:ensure_outside_tdx(path,Path(source))
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)

def build():
    with urllib.request.urlopen('http://127.0.0.1:28765/api/v4/operations/daily-update/status',timeout=30) as response:status=json.load(response)
    assert status['last_good_trade_date']=='2026-10-09' and status['settings']['auto_enabled'] and status['settings']['service_alive']
    assert status['last_catch_up_job']['status']=='PUBLISHED_FULL'
    oracle=json.loads((E/'DD07_REAL_20261009_PERIOD_NUMERIC_ORACLE.json').read_bytes())
    deterministic=json.loads((E/'DD07_FULL_FROZEN_REBUILD_DETERMINISM.json').read_bytes())
    tests=json.loads((E/'DD07_TARGETED_TEST_RECEIPT.json').read_bytes())
    result=dict(contract_id='DD01_DD07_KEY_DELIVERY_V1',acceptance='PASS_ALL_SEVEN_ENGINEERING',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        formal_cutoff='2026-10-09',auto_enabled=True,service_alive=True,next_trigger_at=status['next_trigger_at'],
        job_id=status['last_catch_up_job']['job_id'],job_status='PUBLISHED_FULL',published_at=status['last_catch_up_job']['finished_at'],
        operational_head_sha256=sha256_file(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),
        strict_0930_head_sha256=sha256_file(ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json'),
        official_zip_sha256='635c775940b2efdb8c9779c9898306c475822517f072c0eddcec8273b14e7ad6',
        source_counts=dict(tdx_actual_target_rows=5559,baostock_daily_rows=5224,baostock_factor_rows=8,accepted_universe=5224,traded=5210,suspended=14),
        qa=dict(core_dates=5,core_errors=0,period_checks=oracle['checks'],period_errors=len(oracle['errors']),
            frozen_rebuild_files=deterministic['files'],frozen_rebuild_differences=len(deterministic['differences']),tests=tests['tests'],failures=tests['failures'],errors=tests['errors']),
        browser=dict(name='Codex In-app Browser',user_override=True,widths=[1366,1920]),
        actual_service_restart='PASS_AFTER_COMMITTED_CAS',actual_windows_reboot='NOT_PERFORMED',external_acceptance='NOT_GRANTED',
        separate_open_audits=['Amount representation differences: 4946; historical Amount A remains open','Rotation/Forward independent acceptance and original FP page gaps unchanged'],
        delivery_scope='Key report, actual release/source/QA/restart/test receipts and screenshots only; bulk numerical API upload stopped by user; manual web upload is user-owned',
        git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    atomic_json(ROOT,E/'DD07_KEY_DATA.json',result)
    names=['DYNAMIC_DAILY_FINAL_DELIVERY.md','DYNAMIC_DAILY_EXTERNAL_AUDIT.md','DD07_KEY_DATA.json',
        'DD07_REAL_20261009_RELEASE_READBACK.json','DD07_REAL_POST_CAS_SERVICE_RESTART.json',
        'DD07_REAL_20261009_PERIOD_NUMERIC_ORACLE.json','DD03_REAL_20261009_CORE_QA.json',
        'DD03_REAL_20261009_PROFILE_SECTOR_MARKET.json','DD07_TARGETED_TEST_RECEIPT.json',
        'DD07_FULL_FROZEN_REBUILD_DETERMINISM.json','INDEPENDENT_AUDIT_ITEMS.md',
        'DD07_REAL_20261009_PUBLISHED_1366.png','DD07_REAL_20261009_PUBLISHED_1920.png','DD07_REAL_20261009_WORKBENCH.png']
    payload=[]
    for name in names:
        data=(E/name).read_bytes();destination=OUT/('README.md' if name=='DYNAMIC_DAILY_FINAL_DELIVERY.md' else name)
        write(destination,data);payload.append(dict(name=destination.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    manifest=dict(contract_id='DD07_KEY_FILES_MANIFEST_V1',payload=payload,git_sha=result['git_sha'],scope=result['delivery_scope'],external_acceptance='NOT_GRANTED')
    write(OUT/'KEY_FILES_MANIFEST.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    final=OUT/'DD01-DD07_关键交付.zip';tmp=OUT/'DD01-DD07_关键交付.tmp'
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as archive:
        for row in payload:archive.write(OUT/row['name'],row['name'])
        archive.write(OUT/'KEY_FILES_MANIFEST.json','KEY_FILES_MANIFEST.json')
    with zipfile.ZipFile(tmp) as archive:
        assert archive.testzip() is None
        for row in payload:
            data=archive.read(row['name']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    os.replace(tmp,final)
    receipt=dict(contract_id='DD07_USER_KEY_DELIVERY_LOCAL_RECEIPT_V1',acceptance='PASS_KEY_DATA_LOOSE_FILES_AND_ZIP_CRC_SHA256',
        path=str(final),bytes=final.stat().st_size,sha256=sha256_file(final),folder=str(OUT),file_count=len(payload)+1,git_sha=result['git_sha'],
        operational_head_sha256=result['operational_head_sha256'],scope=result['delivery_scope'],external_acceptance='NOT_GRANTED',next_stage='USER_OPTIONAL_MANUAL_WEB_UPLOAD_AND_INDEPENDENT_AUDIT')
    atomic_json(ROOT,E/'DD07_KEY_DELIVERY_LOCAL_RECEIPT.json',receipt);print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':build()
