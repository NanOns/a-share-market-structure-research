# TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1

- **合同 ID：** `TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1`
- **合同状态：** `FROZEN_SPEC / EMPIRICAL_ACCEPTANCE_OPEN`
- **价格身份：** `TDX_NATIVE_AFFINE_QFQ`
- **实现基线：** `tdx-affine-qfq-v0.2` + `tdx-local-gbbq-v0.2`
- **依据：** V4.2.2 REV2 §3B、§3F、§7.7、§41A.3、§78；承接 `adjustment-contract-v0.3`，不覆盖旧合同/既有 publication。

## 1. 输入身份与权威

1. RAW OHLC 唯一来自已接受、不可变的本地 TDX `.day` source package/local snapshot。公司行为来自同一 source manifest 所绑定的 `T0002/hq_cache/gbbq` 与 `gbbq.map`。两文件 SHA-256、snapshot/package ID、trade cutoff、观察/摄取时间和解析版本都是必需身份。
2. 合同计算身份至少为 `(source_manifest_digest, .day identity, gbbq SHA-256, gbbq.map SHA-256, decoder_version, adjustment_engine_version, contract_id, calendar_digest, target_trade_date, system_available_cutoff)`。变更任一项必须产生新的 parse/adjustment artifact 和 digest；禁止原地覆盖旧版。
3. `D:/new_tdx` 与配置的 TDX 输入目录永远只读。处理、暂存、发布均在项目目录；线上复权服务和 BaoStock 调整价不得作为正式价或 fallback。
4. 本地当前 GBBQ 是当前 source snapshot，不自动证明历史知识时间或全部历史证券/行为完备。缺 PIT 可见时间的历史计算归 `DIAGNOSTIC_NON_PIT`，不得标 `PIT_OBSERVED`。只有系统在当时实际观测并封存的输入可进入 `PIT_OBSERVED`；可重建且所有消费 revision 在截止时可见的历史输入标 `RECONSTRUCTED_ASOF`；截止后更正使用新 lineage `RECONSTRUCTED_CORRECTED`，不可覆写原结果。

## 2. 支持的行为、变换及精度

仅接受经验证映射的 category-1 `XRXD` 参数：`C1=cash dividend per 10`、`C2=rights price`、`C3=bonus/transfer shares per 10`、`C4=rights ratio per 10`。参数按锁定解码参考规范化为 0.01；非有限、负值/不合理分母、证券或日期身份歧义均使受影响证券的 adjusted series `UNAVAILABLE`，RAW 仍可独立 `READY`。

```text
m = (10 + C3 + C4) / 10
c = (C1 - C4*C2) / 10
Q[j] = A[j] * RAW[j] + B[j]
```

对某观察 cutoff `T` 与 raw bar 日期 `d`，只组合 `d < ex_day <= T` 且在所选消费 manifest 中 `system_available_at <= cutoff` 的有效事件；按 `(ex_day, source_record_index)` 稳定排序，按现有本地实现逆序复合系数。未来生效日永不消费；无 ex-day 实际 bar 的停牌间隔事件仍需纳入。`A`、`B` 用 Decimal/40 位上下文计算并以十进制无损字符串存储，`A>0`；仅最终 OHLC 按 CNY 0.01 `ROUND_HALF_UP`。volume 与 amount 保持 RAW。

当前实现只把 category 1 输入 QFQ。其他类别保留在源审计中且不得静默丢弃；若其是否改变价格/股本仍未分类，无法证明受影响证券调整完整性时，该证券 adjusted 为 `UNAVAILABLE` 并记录原因。当前封存包发现 category 15 共 91 条，语义/影响尚未独立定案；不得因为旧 v0.3 曾排除该类就把它视为 V4 已验收。

## 3. 生命周期、停牌、缺失与失败降级

- **新上市：** 不从第一根 bar 推断上市日期或历史身份；第一根可验证 raw bar 之前没有价格行。无充分原始/行为覆盖或证券身份时 adjusted `UNAVAILABLE`；历史窗口不足由消费者按各自合同标记 warmup/UNKNOWN。
- **停牌：** 无实际 bar 时 raw/adjusted OHLC 均为空；只允许经独立停牌证据合同构造单独的 aligned view，不写入 canonical daily。停牌期内除权事件按真实 effective date 参与后续复权。
- **缺失/未知行为：** gbbq/map 缺失、结构无效、security 映射歧义、未分类潜在价格行为、参数异常或无法验证覆盖时：`raw_quality=READY` 可独立保留，`adjusted_quality=UNAVAILABLE`，含稳定 reason code；依赖调整价的因子输出 `BLOCKED_BY_ADJUSTMENT`，不得静默退回 RAW、丢弃可疑事件或切换外部复权。
- **更正：** 上游更正须新 source revision、调整 revision、digest 与重构 lineage。不可改写既有已接受快照、PIT Universe 或 enrollment。

## 4. 共同坐标与 Anchor

若同一 verified artifact 对 bar `j` 的系数满足 `Q[j]=A[j]*RAW[j]+B[j]`，观察日 `t` 的同锚价格为：

```text
P[j|t] = (A[j]*RAW[j] + B[j] - B[t]) / A[t],  A[t] > 0
```

只可使用同一 package/snapshot、parser、decoder、engine、contract、adjustment artifact 和 cutoff 的系数；混用 artifact 或无法核实 `A[t]>0` 时拒绝换基。价格水平与冻结 Anchor 区间做完整仿射变换；Anchor 原始 basis、contract/source identity、as-of、anchor basis trade date、系数、source event/digest 永久冻结，日后只生成 `anchor_view_asof_t`。差值/ATR 只乘正尺度不加 beta；收益、百分比阈值必须在共同坐标上重算，不可直接沿用旧百分比或价格水平。

结果比较固定为目标/期限末日 `e` 的共同调整坐标：使用 `e` 截止且在评价输入 manifest 可见的行为版本，对 `[signal_date,e]` 全区间 O/H/L/C 统一重算后再算 FRET/MFE/MAE/MDD。迟到修订产生新 evaluation revision，绝不回写信号或旧评价；到期和缺失状态依 Forward 合同表达，不填零。

## 5. 可复现与放行条件

相同 `.day`、GBBQ、map、calendar、source manifest、parser/decoder/engine/contract、cutoff 与数值运行边界必须得到相同 `QFQ series logical digest`。摘要比较不能替代逐样本预期值。V4 `ADJUSTED_CANONICAL_PRICE=READY` 还需要：V4-00D source package overlap gate 通过、原始/身份/行为来源完整、独立实证样本和数学向量通过、source 可见时间及 cutoff 绑定清楚、失败降级回执可读。否则只准标 `FROZEN_SPEC`，不得把已有 V0.3/P1 `FULL_PASS/PASS` 外推为 V4 接受。

## 6. 已知证据与边界

- 已有 `adjustment-contract-v0.3` 冻结 `A*RAW+B`、现金/配股/送转参数语义、分币 HALF_UP、量额 RAW 和未来生效日截断；实现为 `tdx-affine-qfq-v0.2`。decoder `tdx-local-gbbq-v0.2` 可读取 `.map` 并解密 GBBQ。
- 当前项目封存 metadata snapshot `4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc` 的 `gbbq` SHA-256 `f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1`，map SHA-256 `f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8`；结构/解码报告 193,352 条记录，63,616 条 category-1，91 条 category-15；没有结构解码错误。源于 2026-09-24 snapshot，但 V4-00D overlap 尚未接受。
- Phase 1 历史回执记录 cutoff `20260924`、adjusted rows `19,696,345`、adjusted file SHA-256 `c6fc7b5455355390b0740b46e4bf24a2c5f458084cd6155478eae6c0be75c05a`。P12-02 已有 2026-03-31、06-30、09-14 两证券的 current-GBBQ 重建与未来生效事件排除、两个 Anchor 重锚例；其明确身份为 `RECONSTRUCTED_CURRENT_SOURCE`，不能证明 PIT。
- 未有本阶段独立核验的长停牌复牌/近期上市样本、现金/送转/配股各型预期价对照、category-15 影响分类及来源更正时间链。旧 `reports/phase0_1/ADJUSTMENT_VALIDATION.json` 是 V0.1，记录样本为 0；被后续 V0.3 替代，不能拿来宣称 V1 验收。
