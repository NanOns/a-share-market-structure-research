# V4-11 R4A｜Adjustment Basis Identity Rebinding + V4-03 Parity Repair｜2026-10-02

**优先级：** P0 Mainline  
**审计基线 HEAD：** `65774de20108beafaa15c0b557b4cd2ee58edb29`  
**父阶段：** V4-10 Accepted  
**Stage/Data Head：** KEEP

# 1. 目标

修复 R3A/R3C 对 adjusted-price identity 的错误解释。

不得修改：

```text
V4-03 accepted contracts
V4-03 thresholds
V4-11 legacy thresholds
scenario priority
A02/A05/A04 accepted scoped results
```

# 2. 唯一正式 adjustment identity

必须与已接受 V4-03 完全一致：

```text
adjustment_basis_id
=
price_basis + adjustment_source_revision
```

语义来源：

```text
scripts/run_v4_03_full_scope_candidate.py
src/v4/factors/core.py
V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3
```

禁止继续使用：

```text
qfq_mul/qfq_add literal equality
digest(qfq_mul,qfq_add)
TARGET_AFFINE_IDENTITY_MUST_MATCH_EVERY_PRICE_SLOT
```

作为正式 adjustment identity。

# 3. qfq 系数定位

`qfq_mul/qfq_add` 只允许作为：

```text
affine calculation evidence
reproducibility evidence
diagnostic metadata
```

不得替代：

```text
price_basis
adjustment_source_revision
```

# 4. R3A source adapter

历史 parent parquet 与 DM-01 incremental `ADJUSTED_DAILY` 都必须读取并保留：

```text
price_basis
adjustment_source_revision
qfq_mul
qfq_add
adjusted quality
```

窗口 admission：

```text
accepted adjustment basis compatible
→ evaluable

different / unknown accepted basis
→ MIXED_ADJUSTMENT_IDENTITY / UNKNOWN
```

不得因 affine 系数发生合法变化自动判 UNKNOWN。

# 5. 9/24 Exact Parity Gate｜P0

必须新增独立 parity replay。

用 R4 adapter 在：

```text
target = 2026-09-24
```

重放已接受 V4-03 Stock Core。

对于可直接对应的 fields，逐：

```text
security_id
field
value
quality_state
unknown_reason
window identity inputs
adjustment basis identity
```

与已接受 V4-03 artifact 比较。

要求：

```text
row scope = 5222
business mismatches = 0
quality mismatches = 0
unknown-reason mismatches = 0
numeric tolerance <= 1e-12
```

若由于 V4-11 projection 名称不同，必须提供明确 field mapping；不得跳过核心价格窗口。

# 6. Corporate Action Boundary Proof

至少建立真实或冻结可复核样本：

```text
qfq_mul/qfq_add 在窗口内发生变化
但 price_basis + adjustment_source_revision 保持同一 accepted basis
```

证明：

```text
合法 comparable adjusted window
不能仅因 coefficient change 变 UNKNOWN
```

另做反例：

```text
price_basis / adjustment_source_revision 真变化
→ MIXED_ADJUSTMENT_IDENTITY
```

# 7. UNKNOWN Diff

重新统计 R4A 前后：

```text
MISSING_OR_MIXED_COORDINATE_MASTER_SESSION
MIXED_ADJUSTMENT_IDENTITY
ADJUSTMENT_UNKNOWN
CURRENT_BAR_SUSPENDED
UNEXPLAINED_DATA_GAP
```

必须解释每一类变化。

禁止以“UNKNOWN 变少”为验收标准；标准是 contract correctness。

# 8. Independent Oracle

独立 verifier 不得调用被测 adapter 的 basis admission helper。

至少验证：

```text
same accepted basis + different qfq coefficients = evaluable
different accepted basis = UNKNOWN
missing source revision = UNKNOWN
unsupported adjustment = UNKNOWN
confirmed suspension crossing follows accepted V4-03 rule
unexplained gap = UNKNOWN
```

# 9. Clean regression

至少覆盖：

```text
V4-03 parity
V4-09
V4-10
V4-11 R3/R4
DM01 Data Head
A02/A05/A04 scoped heads
no-symbol
```

# 10. 禁止

```text
创建 V4_11_ACCEPTED_HEAD
推进 Stage Head
修改 Data Head
执行 V4-12
开启 Production/Shadow/Focus
```

# 11. 完成状态

仅允许：

```text
V4_11_R4A_ADJUSTMENT_BASIS_REPAIR_CANDIDATE_READY
```
