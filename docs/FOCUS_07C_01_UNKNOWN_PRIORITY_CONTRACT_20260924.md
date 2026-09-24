# 07C-01：UNKNOWN 优先级裁决

## 阶段合同

依据 `FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 24～25 节，07C 属于算法合同变更。07C-01 先冻结裁决原则：高优先级谓词为 `UNKNOWN` 时，不得把低优先级 `TRUE` 宣称为最终主状态；同时不能抹掉已经确认的低优先级事实。现有 `FOCUS_PATH_STATE_V1` 保持原语义，后续以 `FOCUS_PATH_STATE_V2` 表达两层结果。

## 证据与裁决

`src/focus_tracker/states.py` 的 `_select` 按优先级扫描，遇到首个 `UNKNOWN` 即返回 `DATA_UNAVAILABLE`；`PathDecision` 目前只有一个 `current_path_state`。因此在 `STRUCTURE_DAMAGED=UNKNOWN`、`TREND_ACCELERATING=TRUE` 时，直接跳过 UNKNOWN 会错误声称最终状态是 `TREND_ACCELERATING`，维持 V1 则会隐藏已确认的加速事实。

V2 采用下列裁决，不把 `UNKNOWN` 当作 `FALSE`：

| 高优先级状态 | 低优先级状态 | 最终主状态 | 已确认候选 | 解析状态 |
| --- | --- | --- | --- | --- |
| `TRUE` | 任意 | 该高优先级状态 | 可保留其他 TRUE | `READY` |
| `FALSE` | `TRUE`，中间均为 `FALSE` | 该低优先级状态 | 该低优先级状态 | `READY` |
| `UNKNOWN` | `TRUE` | 空 | 该低优先级状态 | `PARTIAL` |
| `UNKNOWN` | 无 `TRUE` | 空 | 空 | `UNAVAILABLE` |

多个 `UNKNOWN`、多个 `TRUE` 时，保留全部已确认状态及位于最佳候选之前的未决高优先级状态；若最高优先级 `TRUE` 已确认，较低优先级的 UNKNOWN 不影响最终主状态。`NOT_APPLICABLE` 不参加优先级竞争。数据前提本身不可用时，最终主状态为空，路径解析为 `UNAVAILABLE`，不凭其他来源填补。

`PARTIAL` 与 `AMBIGUOUS` 的精确定义、旧读者兼容方式和存储字段在 07C-02/03 落地前单独核对，不能在此阶段悄悄改变已接受的 V1 observation/head。

## 验收结果与下一阶段

`07C-01 / CONTRACT_DECISION_ACCEPTED`：完成算法边界和冲突样例裁决；没有改变生产分类、数据库或已接受数据。这是设计验收，不是 V2 运行验收。下一项 07C-02 实现版本化 V2 输出与兼容接入，并以优先级真值表验证；24 日真实数据不是开始实施的前提，正式 forward 回查仍独立待办。
