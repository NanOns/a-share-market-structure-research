# A03/A06/A07/Owner Registry/Reader DI 外部接受正式化任务卡 R1｜2026-10-01

**基线 HEAD：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`

## 1. A03

正式记录：

```text
PASS_FORWARD_PIT_BUILDER_SCOPE
FORWARD_ACCUMULATION_CONTINUES
```

允许每日 immutable append、late/revision/gap/schema detectors。

禁止 retroactive AS_RECORDED fabrication 和 production permission。

未来 observations 自然积累，不再把“还没有未来交易日”当工程 OPEN blocker。

## 2. A06

正式关闭为：

```text
PASS_FAIL_CLOSED_NO_TOLERANCE_AUTHORIZED
```

保持：

```text
strict_binding_allowed=false
all undocumented numeric tolerance=null
BaoStock supplemental only
TDX core never blocked by supplemental mismatch
```

不要继续寻找经验百分比容差。

## 3. A07

正式接受：

```text
PASS_LINEAGE_CAPTURE_SCOPE_WITH_PERMANENT_PRECAPTURE_BLOCK
```

明确：

```text
pre-capture AS_RECORDED permanently blocked
go-forward real capture 可从真实 capture time 开始建立 lineage
formal adjusted-price consumer permissions separate
```

## 4. Owner Registry

将 R4 candidate 正式化为：

```text
SCOPED_ACCEPTED_OWNER_BOOTSTRAP_R1
```

但保持：

```text
active_global_trust_root=false
global_mandatory_adoption=false
formal global consumer cutover=false
```

逐字段 limitation 不得删除。

不得替换当前 active Registry R3。

## 5. Historical Reader DI

正式接受：

```text
PASS_HISTORY_ONLY_DI_HARDENING
```

将 v2 设为 accepted history-only reader。

v1 保留历史，不删除。

明确：

```text
business_reacceptance=false
production_authorization=false
```

## 6. Registry

新增下一版 registry/current-state formalization，不能覆盖 R10/R11 candidate。

current 状态要区分：

```text
ACCEPTED_SCOPED
ACCUMULATION_CONTINUES
PERMANENT_CAPABILITY_BLOCK
INACTIVE_ACCEPTED_METADATA
```

## 7. Heads

不得移动：

```text
V4_DATA_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4-06/V4-09/V4-10 heads
```

## 8. Clean validation

逐项验证：

```text
A03 immutable append/readback
A06 no-tolerance fail-closed
A07 lineage boundary
Owner R4 exact field scopes and inactive root
Reader DI concurrent parity / wrong hash / path traversal
```

## 9. 完成

```text
A03_SCOPED_ACCEPTANCE_FORMALIZED
A06_FAIL_CLOSED_ACCEPTANCE_FORMALIZED
A07_LINEAGE_ACCEPTANCE_FORMALIZED
OWNER_BOOTSTRAP_SCOPED_ACCEPTANCE_FORMALIZED
HISTORICAL_READER_DI_ACCEPTANCE_FORMALIZED
```

仍不得声明 production/shadow/global mandatory ready。
