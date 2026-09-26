# V4-01 R6 Required Scope 执行记录 — 2026-09-26

## R6.1 外部审计续办记录（2026-09-26，取代 R6 final authorization）

- 输入审计：`V4_01_R6_EXTERNAL_AUDIT_AND_R6_1_FINAL_SEAL_20260926.md`。
- R6 原 Final Receipt 的 `stage_completion_authorized=true` 暂停生效；在 R6.1 all-day lifecycle coverage 通过之前，V4-01 维持 `BLOCKED`，V4-02 不获授权。
- 本地逐日覆盖（保留既有 R6 inclusive `symbol_effective_to` 语义）检查 786 日，发现 31 日缺失 39 条：`SH_MAIN=19`、`SZ_MAIN=11`、`CHINEXT=8`、`STAR=1`。最大单日缺失 2。
- 按审计要求只复查这些 31 日：每个日期执行两次独立新会话 `query_all_stock(day)`，并查同日全市场日线。31/31 两次名单稳定、摘要与已封存 R6 roster 完全一致，重复数 0、API 错误 0；因此没有发现新截断，不能把原始名单改写或从其他来源伪造补入证券。
- 生命周期结束日存在实证冲突：39 条缺失身份均在其 `symbol_effective_to` 当日缺席；另有 90 条身份在各自同日出现在已封存 R6 roster。90 条记录主要在 2023-07 至 2025-04，39 条缺失主要在 2025-05 至 2026-07。该反证不允许将所有 `outDate` 一律改为右开边界；结束日语义仍待根据有独立证据的业务规则裁定。R6.1 不据 roster absence 单独推断退市，不改生命周期表、不改 R6 源 roster。
- R6.1 覆盖回执为 `BLOCKED`，31 日仍有 39 条 lifecycle-active missing；下一步为 `RECONCILE_OUTDATE_BOUNDARY_SEMANTICS`。Final Receipt 必须保持 `stage_completion_authorized=false`。在线模型外部验收仍由用户指定的在线模型处理。
- 新增必需回归：全日零缺口、非触发 partial roster 检测、Final Gate 依赖 all-day coverage，以及 R6 结束日边界保留现有 inclusive 语义。`tests/v4_phase0` 最新结果 `126 passed, 2 skipped, 0 failed`，仅代表本地代码/规则测试，不构成范围验收。
- R6.1 实现 HEAD：`c4547e23d8132344e099e617401ec26fe80d1824`。对 BaoStock 的重查仅在 31 个实际缺口日期进行，账本保留调用记录。
- 边界复核补充：曾试算统一右开结束日，但随后发现 90 个 Required 身份确实在各自 `symbol_effective_to` 当日出现在 R6 roster；因此撤回统一边界变更，未将试算 universe 或回执纳入正式证据。当前结束日口径仍保持原 R6 inclusive 规则，39 条缺口仍为 blocker。
- 相关回执：`V4_01_ALL_DAY_REQUIRED_ROSTER_COVERAGE_R6_1.json`（`BLOCKED`）、`V4_01_MISSING_DAY_REQUERY_R6_1.json`（31 日复核 `PASS`）、`v4_01_test_receipt_R6_1_20260926.json`（126 passed/2 skipped）、`v4_01_final_stage_receipt_R6_1_20260926.json`（`BLOCKED`，`stage_completion_authorized=false`）。

## 阶段合同与当前状态

- 执行合同：REV2 §78 与用户本轮指定的 `V4_01_R5_EXTERNAL_AUDIT_AND_R6_REQUIRED_SCOPE_CLOSURE_20260926.md`。
- Required Scope：`SH_MAIN`、`SZ_MAIN`、`CHINEXT`、`STAR`；Optional Scope：`BSE`。
- 本阶段只处理 R6 roster 完整性、Required Scope 身份/生命周期/Universe/异常闭合、最终回执和测试。V4-02 的复权、日历、交易状态、周月、AS_OF、时间泄漏及涨跌停不在范围内。
- 外部在线模型验收由独立在线模型处理；本执行记录不代表外部验收。
- 执行开始 HEAD：`2b94f70da016f2f5c7a22acefcf604d81428e047`。
- R5 基线回执声称 786 日 `BUILT`，但审计列出 16 个 2,000 的整数倍边界日。2026-09-24 本地回执仅 2,000 行；新 BaoStock 会话实际重查返回 7,413 个唯一证券代码。独立 `query_daily_history_k_AStock(2026-09-24)` 返回 5,222 行。该实测证据确认 R5 `BUILT` 不等于内容完整，R5 roster PASS 判据撤销。
- 原 R5 身份回执的 `core_a_stock_unexplained_count=2997` 是 SH/SZ 前缀代理统计，不作为 Required Scope 验收指标。Required Scope 仅采用 `security_type=A_STOCK`、交易所、board、security_id、挂牌锚点及 source revision 字段；未知证券进入待分类隔离区。

## R6 实现计划

1. 冻结 `BAOSTOCK_DATED_ROSTER_COMPLETENESS_V1` 与 `REQUIRED_EQUITY_SCOPE_V1`。
2. 自动扫描分页边界整数倍、较大日降幅和生命周期规模差异日；异常日要求两次相互独立的新登录名册摘要一致，并由全市场日行情 A 股数据交叉核验。Provider `page_count` 仅记诊断信息。
3. 只在全部 786 日完整、所有触发日复查通过时原子发布 R6 roster；账本硬/软预算异常时失败关闭。
4. Required Scope 只纳入有类型、交易所、board、stable ID、生命周期区间及源修订绑定的 A 股身份。未知行保留为 `OUT_OF_REQUIRED_SCOPE_PENDING_CLASSIFICATION`。BSE 单独输出 DEGRADED，不阻塞 Required Scope。
5. 生命周期数据库逐板核对；历史 Universe 分 Required、BSE Optional、Pending 三个域生成独立摘要，BSE 不进入 Required digest。
6. 来源异常按 Required Scope 重新闭合；新增回归测试覆盖分页边界、重复会话、逐板身份、未知证券隔离和 BSE 降级不阻塞。

## R6 验收条件

- 786/786 日期具备有效逐日摘要，自动触发的每一天均完成双会话稳定性、required traded subset、生命周期规模三类核验。
- `SH_MAIN`、`SZ_MAIN`、`CHINEXT`、`STAR` 的身份和正式生命周期未决数均为 0。
- Required Historical Universe 的身份未决数和 Required Scope 未解释异常数均为 0；BSE 状态明确为 `DEGRADED_BSE` 并与 Required 输出隔离。
- 测试通过、测试回执绑定实现 HEAD、最终阶段回执引用 R6 小型证据回执。在线模型验收结束前 V4-02 仍保持未启动。

## 最终证据与下一阶段

### R6 实测结果

- **Dated roster completeness：PASS。** 自动扫描识别 16 个异常日期。每个日期均以两个独立新登录会话重查；32 次摘要全部稳定一致。另对同日 `query_daily_history_k_AStock` 做 16 次全市场交叉核验；已知 Required Scope 已成交 A 股都包含在新 roster 中，缺失数 0，未知已成交 A 股身份数 0，活动 Required 生命周期代码缺失数 0。R5 共 4,674,161 行，修复后的 786 日 R6 roster 共 4,721,349 行；R6 gzip SHA-256：`06ae1394a0de31f0abba98eab5203036fcab8e848a6db289edbb5a19aef581ac`。
- 主要边界日实测：2026-09-24 从 R5 2,000 行修复到 7,413 行；2026-02-24 从 6,000 行修复到 7,133 行。其余 14 个触发日也通过双会话与全市场交叉核验。
- 请求账本：R6 异常日复核共发起 48 个数据查询（32 次 roster、16 次全市场日行情，另计登录/退出）；保守登记后的 2026-09-26 日预算低于 40,000 系统软上限、45,000 硬上限和 BaoStock 50,000/日上限。未将账号、密码或 API key 写入代码或回执。
- **Required identity/lifecycle：PASS。** `SH_MAIN` 1,846、`SZ_MAIN` 1,641、`CHINEXT` 1,449、`STAR` 621 条身份记录均有 security ID、挂牌日期、type=1 源事实及修订绑定；四板块身份未决均为 0。DB lifecycle 对应 5,557 行全部物化，缺失行、source revision 绑定违规、时间戳违规均为 0，append-only trigger 存在。
- **Required source exceptions：PASS。** 38 条异常均保留；Required A-stock 未解释异常 0。26 条代码族候选继续留在非核心待分类队列，不伪装成已验证事实。
- **Required Historical Universe：PASS。** 786 日、4,036,121 条主线成员记录；沪主板 1,331,624、深主板 1,174,019、创业板 1,071,896、科创板 458,582。每个板块身份未决均为 0，bar 文件校验错误 0。9,119 条 bar 缺失单独记录，不推断停牌或交易状态，不阻塞 V4-01 membership。
- **BSE：`DEGRADED_BSE`，与 Required digest 隔离。** 保留 191,423 条候选/名册成员记录、101 个未解决来源身份、16 个待核实非股票候选；不阻塞四个 Required Board。
- R6 新增合同、实现与回归测试已执行：`tests/v4_phase0` 为 122 passed、2 skipped、0 failed；R6 脚本 `py_compile` 通过。测试仅是证据之一，不代替外部在线模型验收。
- R6 代码已在 `c8c2ed1` 封存；提交后再次完整运行测试仍为 122 passed、2 skipped、0 failed。外部 API 采集回执保留采集时 HEAD，并另绑定已提交的 R6 合同与实现 SHA；提交后的纯本地逐板/Universe 证据均在 `c8c2ed1` 上重建。API 复核使用的阈值与冻结合同相同，没有为封存而重复消耗 BaoStock 请求。
- R6 小型回执包含异常日逐项双会话摘要、独立行情集合摘要、缺失集合数量、source/data SHA 和 request ledger SHA；全量名册、Required/BSE Universe 与待分类集合 gzip 保存在本机忽略的 artifact store，不提交到 Git。

### 当前验收结果与下一阶段

本地技术门禁为 `PASS_WITH_BSE_SCOPE_DEGRADED`，符合用户明确授权的 Required Scope。它不代表在线模型外部验收已经通过。V4-02 继续保持 `BLOCKED_PENDING_EXTERNAL_ACCEPTANCE`，直到在线模型独立复核完成。R6 代码、紧凑回执和请求账本提交推送后，下一步为外部在线模型验收；如任何 Required Scope 复核发现反证，重新打开对应门禁，不以 BSE 降级掩盖主线问题。
