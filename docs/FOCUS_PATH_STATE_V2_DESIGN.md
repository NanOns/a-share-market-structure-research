# FOCUS_PATH_STATE_V2 设计合同

## 适用依据与边界

依据 `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 24～29、41 节，以及 `docs/FOCUS_07C_01_UNKNOWN_PRIORITY_CONTRACT_20260924.md` 至 `docs/FOCUS_07C_05_SESSION_GAP_SEMANTICS_20260924.md`。本合同只作用于新建 observation；已接受的 `FOCUS_PATH_STATE_V1`、历史 observation 和 head 保持原记录。

## 版本化输出

`FOCUS_PATH_STATE_V2` 在 V1 `current_path_state` 之外输出 `resolved_primary_state`、`best_confirmed_state`、`higher_priority_unresolved`、`confirmed_secondary_states`、`path_resolution` 和逐项 predicate evidence。新 observation 使用 `FOCUS_OBSERVATION_ASSEMBLY_V2` 将该结构写入 `facts.path_state_v2`，并纳入 digest 与 core input closure；旧记录经 API 读取时该字段为 null。

优先级由版本合同中股票、板块的显式顺序决定，不读取 JSON object 的键顺序。高优先级 UNKNOWN 阻止较低 TRUE 成为无保留主状态，同时保留已确认的 TRUE。最高可确定的唯一 TRUE 为主状态；同一最高层多个 TRUE 为 `AMBIGUOUS`。无 TRUE 但有 UNKNOWN 或前置数据不可用为 `UNAVAILABLE`；高层 UNKNOWN 且低层 TRUE 为 `PARTIAL`；可确定唯一 TRUE 或全部 FALSE/NOT_APPLICABLE 为 `READY`。当前生产顺序为严格全序，`AMBIGUOUS` 作为未来同层合同冲突的显式表达。

`FOCUS_SESSION_GAP_SEMANTICS_V1` 将主日历会话划为 `ACTUAL_BAR`、`SUSPENDED`、`DATA_GAP`、`SOURCE_UNAVAILABLE`。CONSECUTIVE 和 ROLLING 使用固定主日历窗口，三类非实际 bar 均使涉及的判断为 UNKNOWN，并保留原因。PATH 仅允许在首尾实际行情之间桥接证据一致的确认停牌；DATA_GAP 与 SOURCE_UNAVAILABLE 不可桥接。当前 AST 尚无 ROLLING 运算符，这一规则先作为未来合同冻结。

实现位置：`src/focus_tracker/path_state_v2.py`、`src/focus_tracker/session_gap_semantics.py`、`src/focus_tracker/observation.py`、`src/focus_tracker/core_input_closure.py`。源能力、谓词需求、按日事实和 AST 分别使用 `FOCUS_SOURCE_PATH_CAPABILITIES_V3`、`FOCUS_PREDICATE_REQUIREMENTS_V2`、`FOCUS_PREDICATE_FACTS_BY_DATE_V2`、`FOCUS_INVALIDATION_AST_V2`。
