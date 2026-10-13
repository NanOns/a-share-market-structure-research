"""Read-only production observation and independent final-delivery reconciliation."""
import csv, gzip, hashlib, json, os, shutil, subprocess, sys, urllib.request, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/audits/v4_full_closeout_20261012/continuation_20261013'
OUT=BASE/'PRODUCTION_INDEPENDENT_AUDIT_FOLLOWUP_R1'
DESKTOP=BASE/'WINDOWS_PRODUCTION_CUTOVER_R4'
RUNTIME=Path('G:/codex work/v4-production-20261012')
DELIVERY=Path('G:/codex_tmp/V4_R4_R3_FINAL_DELIVERY/V4_FULL_CLOSEOUT_FINAL_20261013')
sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    raw=v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf8')
    t=p.with_name(p.name+'.tmp');t.write_bytes(raw);os.replace(t,p)

def get(route):
    o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with o.open('http://127.0.0.1:28765'+route,timeout=90) as r:return r.status,r.read()

def observe(label):
    import psutil
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_db.v4_native import connection,workspace_schema
    folder=OUT/label;assert not folder.exists();folder.mkdir(parents=True)
    reads={}
    for name,route in [('daily','/api/v4/operations/daily-update/status'),('desktop','/api/v4/desktop/status'),('context','/api/v4/context')]:
        code,raw=get(route);write(folder/(name+'.json'),raw);reads[name]=json.loads(raw);assert code==200
    process=psutil.Process(reads['desktop']['pid'])
    listeners=[c.pid for c in psutil.net_connections('tcp') if c.status=='LISTEN' and c.laddr.port==28765]
    credentials=load_credentials(RUNTIME/'config/native_pg_roles.dpapi')
    with connection(workspace_schema(RUNTIME,'jobs'),dsn=credentials[ROLES[1]],read_only=True) as pg:
        identity=list(pg.execute('SELECT current_user,current_database(),inet_server_port(),current_setting(\'transaction_read_only\')').fetchone())
        tables={}
        for name in ['scheduler_policy','scheduler_dispatch','scheduler_attempts','source_probe_state','update_jobs','update_job_days','update_events']:
            rows=pg.execute('SELECT * FROM '+name).fetchall()
            tables[name]=[list(r) for r in rows]
    write(folder/'PG_SCHEDULER_SELECT_ONLY.json',dict(identity=identity,schema=workspace_schema(RUNTIME,'jobs'),tables=tables,read_only=True))
    heads={p:sha(RUNTIME/p) for p in ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','config/v4_current_native_joint_authority_v3.json']}
    result=dict(observed_at=datetime.now(timezone.utc).isoformat(),pid=process.pid,executable=process.exe(),command=process.cmdline(),started_at=datetime.fromtimestamp(process.create_time(),timezone.utc).isoformat(),listeners=listeners,package=reads['desktop']['BUILD_RELEASE_ID'],source_sha=reads['desktop']['SOURCE_SHA'],T0=reads['context']['context']['trade_date'],token=reads['context']['context_token'],heads=heads,daily=reads['daily'],pg_identity=identity)
    assert listeners==[process.pid] and result['source_sha']=='fe11c18cfdf75e9b0713b43a57139672792df8e11c5002fd67754a26af930744'
    assert identity==[ROLES[1],'market_research',5432,'on']
    write(folder/'RESULT.json',result)
    print(json.dumps(dict(label=label,T0=result['T0'],daily_status=reads['daily']['status'],last_job=reads['daily'].get('last_job'),worker_error=reads['daily'].get('worker_error')),default=str),flush=True)

def reconcile():
    OUT.mkdir(exist_ok=True)
    rows=list(csv.DictReader((DELIVERY/'01_CURRENT_ISSUES_MATRIX.csv').open(encoding='utf-8-sig')))
    fixes={'FA-013','FA-014'}
    for r in rows:
        if r['id'] in fixes:
            p=DESKTOP/'IAB_PRODUCTION_R4/RESULT.json';r['evidence']=str(p);r['evidence_sha256']=sha(p)
        if r['evidence']:
            p=Path(r['evidence']);assert p.is_file(),str(p)
            assert sha(p)==r['evidence_sha256'],r['id']
            if p.is_relative_to(ROOT):r['evidence']=p.relative_to(ROOT).as_posix()
    assert len(rows)==len({r['id'] for r in rows})==39
    counts=dict(Counter(r['status'] for r in rows))
    assert counts=={'CURRENT_PRODUCTION_GATE_PASS':33,'FUTURE_DATA_WATCH':3,'HISTORICAL_ONLY':3}
    target=BASE/'AUDIT_MATRIX_R4';target.mkdir(exist_ok=True)
    t=target/'MATRIX.csv.tmp'
    with t.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    os.replace(t,target/'MATRIX.csv')
    write(target/'RESULT.json',dict(contract_id='V4_ALL39_FINAL_EVIDENCE_RECONCILIATION_R4',acceptance='PASS_CURRENT_SCOPED_EVIDENCE_BINDINGS',counts=counts,all_evidence_sha256_verified=True,full_product_release=False,external_acceptance=False))
    manifest=json.loads((DELIVERY/'09_SHA256_MANIFEST.json').read_bytes())
    for r in manifest['files']:
        assert sha(DELIVERY/r['relative_path'])==r['sha256']
    archive=DELIVERY.with_suffix('.zip')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for r in manifest['files']:
            assert hashlib.sha256(z.read(DELIVERY.name+'/'+r['relative_path'])).hexdigest()==r['sha256']
    xml=ET.parse(DELIVERY/'02_LEGAL_FULL_TESTS.xml')
    cases=xml.findall('.//testcase');counts_xml=dict(total=len(cases),skipped=sum(c.find('skipped') is not None for c in cases),failures=sum(c.find('failure') is not None for c in cases),errors=sum(c.find('error') is not None for c in cases))
    assert counts_xml==dict(total=7288,skipped=63,failures=0,errors=0)
    write(OUT/'EXISTING_DELIVERY_READBACK_R1.json',dict(contract_id='V4_FINAL_DELIVERY_CRC_SHA_XML_READBACK_R1',acceptance='PASS',archive=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,manifest_files=len(manifest['files']),xml=counts_xml,matrix=counts,crc=True))
    print(json.dumps(dict(matrix=counts,xml=counts_xml,archive_sha256=sha(archive))))

def business():
    latest=json.loads((OUT/'AFTER_1835_R1/RESULT.json').read_bytes())
    token=latest['token'];day=latest['T0'];records=[]
    from urllib.parse import urlencode
    for name in ['context','home','stocks','sectors','focus','market','diagnostics']:
        code,raw=get('/api/v4/'+name+'?'+urlencode(dict(context_token=token,trade_date=day,limit=30)))
        data=json.loads(raw);write(OUT/'HTTP_LAST_GOOD_R1'/(name+'.json.gz'),gzip.compress(raw,mtime=0))
        assert code==200 and data['context_token']==token and data['context']['trade_date']==day
        records.append(dict(route=name,http=code,T0=day,token=token,sha256=hashlib.sha256(raw).hexdigest(),total=data.get('total')))
        print(name,code,flush=True)
    write(OUT/'HTTP_LAST_GOOD_R1/RESULT.json',dict(acceptance='PASS_SEVEN_ROUTES_LAST_GOOD_CONSISTENT',records=records))

def package():
    latest=json.loads((OUT/'AFTER_1835_R1/RESULT.json').read_bytes())
    job=latest['daily']['last_job']
    assert job['trigger']=='SCHEDULER' and job['through_date']=='2026-10-13' and job['status']=='QA_BLOCKED'
    assert job['error']=='SOURCE_EXECUTION_UNPACKAGED_LOCAL_MODULE'
    acceptance=json.loads((DESKTOP/'FINAL_ACCEPTANCE_R4.json').read_bytes())
    assert latest['token']==acceptance['business_token'] and latest['T0']==acceptance['T0']
    assert latest['heads']['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json']==acceptance['business_token']
    item=dict(id='V4-NEW-EXE-REAL-SCHEDULER-20261013-R1',status='BLOCKED_PACKAGED_SOURCE_EXECUTION',scope='Actual new EXE scheduler source capture/derive/publication; separate from accepted 2026-10-12 desktop cutover',evidence='AFTER_1835_R1/PG_SCHEDULER_SELECT_ONLY.json',job=job,source_ready='NOT_VERIFIED_EXECUTION_BLOCKED_BEFORE_READY',head_preserved=True,current_desktop_gate_invalidated=False,acceptance_required='New versioned package must resolve the exact missing import, preserve original bindings, pass packaged real source execution and independent numeric/PG gates, then record real scheduler and seven-route atomic publication readback. Never reclassify current failure as provider WAIT or grant full_product_release.',next_stage='SEPARATE_VERSIONED_PACKAGE_DAILY_REPAIR_GATE',historical_failure='2026-10-12 SOURCE_EXECUTION_FileNotFoundError is a separate retained job')
    write(OUT/'NEW_SEPARATE_AUDIT_ITEM_R1.json',item)
    summary=dict(contract_id='V4_PRODUCTION_INDEPENDENT_AUDIT_FOLLOWUP_R1',stage_contract='User-requested independent audit R1 section 4; latest continuation R2 and accepted Stage6',acceptance='DESKTOP_CUTOVER_AND_DELIVERY_PASS_REAL_DAILY_BLOCKED',observed_at=latest['observed_at'],matrix='AUDIT_MATRIX_R4/MATRIX.csv',inherited_39=dict(current_scoped=33,historical_only=3,future_watch=3),new_independent_audit_item=item['id'],real_scheduled_success=False,production_head_preserved=True,full_product_release=False,PIT_ELIGIBLE=False,AS_RECORDED=False,next_stage=item['next_stage'])
    write(OUT/'RESULT.json',summary)
    report=('# 生产独立审计 R1 处理结果\n\n合同：用户指定 2026-10-13 独立审计 R1 第4节；最新续行 R2 与 Stage6 已接受范围。\n\n验收：桌面切换与交付核验通过，真实自动日更 BLOCKED。\n\n18:35:04 新 EXE/PID 34828 的 PostgreSQL 调度生成 2026-10-13 新任务；18:35:05 以 SOURCE_EXECUTION_UNPACKAGED_LOCAL_MODULE 进入 QA_BLOCKED。不是 BaoStock factor 已核实未 ready，也不是10月12日旧 FileNotFoundError。Windows 启动任务实际在17:55:50运行，18:35为该进程内部15秒轮询PG worker调度，不虚称 Windows 任务再次触发。实际源读取和发布未完成，首获/PIT/成熟仍未获准。\n\n10月12日 last-good Head/token 保持不变，七路 GET 同日期/token 返回200。新失败独立登记 V4-NEW-EXE-REAL-SCHEDULER-20261013-R1，不抹去原桌面切换，也不能把39项原有范围通过解释成自动日更通过。\n\n39项最终矩阵已逐项核对证据 SHA；原10条 pending 由冻结全量回归和原端口重启回执收口。33当前范围、3历史排除、3未来观察。FA-013/014 改绑定真实原端口浏览器回执。合法XML 7288：7225通过、63合同跳过、0失败/错误。未重跑已冻结巨量数值或全量测试。\n\n原18:15交付ZIP的CRC、清单SHA、XML已独立读回通过。正式更新包采用任务文档指定目录内同名ZIP；原目录外ZIP保留为18:15历史版本，不代表本次最终包。全产品、预测、交易、性能、正式回滚、移动端未授予/未执行。\n\n下一阶段：单独的版本化安装包日更修复门。当前回执只证明失败层级，尚不能断言具体缺失模块；需保留完整异常模块名并在新包受控复现，通过发布硬门后才能调度重试。保留原任务、原包、原HEAD与现场，无重复源请求或强制重试。\n')
    write(OUT/'STAGE_ACCEPTANCE.md',report.encode('utf8'))
    extra=DELIVERY/'10_INDEPENDENT_AUDIT_FOLLOWUP_R1';assert not extra.exists();shutil.copytree(OUT,extra)
    matrix=DELIVERY/'11_AUDIT_MATRIX_R4';assert not matrix.exists();shutil.copytree(BASE/'AUDIT_MATRIX_R4',matrix)
    write(DELIVERY/'10_LATEST_STATUS_READ_FIRST.md',report.encode('utf8'))
    manifest=[dict(path=p.relative_to(DELIVERY).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(DELIVERY.rglob('*')) if p.is_file()]
    write(DELIVERY/'12_FINAL_MANIFEST_R1.json',dict(contract_id='V4_FINAL_DELIVERY_FOLLOWUP_SHA256_R1',files=manifest,self_excluded=True,archive_excluded=True,acceptance=summary['acceptance']))
    archive=DELIVERY/(DELIVERY.name+'.zip');assert not archive.exists()
    t=archive.with_suffix('.zip.partial')
    files=[p for p in sorted(DELIVERY.rglob('*')) if p.is_file() and p!=t]
    with zipfile.ZipFile(t,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(DELIVERY).as_posix())
    with zipfile.ZipFile(t) as z:
        assert z.testzip() is None
        assert set(z.namelist())=={p.relative_to(DELIVERY).as_posix() for p in files}
        for r in manifest:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
    os.replace(t,archive)
    receipt=dict(contract_id='V4_FINAL_CANONICAL_ZIP_READBACK_R1',acceptance='PASS_CRC_SHA256_MANIFEST_XML',archive=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,files=len(files),all_hashes_verified=True,crc=True,real_daily_status='BLOCKED_PACKAGED_SOURCE_EXECUTION',historical_sibling_zip_preserved=True)
    write(OUT/'FINAL_DELIVERY_RECEIPT_R1.json',receipt)
    write(DELIVERY/'FINAL_DELIVERY_RECEIPT_R1.json',receipt)
    print(json.dumps(receipt))

if __name__=='__main__':
    if sys.argv[1]=='observe':observe(sys.argv[2])
    elif sys.argv[1]=='reconcile':reconcile()
    elif sys.argv[1]=='business':business()
    elif sys.argv[1]=='package':package()
