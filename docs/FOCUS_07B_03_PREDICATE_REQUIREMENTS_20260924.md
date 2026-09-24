# 07B-03 Predicate lookback planner（2026-09-24）

## 阶段合同

依据修订方案第 19 节，`FOCUS_PREDICATE_REQUIREMENTS_V1` 从失效 AST 静态产生 `required_sessions`、`required_fields`、`required_frozen_facts`。连续谓词对主交易日历计数；嵌套连续窗口按重叠日计算。`rps20_delta3` 需 4 日底层历史，动态 MA5、MA20 分别需 5、20 日。无效 AST 拒绝规划。

## 实施与证据

- 新增 `src/focus_tracker/predicate_requirements.py`。启动确认要求 2 日、`close`、`structure_break_v3`、实际行情标记及 `frozen_phh20`。恢复 MA20 分支要求 21 日历史，同时包含 `rps20_delta3` 与冻结的 `reclaimed_ma_kind` 身份。
- `daily_builder` 在读取标准化切片前规划各 V3.3 episode，以最大需求扩展切片起点；每个 episode 向 AST 评估器传入自己的最小主日历窗口。
- 规划器只声明需求。逐日事实构建是 07B-04；需求字段当前缺失时维持 `UNKNOWN`，不能把扩展日历窗口误作完整事实供给。
- 定向测试 6 项通过，Focus 测试 102 项通过。
- 23 日已接受来源只读构建通过：310 条观察（V3.3 273 条），全部 validity 为 `UNKNOWN`，写入 0；输入闭包摘要 `d0e82377b431a8ac8e2ad5d1bfd606d06c9aae7b0088a1afbfdfe486806e2603`。摘要相对 07B-02 改变是历史切片范围扩展后的预期结果，既有 23 日正式 head 未改写。

## 验收与下一阶段

07B-03 的 AST 静态需求和窗口接入已完成。下一阶段 07B-04 按规划器要求构建 `facts_by_date`，并验证缺口、停牌与实际行情标记。
