# 07C-02：Path State V2 输出

## 阶段合同

依据修订方案第 26 节及 07C-01 裁决，新增 `FOCUS_PATH_STATE_V2` 独立分类输出。保留 V1 已接受观察语义；V2 不以高优先级 `UNKNOWN` 覆盖低优先级已确认事实，也不将低优先级事实冒充最终主状态。

## 证据

`src/focus_tracker/path_state_v2.py` 提供 `resolved_primary_state`、`best_confirmed_state`、`higher_priority_unresolved`、`path_resolution`、`confirmed_secondary_states` 及谓词证据。股票和板块均复用现有谓词计算，再依原顺序解析 V2，避免两套谓词表达式漂移。`NOT_APPLICABLE` 不进入竞争；数据前提未知且无确认状态返回 `UNAVAILABLE`。测试 `tests/upgrade_v3/test_focus_07c_path_state_v2.py` 四项通过，覆盖高优先级未知、低优先级未知、缺行情和全部假值。

## 验收与下一阶段

`07C-02 / CODE_PASS / INTEGRATION_PENDING`。V2 纯分类输出可用，尚未接入正式 observation、存储及读 API，也未改写 V1 accepted head。07C-03 应明确 `READY/PARTIAL/AMBIGUOUS/UNAVAILABLE` 完整语义和兼容投影，再接入观察链路；此步骤不依赖 24 日数据，正式 forward 验收仍待真实连续日运行。
