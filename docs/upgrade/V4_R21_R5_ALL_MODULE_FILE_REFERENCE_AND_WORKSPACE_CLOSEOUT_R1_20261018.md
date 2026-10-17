# V4 R21-R5 全模块文件引用与 Workspace 集中实修收尾

- 日期：2026-10-18；分支：`codex/v4-workspace-cleanup`。
- 状态：`CODE_SCOPE_PG_BOUND_CANDIDATE_COMPLETE / LIVE_PG_PASS / BROWSER_PARTIAL / FORMAL_HEAD_RECONCILIATION_PENDING`。
- 范围：本轮继续修复现役 V4 的历史源 ingress、Operational Owner authority、Workspace 来源路径与前端调用链；非 V4 调用点仅登记。

## 代码与调用点

- V4 P1 基线 266 个调用点中，265 个现有调用链已具备 PG-bound candidate/consumer 路径；1 个非 V4 调用点登记为 out of scope。历史 inventory 有 22 条 reference edge 无精确 join，故正式 Head/source-edge reconciliation 仍为 0/266，不能声称正式发布闭环。
- 修复 `v4_historical_source_ingress_pg_r1.py::ingest_file`：仅在显式 Head/candidate source-ingress、精确 SHA 校验失败时解析 Git LFS pointer，读取对应 `.git/lfs/objects` 缓存并校验 pointer SHA、文件 bytes 与对象 SHA；数据库消费者不回读工作区。
- 修复 `v4_operational_owner_authority_v2.py` 的旧 Owner predecessor 兼容：支持 `V4_DATED_OPERATIONAL_RECONSTRUCTED_OWNER_V1`，逐 Owner source binding 从精确 PG ingress 读取；按 predecessor binding/digest 记录 ingress receipt。
- 新增 `prepare_legacy_candidate`，按精确 Head 与 predecessor JSON bindings 构建 Owner authority 和 candidate-only successor；验证权威清单及 candidate canonical PG readback。未创建/更新 accepted Head。

## 共享 PostgreSQL 实际读写

- 实例：`127.0.0.1:5432/market_research`，OID `646711`；Schema `v4_forward_812843566da3f180`。
- 输入：`data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json` SHA `55d78be5…acf4dc83e`（29,799 bytes）；predecessor `data/v4/predecessors/e751fb6e…d853c8.json` SHA `e751fb6e…d853c8`（17,096 bytes）。
- 完成 88 个 Owner domain fact append；创建数 88、复用数 0。Authority manifest fact key `ec708c8f…d67e15e`；successor candidate fact key `19b26172…21d1d2`；二者 canonical PG readback 通过。
- 本次迁移回执为 `publication=false`、`accepted_head_changed=false`。上一轮日更 source candidate、TDX snapshot/package 等 PG append/readback 结果见前序升级记录；本轮未另起实例或端口。

## 28766 真实浏览器验收

开发服务 `127.0.0.1:28766`；生产 `28765` 未触碰。

- 首页、市场与事件、Focus/Forward、Diagnostics（Health/Jobs/Sources/Contracts）、股票列表/详情及板块列表/详情真实加载并交互。详情数据保持候选快照标记 `PG 候选快照 · 不代表正式 Head`。
- 板块详情「区域地产」43 个成员；搜索「中华企业」精确返回 1 条（SH.600675，收盘 2.520），通过可见链接进入股票详情。
- 个股详情可见 2026-09-30 数据、OHLC/指标、研究状态、来源按钮；周期选择从日线变为周线。但周期变更后图表区域保持「正在读取研究数据…」，该功能未验收通过。
- 比较页显示 `2026-09-30`、严格 PIT 可用日期 0、重建版本且明确声明 PIT 不可用。冻结回放「时序身份与缺口」实测返回 `AS_RECORDED=false`、`PG_CANDIDATE_SNAPSHOT`，正确拒绝将重建快照伪报为 PIT。
- 28766 PID `42876` 是本轮代码改动前启动的服务进程。尝试停止该精确 PID 被自动审查拒绝；没有以替代命令绕过，所以当前服务没有加载本轮新后端。浏览器通过仅证明当时服务运行版本的 UI/API 行为；新 Owner ingress 路径以 PG 写入/读回收据验证。

## 剩余开放点

- 正式 266 条 callsite 与 source edge、accepted publication Head、T0/namespace 的 reconciliation 仍开放；22 条 edge unmapped，PG 当前没有 accepted operational publication Head。本轮不构造来源身份、不做 Head CAS。
- 周线图表操作后图表组件停留在加载态；须在允许加载新后端的 28766 实例后进一步确认并修复。如仅前端代码即可定位则继续归属本批；如需重启现服务，当前自动审查对停止 PID 42876 的精确动作拒绝，不能把未加载新代码的浏览器结果算作本批后端验收。
- 本轮未运行全仓基线扫描、GitHub CLI 流程测试、完整测试套件或 GitHub Actions；仅保留语法编译、diff 检查、staged policy 与浏览器操作。
- 不在本轮执行正式 Head 切换、生产 28765 部署、物理删除、历史改写或强推。提交推送只代表代码已送达分支，不代表正式数据发布或生产验收。

## 检查与交付

- 保留 5 个已有无关 untracked 文件，未暂存。
- 代码与本报告将经 repository staged policy 后正常提交并推送至 `codex/v4-workspace-cleanup`。
