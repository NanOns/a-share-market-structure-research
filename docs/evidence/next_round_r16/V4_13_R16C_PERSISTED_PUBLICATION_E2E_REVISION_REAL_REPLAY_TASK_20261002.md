# R16C｜V4-13 Persisted Publication + E2E / Revision / Real Capability Replay｜2026-10-02

**前置**：

```text
R16A PASS
R16B PASS
```

**任务性质**：Runtime Closure / External Audit Candidate

# 1. 唯一目标

把 V4-13 从单元 Runtime 收口成：

```text
accepted input binding
→ LOO Context
→ Advanced Profile
→ append-only persisted publication
→ fresh-process readback
→ revision isolation
→ real capability-scoped run
```

形成可独立外审 candidate。

# 2. Persisted Candidate Bundle

新增 versioned candidate publication bundle。

建议每个 trade_date / revision：

```text
manifest.json
profile_advanced.jsonl(.gz)
loo_context.jsonl(.gz)
source_refs.json
diagnostics.json
publication_index.json
```

具体命名可按项目现有 runtime bundle 规范。

必须记录：

```text
contract refs + digests
input accepted-head refs
membership snapshot identity
LOO history digest
Structure source digest
prior_session_ref
revision
available_at
knowledge_lineage
AS_RECORDED
formal_accepted
```

# 3. Append-only

同 security/date：

```text
r1
r2
r3
```

必须：

```text
append
not overwrite
```

membership correction：

```text
new revision
old observation immutable
```

# 4. Same-day Revision Predecessor

同一交易日：

```text
r1 / r2 / r3
```

需要历史/previous-session lineage 的字段必须都读取：

```text
exact previous accepted market session
```

禁止：

```text
r1 -> r2 -> r3
```

作为 prior-session chain。

# 5. Fresh-process

必须证明：

```text
process A:
run 2026-09-30 r1
write bundle
exit

process B:
read exact persisted refs
run same inputs / r2 correction
```

不依赖 Python in-memory cache。

# 6. Real Accepted-source Run

正式 real case 首选：

```text
2026-09-30
```

因为当前正式 PIT Membership Accepted Head 明确绑定该 trade date。

必须覆盖全可处理股票 universe；如 universe scope由 Accepted Head限定，严格按 accepted scope。

# 7. Real Capability Degradation

这是本轮关键真实验收点。

在 2026-09-30：

如果 current exact membership available，但 LOO historical lineage 或 V4-12 target-date accepted publication不足：

必须出现：

```text
primary_industry/supporting_concepts =
KNOWN or NOT_APPLICABLE where current membership supports it

algorithmic_support_sector =
UNKNOWN if history unavailable

Structure projection =
UNKNOWN if exact V4-12 accepted publication unavailable

sector_context_state =
component-scoped degradation
```

禁止整个 profile 因一个 history capability 缺失全部 UNKNOWN。

# 8. Historical Date 禁止倒灌

如测试 2026-09-29 或更早日期：

当前 2026-09-30 PIT Membership 不得直接作为 formal PIT membership。

只能：

```text
diagnostic current-membership replay
→ DEGRADED
→ formal_context_eligible = false
```

或：

```text
UNKNOWN
```

# 9. Authority Counters

Final handoff 必须统计：

```text
raw_fallback_count
provider_direct_read_count
raw_reconstruction_count
current_membership_silent_fallback_count
self_including_context_reuse_count
unauthorized_v4_12_candidate_use_count
context_to_raw_qualification_mutation_count
```

全部必须：

```text
0
```

# 10. Perturbation E2E

至少：

```text
P01 perturb sector membership/context
→ A raw unchanged
→ C raw unchanged

P02 perturb D1 Structure
→ B0/B1/B2 unchanged

P03 reorder input sector rows
→ deterministic output digest unchanged

P04 reorder concepts
→ supporting_concepts stable ordering

P05 change display cap
→ algorithmic support set unchanged

P06 same-day membership correction
→ new revision only
```

# 11. Independent Runtime Oracle

必须有一套不调用 V4-13 Runtime helper 的 oracle。

至少覆盖：

```text
membership relation
LOO member exclusion
coverage/min-member
sector selector sort
relative-sector substitution
component quality fold
Structure copy-only
dual-source enrichment
revision predecessor
append-only identity
```

# 12. Regression

必须继续通过：

```text
R15 14 contract vectors
R15 15 business negative gates
R15R1 lineage tests

V4-12 Accepted Head protected exact
Stage/Data Head protected exact

V4-08 context-routing authority
V4-09 Stock PREWATCH raw
V4-10/11/12 DAG boundaries
```

# 13. Clean Detached Validation

tested source 必须 clean detached。

记录：

```text
git clean before/after
source SHA
test count
candidate bundle digests
protected head bytes
runtime source files
no migration
```

Final HEAD 相对 tested source 只允许：

```text
seal / handoff / test evidence
```

# 14. Tests

必须包含：

```text
unit
contract parity
synthetic
fresh-process
same-day revision
real accepted-source
perturbation
independent oracle
negative authority
```

不得只跑新测试；保留相关前序 regression。

# 15. Heads / Permissions

全轮保持：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_12_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

不得创建：

```text
V4_13_ACCEPTED_HEAD
```

权限：

```text
production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 16. 完成状态

唯一允许：

```text
V4_13_R16_RUNTIME_CANDIDATE =
READY_FOR_EXTERNAL_AUDIT

V4_13_RUNTIME =
IMPLEMENTED_SCOPED_ENGINEERING_CANDIDATE

V4_13_ACCEPTED_HEAD =
NOT_CREATED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

统一 commit + push 后立即 STOP。
