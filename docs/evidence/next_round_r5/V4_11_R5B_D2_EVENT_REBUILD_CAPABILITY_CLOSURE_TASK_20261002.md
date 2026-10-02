# V4-11 R5B｜D2 + Event Rebuild + Final Capability Closure｜2026-10-02

**优先级：** P0 Mainline  
**前置：** R5A exact owner parity PASS + sealed  
**Stage/Data Head：** KEEP

---

# 1. 目标

只使用 R5A sealed owner publications，重新生成：

```text
2026-09-29 D2 prior candidate
2026-09-30 D2 current candidate
Frozen Prior State
STATE_EVENT_V1
Residual UNKNOWN attribution
R4 -> R5 business diff
V4-11 external re-audit handoff
```

---

# 2. D0 保持冻结

```text
LAUNCH_CONFIRM   = FORMAL_CANDIDATE
RECOVERY_TURN    = FORMAL_CANDIDATE
STRONG_PULLBACK  = DIAGNOSTIC_ONLY
TREND_CONTINUE   = DIAGNOSTIC_ONLY
```

允许修 source refs/lineage，不得改 detector formula、threshold、priority。

---

# 3. D2 exact owner source set

D2 source set 必须绑定：

```text
R4A sealed D0 confirmation publications
R5A sealed BASE_SEED/PREWATCH target publications
accepted dated status
accepted RPS history
V4-10 reducer/provenance source
R3B diagnostic capability seal
calendar identity
```

禁止从 calculation payload/raw window/unsealed helper 直接跨过 R5A owner publications 进入 D2。

---

# 4. V4-10 reducer 保持 exact

继续要求：

```text
normalized business AST exact
rule order exact
threshold exact
parameter set exact
```

仅允许 candidate admission/namespace/sealed-source wiring 差异。

---

# 5. R4 → R5 Business Diff

必须报告：

```text
SEED
PREWATCH
D2 maturity
D2 final eligibility
FRESH/STALE
Event
```

量化：

```text
多少 row 因 t-1 从 reconstructed-known 恢复 accepted-UNKNOWN
多少 Seed 改变
多少 PREWATCH 改变
多少 D2 改变
多少 Event 改变
```

不得以 UNKNOWN 更少/结果更好看为验收标准。

---

# 6. Residual UNKNOWN / STALE

每个 STALE 必须追溯到：

```text
required input UNKNOWN
+
exact producer publication
+
source root cause
```

允许原因包括：

```text
accepted adjustment unsupported
confirmed suspension
unexplained data gap
insufficient history
accepted RPS unavailable
accepted t-1 owner field unavailable
prior episode unavailable
same-day LOO not formally admitted
V4-12 invalidation not authorized
other explicit accepted capability limitation
```

禁止：

```text
producer wiring missing
unsealed helper source
generic coefficient gate
raw reconstruction fallback
```

---

# 7. Event safety

继续验证：

```text
UNKNOWN prior != FALSE
STALE prior != FALSE
UNKNOWN current D2 cannot emit deterministic NEW_CONFIRMED
same-day revision cannot create fake predecessor
NEW_CONFIRMED uses exact valid prior-session state
```

2026-09-29 prior 继续标记：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
event evidence = RECONSTRUCTED_LEFT_CENSORED
```

---

# 8. 修复 scenario lineage metadata

当前残留：

```text
reason = R3A_SEALED_TARGET_FACT_SET
```

必须改为真实父 lineage。

不要只改字符串；记录：

```text
parent_producer_set:
  path
  sha256
  contract_id
  status
```

指向 R4A sealed producer set，并保留 R3B diagnostic capability seal。

---

# 9. Independent D2 owner-input oracle

新增独立 oracle，除证明 reducer AST exact 外，还必须证明 D2 实际收到的：

```text
SEED
PREWATCH
core_price_damage
risk
delta3
suspended
CONFIRMED
scenario
```

全部来自 sealed authoritative publication。

至少验证：

```text
entity_id
trade_date
producer_contract_id
publication_id
source_output_digest
quality
value
```

不得由 serialized input payload 自报 authority。

---

# 10. Clean regression

至少覆盖：

```text
V4-03 accepted parity
R4A
R5A owner parity
V4-09
V4-10
V4-11
DM01 Data Head integrity
A02/A05/A04 scoped heads
no-symbol
```

M14/M2 若仍与基线完全相同，单列：

```text
PREEXISTING_NON_MAINLINE
```

不要求本轮修复，也不得声称 full repository runtime PASS。

---

# 11. V4-11 acceptance candidate

最终只可生成：

```text
V4_11_R5_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

能力必须声明：

```text
D0 LAUNCH/RECOVERY = FORMAL_CANDIDATE
Pullback/Trend = DIAGNOSTIC_ONLY
D2 bridge = ENGINEERING_CANDIDATE
Event engine = ENGINEERING_CANDIDATE
Event evidence = RECONSTRUCTED_LEFT_CENSORED
Production/Shadow/Focus = false
```

---

# 12. 禁止

```text
创建正式 V4_11_ACCEPTED_HEAD
推进 V4_STAGE_ACCEPTED_HEAD
修改 V4_DATA_ACCEPTED_HEAD
执行 V4-12 runtime
开放 Production/Shadow/Focus
重开 R4A
修改 accepted V4-07 business rules
```

---

# 13. 完成状态

```text
V4_11_R5_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

完成后统一 commit + push，STOP，等待独立外部验收。
