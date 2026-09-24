# 07C-03：Path Resolution 合同

## 阶段合同

依据修订方案第 26、27 节及 `FOCUS_PATH_STATE_V2`。解析状态描述“当前证据能否确定主路径状态”，不替代具体 path state，也不回写 V1 已接受结果。解析顺序以版本合同显式给定的股票/板块优先级序列为准，不依赖 JSON object 的键顺序。

| 状态 | 规则 | V2 输出
|---|---|---|
| `READY` | 首个非 FALSE/NOT_APPLICABLE 的优先级层只有一个 TRUE；或所有谓词均为 FALSE/NOT_APPLICABLE | 首个 TRUE 为 `resolved_primary_state`；全假时主状态为空
| `PARTIAL` | 更高优先级层有 UNKNOWN，较低层已有一个或多个 TRUE | 主状态为空；列出已确认状态与阻塞它们的 UNKNOWN
| `AMBIGUOUS` | 在没有更高层 UNKNOWN 时，同一优先级层有多个 TRUE | 主状态及 `best_confirmed_state` 为空；全部并列确认事实保留
| `UNAVAILABLE` | 没有 TRUE，且仍有 UNKNOWN，或行情/覆盖前置条件不可用 | 无主状态；UNKNOWN 不降格为 FALSE

当前 stock/sector V1 顺序是严格全序，各层只有一个谓词，因此 `AMBIGUOUS` 当前不会由生产分类产生；保留该值是为合同明确未来可表达的同优先级冲突。解析器拒绝重复优先级谓词或与证据键不匹配的合同输入。

## 兼容投影

V2 输出独立于 `current_path_state`。消费者可继续读 V1 原字段；V2 的 `resolved_primary_state` 仅在 `READY` 且唯一 TRUE 时有值。`best_confirmed_state` 表示严格最高优先级的已确认事实；同层并列时为空。`confirmed_secondary_states` 保留所有 TRUE（包括 partial/ambiguous 时的事实）；`higher_priority_unresolved` 只列出优先级更高且可阻断主状态的 UNKNOWN。`actual_bar` / `coverage` 前置输入未知映射为 `UNAVAILABLE`，不视作 path predicate。

## 证据与验收

`src/focus_tracker/path_state_v2.py` 增加可单测的 `resolve_evidence_v2`，按优先级层实现上述四态；分类输出仍复用 V1 谓词。`tests/upgrade_v3/test_focus_07c_path_state_v2.py` 定向验收 10 项通过，覆盖高优先级未知保留低层 TRUE、已确认高层不受低层 UNKNOWN 影响、全假 READY、前置数据缺失 UNAVAILABLE、同层并列 AMBIGUOUS、未知阻断下层并列时 PARTIAL、合同键不匹配失败。

验收结果：`07C-03 / CONTRACT_AND_RESOLVER_PASS / OBSERVATION_INTEGRATION_PENDING`。仅新增 V2 resolver 逻辑，没有更改 `FOCUS_PATH_STATE_V1`、23/24 accepted run/head 或 24 日持久化 observation。

## 下一阶段

07C-04 将把 V2 字段附加到新 observation 的可解释证据中，保留 V1 主字段与历史记录；再核对 API 可读性以及 24 日真实输入的只读 V2 解析，不覆盖旧 observation。
