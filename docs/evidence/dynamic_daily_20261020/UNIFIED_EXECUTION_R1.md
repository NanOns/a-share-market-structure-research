# V4 连续日更与现役页面定点修复 R1 — 执行证据

- 执行日：2026-10-20（Asia/Shanghai）
- 阶段 0：**BLOCKED**；连续日更准入未通过。
- 基线：`codex/v4-unified-development`，`bc931afea2e2e49905a2550d9b982ea12bce0da1`。本轮只在唯一工作目录执行；开发 HTTP `127.0.0.1:28766`，PostgreSQL `127.0.0.1:5432/market_research`。
- 合同：Google Drive《V4｜连续日更与现役页面定点修复｜统一执行任务 R1》；核对适用升级文档：`V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`、`V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`、`V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`、`V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md`、`V4_INCREMENT_IDENTITY_PARITY_AMENDMENT_R1_1_20261013.md`。

## 日期结果

| 交易日 | Source | Core | Profile | Sector/Rotation | Focus | Forward | ReadIndex/API | UI | 正式发布 | 耗时 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-12 | DEGRADED：10月20日晚采；`AS_RECORDED=false`、`PIT_ELIGIBLE=false` | 5,224 行（候选证据） | 未独立重算 | 板块 400；轮动完整性/数值仍未独立验收 | 3,025（候选证据） | 5,624 晚采候选；不是 LIVE_OOS / 正式样本 | 当前 token `554f702da47e132156965a2b19e56d82d7841088478aca0511f527aa4d8fa7a5`；28766 context/home/个股/板块 HTTP 读回 200；token一致 | 本轮重载页面后停在“正在读取当前快照…”，导航与正文未渲染，未验收 | 否；运营 Head 仍为 10-09，数据 Head 为 09-30 | 本轮未重算 |
| 2026-10-13 | DEGRADED/BLOCKED：TDX 目标日行已提取；来源准入文件输出 `SOURCE_READY`，但下层交叉核验仍有 `SOURCE_RECONCILIATION_FAILED` / `UNADMITTED_NATIVE_IDENTITY:SZ.301660` | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无候选索引/独立读回 | 无日期候选页面 | 否 | 未运行 |
| 2026-10-14 | BLOCKED：缺目标日冻结来源 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-15 | BLOCKED：缺目标日冻结来源 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-16 | BLOCKED：缺目标日冻结来源 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-19 | BLOCKED：缺目标日冻结来源（包日期不能替代冻结行证据） | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-20 | BLOCKED：未发现目标日冻结/Owner；10-19 官方包提取只验证了 10-13 目标行 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无候选索引 | 无 | 否 | 未运行 |

官方会话表确认目标序列为 10-12、10-13、10-14、10-15、10-16、10-19、10-20；不能跳过缺失日。`D:/new_tdx/vipdoc/{sh,sz}/lday` 保持只读，本机目录没有这段目标日原生日线覆盖。

## 来源与读回证据

- 10-13 本地晚采官方包：TDX 包 SHA-256 `a56c962378a5d3dd86a90186cc830ee6c8fd968557ce6eddeb310d203c5ff3c0`，549,367,720 bytes，包版本日 10-19；目标提取捕获于 10-20 13:04:33 +08，目标行文件 SHA-256 `17d87a711262b7710098b3ac29717a56d440cede0214c39b7d94a63d3124c0b8`，原生行 5,561，目标日行 5,225。BaoStock 10-13 原始响应于 10-20 13:05:26 +08 捕获，候选池 5,224。不得把这些晚采字节称为 PIT 或当时留存数据。
- 10-13 来源冻结本地路径 `data/v4/dynamic_daily_sources/daily_freezes/2026-10-13/aebe3c5c3b83d9769017dd4f89249f39912b2c07d87dfa5d7de5c2ff3efe9cfb.json`，1,791,540 bytes，SHA-256 `4053ccb99f3f21994278d46766a540cdabfb38fdf8713a9ba6a8b3cd0bd70c87`；最新来源准入文件 `data/v4/dynamic_daily_sources/source_readiness/2026-10-13/dcd942c28f392556347ac25ad5f80efa0ef5c3f468994c331202d080223c96f7.json`，状态 `SOURCE_READY`、`derived_ready=false`。文件在本机忽略数据目录中，不包含于代码提交；其内部原生证券集合仍报告 `SZ.301660` 未准入，故不得将下游称为 READY。
- 10-12 独立数据库身份按仓库候选记录为 `market_research` / DB OID `646711` / PG 5432；28766 HTTP 返回 5,224 股票、400 板块，R1/R2 候选索引日期/token 可读。业务写入/Head 更新均未做。
- 当前本地实际 Head：`V4_OPERATIONAL_RESEARCH_HEAD.json` 日期 10-09；`V4_DATA_ACCEPTED_HEAD.json` 日期 09-30。10-12 候选 token 与当前运营 Head 不同。旧服务 context 仍报 `production_accepted=true`，这是本轮修复的标签缺陷证据；不能把该标记、API 200 或索引 READY 当作正式接受。

## 定点修复与验收

- 轮动完整性使用同一候选的实际板块 Owner 身份集合计算期望行数；同时检查缺失、重复、额外身份和 Owner 绑定。`AUTO_ACCEPTED_WITH_LIMITATIONS` 仅表示可展示，不代表数值独立验收或正式发布；保留 `UNKNOWN` / `NONE` 原值。
- 轮动两套前端校验要求动态总数、全部分页、同 token、身份唯一和候选仅展示范围；补齐 research 状态筛选枚举。
- Forward 晚采读使用当前候选日期、完整候选 token 与 source-registry freeze 绑定，缓存按 `(token,date)` 隔离，并保留非 PIT/非正式样本标记。页面候选日期改为响应日期，不再固定写 10-12。修复两套文案中固定 9-30 来源日期；页面快照标签依据 `production_accepted` 显示候选/现役。
- 后端 Head 状态现在要求候选日期与完整候选摘要都精确匹配现役 Head，才可标记 `production_accepted=true`；测试覆盖日期和摘要不匹配的候选状态。
- 本地定向测试：`49 passed`（轮动、Operational Successor、新股准入、Forward）；Node UI：`5 passed`；目标 ES module `node --check` 与 `git diff --check` 通过。另一次较宽读测试因 `V4_NATIVE_PG_DSN` 未配置而无法运行数据库图表用例，不提供凭据或改用未知 DSN。

## 未关闭项与恢复位置

- **P0-A BLOCKED**：10-13 虽有真实晚采源字节，仍有证券身份差异且未生成完整增量 Owner；10-14 首个未完成交易日无冻结来源。不得进入 10-15 之后计算。
- **P0-B DEGRADED**：10-12 候选 API 读取可用，但旧 28766 Python 进程还在运行本轮修改前加载的模块；计划热重载未能执行。直接 HTTP 可读不证明最新后端已上线，浏览器重载停在加载态，因此当前版本的页面、候选/现役标记修复尚未完成运行态验收。
- **P1 PARTIAL**：轮动与 Forward 逻辑及 UI 文案已修，未在最新 Python 服务重启后进行端到端 DOM 验证；搜索/筛选、详情、图表、Focus、Radar 等完整页面冒烟仍待服务恢复。
- 下一最小动作：先为 `SZ.301660` 按当前带版本身份合同解决准入/异常范围并关闭 10-13 来源差异；再取得 10-14 真实输入，基于已验证的 10-12 候选建立受限连续候选链；最后经授权的 28766 后端重启执行独立读回与桌面/窄屏 UI smoke。未切 28765、Head、正式调度；未执行破坏性数据库操作。