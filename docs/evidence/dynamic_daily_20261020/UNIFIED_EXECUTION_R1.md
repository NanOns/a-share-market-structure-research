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
| 2026-10-14 | **SOURCE_CAPTURED；身份门阻断**：官方 ZIP 提取 5,563 行；BaoStock 匿名 smoke 取得日线 5,225 行、因子 22 行，原始响应已哈希并冻结。来源数值一致，但 formal 09-30/运营 10-09 身份集缺少 10-13 首见的 `SZ.301660`，须先完成 10-13 候选身份继承 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 来源门 `WAIT_DATED_IDENTITY_AUTHORITY`；候选冻结已保存 | 未运行 | 否 | smoke 17:51 +08；source freeze `089f070b…` |
| 2026-10-15 | BLOCKED：已确认同一官方 ZIP 含 9,727 个 `.day` 成员目标日记录；10-13/10-14 Owner 与新股身份连续链尚未建立，未提取/派生本日 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-16 | BLOCKED：已确认同一官方 ZIP 含 9,722 个 `.day` 成员目标日记录；前序候选链未通过，未提取/派生本日 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-19 | BLOCKED：已确认同一官方 ZIP 含 9,715 个 `.day` 成员目标日记录；包更新日期不能替代日期绑定冻结，前序候选链未通过，未派生 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无 | 无 | 否 | 未运行 |
| 2026-10-20 | BLOCKED：本地最新版 ZIP 的 `.day` 内容最大日为 10-19，未发现 10-20 目标行 | 未运行 | 未运行 | 未运行 | 未运行 | 未运行 | 无候选索引 | 无 | 否 | 本轮只读检查 |

官方会话表确认目标序列为 10-12、10-13、10-14、10-15、10-16、10-19、10-20；不能跳过缺失日。`D:/new_tdx/vipdoc/{sh,sz}/lday` 保持只读，本机目录没有这段目标日原生日线覆盖。对已冻结 TDX ZIP 的只读扫描确认其中含 10-13、10-14、10-15、10-16、10-19 目标行；全包 `.day` 目标行分别为 9,717、9,726、9,727、9,722、9,715 个（含指数/非股票成员）。A 股提取器过滤后 10-13 为 5,561 行、10-14 为 5,563 行；10-20 无目标行。10-14 提取 artifact `d0cd1e3fc389c3099308b9067f6ceeae6dd4afa6b9066e232e5bfc996e990fc1/bars.json`，SHA-256 同 artifact id，绑定包 SHA `a56c962378a5d3dd86a90186cc830ee6c8fd968557ce6eddeb310d203c5ff3c0`，package 内容最大交易日为 10-19；晚采、非 PIT。独立字节读回抽样 `SH.600000` 与 ZIP 原成员一致，open/high/low/close/volume/amount 六字段逐项相同（9.60/9.71/9.57/9.65/59,539,771/573,962,880.0）。

## 来源与读回证据

- 10-13 本地晚采官方包：TDX 包 SHA-256 `a56c962378a5d3dd86a90186cc830ee6c8fd968557ce6eddeb310d203c5ff3c0`，549,367,720 bytes，包版本日 10-19；目标提取捕获于 10-20 13:04:33 +08，目标行文件 SHA-256 `17d87a711262b7710098b3ac29717a56d440cede0214c39b7d94a63d3124c0b8`，原生行 5,561，目标日行 5,225。BaoStock 10-13 原始响应于 10-20 13:05:26 +08 捕获，候选池 5,224。不得把这些晚采字节称为 PIT 或当时留存数据。
- 10-13 来源冻结本地路径 `data/v4/dynamic_daily_sources/daily_freezes/2026-10-13/aebe3c5c3b83d9769017dd4f89249f39912b2c07d87dfa5d7de5c2ff3efe9cfb.json`，1,791,540 bytes，SHA-256 `4053ccb99f3f21994278d46766a540cdabfb38fdf8713a9ba6a8b3cd0bd70c87`。按现役新股合同重算后，当前来源门 `data/v4/dynamic_daily_sources/source_readiness/2026-10-13/a5be96980c2e4cfd6c1862dcbc72128d1f7e12a2d2401c623d52ef1047cda1f5.json` 为 `SOURCE_READY`，`derived_ready=false`；新身份绑定 SHA-256 `bdeb082d1789029fd57c0041d270e9d1941c503fb96d1186bd191fe1a7e09fee`，仅将 `SZ.301660` 作为 10-13 首次观察身份加入本日候选，前序身份 Owner 未修改。原始 BaoStock `query_stock_basic` 行记载代码名“粤芯半导体”、IPO 日期 2026-10-13，采集时间 10-20 15:48:29 +08；[深交所 2026-10-12 上市公告](https://www.szse.cn/www/disclosure/notice/company/t20261012_623256.html)独立确认证券代码和上市日期。该身份仍是晚采、非 PIT，alias 未验证，不得据此回填更早历史。来源门中的父身份范围差异被保留为审计记录；当前提供方事实重算结果为 `NATIVE_PROVIDERS_RECONCILED`。文件在本机忽略数据目录中，不包含于代码提交。
- 10-12 独立数据库身份按仓库候选记录为 `market_research` / DB OID `646711` / PG 5432；28766 HTTP 返回 5,224 股票、400 板块，R1/R2 候选索引日期/token 可读。业务写入/Head 更新均未做。
- 10-14 首次来源尝试复用同一已验证官方 ZIP 并完成 A 股目标行提取，未使用 `D:/new_tdx` 缺失目标行作补造。BaoStock runtime smoke 于 16:21 和 16:25 +08 登录失败；限一次有界重试后仍失败，provider error code `10002007`、消息“网络接收错误”，第二次回执 `reports/v4_baostock/runtime_acceptance/20261014/20261020T162537835721_live_smoke_receipt.json` SHA-256 `8a1c045cb1eddc34ac4a3d1ddaefcb0e3b1c94fdb3c6b198771c8315e7f7f10f`。定向诊断修复已使净化的 provider code/message 写入失败回执；request ledger 当日总计 44，低于既定 40,000 soft / 45,000 hard cap。未构造 10-14 BaoStock 行或 complete freeze。
- 当前本地实际 Head：`V4_OPERATIONAL_RESEARCH_HEAD.json` 日期 10-09；`V4_DATA_ACCEPTED_HEAD.json` 日期 09-30。10-12 候选 token 与当前运营 Head 不同。旧服务曾误报 `production_accepted=true`；新进程已验证为 false，不能把 API 200 或索引 READY 当作正式接受。

## 定点修复与验收

- 轮动完整性使用同一候选的实际板块 Owner 身份集合计算期望行数；同时检查缺失、重复、额外身份和 Owner 绑定。`AUTO_ACCEPTED_WITH_LIMITATIONS` 仅表示可展示，不代表数值独立验收或正式发布；保留 `UNKNOWN` / `NONE` 原值。
- 轮动两套前端校验要求动态总数、全部分页、同 token、身份唯一和候选仅展示范围；补齐 research 状态筛选枚举。
- Forward 晚采读使用当前候选日期、完整候选 token 与 source-registry freeze 绑定，缓存按 `(token,date)` 隔离，并保留非 PIT/非正式样本标记。页面候选日期改为响应日期，不再固定写 10-12。修复两套文案中固定 9-30 来源日期；页面快照标签依据 `production_accepted` 显示候选/现役。
- 后端 Head 状态现在要求候选日期与完整候选摘要都精确匹配现役 Head，才可标记 `production_accepted=true`；测试覆盖日期和摘要不匹配的候选状态。
- 最新定向测试：Python `96 passed`（V4 UX/routes、Operational Successor、轮动完整性、Forward、新股准入、日更执行器及 BaoStock 失败回执）；Node UI `6 passed`；目标 ES module `node --check` 与 `git diff --check` 通过。另一次较宽读测试因 `V4_NATIVE_PG_DSN` 未配置而无法运行数据库图表用例，不提供凭据或改用未知 DSN。

## 未关闭项与恢复位置

- **P0-A BLOCKED（候选重验及身份继承）**：10-13 真实晚采来源与 `SZ.301660` 当日首次观察身份门已通过，Owner 尚未生成。10-14 BaoStock 接收已修复并取得 5,225/22 行真实回执及冻结；来源门等待从 10-13 候选身份继承。旧 10-12 candidate 用当前分支 `operational_successor.validate()` 重验时，在 `src/workbench_service/v4_server.py` 摘要绑定处失败，因此不能作为 R8 数值验收父节点；必须先从冻结源重算当前源码的 10-12 candidate，再接 10-13。后续交易日按序等待，不越过该候选链门。
- **P0-B 已关闭（运行态修复）**：已按进程命令行与端口归属核对并停止旧 28766 进程，再以同一只读预览入口重启最新源码；未触碰 28765。发现并修复 `research/components.js` 的 `ResearchHeader` 括号缺失（浏览器模块解析错误导致整个页面停在加载态），并增加模块导入回归测试。重启后 `/api/v4/context` 与索引页面统一返回 `production_accepted=false`、`formal_head_match=false`、正式 Head 日期 10-09；首页、轮动、Forward 页已完成浏览器 DOM 验收。
- **P1 页面定点验收已关闭**：28766 Chrome 桌面与 390×844 窄屏验收首页、轮动和 Forward；8 个主路由、个股/板块列表与详情、搜索/研究状态筛选、Focus 到期观察、Radar 范围/优先级筛选、日/周线与复权口径均已读回，未见横向溢出或 JS/API 错误。Forward 明确显示 10-12 晚采、非 PIT、非正式样本。
- **10-12 Radar 优先级读取已恢复**：候选 token `554f702da47e132156965a2b19e56d82d7841088478aca0511f527aa4d8fa7a5` 的 400 生命周期行逐项读回；Priority 股票 5,224（可排序 1,752、不可排序 3,472）、板块 400（可排序 143、不可排序 257）。仍为候选只读，不构成正式接受。
- 下一最小动作：基于当前源码重新构建/验证 10-12 candidate-only successor，再以其严格数值验收结果作为 10-13 的候选父节点，继承 `SZ.301660` 当日身份；之后重验 10-14 来源门。未切 28765、Head、正式调度；未执行 PG 写入或破坏性数据库操作。

## 运行态修复追加证据（2026-10-20 16:13 +08）

- 核验旧 28766 PID `45608` 命令行为 `E:\python\python.exe -B G:\codex_tmp\v4_20261012_readonly_preview.py`，端口归属为 127.0.0.1:28766；停止后确认端口释放，随后启动 PID `31092`，读回启动日志日期 2026-10-12、worker disabled。28765 未启动；PG 5432 仍为已有实例 PID `8640`。
- 浏览器最初的加载态来自 `components.js` `ResearchHeader` 中少一个 `)`：模块未解析，导航和页面脚本均未运行。补齐后刷新，8 个导航入口和首页内容正常出现，控制台未新增解析错误。
- 首页实显候选头部、股票 5,224、板块 400、Radar 311（部分）及 Forward 5,624（晚采候选）；轮动卡片显示 400/400 唯一身份且明确“不代表数值独立验收或正式域发布”。Forward 页面显示 `2026-10-12`、5,624 条、采集时点 `2026-10-20T10:19:45.760110+08:00` 和“非 PIT、非当时可知”。Forward settlement 为 `EMPTY_VALID`、0 条。
- API 读回 200：context、home、stocks（5,224）、sectors（400）、focus（3,025）、radar（311）、forward/statistics；settlement 返回 200 / `EMPTY_VALID` / 0。以上候选接口 token 均一致；正式标记均为 false。
- 最新定向 Python 测试：57 passed；Node UI 回归：6 passed（新增 research UI 模块可导入测试）；`node --check` 与 `git diff --check` 通过。
- 10-13 新股身份候选追加：现役 new-listing 合同测试与 source-gate 重算测试 `37 passed`；只重算并原子追加本地候选身份/来源门文件，没有运行 Owner、PG 写入或正式调度。

## 来源失败诊断修复（2026-10-20 16:26 +08）

- `scripts/accept_dynamic_daily_baostock_v2.py` 原 smoke failure receipt 仅留下通用 `BAOSTOCK_LOGIN_FAILED`，抛弃 SDK 已净化的 provider error code/message。本轮新增 `provider_failure` 安全诊断字段和返回值，保留受限字符 provider code、最多 240 字符净化消息；无 provider metadata 时仍使用原通用错误。新增回归覆盖 provider metadata 和 generic failure。
- 最小重试仍返回 `10002007`、消息“网络接收错误”，耗时 31.15 秒（SDK 30 秒 timeout）。此证据表示 BaoStock 网络接收失败；没有切换端点/认证模式或绕过来源门。诊断字段改善定位，不将失败标记改成成功。

## 遗留问题重新尝试与交互收尾（2026-10-20 17:10 +08）

- **10-14 BaoStock 重试仍受上游网络阻断**：再次按官方入口执行 `scripts/accept_dynamic_daily_baostock_v2.py --target-date 2026-10-14`，新回执 `reports/v4_baostock/runtime_acceptance/20261014/20261020T165148184320_live_smoke_receipt.json` SHA-256 `6511b46977598123daa07ac713e78f74b1a77d7b2889c54fe9be259d6b1ca9c1`；状态 FAIL，`BAOSTOCK_LOGIN_FAILED`，provider code `10002007`，消息“网络接收错误”。官方主机 DNS 解析成功，但 TCP 10030 连接超时；本次没有拿到 daily/factor 响应。Ledger 总请求 45、登录 21，未触及配置上限。未切换端点、认证或来源，也没有伪造行；连续日更仍准确停在 10-14。
- **10-12 Radar 优先级读取已恢复**：独立生命周期审计 oracle 已按合同的最少匹配数处理已知谓词；补充缺失较早单字段、但两项有效 weakening 比较满足门槛的回归。定向单元测试 9/9 通过；400 板块独立样本复核 20/20 通过。只为候选 token `554f702da47e132156965a2b19e56d82d7841088478aca0511f527aa4d8fa7a5` 追加内容寻址、不可变 lifecycle/priority Owner：400 生命周期行读回逐项相等；Priority 读回股票 5,224（可排序 1,752、不可排序 3,472）、板块 400（可排序 143、不可排序 257）。市场权限仍为 `FACT_ONLY_NO_FORMAL_PERMISSION`；候选仍非 PIT、非正式发布，Head 未更新。
- **现役页面逐项补验**：Radar 股票/板块范围和可排序/不可排序筛选读回分别为 1,752/3,472、143/257；股票页搜索及研究状态筛选有返回结果。板块列表加载 400 行，板块详情、来源证据与成员区域可打开。Focus 的真实关注锚点、价格路径证据、到期观察抽屉均可打开且保留待到期语义。股票图表成功读回截至 10-12 的日线、周线以及前复权/不复权口径。发现 stocks/sectors 列表入口之前没有路由、股票表引用了未接入字段；已增加列表路由并换用已接入字段，页面不再落到“没有找到该入口”或“字段未接入”。
- **定向验收**：Python 生命周期/优先级测试 9 passed，UX/route/轮动完整性测试 46 passed；Node UI 测试 6 passed；app.js、labels.js `node --check` 通过。板块列表/详情、Focus、Radar、股票筛选与图表在 28766 浏览器实际读回。28766 当前仅由 PID 48492 的只读候选预览入口监听；28765 无监听；PG 5432 仍为既有 PID 8640。候选 API 生产接受标记仍为 false。
- **状态**：已关闭 10-12 Radar Owner 缺失及页面冒烟缺口、10-14 BaoStock 数据接收；未关闭项为 10-13 Owner 候选生成及其到 10-14 的身份连续绑定，故 10-15、10-16、10-19、10-20 仍按顺序阻断。没有切换正式 Head、28765 或生产调度。

## BaoStock 10-14 接收超时修复与重新验收（2026-10-20 17:51 +08）

- 直连成功样本的全市场日线查询耗时 66.352 秒（SDK 0.9.3、`bs.login()` 匿名模式）；既有日更 smoke 使用项目客户端默认 30 秒 socket 接收超时，旧失败回执约 31 秒出现 `10002007 / 网络接收错误`。这是批量响应的接收超时窗口过短，并非用户名/API key 缺失，也不是接口从未成功。
- 仅将完整市场 smoke 的单次 socket 超时设为 90 秒；调用数仍为 2（daily + factor）、页上限 1、行上限 20,000，不增加重试。定向回归覆盖此配置及原失败诊断：`tests/test_dynamic_daily_runtime_smoke_receipt_v1.py` 与 BaoStock client 定向测试共 5 passed。
- 修复后官方 runtime smoke 回执 `reports/v4_baostock/runtime_acceptance/20261014/20261020T175128444262_live_smoke_receipt.json` SHA-256 `b52b98247332f847237cc96b2d07b83d116b480426e84dceab756624f61ce0d6`，状态 `PASS`、`PUBLIC_ANONYMOUS`；日线 5,225、因子 22。原始响应 SHA-256 `4fe7236d67cb878eb4b1624c13dfcff2370d2c341774a0e7045addcc57f4e1be`。source freeze `data/v4/dynamic_daily_sources/daily_freezes/2026-10-14/30c5929855e09f6c1d15da94b0b8da3f72fc2c7f1923eb43b9a955a6d528fdcb.json` SHA-256 `089f070beb8fc8d6d1cc0dfa6a8bceb56dacfc2eb2b1fde7e30e9aec48a6c8ba`。
- 重新读回 10-14 来源门为 `WAIT_DATED_IDENTITY_AUTHORITY`，不是 BaoStock 失败：`SZ.301660` 在 10-13 已认定为首次观察代码，但 formal 10-09 身份集不含该身份。未在 10-14 重新定日首见、未伪造 Owner、未更新 Head 或写正式业务数据。连续链下一步是以严格 candidate-only 机制完成 10-13 Owner 并将身份绑定传给 10-14。

## R8 候选 Owner 接口恢复与父节点重验（2026-10-20 18:01 +08）

- 当前分支的 `operational_daily_ready_owner_v2` 仍按 R8 候选链传递 `adjustment_contract`、`candidate_only_exact`、`lifecycle_binding` 和精确算子参数；后续“恢复基线”变更却把 Owner/IO adapter 的对应签名与身份流程回退，实际候选运行会在参数绑定处失败。仅恢复已有版本 `00dc0afb8` 的 Owner、Owner adapter 和 Core IO lifecycle plumbing；不改发布 Head、算术合同或生产读取路径。
- 定向 R8 lifecycle admission、isolated day baseline、Owner adapter 接口、BaoStock smoke/client、日更执行器测试共 `18 passed`；`git diff --check` 通过。
- 旧 10-12 candidate 的只读 successor 校验返回 `CORRECTED_INPUT_DIGEST_MISMATCH:src/workbench_service/v4_server.py`，证明该历史 token 的源摘要已过期；没有改写该不可变候选或用它作 10-13 父节点。当前需要以 10-12 冻结输入按现源码重算，之后才能通过 R8 数值门并继续 10-13。
- 28765、28766、formal/data Heads 和 PostgreSQL 数据均未变更；未执行 PG 写入、正式调度或破坏性操作。

## R8 现役 Owner 接口恢复与 10-12 候选重算（2026-10-20 18:40 +08）

- 从当前 exact-policy 指定的不可变 runtime source archive 恢复四个配套实现文件：`r43_structure_replay.py`、`tdx_sector_retro_r43.py`、`r43_market_replay.py`、`r43_focus_replay.py`。其 API 与 R8 Owner adapter 实际传参一致（结构 prior/progress、扇区 predecessor/progress、市场 predecessor、Focus predecessor/progress）；此前当前工作树混用了较旧函数签名，依次触发 `unexpected keyword argument`。新增接口合同回归；R8 candidate、isolated day、ready Owner、BaoStock smoke/client、daily executor 定向测试 `18 passed`，`git diff --check` 通过。
- 10-12 gate 与 exact policy 均通过。候选快照内 6 个冻结 TDX 文件路径做了临时根目录本地化；原冻结/来源门未改，逐文件 payload SHA 与字节数不变，TDX package snapshot identity 和目标 bars SHA 保持不变；本地化映射证据只在 G 盘 candidate-only 快照。
- 10-12 当前源码候选本地阶段读回：CORE `5,224` 行、原始行 `5,212`、独立 core oracle `0` 错误；PROFILE `5,224` 行、结构锚点 `2,630`；SECTOR 与 rotation 各 `400` 行，sector oracle `FOUR_DAY_RETRO_SECTOR_PASS`；Focus D0/D2 `5,224` 行。读回摘要在 G 盘临时快照，formal Head SHA 仍为 `55d78be5…`。
- 尚未得到可封存 successor：Focus 收尾调用 `v4_series_pg_r1.build()`，它会在共享 `127.0.0.1:5432/market_research` 新建确定性 `v4_research_*` candidate schema、创建 immutable-series tables/index/triggers 并插入本候选的 dated bars。当前没有执行该数据库写入；运行在缺少 producer DSN 时按合同失败关闭（`V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK`）。这是下一步所需的唯一数据操作，不能写成只读验收或候选已封存。
- PostgreSQL 写入前仍需用户确认该单个 candidate-only schema 的创建和数据范围；获准后可从 G 盘已完成的 CORE/PROFILE/SECTOR 缓存续跑，随后再执行 10-12 数值读回门、10-13 身份延续和 10-14 source gate。未写入 PG、未封存 candidate、未动正式/数据 Head、28765 或生产调度。
