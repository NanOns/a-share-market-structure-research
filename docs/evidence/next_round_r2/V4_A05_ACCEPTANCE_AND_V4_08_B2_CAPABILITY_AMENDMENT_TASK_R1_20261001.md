# A05 外部接受正式化 + V4-08 B2 Capability Amendment 任务卡 R1｜2026-10-01

**基线 HEAD：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`  
**外部结论：** `PASS_EXACT_CURRENT_SNAPSHOT_PRODUCER_SCOPE`

## 1. A05 formalization

正式接受：

```text
LEGACY_VALID_MEMBER_EXACT_PRODUCER_V1
CURRENT_SNAPSHOT_ONLY
```

绑定 exact：

```text
src/sector/phase2.py
sector.phase2.prepare
exact AST digest
real observations = 6188
real mismatch = 0
```

## 2. 禁止扩大

不得声明：

```text
historical PIT equivalent
AS_RECORDED historical membership
```

当前 snapshot exact producer 只证明当前快照语义。

## 3. V4-08 B2 replay

使用 formalized A05 producer，按原 V4-08 B2 algorithm/parameter 不变重放 current-snapshot scope。

## 4. Diff

与现有 V4-08 accepted artifact 比较：

```text
B2 rows
sector qualification effects
rotation/context downstream effects
UNKNOWN/NOT_IMPLEMENTED reductions
```

输出完整 business diff。

## 5. Amendment candidate

若 current-snapshot capability 可恢复，生成：

```text
V4_08_ACCEPTED_HEAD_B2_CAPABILITY_AMENDMENT_CANDIDATE
```

必须明确：

```text
CURRENT_SNAPSHOT_ONLY
historical replay remains limited
```

## 6. 不 promotion

不得覆盖 V4-08 Accepted Head，不得推进 Stage Head，等待下一轮独立验收。

## 7. 完成

```text
A05_EXTERNAL_ACCEPTANCE_FORMALIZED = PASS
V4_08_B2_AMENDMENT_READY_FOR_EXTERNAL_REAUDIT
```
