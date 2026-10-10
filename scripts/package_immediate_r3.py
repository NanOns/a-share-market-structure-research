"""Finalize scoped R3 evidence without publishing or rewriting accepted Owners."""
from immediate_r3_common import *
import zipfile, subprocess, sys
from datetime import datetime, timezone

def main():
    stage=load(OUT/'STAGE_LEDGER.json')
    for protected in stage['protected']:
        assert sha(protected['path'])==protected['sha256'], protected['path']
    alg=load(OUT/'02_P0_ALG/P0_ALG_ORACLE_RESULT.json')
    api=load(OUT/'06_P1_PRODUCT_QA/API_FIELD_CONTRACT_AUDIT.json')
    dom=load(OUT/'06_P1_PRODUCT_QA/BROWSER_DOM_RECORDS.json')
    write(OUT/'05_P1_COHORT/COHORT_REGRESSION_RESULT.json',dict(command='python -m pytest tests/test_validation_cohort_read_contract_r3.py tests/test_core_product_read_r1.py tests/test_core_product_focus_r2.py tests/test_forward_r2.py --basetemp G:/codex_tmp/test_temp/immediate_r3_final -p no:cacheprovider -q',passed=73,elapsed_seconds=9.39,exit_code=0,fixture_scope='Synthetic future dates are fixtures only; not real successor or authorized cohort enrollment'))
    statuses={'PRE-00':'PASS_SCOPED','P0-ALG':'PASS_SCOPED_PARTIAL_OPEN_ENGINEERING','P0-OWNER':'PASS_SCOPED_SOURCE_GAPS','P0-AMOUNT':'AMOUNT_A_OPEN_PRECISE_BLOCKER','P1-COHORT':'COHORT_ENGINEERING_PASS_SCOPED_NO_ASOF_OWNER','P1-PRODUCT-QA':'UI_CURRENT_SNAPSHOT_PASS_SCOPED'}
    for row in stage['stages']:row['acceptance']=statuses[row['stage']]
    stage['finished_at']=datetime.now(timezone.utc).isoformat();stage['current_engineering_complete']=False
    write(OUT/'STAGE_LEDGER.json',stage)
    p=OUT/'04_P0_AMOUNT/P0_AMOUNT_AUTHORITY_DIFF.md'
    p.write_text(p.read_text(encoding='utf8').replace('9/30 and 10/08 are OPEN until exact frozen cross-source bindings are recovered and compared.','9/30, 10/08 and 10/09 frozen captures are now compared (15,632 comparable rows). 345 residual differences remain INSUFFICIENT_EVIDENCE; a binary32 representation match does not establish economic-feed equivalence.'),encoding='utf8')
    ledger=load(OUT/'08_REMAINING_LEDGER.json')
    ledger['appended_R3'][0]['scope']='Remaining ATR/structural input proof, first pulse baseline, full LOO rank and recursive baskets'
    write(OUT/'08_REMAINING_LEDGER.json',ledger)
    markdown(OUT/'06_P1_PRODUCT_QA/PRODUCT_QA_RESULT.md',f'# Current accepted snapshot QA R3\n\n42 routes and six RAW/QFQ daily/weekly/monthly chart contracts checked, zero API errors; exact route records and numeric source samples are in JSON. 322 electric-equipment members conserve pagination. Strongda 301628 remains INVALIDATED and exited. Future unpublished date and stale-token negative checks pass.\n\n{len(dom)} actual browser DOM records: six entries at 1366×768 and 1920×1080; search/detail/paging, historical switch/reload, single-route fault and recovery. Injected transport failures are explicitly QA-only; real SOURCE_INCOMPLETE remains separate. Browser DOM proves rendered content; it does not sign full independent FP13/FP14 or comprehensive visual-layout acceptance. Source explanation and competition/health source gaps are separately OPEN.\n')
    markdown(OUT/'00_EXECUTION_RESULT_R3.md',f'''# V4 Immediate R3 执行结果（范围化工程证据）

合同 V4-IMMEDIATE-R3-20261010；T0=2026-10-09。BASE_SHA={stage['BASE_SHA']}。本报告不代签外部验收，不启用新生产域。

| 工作包 | 当前结果 | 精确限制 |
|---|---|---|
| P0-ALG | {alg['checks']} 独立比较、{alg['errors']} 差异，PASS_SCOPED | ATR/结构输入、首次 pulse 和完整 LOO 排名递归尚需独立闭环，工程总体仍 OPEN |
| P0-OWNER | 349 原始成员→322 已映射+27 逐条待证；已有字段来源/API/DOM贯通 | 27 条 INSUFFICIENT_EVIDENCE；板块成熟度/健康度无正式日期 Owner，精确 SOURCE_INCOMPLETE/UNKNOWN |
| P0-AMOUNT | 三实际日期15,632条可比较，14,292条 binary32精度匹配、995条完全相同 | 345条待解释；Amount A独立审计 OPEN，不切换Native权限 |
| P1-COHORT | 新冻结读取契约、去重/改写拒绝/交易会话成熟规则；73项回归通过 | NO_ASOF_OWNER；FEP模型与权限 NOT_READY，无历史正式入组或真实预测 |
| P1-QA | 42路由、6种行情、六入口双尺寸DOM及隔离故障恢复 | 当前快照范围化PASS；独立FP13/FP14仍未授权 |
| PIT inventory | 五日期88条Owner清单 | corrected/latest reconstructed不等于历史AS_RECORDED，严格PIT缺口保留 |

生产Head、严格Head和10/09回执逐字节SHA保持不变。通达信只读；不生成10/12实际日更。各代码提交在Git中可追踪；归档复核小包含stdlib离线oracle和冻结输入，上传/回读收据单独记录精确RESULT_SHA。

R2旧oracle使用原SHA绑定，未冒充本轮重跑；R3脚本不导入被测业务计算模块。独立对比的零差异只支持列明字段。当前未完成项目和下一动作见08_REMAINING_LEDGER.json，外部方据此分别判定PASS_SCOPED/FAIL/NOT_VERIFIABLE。
''')
    manifest=[binding(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('EVIDENCE_SHA256_MANIFEST.json','DRIVE_DELIVERY_RECEIPT.json')]
    write(OUT/'EVIDENCE_SHA256_MANIFEST.json',dict(items=manifest,protected=stage['protected']))
    archive=Path('G:/codex_tmp/V4_IMMEDIATE_R3_REVIEW_20261010.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and p.name!='DRIVE_DELIVERY_RECEIPT.json':z.write(p,p.relative_to(OUT))
    assert archive.stat().st_size<10*1024*1024
    offline=Path('G:/codex_tmp/test_temp/r3_offline_'+datetime.now().strftime('%H%M%S'));offline.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:z.extractall(offline)
    runs=[]
    for folder,script,inputname in [('02_P0_ALG','P0_ALG_FULL_RECURSION_ORACLE.py','P0_ALG_ORACLE_INPUT.json'),('04_P0_AMOUNT','P0_AMOUNT_INDEPENDENT_ORACLE.py','P0_AMOUNT_SOURCE_COMPARISON.json')]:
        proc=subprocess.run([sys.executable,str(offline/folder/script),str(offline/folder/inputname),str(offline/folder/'rerun.json')],capture_output=True,text=True)
        assert proc.returncode==0,proc.stderr
        runs.append(dict(script=script,exit_code=proc.returncode,stdout=proc.stdout.strip()))
    write(OUT/'OFFLINE_REVIEW_RECEIPT.json',dict(archive=binding(archive),runs=runs,report=binding(OUT/'00_EXECUTION_RESULT_R3.md')))
    print(json.dumps(dict(archive=binding(archive),runs=runs),ensure_ascii=False))

if __name__=='__main__':main()
