# V4 R21 R6 开发全权限与 PG 全链路实修报告 R2

- 阶段状态：`DEGRADED_PASS`。开发候选服务可读，部分权限边界与文件读取已修复；完整 workspace alias 迁移、真实 Owner/DEV Head 写读和全模块验收仍在推进。
- 授权依据：Drive 任务卡 `V4_R21_R6_开发全权限_工作空间清理_PG全链路与全模块连续实修总任务卡_R2_20261018.md`、长期开发授权 SOT R2。
- 生产边界：未切换或触碰 28765；仅在 28766 验证。未启用采集器、自动 worker 或生产 Head。

## 本轮代码实修

- `v4_native.configured_dsn()` 写连接仅接受显式 `V4_NATIVE_PG_DSN`；不再从 `WORKBENCH_PG_DSN` 回退推导写权限。补齐无本机 `.env` 污染的连接策略测试。
- 同步修正 V4 foundation、Focus schema、runtime heads 三个迁移入口，只从显式 `V4_NATIVE_PG_DSN` 获取写连接。
- 新增不暴露路径的 `logical_workspace_id`，同一 Git 项目搬迁目录后可保持稳定身份；现有物理 schema 仍按旧绝对根路径生成，PG alias 注册及调用方切换尚未完成，因此暂不改名或移表。
- SourceIngress 合同升至 1.1.0，兼容读取 1.0.0 并限制 64 MiB 内联数据；超大源包仍需后续受控的包/成员流式接入。
- Corrected Owner 与 R43 Owner 从 PG DM01 accepted Data Head 取快照及 SHA。个股图表去除非 PG 文件读取分支；无 PG 历史绑定时明确降级为 `SOURCE_INCOMPLETE / PG_HISTORY_BINDING_REQUIRED`。
- DM01 增量构建器的真实 Parent 校验也从 PG Head/ SHA 读回，不再重新读取 Data Head 本地文件；保留精确路径与摘要匹配。

## PG 与 28766 实况

- 数据库仍为唯一实例 `127.0.0.1:5432/market_research`（OID `646711`）。本轮执行了只读目录、来源覆盖及快照核查；未执行 DDL/DML、合同注册、Owner/Head 写入。正式 publications、publication heads、operational research heads、日历、universe、source packages/core results 等关键事实表仍为空；不能据此声称完整业务写读链已完成。
- 最新完整候选仍为 `v4_research_e30350bf444bbb9980cf3e2c`，T0 `2026-09-30`，5,213 股票、5,224 身份、378 板块、469 Focus、117 Forward、33 事件；仅为候选快照，不是正式 Head。
- 数据库虽有新行情行至 `2026-10-15`，但在无 snapshot manifest 的局部 schema 中最多覆盖 9 个证券（最新 schema 共 46,906 行，覆盖 `2026-09-28` 至 `2026-10-15`）。它不构成全市场完整 T0；严格 PIT 仍为 `PIT_NOT_PROVEN`，不得用于伪造接受状态。
- 只读查看 TDX `sh/sz/lday` 的 11,810 个沪深日线末记录，最新到 `2026-10-08` 的仅 8 个文件；`2026-09-10` 有 8,984 个文件。故未发现可替代 9-30 完整候选的更新全市场源快照。
- 在 `127.0.0.1:28766` 的候选 PG 服务上验证总览、股票、板块、Focus、市场/事件、诊断、Forward、日更预览。回放和个股比较页也已实际渲染：T0 `2026-09-30`、严格 PIT 可用日期 0；对照明确标注事后重建，展示股票区间收益 1.205% 与 2.011%，共同日期 `2026-09-29` 至 `2026-09-30`。日更页未接受日历、worker 未启动、写操作禁用。
- 当前运行环境没有显式 `V4_NATIVE_PG_DSN`（`configured_dsn()` 实测返回 `V4_NATIVE_PG_DSN_REQUIRED`）。遵守写连接边界，本轮不能执行 PG DDL/DML/合同注册/DEV Head；继续读核查、代码修复和 28766 测试。配置显式开发写 DSN 后即可续跑迁移及 Owner/Head 写读。
- 修改过的 Python 编译通过；连接/迁移、DM01 Parent 绑定及 PG schema 静态回归共 31 项通过。`tests/test_v4_universe_pg_r1.py` 因环境缺少 `cryptography` 未能收集；`tests/test_corrected_owner_replay_r4.py` 被仓库隔离插件以 `DISPOSABLE_PG_CLUSTER_REQUIRED` 阻断；均未绕过环境/隔离门禁。

## 工作空间与清理

- 新逻辑 workspace ID 为后续 alias 迁移提供稳定键，但尚未注册 PG alias；现有 Owner 映射按旧 root identity 授权，切换前仍需逐项保全并验证 schema/Owner 引用。
- 清除了 G 临时目录中已确认可重建的 pytest 缓存、纯 `.pyc` 与 pip 缓存，共 `2,674,361,197` 字节（约 2.49 GiB）；只 prune 指向缺失 checkout 的陈旧 Git worktree 登记，没有删除 checkout/源数据。TDX 只读源和用户未跟踪文件未动。
- 其他大型临时目录包含独有来源、测试证据、恢复包或带未跟踪源码的数据，未盲删；`r7_active_baseline_20261015` 需对其 5 个修改文件与 1,845 个未跟踪文件完成归属/回收核对。

## 后续必须继续的工作

- 建立稳定 workspace ID 到既有物理 schema 的 PG alias 表/迁移与读回，再按调用链切换；保持 Owner authority 与现有数据连续。
- 从真实来源补足完整且有合同的最新 T0；完成 Source → PG facts → 候选 Owner → `DEV_VALIDATED` Head/读回 → BFF/UI 的真实写读链，并覆盖全模块日更联调。
- 逐项登记可删除工作区产物；执行可运行的 PG/浏览器功能验收并记录证据。完成开发分支代码与正式规范后提交、推送并更新同一跟踪项。
- 正式生产切换和最终生产打包仍须等全功能、全模块验收及用户另行明确启动。
