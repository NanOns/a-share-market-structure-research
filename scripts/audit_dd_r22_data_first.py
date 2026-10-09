"""R2.2 read-only production/preflight and bounded frozen sector extraction.

Never starts a producer, fetches source data, writes TDX, or publishes a Head.
"""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, json, os, subprocess, sys, urllib.request, urllib.error
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.dm01_runtime_r4 import calendar
from workbench_analysis.operational_daily_calendar_v2 import gap_plan,SHANGHAI
OUT=ROOT/'docs/evidence/dynamic_daily_r22_20261010'

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def checked(b):
    p=Path(b['path']);p=p if p.is_absolute() else ROOT/p
    if not p.exists() and '\\data\\' in str(p):p=ROOT/'data'/str(p).split('\\data\\',1)[1].replace('\\','/')
    assert sha(p)==b['sha256'],str(p)
    return p

def load(b):return json.loads(checked(b).read_bytes())
def rows(b):
    with gzip.open(checked(b),'rt',encoding='utf8') as f:return [json.loads(x) for x in f]
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def http(path,params=None):
    url='http://127.0.0.1:28765'+path+('?' + urlencode(params) if params else '')
    try:
        with urllib.request.urlopen(url,timeout=30) as r:raw=r.read(4*1024*1024+1);code=r.status
    except urllib.error.HTTPError as e:raw=e.read(65536);code=e.code
    assert len(raw)<=4*1024*1024
    return code,raw,json.loads(raw)

def main():
    now=datetime.now(SHANGHAI);hpath=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head=json.loads(hpath.read_bytes());token=sha(hpath);day=head['accepted_trade_date']
    protected={str(p.relative_to(ROOT)):sha(p) for p in [hpath,ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json',checked(head['day_receipt'])]}
    cal=calendar(ROOT);next_day=next(d for d in cal['session_dates'] if d>day)
    plan=gap_plan(ROOT,now)
    process=json.loads((Path('G:/codex_tmp/dd_r22_process.json')).read_bytes())
    modules=[]
    for name in ['operational_daily_executor_v1','source_readiness_v2','operational_daily_ready_owner_v2','operational_daily_owner_v1','operational_daily_jobs_v1','operational_daily_periods_v1']:
        p=ROOT/'src/workbench_analysis'/f'{name}.py';rel=p.relative_to(ROOT).as_posix()
        modules.append(dict(path=str(p),sha256=sha(p),mtime=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),git_blob=git('rev-parse','HEAD:'+rel),git_ref=git('rev-parse','HEAD'),runtime_module_path='NOT_PROVEN_IN_RUNNING_PROCESS',disk_import_path=str(p),runtime_loaded_sha='NOT_PROVEN'))
    reads=[]
    for path in ['/api/v4/context','/api/operations/status','/api/v4/stocks','/api/v4/sectors','/api/v4/market','/api/v4/focus']:
        code,raw,payload=http(path,dict(context_token=token,trade_date=day,limit=3));context=payload.get('context',{})
        passed=code==200 and payload.get('context_token')==token and context.get('accepted_trade_date')==day
        stale,sraw,spayload=http(path,dict(context_token='0'*64,trade_date=day,limit=1))
        reads.append(dict(path=path,http_status=code,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),context_token=payload.get('context_token'),accepted_trade_date=context.get('accepted_trade_date'),status='PASS' if passed else 'FAIL',stale_token_http=stale,stale_response_sha256=hashlib.sha256(sraw).hexdigest(),response_keys=list(payload)))
    _,_,status=http('/api/v4/operations/daily-update/status')
    attestation_path=ROOT/'runtime/dynamic_daily/loaded_modules_r22.json'
    attestation=json.loads(attestation_path.read_bytes()) if attestation_path.is_file() else None
    imported={x['runtime_module_path']:x['sha256'] for x in (attestation or {}).get('modules',[])}
    actual_imports=bool(attestation and attestation.get('pid')==process.get('ProcessId') and all(imported.get(m['path'])==m['sha256'] for m in modules))
    if actual_imports:
        for m in modules:m.update(runtime_module_path=m['path'],runtime_loaded_sha=imported[m['path']])
    freeze=load(head['source_registry'][day]['freeze']);raw=load(freeze['native_baostock'])
    native=load(freeze['tdx'])['target_bars'];daily=freeze['normalized']['daily']['rows'];factors=freeze['normalized']['adjustment_factor']['rows']
    frozen=dict(trade_date=day,scope='EXISTING_ACCEPTED_10_09_FROZEN_ONLY_NOT_NEXT_DAY',tdx=dict(binding=freeze['tdx'],bar_count=len(native),actual_dates=sorted({b['trade_date'] for b in native}),package_sha256=freeze['effective_package']['download']['sha256'],package_bytes=freeze['effective_package']['download']['bytes'],package_downloaded_at=freeze['effective_package']['downloaded_at'],source_observed_at=freeze['effective_package']['observed_at']),baostock_daily=dict(binding=freeze['native_baostock'],response_sha256=freeze['native_baostock']['sha256'],normalized_sha256=digest(daily),count=len(daily),actual_dates=sorted({x['date'] for x in daily}),traded_count=sum(x['tradestatus']=='1' for x in daily),suspended_count=sum(x['tradestatus']=='0' for x in daily),observed_at=raw['observed_at']),baostock_factor=dict(normalized_sha256=digest(factors),changes=len(factors),metadata=freeze['normalized']['adjustment_factor']['metadata'],query_target=raw['target_date'],observed_at=raw['observed_at']),gbbq=head['source_registry'][day]['gbbq'],membership=head['membership_snapshot'])
    # Full small frozen membership authority, bounded existing daily Owners only.
    owner=head['owners'][day];snapshot=load(head['membership_snapshot']);membership=rows(snapshot['memberships'])
    identity=load(snapshot['identity_source']);life=load(owner['lifecycle']);active=set(life['active_security_ids']);life_by={x['security_id']:x for x in life['rows']}
    native_sectors=rows(owner['sector']);core={x['security_id']:x for x in rows(owner['core'])};loo={x['security_id']:x for x in rows(owner['relative_sector'])}
    raw_headers={}
    raw_names={}
    for binding in snapshot['sources']:
        p=checked(binding)
        if p.name=='infoharbor_block.dat':
            for line in p.read_bytes().decode('gb18030',errors='strict').splitlines():
                if line.startswith('#'):
                    fields=line[1:].split(',')
                    if len(fields)>2 and '_' in fields[0]:
                        prefix,name=fields[0].split('_',1);raw_headers['THEME:'+fields[2].strip()]=dict(prefix=prefix,name=name)
        if p.name=='tdxzs.cfg':
            for line in p.read_bytes().decode('gb18030',errors='strict').splitlines():
                fields=line.strip().split('|')
                if len(fields)>=6 and fields[5]:raw_names['INDUSTRY:'+fields[5]]=fields[0]
    selected=[]
    for typ in ['INDUSTRY','THEME']:
        candidates=[s for s in native_sectors if s['sector_type']==typ and (typ!='INDUSTRY' or s['primary_industry_rank_eligible'])]
        if typ=='THEME':candidates=[s for s in candidates if raw_headers.get(s['sector_id'],{}).get('prefix')=='GN']
        eligible={m['sector_id'] for r in loo.values() for m in r['memberships'] if m.get('relative_substitutions')}
        s=sorted([s for s in candidates if s['sector_id'] in eligible],key=lambda s:(-len(s['member_ids']),s['sector_id']))[0]
        authority=[m for m in membership if m['sector_id']==s['sector_id']]
        mapped={m['security_id'] for m in authority if m.get('security_id') in active}
        assert mapped==set(s['member_ids']),'SOURCE_MEMBERSHIP_MISMATCH'
        compact=[]
        for sid in sorted(mapped):
            row=core[sid];vals={k:row['fields'][k] for k in ['ret1','ret5']}
            compact.append(dict(security_id=sid,sector_id=s['sector_id'],status=life_by[sid]['status'],weight=1,ret1=vals['ret1']['value'],ret5=vals['ret5']['value'],ret1_quality=vals['ret1']['quality_state'],ret5_quality=vals['ret5']['quality_state'],core_row_sha256=digest(row),ret1_input_sha256=vals['ret1']['input_digest'],ret5_input_sha256=vals['ret5']['input_digest']))
        target,m=next((sid,m) for sid in sorted(mapped) for m in loo[sid]['memberships'] if m['sector_id']==s['sector_id'] and m.get('relative_substitutions'))
        selected.append(dict(sector_id=s['sector_id'],sector_type=typ,user_domain='TDX_INDUSTRY' if typ=='INDUSTRY' else 'TDX_CONCEPT_STORED_AS_THEME',selection_rule='largest target-date eligible member count; industry requires primary leaf; tie sector_id ascending; actual LOO required; no hotness claim',source_names=sorted({m['sector_name'] for m in authority}),source_files=sorted({m['source'] for m in authority}),name_encoding='Frozen normalized labels contain replacement characters; IDs are authoritative',authority_count=len(authority),eligible_count=len(mapped),filtered_unique_id_count=len({m.get('security_id') for m in authority}-mapped),contributions=compact,expected={k:{a:s['fields'][k].get(a) for a in ['value','known_count','unknown_count']} for k in ['sector_rs1','sector_rs5','breadth_ret1','breadth_ret5']},loo=dict(excluded_target_id=target,non_target_member_count=m['non_target_member_count'],expected_relative={k:m['relative_substitutions'][k] for k in ['rel_market_1','rel_market_5']})))
        selected[-1]['name_encoding']='Frozen original source decoded with gb18030; labels agree with normalized snapshot'
        selected[-1]['raw_decoded_name']=raw_names.get(s['sector_id']) if typ=='INDUSTRY' else raw_headers[s['sector_id']]['name']
        selected[-1]['raw_classification']='TDX_INDUSTRY_LEAF' if typ=='INDUSTRY' else raw_headers[s['sector_id']]['prefix']
        selected[-1]['authority_rows']=[{k:m[k] for k in ['security_id','source_security_key','identity_status','list_date','delist_date','source']} for m in authority]
    c=dict(contract='DD_R22_TWO_TDX_SECTOR_NUMERIC_SAMPLE_V1',trade_date=day,tolerance=dict(absolute=1e-10,relative=1e-10),membership_metadata={k:snapshot[k] for k in ['taxonomy','membership_snapshot_id','membership_mode','member_set_asof','membership_observed_at','PIT_ELIGIBLE','AS_RECORDED','knowledge_lineage']},bindings=dict(head=dict(path=str(hpath),sha256=token),core=owner['core'],sector=owner['sector'],loo=owner['relative_sector'],membership_snapshot=head['membership_snapshot'],membership_authority=snapshot['memberships'],membership_raw_sources=snapshot['sources'],identity=snapshot['identity_source'],lifecycle=owner['lifecycle']),formula_scope='Equal-weight known-return median and positive fraction; target minus non-target known-return median. Full relative states NOT_VERIFIABLE.',sectors=selected)
    atomic_json(ROOT,OUT/'sector_oracle/SECTOR_INPUT.json',c)
    evidence=dict(contract='V4-DD-R2.2-DATA-FIRST',observed_at=now.isoformat(),base_sha=git('rev-parse','HEAD'),branch=git('branch','--show-current'),worktree_before=git('status','--short'),production=dict(status='PROD_RELOAD_REQUIRED',process=process,modules=modules,loaded_commit='NOT_PROVEN; unchanged PID 41528 predates final source edits',reload_attempted=False,reason='Prior automatic review rejected stop/reload: blocked by policy; no bypass attempted',http_reads=reads,daily_status=dict(settings=status['settings'],active_job=status.get('active_job'),worker_error=status.get('worker_error'),status=status['status'],next_trigger_at=status['next_trigger_at'])),calendar=dict(binding=cal['binding'],head_binding=cal['head_binding'],acceptance=cal['status'],next_session=next_day,current_day_is_session=now.date().isoformat() in cal['session_dates'],plan=plan),next_day=dict(status='PROD_DEPLOYMENT_BLOCKED',time_status='WAIT_REAL_SESSION',target_date=next_day,trigger=next_day+'T18:35:00+08:00',tdx='NOT_QUERIED_TARGET_NOT_MATURE',baostock_daily='NOT_QUERIED_TARGET_NOT_MATURE',baostock_factor='NOT_QUERIED_TARGET_NOT_MATURE',derived=False,published=False,expected_counts='NOT_HARDCODED',entry='Existing AUTO worker, after actual service reload and real target three-source verification'),frozen_preflight=frozen,protected_before=protected,protected_after={p:sha(ROOT/p) for p in protected},overall='DATA_CHAIN_BLOCKED_PROD_RELOAD',external_acceptance='NOT_GRANTED')
    assert evidence['protected_before']==evidence['protected_after']
    if actual_imports and all(x['status']=='PASS' and x['stale_token_http']==409 for x in reads):
        evidence['production'].update(status='A_PASS',loaded_commit=attestation['git_sha'],startup_attestation=attestation)
        evidence['next_day']['status']='READY_FOR_REAL_SESSION'
        evidence['overall']='DATA_CHAIN_READY_WAIT_REAL_SESSION'
    else:evidence['production']['startup_attestation']='NOT_PRESENT_OR_NOT_MATCHING_CURRENT_PROCESS'
    atomic_json(ROOT,OUT/'DD_R2_2_CRITICAL_EVIDENCE.json',evidence)
    print(json.dumps(dict(next_session=next_day,production=evidence['production']['status'],six_http=[x['status'] for x in reads],sectors=[(x['sector_id'],x['eligible_count']) for x in selected])))

if __name__=='__main__':main()
