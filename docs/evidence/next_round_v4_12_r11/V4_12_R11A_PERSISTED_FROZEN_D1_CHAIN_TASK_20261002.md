# V4-12 R11A｜Persisted Frozen D1 Chain Closure Task｜2026-10-02

**基线 HEAD：** `7d35478780003d866faf85a730d0bb3b86af1134`  
**任务性质：** P0 Persisted Cross-Day Runtime Closure  
**R10A / AST / Binder：** KEEP  
**Stage/Data Head：** KEEP

# 1. 唯一目标

把：

```text
D1[t] runtime candidate
```

真正变成下一市场日：

```text
Frozen D1[t-1]
```

可消费的持久化 snapshot。

必须证明：

```text
process A writes T
→ process ends
→ process B reads T as exact frozen prior
→ computes T+1
```

禁止继续只用内存 `SessionLedger.history` 证明跨日能力。

# 2. 新增 Frozen Snapshot contract

新增 versioned contract，例如：

```text
config/v4_12_frozen_snapshot_contract_v1.json
contract_id = V4_12_FROZEN_D1_CANDIDATE_SNAPSHOT_V1
```

不得修改 R8/R9 已冻结 business AST/parameters。

# 3. Snapshot row 至少包含

```text
snapshot_id
security_id
trade_date
revision
available_at

namespace = Frozen D1[t]

contract_digest
entry_digest
input_digest
observation_digest
source_candidate_manifest_digest

facts
anchor
event
counter_state

support_state
acceptance_state
breakout_state
pullback_state
recovery_state

knowledge_lineage
AS_RECORDED
formal_accepted
```

# 4. facts 唯一来源

只能从当日完成的：

```text
runtime bindings
derived values
runtime outputs
immutable anchor/event candidate
```

投影生成。

禁止为了 snapshot 再读 raw K、V4-11 candidate、别的 provider 或重新计算获得 authority。

# 5. counter_state

至少冻结：

```text
post_creation_evaluable_sessions
held_count
breach_count
recovery_held_count
test_count
separated_sessions
```

并保存：

```text
counter_contract_id
counter_state_digest
```

# 6. Anchor / Event

没有 Anchor：

```text
anchor = null
event = null
```

有 Anchor：

```text
owning/bound Anchor exact
owning Event exact
episode-bound Anchor 不得被 active display Anchor 替代
```

# 7. Bundle 设计

不要创建 5224 个散文件。

允许：

```text
Frozen Snapshot JSONL/JSONL.GZ bundle
+
security index/manifest
+
bundle digest
+
row digest
```

Binder 必须 exact 定位 security row，不允许 latest-file 猜测。

# 8. Candidate Manifest

新增：

```text
V4_12_FROZEN_D1_CANDIDATE_MANIFEST_V1
```

保存：

```text
trade_date
revision
available_at
entry ref
contract digest
snapshot bundle ref
row_count
security_ids_digest
source runtime manifest ref
knowledge_lineage
AS_RECORDED
formal_accepted = false
```

# 9. InputBinder.prior() 改造

支持 exact frozen bundle/index readback，并验证：

```text
trade_date == previous market session
security_id exact
namespace exact
contract_digest exact
available_at <= cutoff
manifest exact
row belongs manifest
knowledge lineage exact
AS_RECORDED explicit
```

same-day / future / unsealed prior 必须 reject。

# 10. Persisted synthetic multi-day E2E

禁止只调 SessionLedger。

必须使用真实：

```text
StructureEngine
CandidateStore
Snapshot Materializer
InputBinder.prior()
```

跨 fresh process / fresh loader 执行：

```text
T0 Anchor creation
T+1 missing/suspended
T+2 first evaluable hold
T+3 second hold
T+4 breach
```

验证 market age、evaluable count、held/breach count、support、acceptance、Anchor immutability、prior snapshot ref。

# 11. Same-day revisions

同日 r1/r2/r3 都必须读取同一个 t-1 frozen snapshot。

禁止：

```text
r2 prior = r1
r3 prior = r2
```

# 12. Real reconstructed chain

工程 replay：

```text
2026-09-29
→ candidate snapshot
→ 2026-09-30
```

必须：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
formal_accepted = false
```

目标只证明 real candidate artifact wiring，不补历史事实。

# 13. Independent oracle

新增独立 validator，不复用 snapshot builder 生成 expected。

至少核：

```text
row count
security identity
previous-session date
counter carry
same-day isolation
anchor/event refs
UNKNOWN reason
snapshot digest
candidate manifest
```

# 14. Idempotency

相同输入：

```text
snapshot bundle digest identical
manifest digest identical
T+1 runtime digest identical
```

同 revision 不同 bytes：

```text
IMMUTABLE_REVISION_CONFLICT
```

# 15. 禁止

```text
V4_12_ACCEPTED_HEAD
Stage/Data Head advance
D2
Radar
Focus
Production
Shadow
V4-13
formal DB migration
```

# 16. 完成状态

只允许：

```text
V4_12_R11A_PERSISTED_FROZEN_D1_CHAIN_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

R11A 本地 PASS 后才进入 R11B。
