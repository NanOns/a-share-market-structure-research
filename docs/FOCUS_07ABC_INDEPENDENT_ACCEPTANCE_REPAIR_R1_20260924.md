# Focus 07A / 07B / 07C 独立验收整改 R1

审计输入：`D:/Users/lps/Desktop/FOCUS_07A_07B_07C_INDEPENDENT_ACCEPTANCE_20260924.md`。该文件作为待核对发现与验收建议；项目修改仍受仓库合同和当前用户请求约束。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 的阶段门；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 4、7、9、10 节；`docs/FOCUS_07D_ENTRY_GATE_20260924.md`。 |
| stage_contract | 只修独立验收中可由当前代码与已接受证据闭合的缺陷；所有事实 provider 继续 fail closed；核心发布、outcome 结算、Auto Apply 和 07D 入口互相独立。每个新事实摘要使用明确合同版本。不得改写已接受 Focus run/head、publication 或 TDX 输入。 |
| evidence | 见 `docs/evidence/FOCUS_07ABC_REPAIR_R1_CORE_EVIDENCE.json` 与 `docs/evidence/FOCUS_20260924_OUTCOME_DIAGNOSTICS.json`。重跑 07ABC 定向套件、M3 bundle verification 测试、compileall 和 diff check 均通过。24 日 bundle 只读复验为 PASS，并提供之前缺失的来源 package SHA。 |
| acceptance_result | `PARTIAL_PASS / POST_EXIT_INVALIDATION_FIXED / SOURCE_IDENTITY_WRITER_FIXED / RPS_GAP_EXPLICIT / REVISION_REPLAY_OPEN`。不可据此宣布 07A/07B/07C 总阶段完成。Auto Apply 仍 OFF，07D 入口仍阻断。 |
| next_stage | 先设计并验收 accepted anchor/outcome revision 可见性，再实现 same-day writer 与 ordered replay；完成后另用临时 PostgreSQL schema 通过 D1→D2→D3 合成链。补做 SOURCE_MODEL_BOUNDARY writer/readback E2E 与历史 publication source-identity migration。之后实现 PIT-safe RPS20 provider，或继续将其保持为明确的独立 provider gap；真实停牌复牌、连续交易日和下一 accepted day 的 Path State V2 落库仍按未来样本门推进。 |

## 已修复

- V3.3 tracked episode 在当天没有 scanner source row 时仍评估冻结 thesis 和可用的本地逐日市场事实。当天 scanner-only 的 `structure_break_v3` 留为 UNKNOWN。合同为 `FOCUS_V33_TRACKED_INVALIDATION_V3`。
- bundle verifier 在验证 sealed receipt、官方 package SHA、metadata snapshot 和 extracted day data 后，返回 receipt 字节 SHA 与 `TDX_OFFICIAL_PACKAGE_SHA256_V1` 输入身份。M4 PostgreSQL writer 已读取这些字段；缺字段的历史 publication 不会被偷偷回填。
- 2026-09-24 的 310 个已到期 T+1 outcome 只读预览全部显示 `TARGET_INPUT_UNSEALED`；publication 被接受 310/310、seal 为 0/310、身份均为 `PUBLICATION_ID_ONLY`。目标日 BAR 为 310/310，路径质量 READY 293、CLOSE_NAV_ONLY 17，无路径缺口；状态全部 PENDING，写入为 0。来源 bundle 现已通过独立复验，package SHA 为 `b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f`。修复后的 verifier 会让后续 publication 获得精确来源身份；历史 publication 需要独立、版本化的身份迁移或保持待处理。
- RECOVERY_TURN 的 `rps20_delta3` 当前仍不可计算。`FOCUS_PREDICATE_FACTS_BY_DATE_V3` 将 provider gap 写入事实 digest；UNKNOWN validity 暴露 `RECOVERY_TURN_INVALIDATION_PROVIDER_INCOMPLETE`。没有把缺 provider 伪装成已实现或已验收。
- SOURCE_MODEL_BOUNDARY context 现在允许同 source family/entity 的 selection contract 变化，保留旧 episode 首日事实并采用当前来源 context；定向 context 测试通过。生产 writer/数据库端到端验收仍未完成，独立记录见 `docs/audits/FOCUS_SOURCE_MODEL_BOUNDARY_WRITER_READBACK_GAP_20260924.md`。
- 小体积 9/24 Focus、technical identity 与 outcome 诊断摘要已经归档到 `docs/evidence/`；Auto Apply 关闭状态也包含在 core receipt。

## 尚未通过的审计门

同日 revision writer 和按交易日顺序 replay writer 尚未实现。现有数据库模型没有按 accepted Focus revision 限定 anchor/outcome 可见性的 head；只取消 writer 的 revision=1 限制会让旧 revision 的 anchor/outcome 继续参与结算，因此该改法不安全。独立跟踪项及所需 schema/事务验收见 `docs/audits/FOCUS_SAME_DAY_REVISION_ORDERED_REPLAY_GAP_20260924.md`。对已接受 publication 补录历史 source identity 也尚未迁移，见 `docs/audits/FOCUS_HISTORICAL_SOURCE_IDENTITY_MIGRATION_GAP_20260924.md`。

RPS20 provider 与 RECOVERY_TURN 全量失效能力缺口独立登记于 `docs/audits/FOCUS_RECOVERY_TURN_RPS_PROVIDER_GAP_20260924.md`。真实退出后的后续 Forward、真实停牌复牌、至少五个连续 accepted 交易日及 07C V2 accepted write/readback 仍未由本次代码测试代替。
