# M10 主线状态合同 v2.4-preview

合同 ID：`MAINLINE_STATE_V2_4_PREVIEW`

本合同在 v2.3 的三态分类和优先级基础上，绑定正式金额 A 合同
`SECTOR_AMOUNT_COMMON_AGG_V1`。旧 `amount_vs_prior20` 与
`current_amount_vs_prior20` 只作为兼容/诊断字段，不参与 v2.4 的分类。

## 1. 正式金额 A

对板块 `s` 和当前交易日 `t`：

```text
H21(t) = C[t-20 : t]                  # 主交易日位置，不按行数补洞
U = members(H21(t)) ∩ qualified_amount_members(H21(t))
S(U, u) = Σ raw_amount[i, u], i ∈ U
D(U, t) = (1 / 20) × Σ S(U, u), u ∈ C[t-20 : t-1]
A(s, t) = S(U, t) / D(U, t)
```

同一集合 `U` 同时用于当前日分子和过去 20 个主交易日分母。`U` 的成员数、当前覆盖率、窗口覆盖率、分母来源、窗口起止日期、集合哈希和质量代码必须随结果保存。

- `OBSERVED`：按每个日期的成员快照对 H21 取交集；
- `RECONSTRUCTED`：使用明确声明的固定成员快照；
- 正数有限原始成交额有效；来源明确确认的零成交额有效；来源不明零、负数、非有限、缺失、质量失败和合成填充均为未知；
- `D <= 0` 或质量门未通过时 `A = NULL`；分子确认是零且 `D > 0` 时 `A = 0`；
- 默认质量门：可比成员数不少于 5，当前和窗口覆盖率均不少于 0.80。具体质量失败原因写入 `amount_quality_codes`。

成员金额比值中位数保存为 `member_amount_ratio_median_vs_prior20`，只用于诊断，不得回填或替代 `sector_amount_vs_prior20`。

## 2. 三交易日比较

比较日严格为主交易日历中 `t` 向前三位的 `C[t-3]`。当前 H21 与比较日 H21 的并集形成最多 24 个主交易日；比较使用该并集上的共同成员集合和相同质量规则：

```text
sector_amount_ratio_delta_3sessions_common
    = A(V, t) - A(V, C[t-3])
```

比较日期、两端 A、两端合计与分母、成员集合哈希、两端覆盖率、窗口覆盖率、窗口起止日期和质量代码保存于 `amount_comparison_evidence`。

## 3. 主线谓词

v2.4 保持原有三态语义：未知不等于失败，也不等于退潮；高优先级状态存在未知时不得提升低优先级状态。金额相关谓词改为：

- `FADING` 使用 `sector_amount_ratio_delta_3sessions_common < -epsilon`；
- `REACCELERATING` 使用当前 `sector_amount_vs_prior20 >= reaccelerating_amount_min`；
- `NEW` 使用当前 `sector_amount_vs_prior20 >= new_amount_min`；
- 正式金额 A 或其质量门结果未知时，对应谓词为 `NULL`，`missing_fields` 指向正式 A 字段或比较证据；不读取旧金额代理。

## 4. 存储、接口和页面

- `sector_cycle_daily` 通过 018 迁移追加正式 A 和完整证据字段；旧列不改义；
- `mainline_daily` 通过 018 迁移追加 `current_sector_amount_vs_prior20`、正式三交易日变化、口径、快照、质量和证据字段；
- `GET /api/sector-cycle`、板块时间线、`GET /api/mainlines` 和主线 evidence 输出正式字段；
- 主线每个 `trade_date` 必须绑定独立的 `analysis_slices` 记录，`analysis_slices.trade_date` 必须与 `analysis_snapshot_entries.trade_date` 相等；API `data_quality.field_coverage` 按 distinct slice 统计并报告日期不一致；
- 分析响应的 `basis_metadata` 显式返回最新域 slice、成员快照、价格口径、调整因子截止日、覆盖率和 capabilities；
- API 字段目录登记单位、窗口、成员口径、质量门和合同；
- 页面金额 A 显示 `NULL`/质量状态，不以旧代理补空；证据中展示口径、快照、质量门和比较证据；
- 旧 slice 继续按 `LEGACY_PROXY` 解释；新 v2.4 slice 的主线合同必须是 `MAINLINE_STATE_V2_4_PREVIEW`。

## 5. 验收样例

至少验证：共同集合分子/分母、H21 与 24 日窗口、主交易日缺口、成员变化排除、缺失/未知/确认零、低成员数、低覆盖率、非正分母、固定快照重建、三交易日共同集合比较、v2.4 不回退旧代理、DB 迁移、API 字段和端到端预览构建。
