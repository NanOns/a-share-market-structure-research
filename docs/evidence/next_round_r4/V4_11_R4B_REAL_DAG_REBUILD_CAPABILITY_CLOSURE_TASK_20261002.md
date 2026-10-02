# V4-11 R4B｜Real D0→D2→Event Rebuild + Capability Closure｜2026-10-02

**优先级：** P0 Mainline  
**前置：** R4A parity PASS 并 sealed  
**Stage/Data Head：** KEEP

# 1. 目标

基于修复后的 accepted adjustment-basis semantics，重新生成：

```text
2026-09-29 target facts / prior candidate
2026-09-30 target facts
D0 Confirmation
V4-10 D2 State
STATE_EVENT_V1
```

形成新的 V4-11 external re-audit handoff。

# 2. R3B 保留

不得重开已通过的 capability boundary：

```text
LAUNCH_CONFIRM   FORMAL_CANDIDATE
RECOVERY_TURN    FORMAL_CANDIDATE
STRONG_PULLBACK  DIAGNOSTIC_ONLY
TREND_CONTINUE   DIAGNOSTIC_ONLY
```

除非本任务获得新的、正式 accepted upstream authority。

禁止为了凑四场景而改变 scope。

# 3. Full-market replay

重新报告：

```text
eligible universe
TRUE/FALSE/UNKNOWN per scenario
overall D0
multi-scenario
D2 maturity
D2 final eligibility
FRESH/STALE
Event counts
Event quality
```

并提供 R3 → R4 business diff。

# 4. Residual UNKNOWN Attribution

R4 后所有 UNKNOWN 必须归入真实原因：

```text
accepted adjustment unsupported
confirmed suspension
unexplained data gap
insufficient history
accepted RPS unavailable
diagnostic-only scenario
prior episode unavailable
same-day LOO not formally admitted
other explicit accepted capability limitation
```

禁止继续出现：

```text
TARGET_AFFINE_IDENTITY_MUST_MATCH_EVERY_PRICE_SLOT
MISSING_OR_MIXED_COORDINATE_MASTER_SESSION
```

作为由错误 qfq coefficient gate 导致的 generic reason。

# 5. D2 Freshness

对当前 R3 的：

```text
FRESH 1365
STALE 3859
```

重新计算。

要求证明每个 STALE 都能追溯到：

```text
明确 required input UNKNOWN
```

而不是 producer 接线缺失。

# 6. Event prior capability

2026-09-29 prior 若仍为本轮 reconstructed candidate，必须明确：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
event evidence = RECONSTRUCTED_LEFT_CENSORED
```

不得声称这是当时真实已冻结的 forward publication。

这属于 forward-evidence limitation，不阻塞 event engine engineering acceptance。

# 7. Event safety

继续验证：

```text
UNKNOWN/stale prior 不得被当 FALSE
UNKNOWN current D2 不得产确定性 event
same-day revision 不得变 PERSISTENT
NEW_CONFIRMED 必须基于有效 prior-session state
```

# 8. V4-11 Acceptance Candidate

本任务可以生成：

```text
V4_11_ACCEPTANCE_CANDIDATE
```

但不得生成正式：

```text
V4_11_ACCEPTED_HEAD
```

candidate 必须精确声明 capability：

```text
Confirmation LAUNCH/RECOVERY = candidate formal
Pullback/Trend = diagnostic-only
D2 bridge = engineering candidate
Event engine = engineering candidate
9/30 event evidence = reconstructed-left-censored
Production/Shadow/Focus = false
```

# 9. Clean checkout

必须全仓 clean validation，并绑定实际 tested commit。

# 10. 禁止

```text
推进 V4_STAGE_ACCEPTED_HEAD
执行 V4-12 runtime
修改 V4_DATA_ACCEPTED_HEAD
重新 promotion A02/A05/A04
开放 Production/Shadow/Focus
```

# 11. 完成状态

```text
V4_11_R4_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```
