# V4-01 R6 Required Scope 执行记录 — 2026-09-26

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

### 当前验收结果与下一阶段

本地技术门禁为 `PASS_WITH_BSE_SCOPE_DEGRADED`，符合用户明确授权的 Required Scope。它不代表在线模型外部验收已经通过。V4-02 继续保持 `BLOCKED_PENDING_EXTERNAL_ACCEPTANCE`，直到在线模型独立复核完成。R6 代码、紧凑回执和请求账本提交推送后，下一步为外部在线模型验收；如任何 Required Scope 复核发现反证，重新打开对应门禁，不以 BSE 降级掩盖主线问题。
