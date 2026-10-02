# V4 R6 Promotion + Stage Entry 交接｜2026-10-02

V4-11 Accepted Head promotion PASS；Stage Head 为 V4_00_TO_V4_11_ACCEPTED；V4-12 Structure / Anchor / Support Stage Entry AUTHORIZED。本轮仅阶段元数据与合同入场，没有 V4-12 runtime / D1 implementation，也未通过 FULL D0/D1/D2 DAG。

外部依据为本轮 R5 独立外部验收原文，精确归档于 docs/evidence/next_round_r6。accepted implementation a8635c6802dc31e3c879207cd470bd63021e35ca，audited sealed HEAD 1c46d6681ba1d0540551bcc0f75b35c545ff2769。promotion validator/candidate clean tested commit 088042cb2b163b346cce932e18f29192913212fd。

## Promotion 顺序与验证

先读取并绑定外审，准备 candidate，在 clean detached checkout 完成独立 read-only validator，再执行正式 Head → Global Stage Head → V4-12 Entry，最后独立 post-readback 与幂等重跑。32 个 validator checks + 20 个 R5 hard gates 在 detached checkout 全 PASS；5 项 promotion 拒绝边界 tests PASS；post promotion 额外 Entry exact gate PASS。重跑前后 Head、Stage、Entry、Data 字节完全相同，repeat mutations=0。

绑定 R5 clean 2067 passed / 2 skipped / 0 failures/errors，无新增 deselection；R5 parity 5222 行，owner-input 8 字段各 10447 行，prior/current/event=5223/5224/5224。重开 sealed owner publications 校验实际 D2 manifest authority，独立核对 frozen prior 与 Event UNKNOWN safety，reducer AST/阈值/顺序 exact。

当前 V4-10 protected gate FAIL 保留为 EXPECTED_FAIL_CLOSED_HISTORICAL_AUTHORITY_BOUNDARY，不是 V4-10 stage failure；没有改旧 protected binding。

初次 preflight P26 遇到既有 M14 collector CRLF worktree 与 Git LF 的字节差异。原字节、Git digest 和只限此路径的换行表示证明保留；该证明仅用于 source preservation，不能用于 producer admission。没有修改 M14/M2 源码。初次失败 candidate 与记录作为 inactive evidence 保留。

## 精确 capability

LAUNCH_CONFIRM / RECOVERY_TURN 为 ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY；STRONG_PULLBACK / TREND_CONTINUE 为 DIAGNOSTIC_ONLY_NOT_FORMAL。D2_SEALED_OWNER_BRIDGE ENGINEERING_ACCEPTED；STATE_EVENT_V1 ENGINEERING_ACCEPTED_RECONSTRUCTED_LEFT_CENSORED_SCOPE。HISTORICAL_AS_RECORDED_EVENT NOT_PROVEN；FULL_D0_D1_D2_DAG 和 V4_12_STRUCTURE_SUPPORT NOT_IMPLEMENTED。

原 R4A、D0、R5 owner/AST/Event/scoped evidence 未改。Global Stage Head 保留所有既有字段，只更新 range/version、追加本轮 binding/capability/entry 与明确 false 的权限字段。V4_DATA_ACCEPTED_HEAD exact unchanged，accepted_trade_date=2026-09-30；Dev Baseline、PIT membership、scoped accepted heads 均 unchanged。

## V4-12 Entry

依据最高合同 REV4 FEP R2 §10J/10K/10L/13A/31/34A/41A0/41A/49A/72/78/81.4，登记 STRUCTURE_EVENT_V1、Anchor schema/identity/coordinates/rebase/lifecycle、invalidation/breakout/pullback/recovery AST、producer/field/parameter registry、time roles、UNKNOWN、schemas 和独立 vectors 的待完成 surface。Breakout/Pullback/Recovery 的规则 seed 与既有参数参考已登记，未执行算法或伪称 machine vectors PASS。

D1 只允许 F0[t] + t-1 frozen Anchor/event。禁止 D2[t]、same-day Final State/Event diff、Focus/UI、future outcome 和同日新 Anchor 自证 confirmation/support。新 Anchor 可产生今日 D1 event，最早 t+1 用于 support/path test。basis identity 继承 price_basis + adjustment_source_revision，系数是换基计算证据；原 Anchor 不回写，无法确定转换时 UNKNOWN/PRICE_BASIS_MISMATCH。

CONTRACT_COMPLETENESS 仍为 CONTRACT_INCOMPLETE：后续独立合同设计/冻结任务必须完成 registry、AST、parameter instance、source capability、UNKNOWN/time semantics、independent vectors 后，才能另行授权 runtime implementation。Stage Entry AUTHORIZED 不等于 runtime implementation 授权。

## 审计与 STOP

M14/M2 保留 PREEXISTING_NON_MAINLINE unresolved，resolution_claim=false，full_repository_runtime_pass_claim=false。本轮外部验收只授权精确 R5 工程 scope，promotion + entry 仍等待下一轮独立审计。所有 production/shadow/focus/global_mandatory_adoption 为 false。

统一 commit + push 后 STOP。不得进入 V4-12 runtime、V4-13 或任何 cutover。用户的“提供本项目任务卡 bundle 即直接执行、无需二次确认”约定已记录于 AGENTS.md；仍遵守每轮 gate 和 STOP 边界。
