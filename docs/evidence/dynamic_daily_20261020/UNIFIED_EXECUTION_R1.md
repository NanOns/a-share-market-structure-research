# V4 连续日更与现役页面定点修复 R1 — 执行证据

- 执行日：2026-10-20（Asia/Shanghai）
- 阶段 0：**BLOCKED**；连续日更准入未通过。
- 基线：`codex/v4-unified-development`，`bc931afea2e2e49905a2550d9b982ea12bce0da1`。本轮只在唯一工作目录执行；开发 HTTP `127.0.0.1:28766`，PostgreSQL `127.0.0.1:5432/market_research`。
- 合同：Google Drive《V4｜连续日更与现役页面定点修复｜统一执行任务 R1》；核对适用升级文档：`V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`、`V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`、`V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`、`V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md`、`V4_INCREMENT_IDENTITY_PARITY_AMENDMENT_R1_1_20261013.md`。

## 日期结果

| 交易日 | Source | Core | Profile | Sector/Rotation | Focus | Forward | ReadIndex/API | UI | 正式发布 | 耗时 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-12 | DEGRADED：10月20日晚采；`AS_RECORDED=false`、`PIT_ELIGIBLE=false` | 5,224 行（候选证据） | 未独立重算 | 板块 400；Owner 覆盖完整可展示，轮动数值仍未独立验收 | 3,025（候选证据） | 5,624 晚采候选；不是 LIVE_OOS / 正式样本 | 当前 token `554f702da47e132156965a2b19e56d82d7841088478aca0511f527aa4d8fa7a5`；28766 context/home/个股/板块/Focus/Radar/Forward HTTP 读回 200；token一致；候选 `production_accepted=false` | 浏览器首页渲染通过；轮动域 400/400 唯一板块候选可展示；Forward 页面展示 5,624 条 10-12 晚采候选，明确非 PIT/非正式 | 否；运营 Head 仍为 10-09，数据 Head 为 09-30 | 本轮未重算 |
| 2026-10-13 | **SOURCE_READY（晚采候选）**：原始目标行 5,225；native TDX/BaoStock 事实一致；按 `V4_CURRENT_OPERATIONAL_NEW_CODE_R2` 将 SZ.301660 绑定为当日新股身份；`AS_RECORDED=false`、`PIT_ELIGIBLE=false` | 未运行（无 Owner） | 未运行 | 未运行 | 未运行 | 未运行 | 新来源门：`a5be96980c2e4cfd6c1862dcbc72128d1f7e12a2d2401c623d52ef1047cda1f5`；`derived_ready=false` | 未运行 | 否 | 未运行 |
| 2026-10-14 | BLOCKED：缺目标日冻结来源 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-15 | BLOCKED：缺目标日冻结来源 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-16 | BLOCKED：缺目标日冻结来源 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-19 | BLOCKED：缺目标日冻结来源（包日期不能替代冻结行证据） | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-20 | BLOCKED：未发现目标日冻结/Owner；10-19 官方包提取只验证了 10-13 目标行 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无候选索引 | 无 | 否 | 未运行 |

官方会话表确认目标序列为 10-12、10-13、10-14、10-15、10-16、10-19、10-20；不能跳过缺失日。`D:/new_tdx/vipdoc/{sh,sz}/lday` 保持只读，本机目录没有这段目标日原生日线覆盖。

## 来源与读回证据

- 10-13 本地晚采官方包：TDX 包 SHA-256 `a56c962378a5d3dd86a90186cc830ee6c8fd968557ce6eddeb310d203c5ff3c0`，549,367,720 bytes，包版本日 10-19；目标提取捕获于 10-20 13:04:33 +08，目标行文件 SHA-256 `17d87a711262b7710098b3ac29717a56d440cede0214c39b7d94a63d3124c0b8`，原生行 5,561，目标日行 5,225。BaoStock 10-13 原始响应于 10-20 13:05:26 +08 捕获，候选池 5,224。不得把这些晚采字节称为 PIT 或当时留存数据。
- 10-13 来源冻结本地路径 `data/v4/dynamic_daily_sources/daily_freezes/2026-10-13/aebe3c5c3b83d9769017dd4f89249f39912b2c07d87dfa5d7de5c2ff3efe9cfb.json`，1,791,540 bytes，SHA-256 `4053ccb99f3f21994278d46766a540cdabfb38fdf8713a9ba6a8b3cd0bd70c87`。按现役新股合同重算后，当前来源门 `data/v4/dynamic_daily_sources/source_readiness/2026-10-13/a5be96980c2e4cfd6c1862dcbc72128d1f7e12a2d2401c623d52ef1047cda1f5.json` 为 `SOURCE_READY`，`derived_ready=false`；新身份绑定 SHA-256 `bdeb082d1789029fd57c0041d270e9d1941c503fb96d1186bd191fe1a7e09fee`，仅将 `SZ.301660` 作为 10-13 首次观察身份加入本日候选，前序身份 Owner 未修改。原始 BaoStock `query_stock_basic` 行记载代码名“粤芯半导体”、IPO 日期 2026-10-13，采集时间 10-20 15:48:29 +08；[深交所 2026-10-12 上市公告](https://www.szse.cn/www/disclosure/notice/company/t20261012_623256.html)独立确认证券代码和上市日期。该身份仍是晚采、非 PIT，alias 未验证，不得据此回填更早历史。来源门中的父身份范围差异被保留为审计记录；当前提供方事实重算结果为 `NATIVE_PROVIDERS_RECONCILED`。文件在本机忽略数据目录中，不包含于代码提交。
- 10-12 独立数据库身份按仓库候选记录为 `market_research` / DB OID `646711` / PG 5432；28766 HTTP 返回 5,224 股票、400 板块，R1/R2 候选索引日期/token 可读。业务写入/Head 更新均未做。
- 当前本地实际 Head：`V4_OPERATIONAL_RESEARCH_HEAD.json` 日期 10-09；`V4_DATA_ACCEPTED_HEAD.json` 日期 09-30。10-12 候选 token 与当前运营 Head 不同。旧服务曾误报 `production_accepted=true`；新进程已验证为 false，不能把 API 200 或索引 READY 当作正式接受。

## 定点修复与验收

- 轮动完整性使用同一候选的实际板块 Owner 身份集合计算期望行数；同时检查缺失、重复、额外身份和 Owner 绑定。`AUTO_ACCEPTED_WITH_LIMITATIONS` 仅表示可展示，不代表数值独立验收或正式发布；保留 `UNKNOWN` / `NONE` 原值。
- 轮动两套前端校验要求动态总数、全部分页、同 token、身份唯一和候选仅展示范围；补齐 research 状态筛选枚举。
- Forward 晚采读使用当前候选日期、完整候选 token 与 source-registry freeze 绑定，缓存按 `(token,date)` 隔离，并保留非 PIT/非正式样本标记。页面候选日期改为响应日期，不再固定写 10-12。修复两套文案中固定 9-30 来源日期；页面快照标签依据 `production_accepted` 显示候选/现役。
- 后端 Head 状态现在要求候选日期与完整候选摘要都精确匹配现役 Head，才可标记 `production_accepted=true`；测试覆盖日期和摘要不匹配的候选状态。
- 本地定向测试：`49 passed`（轮动、Operational Successor、新股准入、Forward）；Node UI：`5 passed`；目标 ES module `node --check` 与 `git diff --check` 通过。另一次较宽读测试因 `V4_NATIVE_PG_DSN` 未配置而无法运行数据库图表用例，不提供凭据或改用未知 DSN。

## 未关闭项与恢复位置

- **P0-A BLOCKED（首缺日已前移）**：10-13 真实晚采来源和当日新股身份门已通过，但没有生成增量 Owner（`derived_ready=false`）；连续链首个未完成交易日现为 10-14，缺冻结来源。不得跳过 10-14 计算后续日期。
- **P0-B 已关闭（运行态修复）**：已按进程命令行与端口归属核对并停止旧 28766 进程，再以同一只读预览入口重启最新源码；未触碰 28765。发现并修复 `research/components.js` 的 `ResearchHeader` 括号缺失（浏览器模块解析错误导致整个页面停在加载态），并增加模块导入回归测试。重启后 `/api/v4/context` 与索引页面统一返回 `production_accepted=false`、`formal_head_match=false`、正式 Head 日期 10-09；首页、轮动、Forward 页已完成浏览器 DOM 验收。
- **P1 PARTIAL**：已验收首页、轮动展示及 Forward 候选页面；个股、板块、Focus、Radar API 读回可用。完整搜索/筛选、详情、图表、Focus/Radar 多交互路径仍未逐项冒烟。
- **现存读取缺口**：`/api/v4/radar/priority` 当前返回 400，原因是当前 10-12 候选没有 `data/v4/research_priority_authority_r1.json` 的优先级 Owner 绑定。没有创建或伪造该 Owner；此日期的正式优先级读取仍不可用。
- 下一最小动作：先为 `SZ.301660` 按当前带版本身份合同解决准入/异常范围并关闭 10-13 来源差异；再取得 10-14 真实输入，基于已验证的 10-12 候选建立受限连续候选链。未切 28765、Head、正式调度；未执行破坏性数据库操作。

## 运行态修复追加证据（2026-10-20 16:13 +08）

- 核验旧 28766 PID `45608` 命令行为 `E:\python\python.exe -B G:\codex_tmp\v4_20261012_readonly_preview.py`，端口归属为 127.0.0.1:28766；停止后确认端口释放，随后启动 PID `31092`，读回启动日志日期 2026-10-12、worker disabled。28765 未启动；PG 5432 仍为已有实例 PID `8640`。
- 浏览器最初的加载态来自 `components.js` `ResearchHeader` 中少一个 `)`：模块未解析，导航和页面脚本均未运行。补齐后刷新，8 个导航入口和首页内容正常出现，控制台未新增解析错误。
- 首页实显候选头部、股票 5,224、板块 400、Radar 311（部分）及 Forward 5,624（晚采候选）；轮动卡片显示 400/400 唯一身份且明确“不代表数值独立验收或正式域发布”。Forward 页面显示 `2026-10-12`、5,624 条、采集时点 `2026-10-20T10:19:45.760110+08:00` 和“非 PIT、非当时可知”。Forward settlement 为 `EMPTY_VALID`、0 条。
- API 读回 200：context、home、stocks（5,224）、sectors（400）、focus（3,025）、radar（311）、forward/statistics；settlement 返回 200 / `EMPTY_VALID` / 0。以上候选接口 token 均一致；正式标记均为 false。
- 最新定向 Python 测试：57 passed；Node UI 回归：6 passed（新增 research UI 模块可导入测试）；`node --check` 与 `git diff --check` 通过。
- 10-13 新股身份候选追加：现役 new-listing 合同测试与 source-gate 重算测试 `37 passed`；只重算并原子追加本地候选身份/来源门文件，没有运行 Owner、PG 写入或正式调度。
