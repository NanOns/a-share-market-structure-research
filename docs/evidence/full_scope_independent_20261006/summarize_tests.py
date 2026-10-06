"""Summarize actual JUnit outcomes, never convert skips/errors into passes."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from write_reports import atomic,EVIDENCE,HEAD

def classify(text):
    if any(v in text for v in ('ISOLATED_FIXTURE_NAMESPACE_ONLY','ISOLATED_TEST_NAMESPACE_REQUIRED')):
        return 'RUNNER_TEMP_NAMESPACE_GATE_REJECTION'
    if "No module named 'scripts'" in text:
        return 'STANDALONE_CLI_PACKAGE_BOOTSTRAP_FAILURE_IA10'
    if 'ModuleNotFoundError' in text:
        return 'MISSING_RUNTIME_DEPENDENCY'
    if 'UnicodeDecodeError' in text:
        return 'RUNNER_SUBPROCESS_ENCODING_FAILURE'
    if any(v in text for v in ('UNAUTHORIZED_V4_13_STAGE','CURRENT_STAGE_NOT_ACCEPTED')):
        return 'HISTORICAL_OWNER_STAGE_AUTHORITY_REJECTION_REQUIRES_TRIAGE'
    if any(v in text for v in ('OperationalError','ConnectionRefusedError','connection refused','actively refused','10061','connection failed:')):
        return 'DATABASE_OR_SERVICE_ENVIRONMENT_FAILURE'
    if 'FileNotFoundError' in text or 'No such file or directory' in text:
        return 'MISSING_FIXTURE_OR_ARCHIVE_REQUIRES_TRIAGE'
    if any(v in text for v in ('EXACT_BYTE','ACCEPTED_BINDING','SHA_MISMATCH','BYTES_CHANGED','sha256','sha=')):
        return 'EXACT_IDENTITY_OR_BINDING_ASSERTION_REQUIRES_TRIAGE'
    if 'AssertionError' in text or 'assert ' in text:
        return 'ASSERTION_DIFFERENCE_REQUIRES_CONTRACT_SCOPE_TRIAGE'
    return 'EXCEPTION_REQUIRES_CONTRACT_AND_ENVIRONMENT_TRIAGE'

def read(name):
    root=ET.parse(EVIDENCE/name).getroot()
    cases=list(root.iter('testcase'));counts=Counter();modules=defaultdict(Counter);failures=[];skips=[]
    for case in cases:
        kind='passed'
        detail=None
        for candidate in ('failure','error','skipped'):
            child=case.find(candidate)
            if child is not None:
                kind={'failure':'failed','error':'errors','skipped':'skipped'}[candidate]
                detail=child;break
        module=case.get('classname','UNKNOWN');counts[kind]+=1;modules[module][kind]+=1
        if detail is not None:
            node=module.replace('.','/')+'.py::'+case.get('name','') if case.get('classname') else case.get('name','').replace('.','/')+'.py'
            record=dict(nodeid=node,classname=module,name=case.get('name'),outcome=kind,message=detail.get('message',''),detail=detail.text or '')
            if kind=='skipped':skips.append(record)
            else:
                record['triage_hint']=classify(record['message']+'\n'+record['detail']);failures.append(record)
    counts['testcases']=len(cases)
    return dict(xml=name,counts=dict(counts),suite_attributes=[dict(s.attrib) for s in root.iter('testsuite')],by_module={k:dict(v) for k,v in sorted(modules.items())},failures=failures,skips=skips)

def main():
    results={k:read(v) for k,v in [('default_global','pytest_full.xml'),('selected_stages_fep','pytest_stages.xml'),('m14_direct','pytest_m14.xml'),('namespace_recheck','pytest_namespace_recheck.xml')]}
    failure_inventory={k:dict(failures=v.pop('failures'),skips=v.pop('skips')) for k,v in results.items()}
    summary=dict(audit_head=HEAD,runs=results,partial_global=dict(status='INTERRUPTED_NOT_COMPLETED',complete_junit=False,counts=None,evidence='global_rerun_interruption.json'),triage_policy='Hints are text-based navigation only, not defect acceptance, expected-failure approval, or historical supersession. No failed test was hidden or marked passed.')
    atomic(EVIDENCE/'pytest_summary.json',(json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    atomic(EVIDENCE/'pytest_failure_inventory.json',(json.dumps(failure_inventory,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    a=results['selected_stages_fep']['counts'];m=results['m14_direct']['counts']
    attrs=results['selected_stages_fep']['suite_attributes']
    time=sum(float(s.get('time',0)) for s in attrs)
    categories=Counter(r['triage_hint'] for r in failure_inventory['selected_stages_fep']['failures'])
    rows='\n'.join(f'| {k} | {v} |' for k,v in categories.items())
    fail_modules=[(k,v) for k,v in results['selected_stages_fep']['by_module'].items() if v.get('failed',0) or v.get('errors',0)]
    module_rows='\n'.join(f"| {k} | {v.get('passed',0)} | {v.get('failed',0)} | {v.get('errors',0)} | {v.get('skipped',0)} |" for k,v in fail_modules)
    ns=results['namespace_recheck']['counts']
    skip_counts=Counter(x['message'] for x in failure_inventory['selected_stages_fep']['skips'])
    skips='；'.join(f'{n}项：{reason}' for reason,n in skip_counts.items())
    text=f'''默认全仓命令：`python -m pytest -q --basetemp tmp/full_scope_audit_pytest_20261006 --junitxml=docs/evidence/full_scope_independent_20261006/pytest_full.xml`。退出1；collection error 1：`tests/upgrade_m14/test_online_batches.py:9`导入退役`_commit_raw_and_batch`失败。未进入全套测试，不能报全仓passed。既有GLOBAL-PYTEST item OPEN/NOT_ACCEPTED范围继续保留，不恢复被禁止的热榜落盘入口来迎合旧测试。

继续收集全仓复跑：加`--continue-on-collection-errors`。发现旧M12浏览器fixture启动实际工作区DB的恢复入口后中止，partial log最后84%，**无完整JUnit/无完整结果，计数不报告**。IA-09记录隔离问题及无法证明零DB写的取证局限。

随后显式选取阶段/FEP相关目录及root stage tests，见`stage_test_selection.json`与`run_stage_tests.py`：首轮**{a.get('passed',0)} passed / {a.get('failed',0)} failed / {a.get('errors',0)} errors / {a.get('skipped',0)} skipped**，JUnit testcases={a['testcases']}，耗时约{time:.2f}秒。这是**限定阶段测试复验，不是全仓绿**。没有把排除的legacy UI/upgrade/root范围计为通过。

首轮68项namespace失败由本轮runner配置触发：E盘basetemp不在`tempfile.gettempdir()`或固定engineering-fixture根下；不是已证明业务bug。按项目E/F政策把child TEMP/TMP与basetemp统一到`E:/codex_tmp/test_temp`，仅重验`test_r20r1r1_maturity.py`及`test_r20r1r2_dm01.py`，结果**{ns.get('passed',0)} passed / {ns.get('failed',0)} failed / {ns.get('errors',0)} errors / {ns.get('skipped',0)} skipped**，选择/环境见`namespace_recheck_selection.json`。首轮失败不删，复验不与首轮简单累加作独立样本，也不重签全仓绿。

M14针对性命令：`python -m pytest -q tests/upgrade_m14/test_hot_rank_api.py tests/upgrade_m14/test_hot_rank_capture_retired.py --basetemp tmp/full_scope_m14_direct_20261006 --junitxml=docs/evidence/full_scope_independent_20261006/pytest_m14.xml`。结果{m.get('passed',0)} passed / {m.get('failed',0)} failed / {m.get('errors',0)} errors；使用fake fetchers，无真实在线重新抓取。

阶段测试失败导航（按异常文本生成hint，**不是自动认定代码bug或允许忽略**；逐node完整message/traceback、skip原因保留于`pytest_failure_inventory.json`）：

| 初步导航分类 | 条数 |
|---|---|
{rows}

有失败/错误的模块统计（其余通过模块见`pytest_summary.json.by_module`）：

| 模块 | passed | failed | errors | skipped |
|---|---|---|---|---|
{module_rows}

实际skip原因：{skips}。其中缺canonical fixture/DSN的PG用例没有执行，不是DDL PASS；本轮没有记录到PG连接错误，不能把38个UNAUTHORIZED_V4_13_STAGE setup errors误写成PG errors。另有5项E3/E4模型测试因当前Python缺sklearn失败、1项DM01 subprocess因GBK解码失败；DM01独立CLI缺repo-root bootstrap的1项失败通过只读--help复验确认（IA-10）。历史PG fresh/upgrade外审只支持原scope，不当作本轮实际部署验证。旧frozen身份/当前supersession差异必须沿合同逐项审查，不因大量失败批量撤销历史接受；同时也不能无确认一概标成“预期失败”。

运行环境：Windows/PowerShell，Python 3.13.14；临时文件在工作区E盘tmp，TDX输入只读。独立semantic probes是synthetic反例、非real统计证据；测试成功不替代独立外审、真实样本、回滚演练或真实迁移验收。
'''
    atomic(EVIDENCE/'TEST_RESULTS.md',text.encode('utf8'))
    print(json.dumps(dict(counts=a,categories=dict(categories),failing_modules=len(fail_modules)),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
