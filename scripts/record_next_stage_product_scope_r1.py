"""Render the observed scope, keeping HTTP, module tests and UI separate."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.record_next_stage_contract_r1 import text, OUT
from workbench_analysis.v4_14_replay_io import ref, publish


def main():
    for name in ('TMP','TEMP','TMPDIR'):
        os.environ[name]='G:/codex_tmp'
    result=json.loads((ROOT/OUT/'D_HTTP_READBACK.json').read_bytes())
    text(OUT+'/D_MODULE_SEMANTICS_JUNIT.xml',Path('G:/codex_tmp/next_stage_ui_junit.xml').read_bytes())
    rows=[]
    for item in result['receipts']:
        if '/api/v4/' not in item['url'] or item['status']!=200:
            continue
        route=item['url'].split('/api/v4/')[1].split('?')[0]
        status=item['business_status']
        meaning='事实可读；未知字段仍逐项保留' if status in ('READY','EMPTY_VALID') else '缺源域不可计算；不阻塞其他研究区块'
        rows.append(f"| `{route}` | {item['status']} | {status} | {item.get('total')} | {meaning} |")
    text(OUT+'/D_PRODUCT_SCOPE_MATRIX.md','# FP13 已投产研究读取范围矩阵\n\n'
        '证据 D_HTTP_READBACK.json：68个有界真实HTTP请求及原字节SHA；当前T0=2026-10-09，token=受保护运营Head。HTTP200仅证明响应成功，计算READY与SOURCE_INCOMPLETE分别列出。\n\n'
        '| 真实请求域 | HTTP | 业务状态 | 数量 | 解释 |\n|---|---|---|---|---|\n'+'\n'.join(rows)+
        '\n\n六页面HTML与六个当前JS模块原字节已读回；模块SHA与本地相同。1366/1920本轮真实DOM/截图均未通过：IAB报net::ERR_BLOCKED_BY_CLIENT，Chrome不可用。不得把HTTP或模块测试写成双视口产品验收。\n\n'
        '当前单独可提审范围：股票事实/日周月行情、板块当前事实/成员、市场事实、Focus受限研究读取、诊断来源、历史corrected日期读取；均仍受原权限合同限制。FP13完整产品签收及FP14_FULL不签PASS。\n')
    text(OUT+'/D_CURRENT_UI_SEMANTIC_QA.md','''# 当前研究UI语义核验

本轮68真实HTTP请求无HTTP状态/日期绑定错误；原始回执见D_HTTP_READBACK.json。当前事实：5224股票、400板块、2805条Focus受限研究清单；这些是研究对象/标签，不能表述为正式观察分母或提前捕捉成功。

实际六种图表：D/W/M × RAW/QFQ，行情非空、真实数值、末日不晚于10/09；历史10/08和9/30请求逐项绑定所选日期，中文名/代码搜索找到相同实体。Focus Episode/anchor/逐日路径/outcome各接口可读，不证明正式Cohort入组或独立成熟样本。市场和首页变化路径可读；个股timeline EMPTY_VALID不代表完整结构/Anchor事件功能已补齐。

旧token返回409 CONTEXT_TOKEN_MISMATCH；10/12股票与Cohort请求400 TARGET_DATE_NOT_GRANTED。10/08候选缺源保持NOT_CAPTURED；10/09 cohort research_signal_count=20896、research_eligible_count=300，observed_count/matured_count=null、正式写入false。缺源Forward/统计/结算/FEP仍SOURCE_INCOMPLETE，HTTP200不算计算READY。

当前JS原字节与服务返回一致。D_MODULE_SEMANTICS_JUNIT.xml的5项实际模块测试确认：HTTP200缺Owner转组件503、临时503只允许显式重试、未失败区块继续读取、409/400保持错误类别、日期/token绑定、AbortError不回退陈旧数据。app.js各section独立ErrorState提供“重试”，读源失败不默认全页面UNKNOWN；模块测试不等于浏览器交互。

来源时钟：旧生产Python未加载新字段，候选冻结/来源再观察时间仍不能用当前UI证明。isolated Python加载见B_ISOLATED_PYTHON_LOAD_HTTP.json；源截止日期不能充当历史first_available。该加载没有重启28765。

浏览器证据限制：本轮IAB打开localhost被net::ERR_BLOCKED_BY_CLIENT拦截；inventory仅IAB/MCP Apps，Chrome不可用。1366和1920真实布局、截图、浏览器503点击重试/组件隔离、跨日实际DOM切换和离线路径仍PENDING_BROWSER_SURFACE。未借旧截图补本轮PASS，也未绕过浏览器限制。

下一阶段：独立审核可读业务scope；接通本机浏览器表面后补双视口DOM/截图与交互验收。FP13整体和FP14全量发布保持未获准。
''')
    text(OUT+'/D_REMAINING_PRODUCT_FUNCTIONS.md','''# 剩余业务功能与独立关闭条件

| 项目 | 当前事实 | Owner/关闭条件 |
|---|---|---|
| 双视口浏览器/离线 | 本轮localhost被拦截，无Chrome | 浏览器执行环境Owner；1366/1920真实DOM/截图和离线、错误重试验收 |
| 个股结构事件/Anchor完整时序 | 当前stock timeline为空；profile和图表可读 | 真实结构/事件Owner、Why Now/失效条件逐字段原件与UI验证 |
| 板块完整D2与成熟跟踪 | 研究当前事实可读，正式六字段未准入 | C Creation-bound Genesis，逐字段独立来源审查，真实到期结算 |
| 严格历史PIT回放 | SOURCE_INCOMPLETE | 首获成员/模型/State/Event/benchmark原件；corrected研究历史不补PIT |
| 正式Cohort/Forward统计 | Owner/Grant缺源 | A真实首获+独立Writer Grant；T+1/3/5真正成熟后再统计 |
| Focus写入及旧历史核对 | 受限研究清单和路径可读 | 独立核对旧历史/生产Source cutover，事务准入；不能由研究2805行开放写入 |
| FEP预测六字段 | SOURCE_INCOMPLETE/null | E可信Registry/Prediction/matured FIT/Grant，独立支线 |
| 原因/等待/失效全字段中文可用性 | 原110字段库存不是全字段UI验收 | 产品字段Owner + 全字段真实源/浏览器覆盖；缺Owner按区块建债 |
| 分钟触板/官方媒体/当前LOO | 无新正式Owner证据 | 分别按批准来源范围接入并独立验收，不恢复退役V3数据库 |
| 全量导出/新日实际全链 | 本轮未把全量导出或未来日演练算现场成功 | 合法真实新T0日更、导出与回退读回；合成夹具只算工程 |
| 来源冻结/再观察时钟展示 | 新Python仅隔离加载 | B安全部署计划+另行生产加载授权+实际UI回读 |

旧FP13 QA13-01～08审计项保持独立；本轮当前事实可以更新各读域，但不覆盖历史冻结裁决。缺Owner字段不得反复导致所有页面UNKNOWN。
''')
    text(OUT+'/D_FP14_RESTRICTED_RESEARCH_RELEASE_CONTRACT.md','''# FP14 受限研究范围提审/回滚合同（准备，未发布）

候选范围只含当前运营研究读取股票/行情、板块当前事实和成员、市场事实、Focus受限读取、诊断和corrected历史日期。FEP、正式D2、正式Cohort/胜率、严格PIT回放没有准入。精确代码/源SHA见阶段索引与B_ISOLATED_PYTHON_LOAD_HTTP.json；部署时必须锁定最终release commit，不把磁盘HEAD当运行loaded SHA。

进入条件：该scope独立Source/API审核、双视口真实UI验收、no active job、两Head备份、明确用户生产加载窗口。HTTP/pytest通过不是产品scope签字。本轮界面验收未齐，FP13_PRODUCT_SCOPE_SIGNOFF=PENDING，FP14_RELEASE_SCOPE_SIGNOFF=NOT_GRANTED。

回滚按B_SAFE_SCOPE_DEPLOYMENT_PLAN.md：在G:保存exact旧源码/配置及两Head只读备份；失败恢复旧运行版本与配置，保留新捕获字节和CAS现场，不覆写合法新Head。复验PID/端口、六入口、源时钟、token/日期边界及last-good。绝不写TDX。本轮无部署、无28765重启、无权限放宽。
''')
    publish(ROOT,OUT+'/D_GATE_DISPOSITION.json',dict(contract_id='FP13_RESEARCH_SCOPE_QA_DISPOSITION_R1',
        http_requests=68,http_read_facts='PASS_SCOPED',module_tests=5,
        junit=ref(ROOT,OUT+'/D_MODULE_SEMANTICS_JUNIT.xml'),
        browser_viewport_1366='PENDING_BROWSER_SURFACE',browser_viewport_1920='PENDING_BROWSER_SURFACE',
        FP13_full='NOT_GRANTED',FP13_product_scope_signoff='INDEPENDENT_REVIEW_REQUIRED',
        FP14_release_scope_signoff='NOT_GRANTED',production_restart=False,external_acceptance=False))
    print('D matrix, semantic QA, remaining functions and restricted release contract recorded')


if __name__=='__main__':
    main()
