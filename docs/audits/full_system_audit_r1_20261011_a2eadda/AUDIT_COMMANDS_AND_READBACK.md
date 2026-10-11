# 审计命令、复算与读回

环境：PowerShell；所有child TMP/TEMP/TMPDIR=G:/codex_tmp、PYTHONDONTWRITEBYTECODE=1。冻结视图 G:/codex_tmp/full_system_audit_a2eadda/frozen；测试basetemp G:/codex_tmp/test_temp。以 `git -c core.longpaths=true`读取本仓库；原HEAD与fetch origin均a2eadda。未改全局Git配置。

主要读命令：git status/rev-parse/fetch/show/diff/ls-files/archive；rg与Python AST静态读取；指定Drive fetch/getmetadata读取；真实HTTP urllib GET与IAB浏览器。HTTP所有请求path/query/code/bodySHA/bytes/latency、浏览器PNG/DOM hash均在权威账本，实际原件在G:/codex_tmp/full_system_audit_a2eadda。源码/权威内容与命令输出分别有SHA；不重传行情ZIP或DB。

隔离PG：G:/codex_tmp/test_temp/audit_full_a2eadda_pg/data、127.0.0.1:55547，仅自建market_research、fep_authority_isolated、fep_e5_legacy_fixture。33版本migration与PG data_directory验证在pg.json；原生产5432未触碰。测试fixture可写G隔离PG，非production接受。测试子例触发的额外PG目录也在TMP G且finally停止清理。

审计环境事故单列：run06试图以GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE读取历史，测试内部git init继承这些变量，给主仓添加core.worktree。发现后停止该run及误启run07，删除仅本轮新增core.worktree配置，验证主HEAD/顶层/track状态恢复且无业务文件变更。其后使用G盘独立Git元数据+只读objects alternate，未再导出这些GIT变量。被中止run不作完成证据。此问题是审计环境错误，不列作产品缺陷。

run01–04缺bound inputs导致collection错误；run05是早期非绿完成run；run06/07中止；run08是正式广范围非绿运行。分别保留收据，不混加passed数字或把后续重测扣成原始零失败。当前依赖sklearn缺失、历史夹具与安全PG端口bootstrap缺证明确保留。

## 已完成pytest命令与exit

### checks_05

```powershell
E:\python\python.exe -B -m pytest tests/v4_phase0 tests/v4_03 tests/v4_04 tests/v4_07 tests/v4_08 tests/v4_09 tests/v4_10 tests/v4_11 tests/fep_e2 tests/fep_e3 tests/fep_e4 tests/fep_e5 tests/test_core_product_read_r1.py tests/test_core_product_focus_r2.py tests/test_windows_package_runtime.py tests/test_dd_r21_process_races.py tests/test_state_publisher_bridge_v1.py tests/test_dated_identity_candidate_v1.py tests/test_next_t0_old_identity_preflight.py tests/test_cohort_first_capture_producer_r1.py tests/test_cohort_daily_capture_boundary_r1.py tests/test_cohort_capture_readiness_r1.py tests/test_full_state_first_observed_v1.py tests/test_followup_semantics_r2.py tests/test_identity_gate_reason_r2.py tests/test_state_trusted_review_candidate_v1.py tests/test_next_stage_c_episode_genesis.py -q --continue-on-collection-errors --tb=short -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/full_audit_a2eadda_05 --junitxml=G:\codex_tmp\full_system_audit_a2eadda\checks_05\unit_junit.xml
```

{"exit_code": 1, "input_type": "ISOLATED_SYNTHETIC_AND_BOUND_ARCHIVED_INPUT_TESTS", "elapsed_seconds": 211.2134051322937, "counts": {"name": "pytest", "errors": "125", "failures": "84", "skipped": "255", "tests": "1403", "time": "210.077", "timestamp": "2026-10-11T07:47:55.735694+08:00", "hostname": "DESKTOP-PMEP5GE"}, "junit_sha256": "cbe466dc58fd3407325a495f1115178a60687861bb537368cf98f57fc47d2403", "stdout_sha256": "18635bc2104b166413ed6546e416d359087c7829a1e3c6b97255fba5ad3a00b6"}

### checks_08

```powershell
E:\python\python.exe -B -m pytest tests/v4_phase0 tests/v4_03 tests/v4_04 tests/v4_07 tests/v4_08 tests/v4_09 tests/v4_10 tests/v4_11 tests/fep_e2 tests/fep_e3 tests/fep_e4 tests/fep_e5 tests/test_core_product_read_r1.py tests/test_core_product_focus_r2.py tests/test_windows_package_runtime.py tests/test_dd_r21_process_races.py tests/test_state_publisher_bridge_v1.py tests/test_dated_identity_candidate_v1.py tests/test_next_t0_old_identity_preflight.py tests/test_cohort_first_capture_producer_r1.py tests/test_cohort_daily_capture_boundary_r1.py tests/test_cohort_capture_readiness_r1.py tests/test_full_state_first_observed_v1.py tests/test_followup_semantics_r2.py tests/test_identity_gate_reason_r2.py tests/test_state_trusted_review_candidate_v1.py tests/test_next_stage_c_episode_genesis.py -q --continue-on-collection-errors --tb=short -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/full_audit_a2eadda_08 --junitxml=G:\codex_tmp\full_system_audit_a2eadda\checks_08\unit_junit.xml
```

{"exit_code": 1, "input_type": "ISOLATED_SYNTHETIC_AND_BOUND_ARCHIVED_INPUT_TESTS", "elapsed_seconds": 241.87000393867493, "counts": {"name": "pytest", "errors": "35", "failures": "41", "skipped": "225", "tests": "1602", "time": "240.757", "timestamp": "2026-10-11T07:57:29.925899+08:00", "hostname": "DESKTOP-PMEP5GE"}, "junit_sha256": "5c849320c0084018936f21b75702050fc659280b25ecfe5c891da985c35f62ad", "stdout_sha256": "670eed73bd2f2641d5490d4802305ed625921e5a88655ff87dd6be9cdca45f6f"}

### checks_targeted

```powershell
E:\python\python.exe -B -m pytest tests/test_operational_successor_release_v1.py tests/test_operational_daily_jobs_v1.py tests/test_operational_daily_calendar_v2.py tests/test_operational_daily_periods_v1.py tests/test_dd_r21_source_orchestration.py tests/test_tdx_latest_daily_source_v2.py tests/test_market_source_acquisition_r4.py tests/test_r4_next_real_source_admission.py tests/test_tdx_adjustment_reference_cases.py tests/test_windows_package_runtime.py tests/test_dd_r21_process_races.py tests/test_core_product_read_r1.py tests/test_core_product_focus_r2.py tests/upgrade_m14/test_eastmoney_hot_rank.py tests/upgrade_m14/test_hot_rank_capture_retired.py tests/upgrade_m14/test_hot_rank_view.py tests/upgrade_m14/test_quotes_capability.py tests/upgrade_m14/test_source_registry.py -q --tb=short -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/full_audit_a2eadda_targeted --junitxml=G:\codex_tmp\full_system_audit_a2eadda\checks_targeted\unit_junit.xml
```

{"exit_code": 1, "input_type": "ISOLATED_SYNTHETIC_AND_PROCESS_FAULTS_NO_LIVE_WRITES", "elapsed_seconds": 65.16702318191528, "counts": {"name": "pytest", "errors": "0", "failures": "3", "skipped": "0", "tests": "106", "time": "64.158", "timestamp": "2026-10-11T08:00:14.561013+08:00", "hostname": "DESKTOP-PMEP5GE"}, "junit_sha256": "e6780d77e4e19a691bbfe2643da913192a93b8d5c022aa4ae57241a0ac62dd5e", "stdout_sha256": "1b5bb1160b48f6c81f83fb12ba99f93505b1d01fcb1fea1ed5d0688df1f8980f"}

### checks_rerun

```powershell
E:\python\python.exe -B -m pytest tests/test_market_source_acquisition_r4.py::test_calendar_holiday_and_exact_predecessors tests/upgrade_m14/test_source_registry.py::test_contract_and_plan_are_present tests/upgrade_m14/test_source_registry.py::test_probe_report_is_metadata_only_and_keeps_capabilities_unverified tests/fep_e5/test_e5_contract.py tests/v4_11 -q --tb=short -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/full_audit_a2eadda_rerun --junitxml=G:\codex_tmp\full_system_audit_a2eadda\checks_rerun\unit_junit.xml
```

{"exit_code": 1, "input_type": "ISOLATED_SYNTHETIC_DB_AND_BOUND_FROZEN_INPUTS", "elapsed_seconds": 99.4655613899231, "counts": {"name": "pytest", "errors": "7", "failures": "2", "skipped": "0", "tests": "95", "time": "98.485", "timestamp": "2026-10-11T08:07:52.385064+08:00", "hostname": "DESKTOP-PMEP5GE"}, "junit_sha256": "e841b484faa13fc7343ee460fc65de2a91a39771986b7cb0c61964b3e86df3d8", "stdout_sha256": "ad41d6be34aea43bd3b4e6e510653afb4fe552d6fe8951c965f15ea980afe030"}

## 收尾真实GET与反例

HTTP047 `/api/v4/compare?trade_date=2026-10-09&as_of=2026-09-28&mode=stock-stock&left=302132&right=688349&context_token=55d78...`，200 READY；HTTP048仅left改300114，200 SOURCE_INCOMPLETE/COMPARE_OBJECT_NOT_PRESENT。完整token与query/响应hash在账本。HTTP049 `/api/v4/operations/daily-update/status`200 UP_TO_DATE。原三个Head最终hash均相同。

FA-001独立反例运行exit1表示预期缺陷被触发，不能统计成PASS；脚本只patch base get/envelope/context校验，用冻结home原函数处理合成输入，CURRENT live_multi_type_entities=[]。FA-005在G临时目录被旧E/F限制拒绝；FA-013/014以真实浏览器/API证明。性能是单客户端观察不作容量benchmark。

既有Windows EXE原件 `G:/codex work/大A交易_交付/windows_package_v1/versions/V4_PACKAGE_1.0.0_27b2ec1ed284/DaAV4/DaAV4.exe` SHA74ae310c2541ac1c281b2f253d81839ee68c7be438e603ad9b23a9a51c820a7c；installer `G:/codex work/大A交易_交付/windows_package_v1/installer/V4_PACKAGE_1.0.0_27b2ec1ed284/大A交易系统安装程序.exe` SHA40256a5cf8b1ec8f4aa6f9e726332a45cfd20133547a0bb52971841fa887348f。只读取，不执行。S0/S1/S2既有receipt为此前工程证据，不伪装本轮现场QA。

## 未执行与原因

未执行实际安装/重启/生产切源/许可签发：超出审计范围且S2真实现场待准入。未执行未来10/12真实source/firstseen/Forward期限：事实尚未发生。未做长期成熟OOS与预测优势判断：真实分母、成熟期、控制组与许可缺证。未全量独立解密GBBQ、全stock原生收益/全部窗口/完整状态DAG/所有UI边界：本轮覆盖仍有缺口，以AUDIT_INCOMPLETE留项，不用未来日门掩盖旧日可验证工作。

## 独立oracle完整源码（审计工具，未入业务代码）

执行 `E:/python/python.exe -B G:/codex_tmp/full_system_audit_a2eadda/independent_oracle.py`，cwd frozen，exit0。脚本使用已验immutable refs与原生ZIP输入，本机大原件路径/SHA/bytes全列oracle.inputs。以下源码可保存到G用于复核；保存本身不授权生产写入。

```python
"""Audit-only oracle. No imports from the audited project; all outputs on G:."""
import os,json,gzip,math,statistics,hashlib,struct,zipfile,bisect,time
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
ROOT=Path('G:/codex work/大A交易'); BASE=Path('G:/codex_tmp/full_system_audit_a2eadda')
start=time.time(); inputs=[];results=[];counts={};errors=[]
def read(ref):
 p=ROOT/ref['path']; h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 actual=h.hexdigest();assert actual==ref['sha256'],('HASH_MISMATCH',str(p),actual,ref['sha256'])
 inputs.append(dict(ref,verified_sha256=actual));return p
def rows(ref):
 with gzip.open(read(ref),'rt',encoding='utf8') as f:
  for line in f:yield json.loads(line)
def check(group,entity,field,expected,actual,tolerance=1e-10):
 ok=(expected is None and actual is None) or (type(expected)==bool and type(actual)==bool and expected==actual) or (isinstance(expected,(float,int)) and not isinstance(expected,bool) and isinstance(actual,(float,int)) and math.isfinite(actual) and math.isclose(expected,actual,rel_tol=tolerance,abs_tol=tolerance)) or (isinstance(expected,list) and expected==actual)
 counts.setdefault(group,dict(pass_count=0,fail_count=0));counts[group]['pass_count' if ok else 'fail_count']+=1
 item=dict(group=group,entity=entity,field=field,expected=expected,actual=actual,pass_result=ok)
 if not ok:errors.append(item)
 if len(results)<150 or not ok:results.append(item)
def avg(xs):return statistics.fmean(xs)
head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_text('utf8'))
receipt=json.loads(read(head['day_receipt']).read_text('utf8'))
replay=json.loads(read(receipt['numeric_core_oracle']).read_text('utf8'))
day=head['accepted_trade_date'];own=head['owners'][day]
all_core={}
for date,owners in head['owners'].items():
 core={r['security_id']:r for r in rows(owners['core'])};all_core[date]=core
 for n in (5,20):
  valid={sid:r['fields'][f'ret{n}']['value'] for sid,r in core.items() if r['fields'][f'ret{n}']['quality_state']=='OBSERVED' and isinstance(r['fields'][f'ret{n}']['value'],(float,int))}
  ordered=sorted(valid.values());N=len(ordered)
  for sid,r in core.items():
   value=valid.get(sid);expected=None if value is None or N<2 else 100*(bisect.bisect_left(ordered,value)+.5*(bisect.bisect_right(ordered,value)-bisect.bisect_left(ordered,value)-1))/(N-1)
   check('RPS_CROSS_SECTION',date+':'+sid,f'rps{n}',expected,r['fields'][f'rps{n}']['value'])
core=all_core[day];sample_ids=list(core)[:8]
hist_ref=next(r['history'] for r in replay['owners'] if r['trade_date']==day)
history={}
with gzip.open(read(hist_ref),'rb') as f:
 for line in f:
  if any(s.encode() in line for s in sample_ids):
   r=json.loads(line);history[r['security_id']]=r['bars']
raw={r['security_id']:r for r in rows(own['raw'])}
seed={r['security_id']:r['base_seed_state'] for r in rows(own['seed'])}
package=read(replay['owners'][-1]['sources']['package'])
read(replay['owners'][-1]['sources']['gbbq'])
with zipfile.ZipFile(package) as z:
 names=z.namelist()
 for sid,bars in history.items():
  key=core[sid]['source_security_key'];symbol=key.lower().replace('.','')+'.day'
  candidates=[n for n in names if n.lower().endswith('/'+symbol) or n.lower()==symbol]
  assert len(candidates)==1,(key,candidates)
  blob=z.read(candidates[0]);assert len(blob)%32==0
  native={}
  for i in range(0,len(blob),32):
   d,o,h,l,c,a,v,_=struct.unpack_from('<IIIIIfII',blob,i);ds=str(d);dt=ds[:4]+'-'+ds[4:6]+'-'+ds[6:]
   if dt<=day:native[dt]=([o/100,h/100,l/100,c/100],a,v)
  for bar in bars:
   dt=bar['trade_date'];assert dt<=day
   for j,label in enumerate(['open','high','low','close']):
    check('NATIVE_ZIP_RAW',sid+':'+dt,label,native[dt][0][j],bar['raw_ohlc'][j])
    if bar['qfq_ohlc'] and not bar['blocked_events']:
     val=float((Decimal(str(bar['raw_ohlc'][j]))*Decimal(bar['qfq_mul'])+Decimal(bar['qfq_add'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
     check('QFQ_STORED_AFFINE_EVALUATION',sid+':'+dt,label,val,bar['qfq_ohlc'][j])
   check('NATIVE_ZIP_RAW',sid+':'+dt,'amount',native[dt][1],bar['amount']);check('NATIVE_ZIP_RAW',sid+':'+dt,'volume',native[dt][2],bar['volume'])
  f=core[sid]['fields'];selected={b['trade_date']:b for b in bars}
  # Use recorded window endpoints to respect explicit suspension/session semantics.
  expected={}
  for name,field in f.items():
   if field['quality_state']!='OBSERVED' or name.startswith(('rps','rel_')):continue
   w=[b for b in bars if field['window_start_trade_date']<=b['trade_date']<=field['window_end_trade_date']]
   if not w or any(not b['qfq_ohlc'] for b in w):continue
   price=lambda b,j:b['qfq_ohlc'][j]
   if name.startswith('ma') and name[2:].isdigit():value=avg(price(b,3) for b in w)
   elif name.startswith(('hhv','llv')):value=(max if name.startswith('hhv') else min)(price(b,1 if name.startswith('hhv') else 2) for b in w)
   elif name.startswith(('prior_high','prior_low')):value=(max if name.startswith('prior_high') else min)(price(b,1 if name.startswith('prior_high') else 2) for b in w)
   elif name.startswith(('amount_ratio','volume_ratio')):
    key='amount' if name.startswith('amount') else 'volume';value=w[-1][key]/avg(b[key] for b in w[:-1])
   elif name.startswith('ret') and name[3:].isdigit():value=price(w[-1],3)/price(w[0],3)-1
   elif name in ('vol5','vol20'):value=statistics.pstdev(math.log(price(b,3)/price(a,3)) for a,b in zip(w,w[1:]))
   elif name in ('atr5','atr20','tr'):value=avg(max(price(b,1)-price(b,2),abs(price(b,1)-price(a,3)),abs(price(b,2)-price(a,3))) for a,b in zip(w,w[1:]))
   elif name.startswith('slope'):
    n=int(name[5:]);off=5 if n==20 else 10;value=(avg(price(b,3) for b in w[-n:])-avg(price(b,3) for b in w[-n-off:-off]))/expected['atr20']
   elif name in ('hh_progress','ll_progress'):
    fun,j=(max,1) if name=='hh_progress' else (min,2);a=fun(price(b,j) for b in w[-5:]);b=fun(price(b,j) for b in w[:5]);value=a>b if j==1 else a<b
   elif name=='clv':b=w[-1];value=(price(b,3)-price(b,2))/(price(b,1)-price(b,2))
   elif name=='prior60_percentile':current=price(w[-1],3);value=100*(sum(price(b,3)<current for b in w[:-1])+.5*sum(price(b,3)==current for b in w[:-1]))/60
   else:continue
   expected[name]=value;check('CORE_WINDOW_FORMULA',sid,name,value,field['value'])
  latest=bars[-1]['qfq_ohlc'][3]
  for name,value in [('pos60',(latest-expected['llv60'])/(expected['hhv60']-expected['llv60'])),('range_ratio',(expected['hhv5']-expected['llv5'])/(expected['hhv20']-expected['llv20'])),('atr_ratio',expected['atr5']/expected['atr20']),('vol_ratio',expected['vol5']/expected['vol20']),('core_price_damage',latest<expected['prior_low20']-.5*expected['atr20'] and expected['ret1']<0)]:check('CORE_DERIVED_FORMULA',sid,name,value,f[name]['value'])
sectors=list(rows(own['sector']))
for r in sectors:
 ids=r['member_ids'];fs=r['fields'];sid=r['sector_id']
 vals=lambda name:[core[m]['fields'][name]['value'] for m in ids if m in core and core[m]['fields'].get(name,{}).get('quality_state')=='OBSERVED' and isinstance(core[m]['fields'][name]['value'],(int,float))]
 check('SECTOR_NATIVE',sid,'sector_member_count',len(set(ids)),fs['sector_member_count']['value'])
 known=vals('ret1');check('SECTOR_NATIVE',sid,'sector_quote_coverage',len(known)/len(ids),fs['sector_quote_coverage']['value'])
 for n in (1,5,20):
  vs=vals('ret'+str(n));check('SECTOR_NATIVE',sid,'sector_rs'+str(n),statistics.median(vs) if vs else None,fs['sector_rs'+str(n)]['value']);check('SECTOR_NATIVE',sid,'breadth_ret'+str(n),sum(v>0 for v in vs)/len(vs) if vs else None,fs['breadth_ret'+str(n)]['value'])
 for source,output in [('amount_ratio20','participation_proxy'),('pos60','pos60')]:
  vs=vals(source);check('SECTOR_NATIVE',sid,output,statistics.median(vs) if vs else None,fs[output]['value'])
 amounts=[raw[m]['amount'] for m in ids if m in raw and raw[m]['amount']>=0];total=sum(amounts)
 for k in (1,3):check('SECTOR_NATIVE',sid,f'top{k}_concentration',sum(sorted(amounts,reverse=True)[:k])/total if total>0 else None,fs[f'top{k}_concentration']['value'])
 states=[seed.get(m,'UNKNOWN') for m in ids];N=sum(s in ('TRUE','FALSE') for s in states);k=states.count('TRUE');p=k/N if N else None
 if N:
  z=1.96;lower=(p+z*z/(2*N)-z*math.sqrt(p*(1-p)/N+z*z/(4*N*N)))/(1+z*z/N)
 else:lower=None
 check('SECTOR_SEED_WIDTH',sid,'seed_width',p,fs['seed_width']['value']);check('SECTOR_SEED_WIDTH',sid,'base_seed_width_adjusted',lower,fs['base_seed_width_adjusted']['value'])
for typ,level in [('INDUSTRY','LEAF'),('INDUSTRY','PARENT_DERIVED'),('THEME','CONCEPT')]:
 for n in (5,20):
  eligible=[r for r in sectors if r['sector_type']==typ and r['industry_level']==level and r['rank_eligible'] and r['fields'][f'sector_rs{n}']['value'] is not None];ordered=sorted(r['fields'][f'sector_rs{n}']['value'] for r in eligible);N=len(ordered)
  for r in eligible:
   v=r['fields'][f'sector_rs{n}']['value'];expected=100*(bisect.bisect_left(ordered,v)+.5*(bisect.bisect_right(ordered,v)-bisect.bisect_left(ordered,v)-1))/(N-1) if N>1 else None
   check('SECTOR_PERCENTILE',r['sector_id'],f'sector_rs{n}_pct',expected,r['fields'][f'sector_rs{n}_pct']['value'])
out=dict(contract='INDEPENDENT_AUDIT_ORACLE_R1',audited_head='a2eadda9151b37b4cc463bd5c6a7e540be85741a',target_trade_date=day,inputs=inputs,counts=counts,errors=errors,sample_results=results,sampled_securities=sample_ids,elapsed_seconds=time.time()-start,limitations=['No audited business imports.','GBBQ raw hash checked, but independent encrypted GBBQ decoding/event composition NOT verified. Affine evaluation uses recorded coefficients.','RPS rank checked for all five accepted days against frozen core returns, not independent all-security native return replay.','Technical formula sample uses owner window endpoints; unknown/suspension boundary rules require separate counterexamples.','Sector native from frozen core/seed/raw; historical reconstructed membership is not PIT.'])
(BASE/'oracle.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(counts=counts,errors=errors[:12],elapsed_seconds=out['elapsed_seconds']),ensure_ascii=False));raise SystemExit(1 if errors else 0)

```

## FA-001反例完整源码

```python
import os,sys,json,gzip,hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
BASE=Path('G:/codex_tmp/full_system_audit_a2eadda');ROOT=BASE/'frozen'
os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(ROOT/'src'))
from workbench_service.core_product_bff_r1 import CoreProductBFFR1,OperationalSuccessorBFFV1
DAY='2026-10-09';SID='SYNTHETIC_SAME_DAY_ENTITY'
class Fixture(CoreProductBFFR1):
 def source(self,domain,day):return {'events':[dict(entity_id=SID,event='NEW'),dict(entity_id=SID,event='INVALIDATED')]} if domain=='forward' else []
 def project(self,domain,day):return [dict(entity_id=SID,symbol='SYNTHETIC',fields={})] if domain=='stocks' else []
obj=Fixture.__new__(Fixture);obj.api=SimpleNamespace(candidate=dict(accepted_trade_date=DAY,owners={DAY:{'forward':dict(path='SYNTHETIC_FIXTURE',sha256='0'*64), 'rotation':dict(path='SYNTHETIC_ROTATION',sha256='0'*64)}},rotation_validation_state='VALIDATION_ONGOING'),token='SYNTHETIC_TOKEN')
with patch.object(OperationalSuccessorBFFV1,'get',side_effect=lambda *a:(200,{'gaps':[]})):
 code,actual=obj._get_product('/api/v4/home',{'context_token':'SYNTHETIC_TOKEN'})
result=dict(contract='HOME_PRIORITY_INDEPENDENT_COUNTEREXAMPLE_R1',input_type='ISOLATED_SYNTHETIC_ONLY',expected_primary='INVALIDATED',expected_risk_entity_count=1,actual_primary=actual['changes'][0]['fields']['effective_event']['value'],actual_risk_entity_count=len(actual['risks']),source='src/workbench_service/core_product_bff_r1.py',base_get_patched='Only envelope/context validation; production home selection function executed unchanged',live_incident_proven=False)
# Inspect current accepted projection separately without executing production code.
live=Path('G:/codex work/大A交易');authority=json.loads((live/'config/core_product_focus_read_authority_r2.json').read_bytes());manifest=json.loads((live/authority['manifest']['path']).read_bytes());ref=manifest['projection'];blob=(live/ref['path']).read_bytes();assert hashlib.sha256(blob).hexdigest()==ref['sha256']
projection=json.loads(gzip.decompress(blob));pairs={}
for e in projection['events']:
 if e.get('trade_date')==DAY and e.get('event') in ('NEW','UPGRADED','WEAKENED','INVALIDATED','EXITED','REENTERED'):pairs.setdefault(e['entity_id'],set()).add(e['event'])
result['live_multi_type_entities']=[dict(entity_id=s,events=sorted(v)) for s,v in pairs.items() if len(v)>1];result['live_incident_proven']=bool(result['live_multi_type_entities']);result['projection_binding']=ref
(BASE/'home_counterexample.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False));raise SystemExit(1 if result['actual_primary']!=result['expected_primary'] else 0)

```

## 交付轻包回读SHA

下表为本文件以外9文件的最终字节SHA。本文件本身的SHA在会话最终回报及本机package_qa.json记录，避免自引用哈希。

|文件|字节|SHA256|
|---|---:|---|
|AUDIT_AUTHORITY_AND_RUNTIME_LEDGER.json|416836|a248fad0c0f0756f591705af87edfd3714f61891504a26d5624b42198e0c3054|
|CODE_TO_DESIGN_REVERSE_MATRIX.csv|5992949|5a31bd6aea59afdf9410f12a5b0ee7b8914caf145e8f4d489e048b77c7868727|
|DATA_LINEAGE_EDGES.csv|702160|c315187f5cae44a4ec1de0c703abf67e586fde71c1efff57755242917921ec2a|
|DESIGN_TO_CODE_TRACE_MATRIX.csv|4318356|90410e9091dfd7c71883cee3c2e50e8e7927e7efe88b2b9bfba1fb6befc23d83|
|FIELD_FACTOR_IMPLEMENTATION_REGISTRY.csv|9148774|5d48923a095a4bdfe99335404ce70c09c4127aa86a3a375549cbae7c9348d37a|
|FULL_MODULE_CAPABILITY_MATRIX.csv|29980|33d9e40fecb2281a9ab892ed45e46e48d446efbe450c12b128a9e7721f6584f3|
|INDEPENDENT_AUDIT_ITEMS.json|13161|0f91859a49b60a1794e4629d5b6ecf6a0b056a38e1fc4e286dc6aec5e338e895|
|NEXT_REPAIR_EXECUTION_BATCHES.md|3833|226ded1f0854a2648cb0e125abb0fcb379ae8a8909f7e0bb6e9b79cf1f3b440d|
|V4_FULL_SYSTEM_CODE_AUDIT_REPORT_R1_20261011.md|20970|c08142ed28690f63d58f678899c9ee2465124e75202587aedc8210201a4ee42e|
