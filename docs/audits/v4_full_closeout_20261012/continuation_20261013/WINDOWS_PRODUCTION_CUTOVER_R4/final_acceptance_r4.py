import os,sys,json,hashlib,urllib.request
from pathlib import Path
from datetime import datetime,timezone
import psutil
source=Path('G:/codex work/v4-full-closeout-20261012');sys.path[:0]=[str(source),str(source/'src')]
base=Path(__file__).parent;runtime=Path('G:/codex work/v4-production-20261012')
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
regression=load(source/'docs/audits/v4_full_closeout_20261012/continuation_20261013/FINAL_REGRESSION_R4/RESULT.json')
restart=load(base/'ACTUAL_ORIGINAL_PORT_RESTART_R4.json');start=load(base/'ACTUAL_ORIGINAL_PORT_START_R4.json');business=load(base/'PRODUCTION_HTTP_AFTER_RESTART_R4/RESULT.json');iab=load(base/'IAB_PRODUCTION_R4/RESULT.json')
assert regression['acceptance']=='PASS_COMPLETE_FROZEN_LEGAL_REGRESSION' and restart['acceptance']=='PASS_RESTART_IDENTITY_AND_AUTO_DAILY' and business['acceptance']=='PASS' and iab['acceptance']=='PASS_REAL_ORIGINAL_PORT_IAB_SIX_ENTRIES'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
 with opener.open('http://127.0.0.1:28765'+path,timeout=60) as r:return json.load(r)
status=get('/api/v4/desktop/status');context=get('/api/v4/context');daily=get('/api/v4/operations/daily-update/status')
assert status['engine_state']=='RUNNING' and status['auto_daily_enabled'] is True
assert status['SOURCE_SHA']=='fe11c18cfdf75e9b0713b43a57139672792df8e11c5002fd67754a26af930744'
assert status['pid']==restart['after']['pid'] and context['context_token']==start['context_token'] and context['context']['trade_date']=='2026-10-12'
listeners=[c for c in psutil.net_connections('tcp') if c.status=='LISTEN' and c.laddr.port==28765];assert len(listeners)==1 and listeners[0].pid==status['pid']
process=psutil.Process(status['pid']);assert Path(process.exe()).resolve()==Path(start['executable']).resolve()
head=load(runtime/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_db.v4_native import connection,workspace_schema
dsn=load_credentials(runtime/'config/native_pg_roles.dpapi')[ROLES[1]]
with connection(workspace_schema(runtime,'jobs'),dsn=dsn,read_only=True) as pg:
 pg_identity=list(pg.execute('SELECT current_user,current_database(),inet_server_port()').fetchone())
assert pg_identity==['v4_closeout_producer_20261012','market_research',5432]
head_refs={name:ref(runtime/name) for name in ('data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','config/v4_joint_release_authority_v1.json','config/v4_current_native_joint_authority_v3.json')}
for name,identity in head_refs.items():assert identity['sha256'].upper()==restart['after_heads'][name]
original_before=load(base/'PREP_RUNTIME_IDENTITY_R4.json')['records'][0]
original_root=Path(original_before['root']);old_preserved={}
for name,prior in original_before['heads'].items():
 current_ref=ref(original_root/name);assert current_ref['sha256']==prior['sha256'];old_preserved[name]=current_ref
result=dict(contract_id='V4_CURRENT_OPERATIONAL_WINDOWS_PRODUCTION_ACCEPTANCE_R4',acceptance='V4_PRODUCTION_CUTOVER_PASS',port=28765,pid=status['pid'],observed_at=datetime.now(timezone.utc).isoformat(),package_release=status['BUILD_RELEASE_ID'],source_sha=status['SOURCE_SHA'],source_commit=regression['source_commit'],executable=start['executable'],runtime_role=pg_identity[0],database=pg_identity[1],business_token=context['context_token'],T0=context['context']['trade_date'],old_business_token=start['old_context_token'],restart_consistent=True,auto_daily_enabled=True,head_identities=head_refs,old_workspace_heads_preserved=old_preserved,native_content={k:v for k,v in head.items() if k.startswith('native_')},business_readback=business,browser_evidence=ref(base/'IAB_PRODUCTION_R4/RESULT.json'),daily_status=daily,regression=ref(source/'docs/audits/v4_full_closeout_20261012/continuation_20261013/FINAL_REGRESSION_R4/RESULT.json'),installed_package_inspection=ref(base/'INSTALLED_PACKAGE_INSPECTION_R4.json'),production_cutover=True,full_product_release=False,scope='CURRENT_DATED_OPERATIONAL_DESKTOP_RESEARCH_ONLY',first_capture_claim=False,PIT_ELIGIBLE=False,AS_RECORDED=False,external_acceptance=False,trading=False,probability_claims=False,performance_test=False,rollback_drill=False,mobile_test=False)
path=base/'FINAL_ACCEPTANCE_R4.json';assert not path.exists();path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(acceptance=result['acceptance'],pid=result['pid'],port=result['port'],T0=result['T0'],auto=True)))
