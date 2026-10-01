# A02 / A05 / A04 scoped promotion closure R3 — 2026-10-02

本轮依据为归档的 `V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md` 与总调度卡 R3，实施基线为 d119c0526e44a819f85b4917159d3eeb5daadf2a 的当前 descendant。阶段入口 Phase 0 = DEGRADED_PASS。三卡均只登记外部已批准的精确 scope；独立 source replay 与 post-promotion readback 均为本轮重新运行。

| Task | Contract / Acceptance | Evidence / result | Next stage |
|---|---|---|---|
| A02 | A02_A05_A04_SCOPED_PROMOTIONS_R3_V1 / PASS_RECONSTRUCTED_CORRECTED_SCOPE | V4-05 / V4-07 / V4-09 各 5222 行；changed = 5222 / 5222 / 2811；15666 full old/new business diff rows，source oracle mismatches = 0 | 三个 append-only Amendment Heads，显式 historical research choice；等待统一提交后外审 |
| A05 | 同一 versioned contract / PASS_CURRENT_SNAPSHOT_ONLY | 2026-09-24，541 sectors，10 zero-member sectors，normal quote universe 5464；FALSE 535 / TRUE 2 / UNKNOWN 4；独立 exact AST mismatches = 0，9/30 rotation/context business diff = 0 | CURRENT_SNAPSHOT_20260924 显式读取，拒绝其他日期；等待统一提交后外审 |
| A04 | 同一 versioned contract / PASS_ENGINEERING_GO_FORWARD_SCOPE | 378 sectors，known Amount-A = 0，warmup UNKNOWN = 378，accepted sessions = 1，missing H21 = 20；实际 source admission / amount / membership replay 字节完全一致 | ACCUMULATION_CONTINUES，逐 accepted session append-only；consumer external acceptance 单独进行 |

最终状态为 `A02_DOWNSTREAM_AMENDMENTS_PROMOTED_SCOPED`、`V4_08_B2_CURRENT_SNAPSHOT_SCOPED_AMENDMENT_PROMOTED`、`A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTED` 与 `ACCUMULATION_CONTINUES`。

A02 每个 Amendment Head 精确绑定独立 RPS Head、old/new replay、business diff、原算法/参数 SHA、外部审计和本轮独立 readback。V4-09 绑定与 V4-07 相同的 exact seed artifact bytes。知识 lineage 为 RECONSTRUCTED_CORRECTED；AS_RECORDED = false；historical_first_availability_proven = false。Reader 必须显式选择 ORIGINAL_ACCEPTED 或 RECONSTRUCTED_CORRECTED_AMENDMENT，并返回所选 Head 与 mode；没有 silent fallback。

A05 独立 capability amendment 精确绑定 A05 acceptance record 与 R3 replay/diff，允许日期仅 2026-09-24，historical_PIT_equivalent = false。Amount-A warm branch 仍为 UNKNOWN / DIAGNOSTIC_AUDIT_OPEN，不注入 2026-09-30 V4-08。

A04 Head 仅接受工程 producer。formal_consumer_enabled = false；historical_reconstruction_accepted = false；H21_warmup_required = true；stock_amr20_dependency = false。未来 accumulation 继续复用严格 admitted daily command `python scripts/run_a04_go_forward_r3_1.py`，实际 accepted membership + amount source → observation → append-only。未到 H21 保持 UNKNOWN；达到 H21 后也不自动启用，必须另做 H21 completeness、source consistency、arithmetic oracle、consumer-specific external acceptance。没有回填不存在的 first availability。

五个新 Head 为 allowlisted scoped pointers，payload 以 SHA-256 命名并 immutable atomic publication。再执行 promotion 保持 pointer/payload 字节一致。实际 rollback 仅在临时副本验证：删除 exact bound pointer，保留全部 durable payload/evidence；真实 Heads 未 rollback。旧 Heads 与 Data/Stage Heads 已按本轮入口 SHA 验证完全不变。

本轮 targeted regression 57 passed / 0 failed / 0 errors / 0 skipped，覆盖 scope escalation、未来日期、unaudited rehashed candidate、consumer/permission escalation、idempotence、rollback 以及原 A04 arithmetic/source/stock independence 与 A02/A05 tests。测试结果与 source oracle、external authority、post-readback 共同构成 scoped readiness，不将测试代替外部验收。

证据目录：`reports/audits/next_round_r3/scoped_promotions/`。生产、Shadow、Focus、Global Mandatory Adoption 均为 false；Data Head KEEP 2026-09-30；Stage Head KEEP V4_00_TO_V4_10_ACCEPTED；本登记不产生 V4-11 Accepted Head，也不授权 V4-12 runtime。下一步仅 root 统一 commit + push 后 STOP，等待本轮独立外部验收。
