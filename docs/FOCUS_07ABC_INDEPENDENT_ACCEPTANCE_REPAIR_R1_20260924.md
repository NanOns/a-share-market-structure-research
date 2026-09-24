# Focus 07A / 07B / 07C 独立验收整改 R1–R8

审计依据为 `D:/Users/lps/Desktop/FOCUS_07A_07B_07C_INDEPENDENT_ACCEPTANCE_20260924.md`。该附件提供问题清单与建议；仓库升级合同和用户请求约束实现及验收。本轮关闭其中 8 项当前可通过代码、事务、已接受日期回查或隔离数据库闭合的修复项。

## 阶段执行记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md`；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md`；`docs/ADJUSTED_DATASET_CONTRACT_V1.md`；`docs/FOCUS_07D_ENTRY_GATE_20260924.md`。 |
| stage_contract | 修复当前可独立闭合的审计发现；事实 provider 保持版本化、可解释及 fail closed；历史 source/publication 采用 append-only 身份迁移；原子写入和数据库回读需提供证据。代码与测试通过不替代真实 Forward 门；Auto Apply 与 07D 门独立。 |
| evidence | 精确代码提交 `3a2f7a8d92e9313b7b2ad4b5120f9a57d82f5601` 已 push。回归、分项测试、临时 PostgreSQL E2E、生产 DB 身份迁移/结算及 schema 回读见 `docs/evidence/FOCUS_07ABC_R1_R8_REPAIR_RECEIPT_20260924.json`。 |
| acceptance_result | `R1_R8_REPAIR_CLOSED / 07A_CODE_AND_TRANSACTION_CLOSURE_PASS / 07B_IMPLEMENTATION_PASS / 07C_CONTRACT_AND_CODE_PASS`。真实多日 Forward、生产 Path State V2 write/readback 与广泛事实覆盖仍待验；Auto Apply OFF；07D BLOCKED。 |
| next_stage | 按真实 accepted 日期继续 07A/07B Forward 验收，并在下一 accepted Focus 日核对 Path State V2 写入、manifest、closure、head 与 API readback；仅在 `docs/FOCUS_07D_ENTRY_GATE_20260924.md` 所有门满足后启动 07D。 |

## R1–R8 修复及验收

| 项 | 修复 | 验收 |
|---|---|---|
| R1 | 在最新修复提交上重新运行测试、compileall 和 diff 检查；归档精确 SHA 回执。 | Focus 153 passed；07A 32、07B 34、07C 18 passed；M3 自动输入 16 passed；静态检查 PASS。 |
| R2 | 正式支持 same-day revision 原子 writer，独立 run、observation、revision anchor 与 head；旧版本行保留。 | 临时 PostgreSQL D1 same-day r1→r2→r3 验收通过；旧 revision anchor 不进入当前 due 集合。 |
| R3 | 增加有界、按交易日顺序执行并在每步重读 replay chain 的执行器；未清链时拒绝向后跳日。 | 临时 PostgreSQL 验证先 D3 后 D4，跳过最早待回放日会阻止写入，最终 replay backlog 清零。 |
| R4 | V3.3 tracked episode 在当天 source row 缺席时仍依据首日冻结事实与当前市场事实运行 invalidation；仅当天 scanner 专属事实继续为 UNKNOWN。 | `test_focus_07b_post_exit_invalidation.py` 与完整 Focus 回归通过。 |
| R5 | 加入 PIT-safe RPS20/RPS20 delta3 provider：逐日 accepted membership、TDX native QFQ、same-date finite universe、120 实际 bars、75% 近期覆盖、最多 251 个交易日窗口。 | provider 专项测试及 Focus 回归通过；缺历史/身份/横截面时 fail closed 并在 evidence 中保留 provider gap。 |
| R6 | 以 append-only overlay 复验历史 publication 的 receipt/package SHA，并使 settlement/manifest/PIT reader 使用迁移身份。 | 2026-09-24 已到期 T+1 的 310/310 目标输入均 sealed；结算 310/310 `OBSERVED`，PENDING 0；原 publication 行未改写。 |
| R7 | 补齐 SOURCE_MODEL_BOUNDARY segment schema、writer、reader 与边界后持续跟踪。 | 隔离 PostgreSQL E2E 12 个断言通过，覆盖合同边界、同一 episode 延续、revision 可见性、旧 anchor 隔离及有序回放。 |
| R8 | 将独立审计回执、生产 settlement 摘要和迁移读回写入 `docs/evidence/`。 | 精简总回执、E2E receipt 与 T+1 settlement summary 已归档；详细 outcome 行明细保存在本地 ignored `reports/` 目录。 |

## 修复以外仍待真实数据验收的阶段门

- 07A：真实连续 accepted Focus 日、真实退出后的 D+1/D+2 observation、真实重入以及更长 horizon outcome 仍需随交易日自然积累。代码事务和合成 D1→D2→D3→D4 不替代这些样本。
- 07B：PIT RPS provider 已实现，但实际日期可能因历史 accepted universe 或覆盖不足而 fail closed；真实 RECOVERY_TURN 及 suspension→resumption 样本需要逐例 Forward 验收。未提供者的状态路径继续按 capability contract 标记 `NOT_APPLICABLE`。
- 07C：V2 resolver 算法及 sidecar 合同通过代码验收，production state 主合同仍按既定 V1 保持；下一 accepted observation 的 V2 sidecar 写入/readback 尚未发生。
- Auto Apply 继续 OFF。07D entry gate 继续 BLOCKED，直到要求的真实 07A/07B Forward evidence 到齐。

跨切面子审计状态见：

- [同日修订与顺序回放](audits/FOCUS_SAME_DAY_REVISION_ORDERED_REPLAY_GAP_20260924.md)
- [RECOVERY_TURN PIT RPS provider](audits/FOCUS_RECOVERY_TURN_RPS_PROVIDER_GAP_20260924.md)
- [历史 publication 来源身份迁移](audits/FOCUS_HISTORICAL_SOURCE_IDENTITY_MIGRATION_GAP_20260924.md)
- [SOURCE_MODEL_BOUNDARY writer/readback](audits/FOCUS_SOURCE_MODEL_BOUNDARY_WRITER_READBACK_GAP_20260924.md)

machine-readable receipts：[R1–R8 总回执](evidence/FOCUS_07ABC_R1_R8_REPAIR_RECEIPT_20260924.json)、[T+1 settlement 摘要](evidence/FOCUS_20260924_OUTCOME_SETTLEMENT_SUMMARY.json) 和 [SOURCE_MODEL_BOUNDARY E2E](evidence/FOCUS_SOURCE_MODEL_BOUNDARY_E2E_20260924.json)。
