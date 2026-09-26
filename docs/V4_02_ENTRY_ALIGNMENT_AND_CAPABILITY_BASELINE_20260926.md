# V4-02 准入对齐与能力基线（2026-09-26）

> 本文记录 02 阶段准入后、RAW runner 实施前的初始基线；后续执行和当前状态见 [RAW canonical candidate progress](V4_02_RAW_CANONICAL_CANDIDATE_PROGRESS_20260926.md)。

## 阶段合同

- 阶段：`V4-02 / Canonical Daily / PIT Periods`
- 最新合同：`DA-MSR-V4.2.2-CODEX-REV2`，SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`，适用 §§3B.6、3C.1–3C.4、5.2–5.3、6A、10N、78。
- 机器合同：`V4_CANONICAL_DAILY_PIT_PERIODS_V2`；执行映射：`V4_02_STAGE_ACCEPTANCE_MAPPING_V1`。
- 范围：RAW / adjusted canonical daily、正式市场日历、交易状态与停复牌、正式周/月线、`CLOSED_ONLY` / `AS_OF`、§3C.4 temporal leakage、`PRICE_LIMIT_RULE_V1`、原子发布、独立后检。沪深主板、创业板、科创板均为 required scope；北交所仅可作为隔离的 optional degraded scope。
- 禁止：写入任何 TDX 源目录、运行 scanner/factor/trading、将 current-universe backfill 称作历史 PIT、合成调整因子、推断历史涨跌停、一般性 `DEGRADED_PASS`。

## 准入证据与执行结果

最新适用准入文件为 [V4-01 R6.2 外部验收](evidence/V4_01_R6_2_FINAL_EXTERNAL_ACCEPTANCE_20260926.md)，SHA-256 `6c8d1c69fc7e473964995b4d00abd5150d9474e5065fca22d7ec112a0b4d3a5c`。它明确 V4-01 为 `PASS_WITH_BSE_SCOPE_DEGRADED`、`EXTERNALLY_ACCEPTED`，V4-02 `AUTHORIZED_TO_START`，V4-03 `BLOCKED`。Phase 0 回执为 `DEGRADED_PASS`，V4-01 R6.2 required scope 为 `PASS`，四个 required board 均为 PASS。

原 V4-02 机器合同仍要求 `V4-01 FULL_PASS`，并不允许用户已授权的 BSE-only 降级。本次升级合同版本到 V2，新增字段级验收映射，并将外部验收全文以其原 SHA 封存于项目证据目录。执行 [V4-02 entry gate](../reports/v4_02/V4_02_ENTRY_GATE_20260926.json) 后，11/11 项通过，`entry_status=ENTRY_AUTHORIZED`。这只确认准入，不代表 02 的数据能力或阶段验收通过。

## 能力基线

| 能力 | 当前结论 | 当前证据 / 待验收边界 |
|---|---|---|
| V4-01 required historical universe 与日期身份 | 上游 PASS | R6.2 回执：4,036,121 条 required membership rows；四个 required board `identity_unresolved=0`。 |
| 本阶段 RAW canonical v2 | OPEN | 旧 2026-09-24 输出标为 `SUPERSEDED_CANDIDATE`；本阶段尚无消费 R4 source-selection 与 R6.2 identity 输入的新 run。 |
| Adjusted canonical | UNAVAILABLE | V4-00E adjustment audit 仍 OPEN；当前 GBBQ snapshot 属 reconstructed lineage，缺类别/真实样本与 system-available 证据。不得从 RAW 或 BaoStock 回退。 |
| 正式交易日历 | UNAVAILABLE | 当前 `config/trading_calendar.yaml` 是旧项目日历配置，`index-bar-derived proxy` 只能用于诊断，不能证明正式交易日集合。 |
| 逐日交易状态、停牌、复牌 | UNAVAILABLE | V4-01 明确 bar 缺失不能推断 suspension/delisting；本阶段尚无通过验收的日期化 status facts。 |
| 正式周/月线与 CLOSED_ONLY / AS_OF | UNAVAILABLE | 需正式 calendar、coverage 与停复牌证据后再验收；旧周/月线只可作诊断。 |
| §3C.4 temporal leakage | OPEN | 尚无多边界截断、未来行扰动不变性及 independent readback 证据。 |
| PRICE_LIMIT_RULE_V1 | UNAVAILABLE | 旧 `M8C` 公开规则合同不能代替本阶段基于日期、身份/状态、上市阶段、除权参考价的正式规则表与独立样本。 |
| 原子发布与独立后检 | OPEN | 旧脚本已有临时文件替换和独立后检代码，但它们绑定旧 R2 输入门与历史 run；尚未对当前输入合同和新输出执行独立验收。 |

## 阶段验收与下一步

- 当前结论：`ENTRY_AUTHORIZED / IMPLEMENTATION_OPEN / ACCEPTANCE_NOT_ACCEPTED`。
- 上述缺失项全部影响正式 V4-02 能力。除 BSE 外不允许以笼统降级通过；任何尚未满足的 required capability 都保持 `BLOCKED`。
- 下一阶段工作：更新 RAW canonical runner，使其消费已接受的逐证券来源优先选择与 R6.2 日期身份输入；绑定 ZIP 与 extraction 中每个源文件；实现新 run 的原子发布和独立后检。此后再逐项关闭 adjustment、calendar/status、formal periods、temporal leakage 和 price-limit gates。
- 暂不执行 V4-03；只有完成并接受 V4-02 后才能进入。
- 本次无 TDX 根目录访问/写入、数据库写入、下载、scanner、factor 或 trading 执行；未运行测试。
