# V4-11 R2｜AMR20 / Amount-A 语义串线定点修复任务卡｜2026-10-01

**基线 HEAD：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`  
**优先级：** P0 Mainline Blocker

## 1. Blocker

当前 runtime 将：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
TREND_CONTINUE
```

无条件追加：

```text
AUD-AMOUNT-A-06:FORMAL_BRANCH_DISABLED
```

这是错误绑定。

## 2. 正确字段边界

旧 V3.3：

```text
amr20_mean_prior
```

是个股 prior-window amount ratio fact，对应 stock `amount_ratio20 / AMOUNT_VOLUME_STATE_V1`。

它不是：

```text
sector amount_a_value / AUD-AMOUNT-A-06
```

必须新增 versioned erratum，机器可读地冻结两个字段族不可互换。

## 3. 删除错误 gate

删除 V4-11 对 `AUD-AMOUNT-A-06` 的 stock scenario gate。

禁止仅改 reason 字符串而保留等价错误 gate。

## 4. AMR20 producer binding

找到并绑定 `amr20_mean_prior` 的真实 producer/source lineage，至少记录：

```text
source field
formula
window
unit
target/prior time role
input source digest
accepted/unaccepted status
```

若 target-date accepted AMR20 unavailable：

```text
predicate = UNKNOWN
```

reason 必须指向真实 AMR20 source capability，不能再指向 A04。

## 5. Legacy thresholds 保持 exact

```text
LAUNCH >= 1.20
RECOVERY >= 1.05
TREND 0.80 <= x <= 2.50
```

不得调参。

## 6. Golden vector erratum

废止把 `AMOUNT_A_DISABLED` 作为 V4-11 stock confirmation 的 golden expectation。

新增：

```text
AMR20_KNOWN_TRUE
AMR20_KNOWN_FALSE
AMR20_UNKNOWN
SECTOR_AMOUNT_A_STATUS_IRRELEVANT_TO_STOCK_CONFIRMATION
```

最后一条必须证明：

```text
A04 OPEN/CLOSED 或 Amount-A payload 改变
不得改变同一组 stock facts 的 V4-11 output
```

## 7. Full-market replay

重新跑 2026-09-30 全市场，报告：

```text
UNKNOWN total
UNKNOWN reason counts
scenario TRUE/FALSE/UNKNOWN counts
```

允许继续因 common-safety accepted facts、episode facts、TREND same-day LOO dependency 等保持 UNKNOWN。

但：

```text
AUD-AMOUNT-A-06 unknown count = 0
```

## 8. Common safety

不得为了让数量好看把未接受 facts 当 TRUE/FALSE。accepted source 不存在就继续 fail closed，并明确 capability limitation。

## 9. TREND same-day LOO

保持 `DIAGNOSTIC_ONLY`，除非能够从 cutoff 内、非 same-day downstream 的纯函数来源重构 exact legacy fact。

## 10. 保持已通过边界

必须保持：

```text
D0 不写 Final State
real D2 未接受前拒绝
prior-session event predecessor
same-day NEW semantics
append-only persistence
migration 026 byte-immutable
```

## 11. Tests

至少：

```text
stock AMR20 vs sector Amount-A namespace separation
A04 state mutation invariance
AMR20 threshold boundaries 1.20/1.05/0.80/2.50
AMR20 missing UNKNOWN
full-market no AUD-AMOUNT-A reason
```

## 12. Heads

不得：

```text
创建正式 V4_11_ACCEPTED_HEAD
推进 Stage Head
执行 V4-12
```

## 13. 完成状态

只允许：

```text
V4_11_R2_SEMANTIC_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```
