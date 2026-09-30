# V4-08 R5.2 独立外部验收审计｜FINAL｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`8200a775d9c4115f479ee60b4c11a16579e86723`  
**R5.2 implementation commit**：`b7d904cbff4f1c4b877838bd129f3925f968d858`  
**上一轮 HEAD**：`c853f0ce1980d338d67fe0afb29d4ccaa95db648`  
**权威合同**：`A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md`

## 1. 唯一总状态

```text
V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE
```

这不是 production permission，也不是 Real Forward / Real Signal PASS。

正式接受范围：

```text
PIT Membership                       = ACCEPTED
Sector Native Core                   = ENGINEERING_ACCEPTED
B0 Sector PREWATCH Raw               = ENGINEERING_ACCEPTED
B1 Rotation Core                     = ENGINEERING_ACCEPTED
Accepted Daily Context Routing       = ENGINEERING_ACCEPTED

B2 Legacy Confirmed/Warm             = NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE
B2 Amount A                          = DIAGNOSTIC_AUDIT_OPEN

REAL_SIGNAL_CAPABILITY
= DEGRADED_BY_TARGET_CORE_DATA_HEAD_PRIOR_RPS_AND_FORWARD_PIT_HISTORY

PRODUCTION_PERMISSION
= FALSE
```

根据总合同 §17，`warm_raw / confirmed_raw` 未就绪时该能力可以 `NOT_IMPLEMENTED`，其他独立路径不受影响。因此 B2 的显式降级不再阻断 V4-08 工程验收。

## 2. 增量提交

相对上一轮：

```text
ahead_by = 2
behind_by = 0
```

提交：

```text
b7d904cb  fix(v4-08): route R5.2 accepted contexts and downgrade unwired legacy B2
8200a775  docs(v4-08): seal R5.2 scoped capability evidence and clean reaudit handoff
```

GitHub combined commit status 当前为空：

```text
statuses = []
```

记录为 CI 外部状态缺失，不单独构成失败。

## 3. R5.1-B04｜Daily Moving Accepted Authority｜PASS

R5.2 已新增：

```text
src/sector/accepted_context_r5_2.py
config/v4_08_accepted_context_contract_r5_2.json
```

正式 loader 改为：

```text
load_accepted_current(..., accepted_input_context=...)
```

不再自行寻找静态 V4-02 authority。

## 4. Three-head 架构保持正确

继续使用既有：

```text
V4_STAGE_ACCEPTED_HEAD = stage baseline
V4_DATA_ACCEPTED_HEAD  = daily moving data authority
V4_DEV_BASELINE_HEAD   = development baseline
```

没有新增第四个 daily head。

`resolve_daily_context()` 的生产路径：

```text
V4_DATA_ACCEPTED_HEAD
→ SHA-bound immutable manifest
→ manifest.accepted_input_context
→ raw_daily / adjusted_price bindings
```

静态 V4-02 读取只保留在：

```text
STATIC_ENGINEERING_BASELINE_CONTEXT
scope = ENGINEERING_REPLAY_ONLY
daily_production_authority = false
```

它不是生产 fallback。

## 5. 当前 Daily Lane 尚未完成，不构成 V4-08 阻断

仓库当前 DM-01 真实增量 component builders 仍为：

```text
NOT_WIRED_FAIL_CLOSED
```

所以当前：

```text
V4_DATA_ACCEPTED_HEAD.accepted_trade_date = 2026-09-24
```

并没有 2026-09-30 的 accepted raw/adjusted publication。

R5.2 对 9/30 正确返回：

```text
TARGET_ACCEPTED_DATA_UNAVAILABLE
```

而不是回退到旧 V4-02 artifact。

上一轮任务卡明确只要求 authority abstraction / context validation，不要求重写 DM-01。因此未来 DM-01 在 accepted manifest 中发布 `accepted_input_context` 属于 Daily Lane 后续能力，不反向阻断 V4-08 engineering acceptance。

## 6. Multi-context generalization｜PASS

同一 adapter source 能执行 Context T 与 Context T+1，二者具有不同 trade_date、artifact path、SHA、raw amount 和 price snapshot identity；不修改 adapter source、不修改固定 V4-02 head、不使用 static fallback。

同时验证：T+1 artifact/context 改变不会修改已冻结 T result/digest。

```text
PASS_CONTEXT_DRIVEN_MULTI_SESSION
```

## 7. Daily context 防伪造门｜PASS

`validate_context()` 对 DAILY_ACCEPTED_DATA scope 会校验：

```text
V4_DATA_ACCEPTED_HEAD contract
accepted_trade_date
source_head_digest
manifest_binding
parent_identity
source_revision
canonical_data_revision
component permission
manifest.accepted_input_context exact binding
```

caller 无法在 Data Head 模式自行替换 raw_daily / adjusted_price 路径；future context / future revision / digest mismatch 均 fail closed。

## 8. R5.1-B05｜Legacy valid-member Producer｜方案 B 合规关闭

R5.2 没有假造 `legacy_valid_member`，而是正式选择 Decision B。

实际 accepted inventory 中 V4-03/V4-05 factor rows 没有 exact `legacy_valid_member` producer；现有 accepted facts 也不能证明 legacy `missing_state` 与 actual_bar / research_universe / trading_status / PIT membership 完全等价。

因此不允许偷偷替代。

```text
PASS_CAPABILITY_DOWNGRADE
```

## 9. B2 capability overclaim 已修复｜PASS

上一轮错误：

```text
B2_NON_AMOUNT_A = ENABLED_ENGINEERING
```

现在正式：

```text
B2_NON_AMOUNT_A
= NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE

B2_AMOUNT_A
= DIAGNOSTIC_AUDIT_OPEN
```

正式输出：

```text
confirmed_raw = UNKNOWN
warm_raw      = UNKNOWN
```

算法诊断另存 `confirmed_diagnostic / warm_diagnostic`，不能作为正式资格。

## 10. Final-boolean injection 不能重新启用 B2｜PASS

R5.2 专门测试：即使向 synthetic factor row 强行注入一个看似合法的 `legacy_valid_member`，正式 adapter 仍将其降为 UNKNOWN，最终：

```text
confirmed_raw = UNKNOWN
warm_raw = UNKNOWN
```

因此 diagnostic path 无法绕过 capability gate。

## 11. §17 合同允许 B2 NOT_IMPLEMENTED

权威合同 §17 明确：

```text
warm_raw、confirmed_raw 来自已提取验收的纯Core legacy合同；
未就绪时该能力 NOT_IMPLEMENTED；
若 legacy资格依赖未关闭 Amount A，则该路径不能作为正式资格，保留diagnostic；
其他独立路径不受影响。
```

所以：

```text
B2 NOT_IMPLEMENTED != V4-08 整体 BLOCKED
```

## 12. Sector Native / B0 / B1 保持通过

Sector Native 保持 PIT membership、common-member delta、entered/exited isolation、§10A0 midrank、coverage/UNKNOWN semantics、raw amount concentration semantics。

B0 保持 parameter instance binding、Kleene tri-state、Seed degraded propagation、same-day feedback isolation。

B1 Rotation 保持 TRUE/FALSE/UNKNOWN/NOT_APPLICABLE、prior-member frozen pulse basket、price-basis identity gate、early/mature retention split、UNKNOWN pause、OUT/FAILED episode semantics。

R5.2 没有改这些算法。

## 13. 真实 2026-09-30 输出｜DEGRADED BUT VALID

当前：

```text
V4_DATA_ACCEPTED_HEAD = 2026-09-24
V4-05 Core            = 2026-09-28
V4-07 Base Seed       = 2026-09-28
V4-08 PIT Membership  = 2026-09-30
```

因此真实 9/30：

```text
B0       UNKNOWN = 378
ROTATION UNKNOWN = 378
B2       UNKNOWN = 378
```

这不是算法失败。原因包括 TARGET_ACCEPTED_DATA_UNAVAILABLE、NO_TARGET_ACCEPTED_CORE_FACTS、NO_PRIOR_ACCEPTED_PIT_HISTORY、DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL、B2_LEGACY_CAPABILITY_NOT_IMPLEMENTED。

禁止把 `0 TRUE` 解释为“市场没有候选”。

## 14. Prior-RPS 仍独立 OPEN

保持：

```text
V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01 = OPEN
```

它影响真实 Seed 能力，但不回滚 V4-07 engineering acceptance、不阻断 V4-08 engineering acceptance、不阻断 V4-09 engineering development。

禁止旧 R3 fallback、UNKNOWN→FALSE、改阈值。

## 15. Amount A 仍独立 OPEN

保持：

```text
AUD-AMOUNT-A-06 = OPEN
```

当前仅 DIAGNOSTIC，不进入正式 B2 资格。

## 16. Clean detached checkout｜PASS

implementation commit：

```text
b7d904cbff4f1c4b877838bd129f3925f968d858
```

回归：

```text
711 total
709 passed
2 skipped
0 failed
0 errors
```

并确认 git clean before/after、config/.env absent/not read、disposable PostgreSQL 18.6、temporary cluster destroyed。

## 17. PostgreSQL / Migration｜PASS

没有新增 migration 021，继续使用 migration 020。

验证：

```text
append-only publication       PASS
append-only results           PASS
1512 rows exact readback      PASS
membership integrity guards   PASS
basis-quality guards          PASS
```

## 18. NO_SYMBOL governance｜PASS

正式扫描：

```text
status = PASS
hard_gated_equity_symbol_hits = 0
unclassified_paths = []
```

未发现针对特定股票代码写死算法、特定股票例外分支或按个股代码调参数。

## 19. Protected Heads｜PASS

R5.2 没有修改：

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_DEV_BASELINE_HEAD
V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
```

当前 Global Stage Head 仍为：

```text
V4_00_TO_V4_07_ACCEPTED
```

在 external acceptance 之前这是正确的。

## 20. V4-09 入场依赖核对｜PASS

§78：

```text
V4-08 = Sector / Rotation Core
V4-09 = Stock PREWATCH
```

§22：

```text
raw_qualification
=
base_seed_state
AND
mandatory_core_quality_READY
```

同时 Sector Context 只在 D3 影响解释和独立 context 排序键，不能成为硬门。

因此 V4-09 不要求 B2 confirmed/warm 已实现、Rotation 已有真实 TRUE、9/30 Data Head 已推进、5/20 个 Forward 交易日完成。

## 21. 最终逐项判定

| 项目 | 结论 |
|---|---|
| PIT Membership | PASS / ACCEPTED |
| Sector Native | PASS_ENGINEERING |
| B0 Sector PREWATCH Raw | PASS_ENGINEERING |
| B1 Rotation Core | PASS_ENGINEERING |
| Daily Context Routing | PASS_ENGINEERING |
| Static V4-02 production fallback | ABSENT |
| Multi-context generalization | PASS |
| Frozen T immutability | PASS |
| B2 Legacy Confirmed/Warm | NOT_IMPLEMENTED |
| B2 capability classification | PASS |
| Amount A | OPEN_DIAGNOSTIC |
| Prior-RPS | OPEN_DEGRADED |
| Real 9/30 signal | DEGRADED_UNKNOWN |
| Migration / PostgreSQL | PASS |
| No-symbol | PASS |
| Clean regression | PASS |
| Production permission | FALSE |
| V4-09 engineering entry | AUTHORIZABLE_AFTER_PROMOTION |

## 22. 最终裁决

```text
V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE
```

正式 Accepted Head 必须记录：

```text
SECTOR_NATIVE_CORE = ENGINEERING_ACCEPTED
B0_SECTOR_PREWATCH_RAW = ENGINEERING_ACCEPTED
B1_ROTATION_CORE = ENGINEERING_ACCEPTED
ACCEPTED_CONTEXT_ROUTING = ENGINEERING_ACCEPTED

B2_LEGACY_CONFIRMED_WARM = NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE
B2_AMOUNT_A = DIAGNOSTIC_AUDIT_OPEN

REAL_SIGNAL_CAPABILITY
= DEGRADED_BY_TARGET_CORE_DATA_HEAD_PRIOR_RPS_AND_FORWARD_PIT_HISTORY

PRODUCTION_PERMISSION = FALSE
```

## 23. 下一动作

不是继续修 R5。

下一步：

```text
1. 执行 V4-08 Accepted Head Promotion
2. 更新 V4_STAGE_ACCEPTED_HEAD → V4_00_TO_V4_08_ACCEPTED
3. 独立验证 promotion
4. 正式进入 V4-09 Stock PREWATCH engineering implementation
```

真实 Forward / Daily Data / Prior-RPS / B2 legacy producer 继续各自并行积累和修复，不阻塞后续独立工程阶段。

**文档结束**
