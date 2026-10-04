# DM01-R4｜Go-Forward PIT Daily Chain Runtime Independent External Audit R1｜2026-10-05

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`

Execution baseline: `41d40692149055b7518751ff0916dbc0e2ff0d12`  
Audited remote HEAD: `862a59c397f1aff1f58acd372ec9048d7b9c508f`  
Exact tested source: `2b0436022112a8d3b1fe4d3fb50ad2f38d9764d2`  
Tested tag: `codex/dm01-r4-go-forward-runtime-tested-source-20261005`

## 1. Unique External Decision

```text
DM01_R4_EXTERNAL_AUDIT = PARTIAL_PASS_R4R1_REQUIRED

DM01_R4_SCOPE_AND_HARD_BOUNDARY = PASS
DM01_R4_CALENDAR_AUTHORITY_DESIGN = PASS_KEEP
DM01_R4_CURRENT_V2_PARENT_ROLLOVER = PASS_KEEP
DM01_R4_ALL_NINE_DAILY_WIRING = PASS_KEEP
DM01_R4_ROUTINE_V2_PROMOTION_CORE = PASS_KEEP
DM01_R4_FUTURE_SESSION_WAIT_GATE = PASS_KEEP
DM01_R4_TESTED_SOURCE_GOVERNANCE = PASS
DM01_R4_PROTECTED_STATE = PASS
DM01_R4_CLEAN_REGRESSION = PASS_SCOPED_NO_NEW_FAILURES

DM01_R4_LINEAGE_COMPOSITION = FAIL_P0
DM01_R4_REAL_FORWARD_EVIDENCE_GATE = FAIL_P0
DM01_R4_FIRST_AVAILABILITY_SEMANTICS = FAIL_P0
DM01_R4_PROMOTED_HEAD_LINEAGE = FAIL_P0

DM01_R4_GO_FORWARD_RUNTIME = BLOCKED_PENDING_R4R1
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_TARGET_SESSION_PACKAGE = NOT_CREATED
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0

NEXT = DM01_R4R1_PIT_LINEAGE_AND_FORWARD_EVIDENCE_REPAIR
```

R4 不需要推倒重来。原先五个 runtime blocker 已基本修复，剩余问题集中在 PIT/前向证据语义。

## 2. PASS_KEEP

### Calendar

R4 已建立 `DM01_R4_CALENDAR_HEAD_V1`，覆盖到 `2026-12-31`，SSE/SZSE 官方来源均做 exact hash 绑定，2026-10-08 已进入正式候选交易日序列。Calendar 当前保持 `LOCAL_READY_FOR_EXTERNAL_AUDIT`，真实 post-close source activity 仍需外部 R4 envelope。

### Current V2 Parent

R4 已改为读取当前 `V4_DATA_ACCEPTED_HEAD_V2 / 2026-09-30`，V1 current parent 被拒绝；当前 parent 的 chain、receipt、9 components、logical digest 都会 readback。

### All-nine Wiring

原永久 blocker `BLOCKED_COMPONENT_BUILDERS_NOT_WIRED` 已解除。R4 为 9 个 R3_3 kernel 建立明确 wrapper，并继续调用 component/cross-component independent postcheck，没有改写核心公式。

### Promotion Core

已具备：exact candidate、all-nine、component digest/receipt readback、cross postcheck、CAS parent、promotion lock、V2-only output、Stage Head protection、Production/Shadow/Focus=false、R25 auto-grant=false、Shadow counter increment=0。

### Future WAIT

当前对 `2026-10-08` 的真实 readback：

```text
WAIT_MARKET_CLOSE
source_requests = 0
candidate_created = false
data_head_moved = false
```

未伪造未来数据。

## 3. P0｜Lineage Laundering

当前 parent：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
first_available_at_target_proven = false
```

但 R4 `_finish()` 对所有非 simulation 输出行无条件写：

```text
knowledge_lineage = PIT_OBSERVED
AS_RECORDED = true
first_available_at_target_proven = true
```

这没有区分：

- 目标日新事实；
- 继承的 parent 历史事实；
- period aggregate 中的历史父状态；
- 目标日前就已知的 identity；
- “历史重构 + 当日实采”混合派生事实。

因此 target session 被实时观察，不等于整份 artifact 的所有历史内容都变成 PIT/AS_RECORDED。

```text
DM01_R4_LINEAGE_COMPOSITION = FAIL_P0
```

## 4. P0｜Candidate 明示非 real-forward，但 promotion 不检查

`build_candidate()` 当前对所有 candidate 写：

```text
real_forward_evidence = false
```

而 `promote()` 只要求：

```text
knowledge_lineage == PIT_OBSERVED
permissions == false/false/false
```

没有要求：

```text
real_forward_evidence == true
```

所以当前状态机理论上能把“自己声明不是 real forward evidence”的 candidate 提升为：

```text
ACCEPTED_UNDER_DM01_R4_MACHINE_POLICY
```

```text
DM01_R4_REAL_FORWARD_EVIDENCE_GATE = FAIL_P0
```

## 5. P0｜First Availability 被自动发明

`validate_lineage()` 能证明：

- target/provider date；
- same-day captured/received/system timestamps；
- exact native readback；
- accepted source authority。

但 `source_provider_available_at` 是可缺省的，也没有独立“第一次可得时间”证明。

因此 same-day capture 只能证明：

```text
observed/received by this system at T
```

不能自动证明：

```text
first available at T
```

当前 `_finish()` 和 `promote()` 却都直接置：

```text
first_available_at_target_proven = true
```

```text
DM01_R4_FIRST_AVAILABILITY_SEMANTICS = FAIL_P0
```

## 6. P0｜Promoted Head 过度声明为 Whole-Head PIT

`promote()` 当前把整个新 Data Head 写为：

```text
knowledge_lineage = PIT_OBSERVED
AS_RECORDED = true
first_available_at_target_proven = true
```

但 parent 明确是 reconstructed。新的 Data Head 含继承状态和目标日实采状态，不能整体变成纯 PIT。

正确方向应是显式组合，例如：

```text
MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT
```

并另设 target-session PIT receipt/observation fields。

```text
DM01_R4_PROMOTED_HEAD_LINEAGE = FAIL_P0
```

## 7. Identity Completeness｜WAIT_REAL_EVIDENCE

当前 accepted identity head 明确：

```text
whole_market_lifecycle_completeness_claim = false
```

R4 可以继续显式保留 UNKNOWN，但首个真实 post-holiday session 必须验证：

- target roster coverage；
- 新上市/退市/代码变化；
- unknown identity counts；
- no silent drop。

这属于真实样本 gate，不阻塞本次 R4R1 设计修复。

## 8. Regression / Tested Source

Tested tag 精确解析到：

`2b0436022112a8d3b1fe4d3fb50ad2f38d9764d2`

当前 HEAD 只多 1 个 evidence closure commit。

R4-specific：

```text
25 passed
0 failed
```

Scoped regression：

```text
1977 passed
26 inherited failures
3 skipped
0 introduced failures
```

## 9. R4R1 Scope

只修：

```text
1. provenance composition
2. real_forward_evidence admission
3. first-availability semantics
4. promoted Data Head lineage semantics
5. R25 uses exact target-session PIT binding
```

不得重开 calendar、V2 parent、all-nine wiring、CAS promotion core。

## 10. Required Local Exit After R4R1

```text
DM01_R4R1_LOCAL_REPAIR = PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
DM01_R4_LINEAGE_COMPOSITION = PASS_LOCAL_REPAIRED
DM01_R4_REAL_FORWARD_EVIDENCE_GATE = PASS_LOCAL_REPAIRED
DM01_R4_FIRST_AVAILABILITY_SEMANTICS = PASS_LOCAL_REPAIRED
DM01_R4_PROMOTED_HEAD_LINEAGE = PASS_LOCAL_REPAIRED

REAL_TARGET_SESSION_PACKAGE = NOT_CREATED
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0

NEXT = STOP_WAIT_DM01_R4R1_INDEPENDENT_EXTERNAL_AUDIT
```
