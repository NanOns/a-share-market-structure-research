# A13 外部验收正式化｜2026-10-01

允许交付状态：`READY_FOR_EXTERNAL_REAUDIT`。A13 外部验收正式化验证 PASS；V4-08 Accepted Head KEEP，业务重建不需要。

唯一 acceptance authority 是仓库内的真实独立外部验收文件 `V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md`，绑定 exact path、bytes、SHA-256 和审计 HEAD `d85f815097a09ca2dceda00d0e29d6ff4fe331d4`。任务卡仅作为执行范围，未作为 external authority。

新增 versioned accepted sidecar 与 Accepted Head，content-addressed artifact 绑定原 candidate exact digest。原 candidate 的 134 条 primary semantic entries、raw/text/identity evidence 和 consumer permissions 全部保持原值。Accepted Head/config/runtime 显式限制为 evidence-governance acceptance。

真实 Accepted Head 的 `require_trading_event()` readback 检查了 24 条 IPO 发行暂缓、6 条 IPO 上市暂缓和 47 条 UNKNOWN，77 条均拒绝进入 trading status truth。当前 primary entries 中没有满足完整 identity/effective-date 与 trading permission 的真实已上市停/复牌事件，因此 positive trading-event authority 暂不消费；未把测试 fixture 作为市场事实。

在 fresh namespace 重新执行原 admission/PIT 和下游 kernel。移除任务指定三份误命名 notice 后，完整 50,162 PIT facts 与 accepted artifact exact 相同，V4-07 Base Seed、V4-08 四类 sector 输出及 V4-09 Prewatch 全部 business changed rows = 0。原反事实 receipts/output、候选、raw 和所有既有 business Accepted Heads exact hashes 保持不变。

新证据位于 `reports/audits/A13_FORMALIZATION_*`；fresh full replay 位于 `reports/audits/a13_formalization_counterfactual_r1/`。Cross-stage registry 更新裁决单独输出供合并，审计项为 ACCEPTED / PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT，并继续保留 accepted semantic truth guard 与 filename/capture-id 推断禁令。

回归范围 A13、V4-01、V4-02、V4-08、V4-09、DM01、NoSymbol，由 clean detached stage receipt 记录实际测试 commit 与结果。正式化元数据完成后提交外部复审，禁止 business head promotion，production/shadow/focus 继续 false。

最终与 P0 共享的一次实际 clean checkout 联合回归：tested commit `7ad623e2f4c845c76b8fb9de3ad752087426ebb7`，1496 passed、2 skipped、0 failures、0 errors，global NoSymbol PASS。正式化最终提交状态为 `READY_FOR_EXTERNAL_REAUDIT`，独立外部验收的既有 evidence-governance 裁决与本轮 metadata 复审边界分别保留。
