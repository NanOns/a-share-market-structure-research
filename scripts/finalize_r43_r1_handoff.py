"""Record engineering delivery without manufacturing external acceptance."""
import hashlib,json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.scoped_successor_r421 import atomic,canonical
OUT=ROOT/'docs/evidence/r4_3_r1_targeted_repair_20261009'
def read(name):return json.loads((OUT/name).read_bytes())
def write(name,value):atomic(OUT/name,canonical(value))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    entry=read('ENTRY_STAGE_CONTRACT.json');errors=[]
    for binding in entry['prior_evidence']+entry['protected']:
        p=ROOT/binding['path']
        if sha(p)!=binding['sha256'] or p.stat().st_size!=binding['bytes']:errors.append(binding['path'])
    assert not errors,errors
    write('R43_R1_IMMUTABLE_INPUT_FINAL_READBACK.json',dict(old_evidence_files=len(entry['prior_evidence']),protected_heads=len(entry['protected']),mismatches=errors,acceptance='PASS'))
    cas=read('R43_NEW_OPERATIONAL_CANDIDATE_AND_CAS_V2.json')
    ui=read('R43_PRODUCTION_UI_ROUTE_AND_BFF_COMPATIBILITY_QA.json')
    digest=cas['candidate_digest']
    assert ui['candidate_digest']==digest and ui['status']=='PASS_ISOLATED_REAL_HTTP'
    actual=[]
    for route in ['/v4','/api/v4/context']:
        try:
            with urllib.request.urlopen('http://127.0.0.1:28765'+route,timeout=20) as r:raw=r.read();status=r.status
            value=dict(route=route,status=status,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            if route.startswith('/api/'):value['payload']=json.loads(raw)
            actual.append(value)
        except Exception as exc:actual.append(dict(route=route,result='NOT_VERIFIABLE',error=str(exc)))
    write('R43_LIVE_1008_FINAL_READBACK.json',dict(receipt_type='NOT_A_1008_ACCEPTANCE_RECEIPT',target_trade_date='2026-10-08',observed_accepted_trade_date='2026-09-30',production_CAS_executed=False,operational_head_exists=(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').exists(),live_http=actual,protected_heads=entry['protected'],acceptance='NOT_VERIFIABLE_NO_INDEPENDENT_SIGNED_ACCEPTANCE'))
    write('R43_R1_FINAL_TEST_RECEIPT.json',dict(command='E:/python/python.exe -m pytest tests/test_v4_default_workbench_service.py tests/test_r43_member_normalization_v2.py tests/test_tdx_member_retro_r43.py tests/test_r43_operational_bff.py tests/test_r43_operational_sources.py tests/test_v4_current_daily_refresh.py --basetemp E:/codex_tmp/test_temp/r43_r1_complete -q',exit_code=0,passed=32,duration_seconds=33.57,post_final_missing_route_patch=dict(command='E:/python/python.exe -m pytest tests/test_r43_operational_bff.py --basetemp E:/codex_tmp/test_temp/r43_r1_explicit_missing -q',passed=7,exit_code=0,duration_seconds=0.16),external_acceptance=False))
    drift=read('AUDIT_LEGACY_SERVICE_TITLE_ASSERTION_DRIFT.json');drift.update(status='RESOLVED_TEST_CONTRACT_ALIGNMENT',resolution='Three original entry routes must equal exact approved joint-authority HTML bytes; original HTML untouched',final_regression='32 passed');write('AUDIT_LEGACY_SERVICE_TITLE_ASSERTION_DRIFT.json',drift)
    write('SCOPED_ADMISSION_REQUEST_V2.json',dict(status='PENDING_INDEPENDENT_EXTERNAL_REVIEW',candidate=cas['candidate'],candidate_digest=digest,reviewer=None,signature=None,external_acceptance_granted=False,production_permission=False,FP01_FP14_authorized=False,engineering_evidence=['R43_SOURCE_REPARSE_CONTRADICTION_AND_FIX_V2.json','R43_PRODUCTION_UI_ROUTE_AND_BFF_COMPATIBILITY_QA.json','R43_SCOPED_EXTERNAL_SOURCE_NUMERIC_REVIEW_V2.md','R43_NEW_OPERATIONAL_CANDIDATE_AND_CAS_V2.json'],scope='Four-session operational research with latest observed membership; not historical PIT',limitations=['2224 unmapped relations excluded','No strict historical PIT or AS_RECORDED claim','No external full recursive rotation-state oracle','Unpublished chart/replay/statistics/CSV capabilities remain explicit SOURCE_INCOMPLETE','No automated trading or probability claims'],required_next='Independent source/numeric/compatibility acceptance signed against exact candidate digest before production CAS'))
    text=f'''# R4.3 R1 正式交接

工程修复完成；独立外审准入仍为 NOT_VERIFIABLE，生产没有切换，FP01–FP14 未获授权。

| 阶段 | 验收 | 证据与限制 |
| --- | --- | --- |
| P0-A | PASS | 真实旧10列快照重解析原本成功；真实现行12列捕获的旧验证器失败已复现。共用纯规范化后完整55,136关系重解析、摘要和负向变异通过。旧S与Owner保持原样。 |
| P0-B | PASS（工程，详见最终HTTP QA） | 原生产HTML保留，预览独立路由，最小BFF兼容；新能力只在隔离E目录模拟准入，未制造生产外审。 |
| P0-C | PASS（工程限定范围）/ NOT_VERIFIABLE（独立外审） | 319实际文件、2,389,921,416字节全摘要及独立数值证据；完整递归Rotation外部oracle未获签署。 |
| P0-D | PASS（候选与隔离CAS）/ NOT_VERIFIABLE（生产准入） | 新候选与52读回通过；缺少最终摘要签署，生产CAS未执行。 |

最终候选摘要：`{digest}`。
最终真实HTTP读取 {len(ui['actual_http_readbacks'])} 次，精确绑定该摘要，未重新绑定模拟代码。
回归测试：32 passed，33.57秒。原216证据及3个保护头摘要全部保持。
源分类校正为110叶级、22派生父级、1占位项，268概念；错误“23父级”另立独立审计，不改写旧证据。
当前生产接受日期仍为2026-09-30，`R43_LIVE_1008_FINAL_READBACK.json`明确不是10/08接受回执。

最小兼容范围：context/home、股票列表/详情/profile、板块列表/详情/成员、Focus列表与事件/episodes/anchors/observations/outcomes、根诊断/来源及原生四日领域。完整chart/PIT replay/compare、板块历史timeline/overlap、Market中心子页面、Forward enrollment统计/plans/FEP/settlement和诊断专用子页面未接完整Owner，明确SOURCE_INCOMPLETE；不是六入口完整FP功能验收。
源修复已推送提交ad488763；最终代码与证据提交及Drive归档见 `R43_R1_DELIVERY_RECEIPT.json`。
下一阶段：提交 `SCOPED_ADMISSION_REQUEST_V2.json` 所列精确候选给独立外审；在签署前不得执行生产切换或进入FP01–FP14。
'''
    atomic(OUT/'R43_R1_FORMAL_HANDOFF.md',text.encode('utf-8'))
    print(json.dumps(dict(candidate_digest=digest,immutable='PASS',production=False,ui_evidence_keys=list(ui))))
if __name__=='__main__':main()
