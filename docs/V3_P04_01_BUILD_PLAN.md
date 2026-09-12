# V3 P04-01 阶段报告

## 结论

`P04-01`：**PASS**。

本阶段只实现每日最小失效范围规划，不执行增量 writer，不写入任何 `*_daily`、result rows、publication 或 snapshot，也不访问或修改 TDX 输入目录。执行依据为当前工作区的 V3 主实施文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，对应 §17.6、§17.7、§18.7 P04-01。

## 阶段合同

- `src/workbench_service/build_planner.py` 提供版本化纯函数 `build_plan`。
- 输入是 `v3-dependency-summary-v1.0`：交易日、行情、关系、板块名称、树父关系、参数和复权锚摘要；只比较摘要内容，不把整个 source bundle 日期变化当作全历史失效。
- 输出是 `v3-build-plan-v1.0`，包含 `plan_id`、输入摘要 hash、差分事件、任务的日期/证券/板块/域范围、传播模式、reason code 和解释文本。
- 相同 `(previous, current, calendar, universe, context)` 输入产生相同 `plan_id`；无变化时返回 `status=NO_WORK` 且 `tasks=[]`。
- `scripts/plan_v3_build.py` 可从 JSON 输入生成可查看的 build plan，并以临时文件加 `os.replace` 原子写出；显式拒绝 TDX 根目录内的输出。

## 规则落地

- 普通新日只产生当天的股票、板块、成员和市场任务，不回写旧日。
- 只改板块名称只产生 `sector_base` 属性/显示任务，不产生 `technical`、`strength`、`high`、结构或成员历史技术任务。
- 只改概念成员只计划受影响板块、成员状态、结构/summary 和板块研究域，不扩散到无关股票技术域。
- 原始价量修订按 `history_windows.yaml` 的 60 日技术/RPS窗口规划；`strength` 对受影响日期展开全证券横截面；`high`、结构和 summary 对受影响证券传播到 cutoff，避免漏掉递推状态。
- 复权锚变化按安全边界传播到 cutoff；不假设只影响当天。
- 每个任务至少带一个解释码；同一任务由多个原因命中时合并并排序，不重复生成。

## 文件与证据

- 新增 `src/workbench_service/build_planner.py`。
- 新增 `scripts/plan_v3_build.py`。
- 新增 `tests/upgrade_v3/test_p04_01_build_planner.py`。
- 本阶段不修改 `D:/new_tdx`、配置的 TDX 源目录、生产数据库或生产结果表。

## 验收记录

定向测试覆盖：新交易日追加、板块改名隔离、概念成员变更隔离、历史价量修订的全市场 RPS、相同输入空计划、复权锚末端传播。

- `pytest -q tests/upgrade_v3 tests/upgrade_m7/test_window_planner.py`：`52 passed`。
- `python -m compileall -q src/workbench_service scripts tests/upgrade_v3`：通过。
- `git diff --check`：通过。
- 本阶段没有生产数据库写入、TDX 访问、结果行写入或发布动作。

验收结论：**PASS**。改名不重算 MA/技术域；概念成员变化不扩散到无关股票技术；历史价量修订规划全证券 RPS 横截面并把递推状态推到 cutoff；相同输入的待算域为空。

## 下一阶段

只有本阶段回归达到 PASS 后，下一项才是 `P04-02`：让增量 writer 严格消费本阶段 build plan。本阶段不实现、不调用该 writer。
