# A04｜Amount-A Go-Forward Producer Scoped Acceptance Formalization 任务卡｜2026-10-02

**优先级：** P1 Parallel  
**外部裁决：** `PASS_ENGINEERING_GO_FORWARD_SCOPE`

## 1. 目标

正式接受 A04 的 go-forward producer engineering capability，而不是接受 Amount-A 业务值。

## 2. 当前事实

```text
sector rows = 378
known Amount-A = 0
warmup UNKNOWN = 378
accepted sessions = 1
missing H21 = 20
historical formal capability = BLOCKED
```

这是合法 warmup，不是工程失败。

## 3. 允许创建

独立 scoped head：

```text
A04_AMOUNT_A_GO_FORWARD_PRODUCER_ACCEPTED_HEAD_R1
```

内容必须声明：

```text
producer accepted = true
formal consumer enabled = false
historical reconstruction accepted = false
H21 warmup required = true
```

## 4. Forward Accumulation

每个新 accepted trading session：

```text
accepted membership
+
accepted amount source
→ observation
→ append-only
```

不得回填不存在的 historical first-availability。

## 5. Consumer Gate

达到 H21 前：

```text
Amount-A formal value = UNKNOWN
```

达到 H21 后也不得自动启用 consumer。

必须另做：

```text
H21 completeness
source consistency
arithmetic oracle
consumer-specific external acceptance
```

## 6. Independence

继续保证：

```text
stock AMR20 independent of A04
```

A04 OPEN/CLOSED、payload变化不得改变相同 stock facts 的 V4-11 输出。

## 7. 完成状态

```text
A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTED
ACCUMULATION_CONTINUES
```
