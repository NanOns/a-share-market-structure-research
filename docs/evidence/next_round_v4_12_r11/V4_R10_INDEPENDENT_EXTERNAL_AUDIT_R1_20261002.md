# V4 R10 独立外部验收审计 R1｜2026-10-02

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R10 基线 HEAD：** `d99c242ff90180372df1055d5fff266a48f38102`  
**tested source：** `4a23d2847ea415cb50d03c76ab4c45c0cc5ab25a`  
**当前远端 HEAD：** `7d35478780003d866faf85a730d0bb3b86af1134`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

# 1. 唯一总裁决

```text
V4_R10_EXTERNAL_AUDIT =
PARTIAL_PASS_R11_PERSISTED_D1_CHAIN_REQUIRED

R10A_CONTRACT_FREEZE_PROMOTION_RUNTIME_ENTRY = PASS

V4_12_RUNTIME_AST_ENGINE = PASS_ENGINEERING_KEEP
V4_12_RUNTIME_INPUT_BINDER = PASS_ENGINEERING_KEEP
V4_12_RUNTIME_SOURCE_AUTHORITY = PASS_KEEP
V4_12_RUNTIME_SINGLE_DAY_FULL_UNIVERSE_REPLAY = PASS_SCOPED

V4_12_RUNTIME_PERSISTED_T_MINUS_1_CHAIN = FAIL_P0
V4_12_RUNTIME_TRANSITION_ARTIFACT_SEMANTICS = FAIL_P1
V4_12_RUNTIME_OUTPUT_PROJECTION_COMPLETENESS = FAIL_P1

V4_12_RUNTIME_ENGINE_R1_EXTERNAL_ACCEPTANCE = BLOCKED_R11
V4_12_STAGE_ACCEPTED_HEAD = NOT_AUTHORIZED
```

已经成立的是：

```text
frozen contracts
→ 独立 runtime AST evaluator
→ registry-driven binder
→ exact accepted source binding
→ blocked capability fail-closed
→ 5224-security single-day replay
```

真正阻塞 V4-12 Runtime 外审通过的是：

> 今天产生的真实 D1 candidate 还不能成为下一市场日真正可消费的 `Frozen D1[t-1]`。

# 2. R10A｜PASS

R10A 已正式创建：

```text
reports/v4_12/V4_12_CONTRACT_FREEZE_EXTERNAL_ACCEPTANCE_R1.json
reports/v4_12/V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json
```

并正确绑定 R8/R9、V4-11 Accepted Parent、V4-12 Stage Entry 与 frozen contract set。

权限继续关闭：

```text
D2 = false
DB migration = false
V4-13 = false
Production = false
Shadow = false
Focus = false
Global adoption = false
formal V4-12 head = false
```

# 3. Runtime 主体可 KEEP 的能力

- `FrozenContracts` 会校验 Runtime Entry、Contract Freeze external PASS 和全部 frozen contract digest。
- `v4_12_ast_runtime.py` 没有 import validator/test，独立实现 frozen AST 与 UNKNOWN/ordered-select 语义。
- `v4_12_input_binder.py` 已做到 accepted source exact binding、blocked capability fail-closed、禁止 unknown F0 默认 Core、禁止 provider/candidate digest 替代。
- 真实 replay：
  - `raw_fallback_count = 0`
  - `provider_replacement_count = 0`
  - `V4_11_candidate_substitution_count = 0`

这些全部 KEEP。

# 4. Single-day full-market replay｜PASS_SCOPED

2026-09-30：

```text
universe_count = 5224
anchors_created = 0
events_created = 0

breakout = UNKNOWN 5224
pullback = UNKNOWN 5224
recovery = UNKNOWN 5224
support = UNKNOWN 5224
acceptance = UNKNOWN 5224
retention = UNKNOWN 5224
```

主要原因是：

```text
NO_ACCEPTED_PRIOR_D1_PUBLICATION
No exact prior ATR publication plus accepted cross-basis transform
ACCEPTED_ADJUSTMENT_NOT_READY
MISSING_ACCEPTED_SOURCE_ROW
```

这在当前 capability boundary 下是正确的 fail-closed 结果，不需要为了降低 UNKNOWN 去补算。

# 5. 测试事实

```text
275 PASS
0 FAIL
0 ERROR
0 SKIP
4 DESELECT
```

R10 tested source：

```text
4a23d2847ea415cb50d03c76ab4c45c0cc5ab25a
```

最终 HEAD 只比 tested source 多 evidence-only seal。

GitHub 当前没有额外 status/workflow，因此不声称 CI 背书。

# 6. P0｜真实落盘结果无法成为下一日 Frozen D1[t-1]

当前 `InputBinder.prior()` 要求 prior snapshot：

```text
trade_date == previous market session
security_id exact
namespace = Frozen D1[t-1]
contract_digest exact
available_at <= cutoff
candidate_manifest required
manifest.status = ENGINEERING_CANDIDATE_NOT_ACCEPTED
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
```

并继续读取：

```text
payload.facts
payload.anchor
payload.counter_state
```

用于下一日 FROZEN_PRIOR_D1、Anchor、Support、Acceptance、Breakout、Recovery。

接口设计合理，但 R10 真正持久化的 runtime candidate **没有产出这种 snapshot**。

当前 manifest 只有：

```text
V4_12_D1_RUNTIME_CANDIDATE.jsonl
V4_12_INPUT_BINDING_CANDIDATE.jsonl.gz
V4_12_ANCHOR_CANDIDATE.jsonl
V4_12_EVENT_CANDIDATE.jsonl
V4_12_TRANSITION_CANDIDATE.jsonl
...
```

没有等价 `Frozen D1[t]` snapshot bundle。

# 7. D1_RUNTIME_CANDIDATE 不能直接作为 prior()

当前 observation row：

```text
namespace = D1_CANDIDATE
identity
security_id
trade_date
revision
outputs
derived
anchor_construction
prior_state_ref
frozen_output_envelope
```

而 `prior()` 需要：

```text
namespace = Frozen D1[t-1]
facts
anchor
counter_state
```

因此：

```text
today runtime artifact
!=
tomorrow binder-readable frozen prior artifact
```

# 8. Synthetic SessionLedger 不能替代 persistence closure

当前 multi-day sequence 运行在 `SessionLedger.history` 内存中。

它证明 counter/state 数学正确，但没有证明：

```text
T0 runtime writes disk
→ process ends
→ T+1 fresh process
→ exact snapshot readback
→ InputBinder.prior()
→ same states
```

所以：

```text
synthetic multi-day PASS
!=
persisted cross-day runtime PASS
```

# 9. P1｜TRANSITION_CANDIDATE 不是实际 transition

当前：

```text
V4_12_TRANSITION_CANDIDATE.jsonl rows = 31,344
31,344 = 5,224 × 6 outputs
```

Runtime 对每个 machine 都无条件写一行，包括 UNKNOWN，甚至把 `retention` 这个数值指标也写成 transition。

当前 transition row 没有：

```text
from_state
to_state
transition_kind
current_observation_ref
```

所以它实际是 daily state observation/projection，不是真正的 state transition。

最高合同明确区分 `structure observations` 与 `state transitions`，正式 storage 前必须拆开。

# 10. P1｜retest_count 没有投影

Field Registry：

```text
retest_count
producer = SUPPORT_STATE_V1
role = D1_OUTPUT
```

AST 已算 `next_test_count`，SessionLedger 也维护 `test_count`，但 StructureEngine 的 output envelope 目前固定：

```text
retest_count = None
```

未来有真实 prior 时会出现“计算存在、正式输出缺失”。

# 11. P1｜invalidation_facts 永远为 null

Runtime 已能计算：

```text
episode_invalidated
hard_invalidated
deep_breach
breach_count
...
```

但 output envelope：

```text
invalidation_facts = None
```

永远如此。

正确应区分：

```text
known TRUE -> explicit triggered facts
known FALSE -> []
UNKNOWN -> null + exact reason
```

# 12. P1｜last_known_support_state 投影不完整

当前：

```text
last_known_support_state = prior_support_state
```

无论今天 support 已经变成 RECLAIMED / HELD_TENTATIVE / HELD_CONFIRMED，都仍指向昨天。

正确：

```text
current support KNOWN
→ last_known_support_state = current support

current support UNKNOWN
→ preserve t-1 last known support
```

# 13. Anchor/Event 为 0 不是 blocker

当前真实 2026-09-30 没有正式 source capability 支持 Anchor 创建，所以 0 anchors / 0 events 可以接受。

R11 不需要等真实样本，只需：

```text
persisted synthetic known-path chain
+
real 2026-09-29 → 2026-09-30 fail-closed candidate chain
```

证明持久化 wiring。

# 14. R11 不重做

KEEP：

```text
R10A Runtime Entry
FrozenContracts
ASTEngine
R2 Source Authority
R2.1 Time Counter
accepted-source InputBinder path
blocked capability policy
69 business vectors
33 sequence steps
12 authority vectors
10 time-domain vectors
DAG negative gates
single-day 5224 replay
```

# 15. 下一步

严格：

```text
R11A Persisted Frozen D1 Chain
→ local PASS
→ R11B Transition + Output Projection Closure
→ unified commit + push
→ STOP
```

# 16. Heads

继续：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

禁止 V4-12 Accepted Head、V4-13、D2、Radar、Focus、Production、Shadow、正式 DB migration。

# 17. 预计后续

若 R11 外审 PASS：

```text
V4-12 Runtime Engineering = PASS
```

下一轮可做：

```text
V4-12 scoped engineering Accepted Head Promotion
Stage Head -> V4_00_TO_V4_12_ACCEPTED
V4-13 Stage Entry
```

当前 blocked source capability 继续作为显式能力边界，不阻塞后续开发。
