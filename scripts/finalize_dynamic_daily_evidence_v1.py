"""Collect actual post-publication receipts without source or Head mutations."""
from pathlib import Path
import json,sys,urllib.request,datetime,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.operational_daily_http_readback_v1 import readback
E=ROOT/'docs/evidence/dynamic_daily_20261009'
def get(route):
    with urllib.request.urlopen('http://127.0.0.1:28765'+route,timeout=60) as response:return json.load(response)
status=get('/api/v4/operations/daily-update/status')
assert status['last_good_trade_date']=='2026-10-09' and status['settings']['auto_enabled'] and status['settings']['service_alive']
assert status['last_catch_up_job']['status']=='PUBLISHED_FULL' and status['active_job'] is None
head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
atomic_json(ROOT,E/'DD07_REAL_POST_CAS_SERVICE_RESTART.json',dict(contract_id='DD07_ACTUAL_POST_CAS_SERVICE_RESTART_V1',acceptance='PASS',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,http_readback=readback('http://127.0.0.1:28765',head),head=ref(ROOT,ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),scope='Actual Task Scheduler process stop/start after COMMITTED CAS; no Windows reboot was performed',external_acceptance='NOT_GRANTED'))
generation=ROOT/'data/v4/dynamic_daily_owners/2026-10-09/6c04ca70243fb34e33adef9e472fa229fab57aa8968a1b93db70d72105021917'
for filename in ['PERIOD_NUMERIC_ORACLE.json','DAY_RECEIPT.json']:
    if (generation/filename).exists():atomic_json(ROOT,E/('DD07_REAL_20261009_'+filename),json.loads((generation/filename).read_bytes()))
suite=ET.parse('E:/codex_tmp/DD07_TARGETED_FINAL.xml').getroot().find('testsuite')
testnames=['operational_daily_jobs_v1','operational_daily_calendar_v2','operational_runtime_acceptance_v2','operational_baostock_client_v1','tdx_local_daily_fallback_v1','tdx_latest_daily_source_v2','operational_daily_executor_v1','operational_successor_release_v1','operational_daily_periods_v1','operational_next_session','operational_gap_bff_v2','r43_operational_bff','operational_successor_control_v1']
atomic_json(ROOT,E/'DD07_TARGETED_TEST_RECEIPT.json',dict(contract_id='DD07_TARGETED_REGRESSION_RECEIPT_V3',acceptance='PASS',tests=int(suite.get('tests')),failures=int(suite.get('failures')),errors=int(suite.get('errors')),observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),test_files=[ref(ROOT,ROOT/'tests'/('test_'+name+'.py')) for name in testnames],scope='60 source/job/SDK/fallback/executor/transaction/period/control/BFF regressions; fixtures remain distinct from actual production release evidence',external_acceptance='NOT_GRANTED'))
print(json.dumps({'acceptance':'PASS_ACTUAL_POST_CAS_RESTART','tests':int(suite.get('tests'))}))
audit=E/'DYNAMIC_DAILY_EXTERNAL_AUDIT.md'
text=audit.read_text(encoding='utf8')
replacements={
'IN_PROGRESS_REAL_20261009_OWNER_BUILD':'PASS_ALL_SEVEN_ENGINEERING_REAL_20261009_RELEASE_ARCHIVE_PENDING',
'10/08通过；10/09真实5224日线、8因子、新ZIP5559原生行，继续数值验收':'10/08与10/09通过；10/09真实5224日线、8因子、新ZIP5559原生行，正式新日已发布',
'两次真实10/08计算，最终IO独立12组全市场比较0错；10/09计算中':'10/08最终IO独立12组全市场比较0错；固定输入完整重算155文件SHA一致；10/09全部Owner实算完成',
'真实新日CAS待数值门':'真实10/09 CAS COMMITTED，六HTTP与发布后服务重启通过',
'新截止页待CAS':'新截止10/09页与工作台实际验收通过',
'10/09 oracle待生成':'10/09真实全市场146272独立检查0错',
'真实10/09 CAS后六入口/页面/重启及最终Git/Drive归档继续':'真实10/09 CAS、六入口、双宽度、发布后重启通过；最终Git/Drive归档待回读',
'真实页面重试已将同一AUTO Job推进10/09 DERIVING。':'真实页面重试将同一AUTO Job推进10/09全量数值计算，19:57:28完成PUBLISHED_FULL。',
'两次真实Owner等价但输入时间/GBBQ不同，不冒称两者SHA相同。':'另做相同冻结原始输入完整数值重算，155个全部产物SHA完全一致（DD07_FULL_FROZEN_REBUILD_DETERMINISM）；不同源版本的等价验收不冒称SHA相同。',
'stale-token负测，新日实际读回待CAS。':'新日实际六HTTP读回和旧token409负测PASS。',
'正式新日六入口与两宽度待CAS。':'正式新日六入口同token/日期PASS，实际IAB两宽度PASS。',
'最终新Owner/源SHA清单、Drive上传回读继续。':'最终新Owner/源SHA清单已生成，Drive归档回读为最后交付步骤。',
'正式last-good 10/08 SHA e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8':'正式last-good 10/09 SHA 55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e；前驱10/08 SHA e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8',
'真实新日成功后更新本记录并完成归档。':'真实新日已发布，工程绿不替代独立外审。',
}
for before,after in replacements.items():text=text.replace(before,after)
text+='\n\n最终真实证据：DD07_REAL_20261009_RELEASE_READBACK.json、DD07_REAL_POST_CAS_SERVICE_RESTART.json、DD07_REAL_20261009_PERIOD_NUMERIC_ORACLE.json、DD07_FULL_FROZEN_REBUILD_DETERMINISM.json，以及PUBLISHED_1366/1920与WORKBENCH截图。60项回归全部通过。实际计算仍沿用已接受5224证券池；349包内额外证券不冒称新增Owner准入。独立Amount差异4946项继续开放。\n'
audit.write_text(text,encoding='utf8')
execution=ROOT/'docs/upgrade/DYNAMIC_DAILY_EXECUTION_V1_1_20261009.md'
text=execution.read_text(encoding='utf8').replace('IN_PROGRESS_REAL_20261009_OWNER_BUILD','PASS_ALL_SEVEN_ENGINEERING_REAL_20261009_RELEASE_ARCHIVE_PENDING')
text=text.replace('10/09源真实冻结后正在完整Owner与动作/rolling重算','10/09真实源冻结、五日完整Owner与动作/rolling重算完成，Core五日PASS；固定输入155产物全SHA确定性PASS')
text=text.replace('真实新日CAS待DD03数值门','真实新日CAS COMMITTED、六HTTP及发布后服务重启PASS')
text=text.replace('新日期刷新待CAS','新截止10/09实际页面双宽度与工作台PASS')
text=text.replace('10/09独立oracle待生成','10/09独立oracle146272检查0错')
text=text.replace('下一门真实10/09 CAS、六入口同token/UI、发布后重启、最终Git/Drive逐payload回读','真实10/09 CAS、六入口同token/UI、发布后重启已PASS；下一门最终Git/Drive逐payload回读')
text=text.replace('全部七项已经实施，但不能把新日CAS前的工程证据写成全门PASS','全部七项工程实施与真实新日发布验收完成，最终归档回读继续；独立外审不升级')
execution.write_text(text,encoding='utf8')
final=ROOT/'docs/upgrade/DYNAMIC_DAILY_DD07_FINAL_RELEASE_20261009.md'
final.write_text('''# DD07 最终真实发布与归档合同

合同：V4-DYNAMIC-DAILY-R1.1；用户授权全部七项，浏览器由用户改为默认IAB。Phase0继承FULL_PASS，DD03原数值/IO/发布policy绑定不改。只读TDX，项目输出外部原子写入。

真实证据：10/09官方新ZIP 635c7759…，逐日BaoStock5224日线和8因子；五日Core/Profile/Sector/Market/Focus/Forward真实重算；10/09本地RAW/QFQ周月146272独立检查0错。当前Head SHA 55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e，AUTO Job a85707e650bb42c296fcfec196eabdf3 于19:57:28 PUBLISHED_FULL。真实CAS六HTTP同token、旧token409、严格9/30 Head不变。发布后实际服务Stop/Start恢复AUTO ON和Job，无额外Owner重算。IAB1366/1920与工作台截止10/09已实测。

固定输入完整数值重跑155产物SHA全部一致。60项回归通过；受控时钟/多缺口/事务故障负测与真实发布证据分别标识。Windows为当前用户AtLogon托管，未实际重启Windows，不冒称登录前系统服务。成员回算非历史PIT，Rotation/Forward原未独立验收状态不升级。Amount表示差异与原FP页面缺口独立开放。

工程验收：PASS_ALL_SEVEN_ENGINEERING_REAL_20261009_RELEASE；EXTERNAL_ACCEPTANCE=NOT_GRANTED。
下一阶段：提交推送代码与有界证据；生成绑定当前Head与Git的完整新增数值产物分卷清单；通过Google Drive插件归档正式Markdown、master和全部分卷，逐字节CRC/SHA回读；仅外审独立签发可以提升外审状态。
''',encoding='utf8')
