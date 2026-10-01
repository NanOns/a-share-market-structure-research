# A05 Legacy Valid Member Exact Producer 任务卡 R2｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**Audit：** `LEGACY_VALID_MEMBER_EXACT_PRODUCER`  
**优先级：** P1 Parallel

## 1. 目标

先做 archaeology，回答旧 B2 / valid_member 到底是什么。

只允许两个结局：

```text
A. 恢复 EXACT legacy producer
B. 明确证明无法恢复，发布 NON_EQUIVALENT replacement + retirement/migration
```

禁止假装近似公式就是旧语义。

## 2. 全仓 archaeology

检索：

```text
missing_state
valid_member
validity
B2
legacy member filter
historical outputs
old SQL/config/code
```

## 3. Exact recovery

若找到：

```text
source path
function/symbol
source SHA
parameters
units
UNKNOWN semantics
time role
```

提取 exact AST / golden examples。

## 4. Golden examples

至少：

```text
valid
invalid
missing
suspended
new listing
boundary
```

有真实旧输出时必须比对 exact。

## 5. 无法恢复时

必须产生：

```text
LEGACY_VALID_MEMBER_EXACT_PRODUCER = UNRECOVERABLE
```

并设计：

```text
B2 retirement
replacement contract
consumer migration
historical comparability warning
```

Replacement 禁止标 `LEGACY_EQUIVALENT`。

## 6. V4-08

V4-08 既有 accepted business head 不动。

只做 consumer graph：

```text
哪些当前模块仍依赖 legacy B2
哪些已经不依赖
```

## 7. Migration

如果需要 DB/schema migration：

```text
先走统一 allocator
```

## 8. 验收

结束只能：

```text
A05_EXACT_PRODUCER_RECOVERED_CANDIDATE
```

或：

```text
A05_NON_EQUIVALENT_REPLACEMENT_CANDIDATE
```

然后 STOP 等外部审计。
