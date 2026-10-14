# V4 R6 最终收口与生产切换记录

- 合同：`V4-R6-PRODUCT-CLOSEOUT-CUTOVER-20261014` / R1
- 终态：`V4_R6_PRODUCTION_CUTOVER_PASS`
- 起点：`codex/v4-r4-closeout-20261014` / `174ac59c94a8ac6e27b651036f3860c2226dd9c8`
- 生产根：`G:\codex work\v4-production-20261012`
- 核验时间：2026-10-14（Asia/Shanghai）

## 生产切换

| 项目 | 结果 |
|---|---|
| 当前包 | `V4_PACKAGE_1.1.6_44d446ed72bd` |
| EXE | `G:\codex work\v4-production-20261012\versions\V4_PACKAGE_1.1.6_44d446ed72bd\DaAV4\DaAV4.exe` |
| 28765 服务 | `RUNNING`，PID 21288；daily worker PID 44688 |
| 上一基线包 | `V4_PACKAGE_1.0.0_88cc19deae3b`；切换前运行包为 1.1.5，回滚副本保留 |
| Head / T0 | token `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3` / `2026-10-13` |
| context | 真实 28765 HTTP 200；SHA-256 `77846169e96007bfe6d3313ad494d173da575ae407b2a25337b7fe2fa8b2784f` |
| 自动日更 | `auto_daily_enabled=false`，保持暂停 |
| 首页 | HTTP 200，272,737 B（小于 512 KiB），三族风险均返回，token 一致 |
| Radar | p2 HTTP 200，30/177；优先级股票 p2 HTTP 200，30/1,410；页间无重复 |
| 板块 / 个股详情 | 真实生产读回 HTTP 200；行业 `INDUSTRY:T0101` 和证券 `SH.600703` |
| Focus / Forward / Market | 列表及空态 API 均 HTTP 200；Forward 明确 `SOURCE_INCOMPLETE` / `NO_AUTHORIZED_COHORT_OWNER`，FEP 明确 `MODEL_OR_PERMISSION_NOT_READY` |
| 历史 10/12 | context HTTP 200，未静默替换为 10/13 |
| 静态资源 | app.js、labels.js HTTP 200，资源 SHA 与包内清单一致 |

部署时连续发现并修复两个真实启动/发布问题：生产 Joint 必须写入精确候选 Joint 文档字节；新包 BFF 需要版本化运行时源码覆盖，并避免风险详情字段挤入首页响应。失败包均触发回滚，最终 1.1.6 经真实 28765 读回后保持稳定。旧 1.0.0 基线包、旧 Head 和 `auto_daily=false` 均未被覆盖或启用。

## 事实审计总表

| 项 | 结论 | 边界 |
|---|---|---|
| U01 Radar | PASS | 独立日研究优先级 Owner 与 177 条状态事件分开；PG p1/p2 分页读回 |
| U02 首捕 / Cohort | 当前状态正确显示未取得首获；隔离首捕/准入接口可运行 | 10/14 没有按时捕获，禁止补写 PIT；下一真实交易日需现役完整 AS_RECORDED 信号生产者、独立准入 Owner 与授权写入凭据 |
| U03 轮动前态 | 继承 `PASS_SCOPED` | 严格历史 PIT 在缺少当日成分快照时不推定 |
| U04 三族风险 | PASS | 股票、板块、市场分别物化，PG 分母与变化量可读；只表达已接受事实，不伪造未发生风险或正式综合环境评级 |
| U05 板块成熟度 / 健康度 | PASS，重建口径 | 400 行 PG Owner；20/20 独立真实来源 oracle；最少 5 个接受交易日；严格 PIT 首获保持 WAIT |
| U06 轮动筛选 | 继承 `PASS_SCOPED` | 未重测未改链路 |
| U07/U08 D2 与资格 | PASS，状态语义明确 | NONE 与 UNKNOWN 分开；未知条件保持 UNKNOWN，不将未实现 detector 冒充 FALSE |
| U09 身份 | PASS | `SH.600703`、`SZ.301660`、`SZ.300114→SZ.302132` Owner/PG/API 语义一致；代码首次观测与 IPO 确认分列 |
| U10 集中度 | 继承 PASS | Focus 3,151、Top5 与 110 行业既有证据保留 |
| U11 Focus 字段 | PASS，重建读域 | 3,151 条保留，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`，不晋升正式队列 |
| U12 事件变化 | PASS，功能边界 | 退出/失效状态机用合成反例覆盖；真实首次 EXIT/INVALIDATED 事件 WAIT_REAL_EVENT |
| U13 Forward / FEP | PASS，隔离引擎串联 | 首捕→授权读取/拒绝→T+1 到期与 T+3 未到期→结算→FEP 读取已通过隔离合成用例；生产真样本数值及模型成熟度 WAIT_REAL_SESSION |
| U14 五指数 | 继承 PASS | 未核实成交量单位继续隐藏 |
| U15 涨跌停可判定性 | 继承 PASS | 原 57 精确首板 / 12 前缀不完整分组保持 |
| U16 连板展示 | 继承 PASS | 不生成分钟级信息 |

### 独立读数

- Sector Lifecycle：400 行；成熟度 `Developing=93 / Early=14 / Mature=3 / None=155 / Unknown=135`；健康度 `Damaged=44 / None=74 / Unknown=151 / Watch=97 / Weakening=34`。保留 `NONE` 与 `UNKNOWN` 的意义差异。
- 三族风险：股票分母 5,225、已覆盖 5,201（99.54%）、变化 87；板块分母 400、已覆盖 249（62.25%）、变化 182；市场分母 1、已覆盖 1、变化 1。未以 Focus 数量代替全市场分母。
- 正式优先级：可排名板块 191/400、股票 1,410/5,225；研究次序不代表概率或收益承诺。
- Joint mismatch：旧封存字节 2,020 B / SHA `1d523251…` 保持不可变；新合法 descriptor 2,032 B / SHA `839f2852…` 已核对，生成的新 Joint 已安装并在生产重启读回。新 Joint SHA `b254905eef1cc9c6e7a3bf6847de54fb661c564c10b29e59eb33c2efc7d542a1`。
- 定向代码验收：5 个受影响测试文件 `51 passed in 3.81s`，包含 Forward 隔离串联 E2E。未运行全仓/旧版大规模测试。

## 仍需等待的真实事件或输入

1. 下一有效交易日的首次 AS_RECORDED 全量信号采集；10/14 缺少首获，禁止历史补记。
2. 严格历史 PIT 板块成员与 Focus 首冻：只能在实际逐日快照到位后判定。
3. 真实 Cohort 的正式独立准入/写授权、T+1/T+3/T+5 自然到期结算和 FEP 可靠成熟样本；合成数据没有写入正式 PG 队列。
4. 真实首次 EXIT/INVALIDATED 事件，以及成交量官方单位契约尚未核实的市场数据。

当前生产 Forward 的显式空态是预期安全行为，不代表“正式样本为零”的统计结论，也不代表 Focus 被用作 Cohort。

## 视觉检查说明

已改用 Codex 内置浏览器完成本轮定点 DOM/可访问性树抽查，记录见同目录 `PRODUCTION_BROWSER_ACCEPTANCE_20261014.json`。真实 28765 首页显示三族风险及独立分母/覆盖率（板块 249/400、市场 1/1、个股 5201/5225）；Sector `INDUSTRY:T050101` 详情显示成熟度“发展中”、健康度“已评估：无当前匹配”及 `CURRENT_RECONSTRUCTED_RESEARCH_ONLY` 边界；Radar 优先级显示板块 191/400、个股 1410/5225 且与 177 条事件分开；Focus/Forward 页面明确显示首捕未取得、正式 Cohort 来源/授权/结算 Owner/FEP 准入未发布，未显示伪造样本数。浏览器子页状态条显示包 `V4_PACKAGE_1.1.6_44d446ed72bd`、引擎 `RUNNING`。`/api/v4/context` 另以真实本机 HTTP 200 读回 token 与 T0 `2026-10-13`，与首页日期一致；该 token 来自 API 读回，不称为页面可见 DOM。此次是 DOM/可访问性树检查，不是像素截图。此前“未做视觉抽查”的记录现已由本次验收补正；未来真实首捕、正式 Cohort 准入与结算等 `WAIT_REAL_SESSION` 边界保持不变。

## 阶段合同与后续阶段

- 本阶段合同、读回和验收结果由本文件及同目录 JSON 证据记录；生产切换成功，终态为 `V4_R6_PRODUCTION_CUTOVER_PASS`。
- 不恢复 `auto_daily`，不授予 Cohort 写入，不进入新的受门控研发阶段。
- 随下一真实采集窗口执行手工首捕，先取得完整实时 Owner，再单独评审准入与 PG 写授权；日期与事实门未满足时保持明确空态。
