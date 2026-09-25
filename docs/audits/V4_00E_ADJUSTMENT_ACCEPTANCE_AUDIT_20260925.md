# V4-00E-REAL-ADJUSTMENT-ACCEPTANCE-01 独立审计回执

| 字段 | 记录 |
|---|---|
| audit_id | `V4-00E-REAL-ADJUSTMENT-ACCEPTANCE-01` |
| status | `OPEN` |
| opened_at | 2026-09-25 |
| scope | `TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1` 的实际公司行为映射/预期值、类别覆盖、停牌/新上市边界、历史来源可见时间、确定性与 Anchor/Forward 坐标验收。 |
| evidence | 既有 V0.3 合同、`tdx-affine-qfq-v0.2`、`tdx-local-gbbq-v0.2` 及 Phase1 旧 PASS；2026-09-24 metadata gbbq/map 为固定 SHA，decoder 读出 193,352 条，其中 63,616 category-1、91 category-15。P12-02 有两只股票、三 cutoff 的 current-source 重建及两例 reanchor；明确 `CURRENT_GBBQ_SOURCE_ONLY_RECONSTRUCTED`。V4-00D package overlap 尚未接受。阶段回执为 `docs/V4_00E_HISTORICAL_ADJUSTMENT_COORDINATES_20260925.md`。 |
| impact | V4 `ADJUSTED_CANONICAL_PRICE` 保持 `UNAVAILABLE`；任何依赖复权的 V4 因子/窗口/Anchor 输出须 `BLOCKED_BY_ADJUSTMENT` 或对应 UNKNOWN；不得按 RAW 或 BaoStock 调整价回退。当前 snapshot 的历史重建不能作为 PIT observed/Forward cohort。 |
| independent_from | V4-00E 的 DEGRADED_PASS、旧 V0.3/P1 PASS、V4-00D overlap 审计、AUD-AMOUNT-A-06 及未关闭 V422 项；彼此独立。 |

## 独立关闭条件

1. 通过 V4-00D 接受的、身份完整且项目内不可变的 `.day + gbbq + map` package；冻结 decoder/engine/contract/calendar/cutoff hashes。
2. 对本地可映射的现金分红、送转、配股/组合行为样本提供逐证券/日期/原始输入/参数/预期 OHLC/实际 OHLC/系数/逻辑 digest；再用至少一个无行为 control 逐条核验，不只比较整表 digest。
3. 独立覆盖长期停牌后复牌和近期上市证券，证明无 ex-date bar 的事件处理、无虚构 OHLC、身份/上市日期未从首末 bar 推断；不满足证据时逐证券 fail closed。
4. 对 category 15 等未识别类别完成权威语义与价格影响裁定；所有仍可能改变 QFQ 的未支持记录均使受影响证券 `adjusted_quality=UNAVAILABLE`。
5. 同一来源/合同在多个历史 cutoff 做相同输入重建，逻辑 digest 可复现；未来事件、晚到旧生效日事件与更正事件分别有无泄漏预期。只有具有历史 system-available 证据的 source revision 才可标 PIT/RECONSTRUCTED_ASOF；后采集或修订事实另建 lineage。
6. 用实际 Anchor frozen-price 区间验证统一 t 坐标映射，再以评价末日 e 对完整 `[signal_date,e]` 重新调整并核对 FRET/MFE/MAE/MDD；混合 artifact、`A[t]≤0`、缺失事件与缺 bars 均 fail closed。
7. 阶段回执/能力快照、数据 digest 与 failure reason 可复核，且确认 `D:/new_tdx` 无任何变化。满足后由独立审计重新判定，不因本合同文件存在而自动关闭。

持续保持 `OPEN`，不将当前 V0.3 或历史 PIT 缺失解释为 V4 READY。
