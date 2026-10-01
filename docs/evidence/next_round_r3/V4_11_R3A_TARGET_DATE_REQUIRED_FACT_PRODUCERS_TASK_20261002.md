# V4-11 R3A｜Target-Date Required Fact Producers 任务卡｜2026-10-02

**优先级：** P0 Mainline  
**基线 implementation：** `d119c0526e44a819f85b4917159d3eeb5daadf2a`  
**执行前：** 必须解析远端 `codex/v4-system-reform` 当前 HEAD，并证明其为上述 implementation 的 descendant。  
**Stage Head：** KEEP `V4_00_TO_V4_10_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

## 1. 目标

把 V4-11 当前因“没有正式 producer”而全量 UNKNOWN 的 target-date required facts，按 exact legacy semantics 建立正式 candidate producer publication。

重点不是改 confirmation detector，而是补齐其输入。

## 2. 必须建立 Capability Matrix

对 `config/v4_11_legacy_extraction_manifest_r2.json` 全部 required fields 逐字段登记：

```text
field
legacy source symbol
formula/AST
unit
time_role
target/prior window
accepted upstream source
producer contract
parameter set
publication namespace
knowledge lineage
AS_RECORDED
current capability
```

状态只能是：

```text
FORMAL_CANDIDATE_PRODUCER
EXISTING_ACCEPTED_PRODUCER
DIAGNOSTIC_ONLY
BLOCKED_EXPLICIT_REASON
```

禁止用一个总的 `COMMON_FACTS_MISSING` 混写。

## 3. AMR20

必须从 accepted RAW_DAILY / accepted calendar 构造：

```text
amr20_mean_prior
```

严格：

```text
prior 20 master sessions
target excluded
raw amount unit = CNY
output = fraction
```

复用 exact V3.3 factor source，不得重写另一套公式。

必须生成 2026-09-30 全市场 target publication candidate。

## 4. 纯价格/流动性/风险 facts

至少闭环：

```text
window_valid
normal_universe
liquidity20
first_day_damage
severe_drop
structure_break
extended
breakout_v3
close_above_phc20
clv
ret1
r5
r20
rps5_delta3
ma5
ma20
slope20
prior_high
trend_background
```

只允许读取当前 cutoff 前 accepted upstream。

## 5. Source Authority

不得把：

```text
当前本地缺文件
```

写成：

```text
provider unavailable
```

必须区分：

```text
LOCAL_ARTIFACT_MISSING
PROVIDER_NOT_QUERIED
PROVIDER_QUERY_FAILED
PROVIDER_TARGET_EMPTY
FORMAL_PRODUCER_NOT_ACCEPTED
```

## 6. UNKNOWN

producer 本身不得用：

```text
missing -> 0
missing -> FALSE
```

必须保留 UNKNOWN + reason。

## 7. 真实 9/30 输出

至少报告：

```text
5224 universe coverage
known/unknown per field
unknown reasons
source digest
publication digest
sample arithmetic oracle
```

## 8. Independent Oracle

每个数值 family 至少：

```text
positive
negative
boundary
missing
```

独立从 accepted source row 重算，不调用被测 producer。

## 9. 禁止

```text
修改 legacy thresholds
修改 V4-11 scenario priority
读取 Final State / Focus
same-day downstream feedback
online supplement 写入正式值
创建 V4_11_ACCEPTED_HEAD
进入 V4-12
```

## 10. Tests

至少：

```text
prior-window target exclusion
AMR20 20-session exact arithmetic
liquidity prior-window exactness
CLV boundary
MA/slope boundary
RPS prior publication exact binding
missing session UNKNOWN
wrong source digest reject
future timestamp reject
same-day feedback reject
no-symbol
```

## 11. 完成状态

只允许：

```text
V4_11_R3A_TARGET_FACT_PRODUCERS_CANDIDATE_READY
```
