# FP14 受限研究范围提审/回滚合同（准备，未发布）

候选范围只含当前运营研究读取股票/行情、板块当前事实和成员、市场事实、Focus受限读取、诊断和corrected历史日期。FEP、正式D2、正式Cohort/胜率、严格PIT回放没有准入。精确代码/源SHA见阶段索引与B_ISOLATED_PYTHON_LOAD_HTTP.json；部署时必须锁定最终release commit，不把磁盘HEAD当运行loaded SHA。

进入条件：该scope独立Source/API审核、双视口真实UI验收、no active job、两Head备份、明确用户生产加载窗口。HTTP/pytest通过不是产品scope签字。本轮界面验收未齐，FP13_PRODUCT_SCOPE_SIGNOFF=PENDING，FP14_RELEASE_SCOPE_SIGNOFF=NOT_GRANTED。

回滚按B_SAFE_SCOPE_DEPLOYMENT_PLAN.md：在G:保存exact旧源码/配置及两Head只读备份；失败恢复旧运行版本与配置，保留新捕获字节和CAS现场，不覆写合法新Head。复验PID/端口、六入口、源时钟、token/日期边界及last-good。绝不写TDX。本轮无部署、无28765重启、无权限放宽。
