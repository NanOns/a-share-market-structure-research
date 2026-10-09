# 大A V4｜R4.1 四交易日数据补齐独立外部审计 R1

- **审计日期**：2026-10-09（盘前）
- **审计对象**：`NanOns/a-share-market-structure-research`，`codex/v4-system-reform`
- **冻结 HEAD**：`c010b818811689ed3056c6500ca5caa5cbadde4e`（Commit：Repair four-session owners, structural metadata, dated sector replay and daily admission）
- **合同**：Drive `V4_R4_1_截至20261008四交易日_通达信BaoStock主动补采与算法闭环任务卡.md`；仓库 `docs/evidence/source_acquisition_r4_20261009/R4_1_TASK_CONTRACT.md`、`AGENTS.md`。
- **交易日范围**：2026-09-28、09-29、09-30、10-08。2026-10-01 至 10-07 为休市日。
- **唯一整体结论**：`EXTERNAL_ACCEPTANCE_BLOCKED`。
- **分层结果**：`ACQUISITION_EVIDENCE_PASS_SCOPED`；`LEGACY_528_CORRECTED_CANDIDATE_PASS_SCOPED`；`FULL_BINARY_INDEPENDENT_VALIDATION_NOT_VERIFIABLE`；`FULL_UNIVERSE_IDENTITY_BLOCKED`；`ALGORITHM_FULL_SCOPE_BLOCKED`；`OCT08_PRODUCTION_CUTOVER_FAIL`。

> 说明：本次通过 GitHub 连接读取当前远端代码、文本收据与 JSON 明细，独立对 `LEGACY_528_AND_35_RECONCILIATION_V2.json` 的 563 条独立键做了逐条计数/状态交叉核对；没有在用户 Windows 本地运行完整流水线或从 Git LFS 实际下载 551,544,006 字节的 ZIP 与大体积 Owner 源。**开发方自称的本机运行测试、超过 620 万次数值校验及 ZIP CRC=PASS 只能列为“提交证据支持，独立底层字节复核未完成”，不得声称完全独立数值执行通过。**

## 1. 对“这次是否真的把数据补回来”的直接回答

**补采工作确实发生，四个交易日已具有完整的原始行情候选输入和 Core/Profile 候选；但正式生产尚未接收 10/08 数据。**

### 1.1 官方通达信 ZIP

`tdx_download_correction/CORRECTION_RECEIPT.json` 记载官方 `hsjday.zip` 551,544,006 bytes，SHA256 `5e973fa2b8919635f7f5f10212ef4c4c33e7a05503c01e58650a2ac376d99ca4`；R3 已存在的下载器对静态 Cookie 挑战能成功，R4 正常入口早期错误返回的是 987 字节非 ZIP 响应，后完成下载器适配。提交的 ZIP 在 GitHub 文件读取接口体现为 133 字节的 **LFS pointer**（oid/size 与收据一致），不是已被审计方独立展开的 ZIP 文件。

官方 BAR 清单：

| 目标日 | 官方股票 RAW BAR（沪+深+北） | 当前 canonical 范围 RAW BAR | 尚未完成 canonical identity 的 RAW BAR | 目标日停牌、预期无 BAR |
|---|---:|---:|---:|---:|
| 09-28 | 5,557 | 5,210 | 347 | 12 |
| 09-29 | 5,559 | 5,211 | 348 | 12 |
| 09-30 | 5,561 | 5,213 | 348 | 11 |
| **10-08** | **5,557** | **5,209** | **348** | **15** |

**判断**：相对于过去“只查已有 ZIP 或本地 TDX .day”的执行问题，此轮是真实推进。`raw_gap=0` 仅表示 **已设定 canonical identity 子集** 的目标日行情缺口归零；不能据此宣称全市场所有身份和板块已正式闭环。未绑定的 347/348 条需按上市、退市、历史别名、北交所（以及股票/指数）逐条分类，不能全部硬塞入当日有效证券。注意本次官方 BAR 统计与此前 5,213 产品股票属于不同口径。

### 1.2 BaoStock 网络查询

`R4_STAGE_PROGRESS.json`、`SHARED_REQUEST_LEDGER_FINAL.json` 与正常日更收据说明 API 请求确实发生，包括 RAW 历史 K、QFQ、调整因子、证券/行业基础资料。原四日采集报告为 548 次 BaoStock 调用，其后正常入口和重试共享全局预算，最终总量报告为 566。四日汇总中“每个日期均 534 shared coverage”的数字**不允许简单相加**，这点仓库已有标记。此轮不能再判“未尝试 BaoStock”。本次未直接访问用户本机 SDK 会话或独立重放 API，故请求真实性依据为其带时刻/响应的本机冻结收据和代码，而非独立在线复验。

### 1.3 原 528 个 QFQ 能力缺口——独立逐行计数结果

独立解析当前 GitHub 上的 `LEGACY_528_AND_35_RECONCILIATION_V2.json` 逻辑字段（含 563 个日期×证券唯一键）：

| 日期 | 原 QFQ 未证明 | 当前与 T-1 ATR20 均可用的 corrected candidate | 原缺口中仍不可用 | 停牌保持无 BAR |
|---|---:|---:|---:|---:|
| 09-28 | 176 | 176 | 0 | 12 |
| 09-29 | 176 | 176 | 0 | 12 |
| 09-30 | 176 | 176 | 0 | 11 |
| **合计** | **528** | **528** | **0** | **35** |

563/563 日期证券键无重复，528 条 `old_qfq_gap` 均同时记录 `qfq_current_ready=true`、`atr20_ready=true`、`prior_atr20_ready=true`、`usable_corrected=true`、`accepted=false`；35 条停牌 `suspended_no_bar=true`。本结论**只适用于这些旧缺口、指定价格坐标和目标指标窗口的 corrected candidates**。跨不支持历史公司行为的更长窗口仍允许 `UNKNOWN`；`RECONSTRUCTED_CORRECTED`、`AS_RECORDED=false`，不能成为其旧 T0 历史 PIT 证明。

10/08 的新口径剩余 `qfq_capability_unknown=9`，属于本轮动态计算结果，不是原来的 176 或 528。

## 2. 逐项验收表

| Gate | 要求 | 外审核对 | 结论 |
|---|---|---|---|
| G01 | 四个有效交易日，国庆期间无伪造 K 线，正确 T-1/T-3 | 四日收据与日历端点吻合，10/08 T-1=09/30、T-3=09/28；09/30 T-3=09/24 | **PASS** |
| G02 | 主动读取本地 TDX、官方 TDX、BaoStock，保留真实错误/请求收据 | 有真实官方下载修复、BaoStock SDK 请求 ledger 与本地读取；此前 987B 错响应按错误保留 | **PASS（提交证据范围）** |
| G03 | 四日 RAW 全部获取、源冲突/证券身份正确 | 官方报告 5557/5559/5561/5557；canonical RAW 空洞为零、交叉重叠冲突为零；但 347/348 identities 无权威绑定 | **DEGRADED_PASS / 全口径 BLOCKED** |
| G04 | 旧三日 528 条复权缺口逐证券补采、数值恢复、35 停牌不造 BAR | 563 行去重，528 均有 corrected 当前/T-1 ATR20，可用；35 仍是停牌无 BAR | **PASS_CORRECTED_CANDIDATE_SCOPE** |
| G05 | 复权原始字节、公司行为、OHLCVA、MA/ATR 独立重算 | R4 提交声称 ZIP CRC、20,843 重叠对照及 6.2M 以上 OHLC 独立数值无误；远端可读大型二进制均为 LFS pointer，当前未真正下载重跑核算 | **NOT_VERIFIABLE_EXTERNAL_BINARY** |
| G06 | 四日 Core/Profile 实际物化，防未来、留时点 | 提供四日期 Core/Profile/前一日 target-coordinate/hash 引用；字段统计完整，当前仅 corrected candidate | **DEGRADED_PASS** |
| G07 | 股票七项结构 Owner/有效状态恢复 | 10/08 relative_market 5170、relative_sector 5129、回踩 520、恢复 446、支撑 590、修复后的结构健康 590；**basic_breakout 仍 0 known**。旧结构健康原始输出也是 0，新投影独立计数；不能称旧七字段正式全恢复 | **FAIL_FULL_STRUCTURE** |
| G08 | 板块有效成员、Seed/Base/Rotation | 已收 4 日 BaoStock CSRC 行业（83 分类，非原产品 378 行业/概念体系）；概念历史时效仍未证明。10/08 B0 21 TRUE/32 FALSE/30 UNKNOWN，rotation 83/83 UNKNOWN | **DEGRADED_PASS / ROTATION FAIL** |
| G09 | 真实 Focus/Forward E2E 与后续状态 | 候选报告 2476 episodes / 7521 events；Forward 3417 OBSERVED/9738 PENDING，非线上生产读数；真实 frozen path 与 due 全样本的独立重算未完成 | **DEGRADED_PASS** |
| G10 | 10/08 走**正式 DM01 来源冻结/当日日更**、自动采集，不仅专项脚本 | 正常入口实际调用源采集和 corrected owner pipeline；但其日更子流程返回 `WAIT_BAOSTOCK_DAILY_UPDATE`，已修错误把 WAIT exit 0 当作可发布；最终 `BLOCKED_SCOPED_OWNER_RELEASE_GATE` | **FAIL_PRODUCTION_DAILY** |
| G11 | 候选独立测试与可回滚 successor | 有 72 测试及候选 append 故障恢复、幂等/陈旧 CAS 收据；没有正式获准的 10/08 successor 发布 | **DEGRADED_PASS** |
| G12 | 线上同 context token 读取最新 10/08 | `/api/v4/context`、IAB 仍然显示 `accepted_trade_date=2026-09-30`、stocks 5213、sectors 378、Focus 469；未切 10/08 | **FAIL** |

## 3. 不得混淆的三个层级

1. **网络抓取成功**：通过提交的请求/响应和 ZIP 下载记录说明源确已尝试并取得可用观察；不是最新日数据头。
2. **corrected candidate 计算成功**：原 528/528 在限定目标窗口恢复，四日 Core、Profile、部分结构和 CSRC 行业候选可读，但不是原本的 `AS_RECORDED`、`strict PIT`，且并不等于所有上市证券、所有结构字段、所有主题轮动齐备。
3. **正式生产验收**：需要经独立 bytes/numeric/oracle、契约及身份/权限、同 context CAS/回滚、实际 10/08 UI/API readback。**当前此项 FAIL**。

## 4. 下一轮应修复的确切阻塞（不要重做已恢复的 528 行）

**P0-1：完成正式数据和 Owner 接受门**。针对 10/08 原始官方 ZIP 与 corrected owner source/contract 的字节绑定、canonical 身份、价格基准/参数版本、来源时间戳和子域准入做外部独立 QA；获取可读取的真实 LFS 对象后 SHA 和关键 OHLC 样本复算。适用生产范围与未覆盖源必须显式隔离；用**新的** successor/head 合法承接，严禁将历史 10/09 补采误标 10/08 当时可见。

**P0-2：正式 DM01 的 `WAIT_BAOSTOCK_DAILY_UPDATE` 与 source acceptance**。检查 `run_v4_dm01_daily_increment.py`、`run_v4_current_daily.py`、`V4_CONTINUOUS_*` 合同。当前有主动源查询但冻结/构建/准入并未完整成功。按源实际状态修复合法数据流，不能把 WAIT 伪造 PROMOTED 或把 `source_requests_this_run=0` 的缓存再使用说成首次实采。提供 10/08 新 accepted head、Core/股票/板块/Focus/Forward 可读同日凭证，或明确 `BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION` 的独立审批对象。

**P0-3：347/348 条 canonical unbound 原始 BAR**。输出逐证券原因和品种/身份归类，既不能当作这 348 个都是 10/08 有效股票，也不能宣布全市场 canonical 身份已穷尽。对北交所、高退市历史、代码改名、ETF/指数鉴别使用现有生命周期映射合同，追加身份来源而非临时代码特例。

**P1-4：`basic_breakout_state` 与历史初始事件**。四日 0 known 的字段不能标整项通过；要查历史锚点首次可判定性与 prior episode 来源，既不强制 UNKNOWN→FALSE，也不能拿 590 条结构健康新候选代替原字段已接受状态。

**P1-5：板块不同分类体系**。CSRC 83 行业与 V4 原 378 行业/概念不能相互替代；历史 TDX 概念 effective membership 和 rotation prior episode 没有接受的来源。完成每日自动冻结并且只按具备有效日的范围准入；轮动仍 UNKNOWN 不能伪称 PASS。

**P1-6：其余模型/特殊风险字段**。市场价格限制压力轴仍缺有效日 Owner；Focus/Forward 的 due、退出/重入、历史 T0 first-available 必须用实际成熟样本验证，不强迫等 20 日才开发未完成代码。

## 5. 推荐下次外审的最小独立证明

- LFS 中对应 551 MB 官方 ZIP 与 4 日 Core/源数据的实际对象可访问性，抽样 OHLCVA 与时间、官方 ZIP SHA/CRC 与目录/身份数额外部复算；GitHub 文本中的 LFS SHA/大小不算解压和独立计算。
- 至少 30 个跨复权/停牌/代码变更/上市短窗真实成对样本，独立计算某日至此前一有效交易日的 ATR20/MA20，源变更与不同坐标仍留 UNKNOWN。
- 528/528 旧 QFQ gap 行级清单保留、10/08 动态 gap 分类、347/348 identity 原因清单与更正状态。
- V4 同 context token 10/08 首页/股票/板块/诊断/Focus/Forward 与独立来源 hash；CAS stale、bad source、roll back、same day rerun 的真实隔离测试。
- 对每一个无法获准的具体字段/域保留 `NOT_VERIFIABLE` 或 `FAIL`，不可因此阻止独立通过的原始行情、Core、Profile 的可使用性，但也不可发布污染既有生产源。

## 6. 核查证据入口

- [GitHub 冻结提交](https://github.com/NanOns/a-share-market-structure-research/commit/c010b818811689ed3056c6500ca5caa5cbadde4e)
- [R4 当前交接](https://github.com/NanOns/a-share-market-structure-research/blob/c010b818811689ed3056c6500ca5caa5cbadde4e/docs/evidence/source_acquisition_r4_20261009/R4_EXTERNAL_AUDIT_HANDOFF.md)
- [四日最终对账](https://github.com/NanOns/a-share-market-structure-research/blob/c010b818811689ed3056c6500ca5caa5cbadde4e/docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/FOUR_SESSION_FINAL_RECONCILIATION.json)
- [528+35 逐条对账](https://github.com/NanOns/a-share-market-structure-research/blob/c010b818811689ed3056c6500ca5caa5cbadde4e/docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/LEGACY_528_AND_35_RECONCILIATION_V2.json)
- [通达信修复收据](https://github.com/NanOns/a-share-market-structure-research/blob/c010b818811689ed3056c6500ca5caa5cbadde4e/docs/evidence/source_acquisition_r4_20261009/tdx_download_correction/CORRECTION_RECEIPT.json)
- [独立 QA 声明、发布门与回滚测试](https://github.com/NanOns/a-share-market-structure-research/blob/c010b818811689ed3056c6500ca5caa5cbadde4e/docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/INDEPENDENT_QA_AND_SAFE_RELEASE_READBACK.json)
- [10/08 正常日更 E2E](https://github.com/NanOns/a-share-market-structure-research/blob/c010b818811689ed3056c6500ca5caa5cbadde4e/docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/NORMAL_DAILY_E2E_RECEIPT.json)

**最终签署**：`EXTERNAL_ACCEPTANCE_BLOCKED`，可认可四日真实获取与旧 528 窗口 corrected candidate 修复的局部工程进展，但**不得签署 R4.1 全链最终验收通过，不得声称 2026-10-08 已进入生产读数**。此次独立审计未触碰源代码、指针或生产数据。
