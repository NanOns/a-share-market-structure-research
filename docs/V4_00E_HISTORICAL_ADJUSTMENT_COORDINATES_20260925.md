# V4-00E Historical Adjustment / Coordinates 阶段回执（2026-09-25）

| 字段 | 记录 |
|---|---|
| stage | `V4-00E / HISTORICAL_ADJUSTMENT_COORDINATES` |
| stage_contract | V4.2.2 REV2 §3B、§3F、§7.7、§41A.3、§78：冻结公司行为来源与 affine 算法、effective/system-available 双时点、历史降级、Anchor 坐标转换和结果评价坐标。 |
| consulted_upgrade | 最新 REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`；文件于本阶段开始时重新 hash，保持不变。合同复审 `docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md` SHA-256 `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`。 |
| input_identity | HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`；V4 合同 `TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1`；旧实现 `tdx-affine-qfq-v0.2` / decoder `tdx-local-gbbq-v0.2`。 |
| execution_boundary | 只读合同、代码、旧回执与项目内封存的 2026-09-24 metadata；未改写行情/复权数据、TDX、数据库或 production head；未运行测试/历史重算/scanner。新增合同、阶段回执、审计项均在项目 `docs/` 原子写入。 |

## 证据核对

- `config/adjustment.yaml` 仍声明 `adjustment-contract-v0.3`、`FORWARD_ADJUSTED`、本地 TDX `.day + gbbq`、`TDX_NATIVE_AFFINE_QFQ`、量额 RAW、`ROUND_HALF_UP_0.01`、future ex-day 截断；`src/adjustment/tdx_adjustment.py` 实现 XRXD per-10 参数和仿射系数。文件 SHA：config `f7a2711e18ba75d1252245ec7a0c947628fa06aca6fa3b0158670f0de0f25ab3`；engine `de8ce814dbdfc2fad7b16f619e1f1085a4dc539591d2bfe6dff876d805e8f6e0`；decoder `8b2b4736bfcec6bed5ae62c58b777c8306792aefd82b362970886c354672d03b`。
- 2026-09-24 source bundle 中 gbbq/map SHA 分别为 `f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1` / `f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8`。只读运行 decoder 审核：193,352 条，category 1 为 63,616，category 15 为 91，结构/解码错误 0。category 1 字段可见现金、送转、配股参数样本，但这不等于调整输出逐类型已独立验收。
- Phase1 receipt SHA `8c8a7efb087bb5f5ff8d137b0053322eef553ec381d44baa45b71d4c0952f9f5`：cutoff 2026-09-24、19,696,345 adjusted rows、旧阶段 PASS；normalized Parquet 当前文件复核 SHA 与 receipt 一致 `c6fc7b5455355390b0740b46e4bf24a2c5f458084cd6155478eae6c0be75c05a`。这是旧 V0.3 当前快照，不证明 historical PIT。
- `reports/p12_02/historical_input_pilot.json` SHA `1ef6c6dbc14d1c9767b2a0b676bdd10e78d98308dfe2926f915879b4b84ad6ff`：三 cutoff 日期、SZ.000001 / SZ.000009 current GBBQ 重建；核对 future ex-date 排除；明确 `CURRENT_GBBQ_SOURCE_ONLY_RECONSTRUCTED`。`reports/p12_02/reanchor_pilot.json` SHA `43c11829838369a2885651d84b2505d56061d84abefc1ada209822f9b5d72c0e`：两例真实 reference price reanchor 且窗口 adjusted OHLC mismatch 为 0；范围只有两例且未重新评估历史信号。
- 当下 V4-00D overlap 状态仍 `NOT_ACCEPTED`；本阶段复权合同虽已冻结，不能将未接受来源转入 Canonical Daily。当前 GBBQ snapshot 的 system-available 时间晚于大部分历史 target；历史重建不具备 as-recorded/PIT 资格。

## 冻结合同与能力门

本阶段新增 [TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1](TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1.md)，冻结本地 `.day + gbbq + map` 身份、XRXD affine 规则、参数/输出精度、new listing/suspension/missing action 策略、source visibility lineage、同一 artifact 的统一坐标变换、Anchor 不变性及以评价末日重锚整个 forward 路径的语义。

**尚未放行：** 当前 source package 未通过 V4-00D；缺少 category-15 影响定性、长停牌复牌与近期上市实证样本及其独立预期值、更正 revision 可见时间链。V1 状态为 `FROZEN_SPEC / EMPIRICAL_ACCEPTANCE_OPEN`；当前 V4 adjusted capability 为 `UNAVAILABLE`。RAW readiness 与 adjusted readiness 必须分开；依赖复权的因子不能回退 RAW。

新开独立审计 `V4-00E-REAL-ADJUSTMENT-ACCEPTANCE-01` (`OPEN`)，范围和关闭条件见 [审计回执](audits/V4_00E_ADJUSTMENT_ACCEPTANCE_AUDIT_20260925.md)。

**阶段接受结果：`DEGRADED_PASS / V1_SPEC_FROZEN_EMPIRICAL_ACCEPTANCE_OPEN`。** 合同和证据盘点完整，既有算法与数值回执可复用作基线；对本阶段要求的全部真实样本、类别覆盖和 PIT 可见性验收未完成，故 V4 调整价格不标 READY。

**下一阶段：`V4-00F / BAOSTOCK_SUPPLEMENTAL_CONTRACT`。** 可继续定义补充源的字段/单位/绑定/请求合同；BaoStock adjusted OHLC 仍不得作为 Core 价格。V4-01 bootstrap 和 scanner 继续受 V4-00D、V4-00H 门禁约束。
# Repair addendum (2026-09-25): `DEGRADED_PASS / ADJUSTMENT_CONTRACT_AND_FAIL_CLOSED_ENGINE_ACCEPTED`

The V4 affine-coordinate contract now has independent cash dividend, stock dividend/split, rights, combined-action, no-action, future-event cutoff, suspension/resumption window, recent-listing, unknown-category, Anchor-rebase, and common Forward evaluation-coordinate vectors under `tests/v4_phase0/test_adjustment_contract_vectors.py`. Unsupported category/action metadata returns `UNAVAILABLE_UNKNOWN_EVENT_CATEGORY`; RAW bootstrap remains authorized. Full adjusted history and historical empirical action coverage transfer to V4-01/V4-02; no adjusted history was synthesized in Phase 0.
