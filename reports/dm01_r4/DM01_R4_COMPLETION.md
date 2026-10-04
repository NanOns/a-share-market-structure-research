# DM01-R4 完成与独立外审交接

DM01_R4_GO_FORWARD_RUNTIME = PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

执行范围为日历、当前 V2 父头、R4 PIT 包装、九组件接线及 V2 机器晋级策略。R3/R3_3 业务函数与独立数值检查源码未改动。日历由保存的沪深官方原文支持，覆盖至 2026-12-31；版本头为 LOCAL_READY_FOR_EXTERNAL_AUDIT，外部接受尚未发生。

真实当前 Data Head 仍为 V2/2026-09-30。2026-10-08 返回 WAIT_MARKET_CLOSE，源请求为 0，真实候选未创建，Data/Stage/Dev 头未移动。九组件证据为 2026-09-28 的显式工程模拟，不能当作真实 PIT 或 Shadow 证据。晋级状态机模拟替换了 PIT/外审/父头/日历准入依赖，未替换九组件业务函数和交叉数值检查；原始准入层的拒绝测试另行记录。

本地与独立干净检出均执行 2006 项：1977 通过，26 失败，3 跳过。R4 的 25 项全部通过，22 个强制向量全部覆盖。26 个失败节点已在 41d40692149055b7518751ff0916dbc0e2ff0d12 基线逐项重跑，结果完全一致；本轮无新增失败。原始 pytest 退出码为 1，因此这不是完整全绿回归。历史债务与并行 V1 框架已登记为独立审计项，等待各自范围的修复与接受。

精确最终受测源码：2b0436022112a8d3b1fe4d3fb50ad2f38d9764d2。
受测标签：codex/dm01-r4-go-forward-runtime-tested-source-20261005。
之后只允许 TESTED_SOURCE_GOVERNANCE.json 中列出的证据闭合文件变化。

外审后启用要求：精确的独立外审文档须给出 PASS_DM01_R4_GO_FORWARD_RUNTIME，并在文档内绑定 runtime_contract、promotion_policy、calendar_head 的 SHA256；机器接受头须为 EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME，三项绑定均须与受测版本一致，permissions 三项保持 false。本轮不创建此接受头，任务卡与本轮自检不能充当外部接受。后续日历版本、不同 GBBQ 分类或来源权威变化不能绕过相应接受门。

CALENDAR_AUTHORITY = LOCAL_READY_FOR_EXTERNAL_AUDIT
CURRENT_V2_PARENT_ROLLOVER = PASS_LOCAL_REPAIRED
GO_FORWARD_PIT_LINEAGE = PASS_LOCAL_REPAIRED
ALL_NINE_DAILY_WIRING = PASS_LOCAL_REPAIRED
ROUTINE_V2_PROMOTION_POLICY = PASS_LOCAL_REPAIRED
REAL_TARGET_SESSION_PACKAGE = NOT_CREATED
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0
NEXT = STOP_WAIT_DM01_R4_INDEPENDENT_EXTERNAL_AUDIT

代码与证据提交、推送不等于外部接受，也不授权进入 R25 或 Real Shadow。
