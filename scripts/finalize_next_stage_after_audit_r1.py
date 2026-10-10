"""Seal scoped engineering delivery. Never issues independent acceptance."""
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.record_next_stage_contract_r1 import text, OUT, BASE
from workbench_analysis.v4_14_replay_io import publish, ref


def main():
    for name in ('TMP','TEMP','TMPDIR'):
        os.environ[name]='G:/codex_tmp'
    xml=Path('G:/codex_tmp/NEXT_STAGE_INTEGRATION_JUNIT.xml').read_bytes()
    suites=ET.fromstring(xml)
    count=sum(int(s.attrib.get('tests',0)) for s in suites.iter('testsuite'))
    failures=sum(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0)) for s in suites.iter('testsuite'))
    skipped=sum(int(s.attrib.get('skipped',0)) for s in suites.iter('testsuite'))
    assert count==87 and failures==skipped==0
    text(OUT+'/INTEGRATION_JUNIT.xml',xml)
    code=['src/workbench_analysis/state_publisher_bridge_v1.py',
        'src/workbench_analysis/next_t0_identity_preflight_v1.py',
        'src/workbench_analysis/operational_daily_executor_v1.py',
        'src/sector/episode_genesis_candidate_v2.py']
    heads=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
    before=json.loads((ROOT/OUT/'PROTECTED_HEAD_READBACK.json').read_bytes())['before']
    after={p:ref(ROOT,p) for p in heads}
    assert before==after
    scope_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    publish(ROOT,OUT+'/TEST_RESULT.json',dict(contract_id='NEXT_STAGE_INTEGRATED_ENGINEERING_TEST_RESULT_R1',
        python=dict(tests=count,failures=failures,skipped=skipped,junit=ref(ROOT,OUT+'/INTEGRATION_JUNIT.xml')),
        javascript=dict(tests=5,failures=0,junit=ref(ROOT,OUT+'/D_MODULE_SEMANTICS_JUNIT.xml')),
        prior_200='Previous engineering nodes, not independent full algorithm audit or trading samples',
        total_current_unique_engineering_nodes=92,formal_samples=None,external_acceptance=False,
        command='python -B -m pytest tests/test_state_publisher_bridge_v1.py tests/test_full_state_first_observed_v1.py tests/test_next_t0_old_identity_preflight.py tests/test_pre_next_t0_executor_chain.py tests/test_operational_daily_executor_v1.py tests/test_next_stage_c_episode_genesis.py tests/test_producer_bootstrap_v1.py tests/test_pre_next_t0_publisher.py tests/test_core_product_read_r1.py tests/test_core_product_focus_r2.py tests/test_pre_next_t0_history_and_clocks.py -q --basetemp=G:/codex_tmp/test_temp/next_stage_integration_r1 -o cache_dir=G:/codex_tmp/pytest_cache_next_stage_r1 --junitxml=G:/codex_tmp/NEXT_STAGE_INTEGRATION_JUNIT.xml'))
    publish(ROOT,OUT+'/FINAL_GATE_DISPOSITION.json',dict(contract_id='NEXT_STAGE_LAYERED_DISPOSITION_R1',
        exact_BASE=BASE,implemented_scope_head=scope_head,
        A='ENG_PRODUCER_READY_PASS_SCOPED',B='ENG_PREFLIGHT_PASS_SCOPED',
        C='ENG_EPISODE_INTERFACE_PASS_SCOPED',D='PASS_SCOPED_HTTP_MODULES_UI_PENDING',E='HOLD_CORRECT',
        ENG_PRODUCER_READY='EVIDENCE_READY_FOR_INDEPENDENT_REVIEW',
        REAL_FIRST_CAPTURE_SOURCE_REVIEWED='PENDING_REAL_SOURCE',STATE_SOURCE_ADMITTED='NOT_GRANTED',
        COHORT_WRITE_GRANT_SCOPED='NOT_GRANTED',SECTOR_D2_FIELD_ADMITTED='NOT_GRANTED',
        FP13_PRODUCT_SCOPE_SIGNOFF='PENDING_INDEPENDENT_REVIEW_AND_BROWSER_QA',
        FP14_RELEASE_SCOPE_SIGNOFF='NOT_GRANTED',FEP_PRODUCTION_AUTHORIZED=False,
        protected_heads=dict(before=before,after=after,unchanged=True),TDX_written=False,
        production_restarted=False,actual_grant_created=False,
        next_stage='Independent scoped audit, actual next T0 capture, separately authorized production load',
        actual_next_T0='2026-10-12_EXPECTED_PENDING',external_acceptance='NOT_SELF_GRANTED'))
    audits=[
        dict(id='NEXT-AUDIT-STATE-SOURCE-AUTHORITY',scope='PIT membership/model/State/event/benchmark and independent reviewer context',
            evidence='A_SOURCE_OWNER_MAP.json; A_REAL_SOURCE_GAPS.json; A_FORMAL_GATE_DISPOSITION.json',status='OPEN_REAL_SOURCE_AND_INDEPENDENT_REVIEW_REQUIRED',
            acceptance='Actual immutable originals plus authenticated independent source review. reviewer_role and synthetic Grant never authenticate production.'),
        dict(id='NEXT-AUDIT-OLD-HEAD-NEW-IDENTITY',scope='Main DD old identity scope versus next-day observed provider codes and legal identity candidate',
            evidence='B_OLD_HEAD_NEW_IDENTITY_NEGATIVES.json',status='OPEN_POLICY_SCOPE_REVIEW',
            acceptance='Actual next-day identity/member originals; independently approved contract before changing old main DD gate.'),
        dict(id='NEXT-AUDIT-LEGACY-QUALIFICATION',scope='Dated A05 missing_state and independent qualification compared with lifecycle',
            evidence='C_D2_SOURCE_AND_EPISODE_GENESIS_MAP.json',status='OPEN_1009_HISTORICAL_NOT_VERIFIABLE',
            acceptance='New actual dated originals; no cross-date inference from 9/24 golden.'),
        dict(id='NEXT-AUDIT-AMOUNT-H21',scope='Old September 20 first-asof members and future strict consecutive window',
            evidence='C_D2_FORMAL_VS_RESEARCH_ADMISSION.md',status='HISTORICAL_NOT_VERIFIABLE_FUTURE_ACCUMULATION_PENDING',
            acceptance='21 strict consecutive actual sessions and explicit independent Amount scope review; Native unrelated scopes continue.'),
        dict(id='NEXT-AUDIT-FP13-BROWSER',scope='1366/1920 DOM/screenshot/offline/error retry and semantic product completeness',
            evidence='D_CURRENT_UI_SEMANTIC_QA.md; D_REMAINING_PRODUCT_FUNCTIONS.md',status='OPEN_BROWSER_SURFACE_BLOCKED',
            acceptance='Actual local browser surface and both viewport receipts; HTTP/module tests do not replace UI.'),
        dict(id='NEXT-AUDIT-PYTHON-LOAD',scope='Actual running module SHA, candidate clocks and scheduler/source diagnostic loading',
            evidence='B_SAFE_SCOPE_DEPLOYMENT_PLAN.md; B_ISOLATED_PYTHON_LOAD_HTTP.json',status='OPEN_SEPARATE_AUTHORIZATION_REQUIRED',
            acceptance='Explicit user load window, no active job, backups, actual loaded SHA and readback; 28765 not restarted here.'),
        dict(id='NEXT-AUDIT-FEP-TRUSTED-SOURCES',scope='Accepted model Registry, Prediction Owner, matured FIT, trusted Head/CAS and Grant',
            evidence='E_HOLD_AND_ADMISSION_REQUIREMENTS.md',status='HOLD',
            acceptance='Independent per-capability trusted admission; no repeated null copies or probability/maturity claims.')]
    publish(ROOT,OUT+'/INDEPENDENT_AUDIT_ITEMS.json',dict(contract_id='NEXT_STAGE_SEPARATE_AUDIT_ITEMS_R1',
        items=audits,independent_from_engineering_acceptance=True,external_acceptance_issued=False))
    text(OUT+'/V4_NEXT_STAGE_AFTER_OVERALL_AUDIT_EXECUTION_RESULT_20261010.md',f'''# 大A V4：整体外审后下一轮执行结果 · 2026-10-10

已完成当前可执行的A/B/C工程、D真实HTTP与模块语义QA、E关闭要求；工程范围证据就绪，未自签外部验收。D的1366/1920真实浏览器验收仍PENDING：IAB访问localhost被拦截，Chrome不可用。完整V4/FP13/FP14与真实新T0首获没有因此获得PASS。

| 范围 | 本轮交付与验证 |
|---|---|
| Task 0 | fetch后exact_BASE `{BASE}` 与卡BASE一致，新增差异为空；单一9行能力账本逐行owner/source/code SHA/阻断/next action/未来日期；优先使用前轮final且保留原件 |
| A | 真gzip Publisher→quarantine→受控候选→FirstObserved→完整资格ledger→独立合成GRANT preflight→prepare；真实build()四场景合成E2E，固定正负组；原300 TRUE固定+随机去重35项原AST/target_values独立数值oracle通过，未重算全市场 |
| B | 原DD旧identity闸不放开；新当天代码失配有明确diagnostic，不误判provider unavailable；两Head/两成员版本和源不齐已得字节保留负例；18:35及全部重试运行手册、安全加载回滚；28768隔离当前Python只读加载且关闭、无DailyJobs worker |
| C | 六字段来源/Genesis map；Creation-bound成员、原失效AST、scenario priority和V4-15 due plan；NO_PRIOR_EPISODE/PENDING/UNKNOWN与合法settlement隔离E2E；独立RS 41,790与q20/dq5_3 800项0差异；9/24黄金只引用，不扩到10/09 |
| D | 68真实28765只读HTTP，六入口、搜索/历史/Focus路径/市场诊断、D/W/M×RAW/QFQ六行情，409/400边界及SOURCE_INCOMPLETE分层；5实际JS模块错误/重试/日期/cancel测试；双视口DOM/截图未完成 |
| E | 一页hold；FEP OFF、六字段null，等可信Registry/Prediction/matured FIT/独立Grant；不重复300个权限检查，不阻塞无关Native研究读取 |

集成回归87 Python PASS + 5 JavaScript PASS（0失败/跳过）；工程节点不是92笔交易。前轮200 pytest也不是交易样本。300 TRUE是股票×场景研究标签，79或任何历史Focus计数不充正式成熟分母。实际10/09仍RECONSTRUCTED_RESEARCH_ONLY/SOURCE_GAPS，正式Cohort观察及成熟分母null。

受保护运营Head SHA `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`、严格Head SHA `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40` 前后完全一致；稳定28765 PID42552未重启，TDX未写入。所有本轮temporary/test/cache均G:。Windows读取深层夹具时使用命令级 `git -c core.longpaths=true`，本轮未修改全局Git/系统设置；证据与新接口设exact-byte属性并逐Git blob复验。

正式层级：ENG_PRODUCER_READY证据就绪 → REAL_FIRST_CAPTURE_SOURCE_REVIEWED待真源 → STATE_SOURCE_ADMITTED未授予 → Cohort Writer/D2字段未授予 → FP13/FP14 scope signoff待独立审核；FEP生产仍独立关闭。reviewer_role文本和合成Grant不构成生产认证，新接口没有接生产独立签发服务。

下一真实会话预计10/12：沿既有DailyJobs实际18:35开始、19:05/19:35/20:05/20:35/21:05/22:05重试，现场保留请求/接收/首获SHA和原件，逐源审same-day Identity/member/GBBQ/BaoStock/State/sector；不改系统时间、不称15:00已经知道、不要求首日成熟T+5。B_T0_CAPTURE_RUNBOOK.md含完整现场读表和失败保留last-good步骤。新增Python生产加载需单独明确授权，当前仅隔离预检。

请独立审核本轮源码、SHA夹具、oracle与分范围工程；不要将Git推送/Drive存档签为EXTERNAL_ACCEPTANCE_PASS。跨切面问题单列INDEPENDENT_AUDIT_ITEMS.json，完整产品缺口见D_REMAINING_PRODUCT_FUNCTIONS.md。Git/Drive原字节核验将记入DELIVERY_READBACK.json，正式MD与轻量证据归档同步现有Drive阶段文件夹。
''')
    files=[ref(ROOT,p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/OUT).rglob('*')) if p.is_file()]
    publish(ROOT,OUT+'/FINAL_EVIDENCE_INDEX.json',dict(contract_id='NEXT_STAGE_EXACT_EVIDENCE_INDEX_R1',
        exact_BASE=BASE,implemented_scope_head=scope_head,evidence=files,code=[ref(ROOT,p) for p in code],
        formal_admission=False,external_acceptance=False))
    print(json.dumps(dict(python=count,javascript=5,evidence_files=len(files),scope_head=scope_head)))


if __name__=='__main__':
    main()
