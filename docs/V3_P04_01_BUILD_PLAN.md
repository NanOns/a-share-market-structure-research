# V3 P04-01 阶段报告

## 结论

原 `P04-01` 记录保留为历史证据；依据最新 V3 主实施文档追加的 `R19-02/R19-03/R19-04` 补项：**PASS**。

最新主实施文档 SHA-256：`3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`。

本次补项关闭了：RET60 的 `d+60` 输出端点、显式空成员与缺失成员映射的区分、价格/复权修订的市场及板块/成员依赖闭包、未知参数域静默跳过问题。P04-02 的生产入口集成、完整快照覆盖和执行器矩阵仍未在本报告中放行。

本阶段只实现每日最小失效范围规划，不执行增量 writer，不写入任何 `*_daily`、result rows、publication 或 snapshot，也不访问或修改 TDX 输入目录。执行依据为当前工作区的 V3 主实施文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，对应 §17.6、§17.7、§18.7 P04-01。

## 阶段合同

- `src/workbench_service/build_planner.py` 提供版本化纯函数 `build_plan`。
- 输入是 `v3-dependency-summary-v1.0`：交易日、行情、关系、板块名称、树父关系、参数和复权锚摘要；只比较摘要内容，不把整个 source bundle 日期变化当作全历史失效。
- 输出是 `v3-build-plan-v1.0`，包含 `plan_id`、输入摘要 hash、差分事件、任务的日期/证券/板块/域范围、传播模式、reason code 和解释文本。
- 相同 `(previous, current, calendar, universe, context)` 输入产生相同 `plan_id`；无变化时返回 `status=NO_WORK` 且 `tasks=[]`。
- 输入 lookback 与受影响输出范围分离；`strength` 的 RPS/RET60 输出明确包含 `d+60` 端点。
- 成员映射区分 `KNOWN`、显式 `EMPTY` 和 `MISSING`；`EMPTY` 不生成成员任务，`MISSING` fail-closed。
- 价格/复权修订必须有已知证券—板块映射；市场、板块、成员和状态递推任务按闭包传播，未知参数域直接拒绝。
- `scripts/plan_v3_build.py` 可从 JSON 输入生成可查看的 build plan，并以临时文件加 `os.replace` 原子写出；显式拒绝 TDX 根目录内的输出。

## 规则落地

- 普通新日只产生当天的股票、板块、成员和市场任务，不回写旧日。
- 只改板块名称只产生 `sector_base` 属性/显示任务，不产生 `technical`、`strength`、`high`、结构或成员历史技术任务。
- 只改概念成员只计划受影响板块、成员状态、结构/summary 和板块研究域，不扩散到无关股票技术域。
- 原始价量修订按 `history_windows.yaml` 的 60 日技术/RPS窗口规划；`strength` 对受影响日期展开全证券横截面；`high`、结构和 summary 对受影响证券传播到 cutoff，避免漏掉递推状态。
- 原始价量修订的 `strength` 端点覆盖 `d+60`；同时更新受影响市场、板块、成员和状态递推域。
- 复权锚变化按安全边界传播到 cutoff，并更新受影响市场、板块、成员和状态递推域；不假设只影响当天。
- 未知参数域不再静默生成空计划；缺历史证券—板块映射直接报错，等待调用方补齐映射。
- 每个任务至少带一个解释码；同一任务由多个原因命中时合并并排序，不重复生成。

## 文件与证据

- 新增 `src/workbench_service/build_planner.py`。
- 新增 `scripts/plan_v3_build.py`。
- 新增 `tests/upgrade_v3/test_p04_01_build_planner.py`，增加 R19-02/R19-03/R19-04 反例与闭包测试。
- 本阶段不修改 `D:/new_tdx`、配置的 TDX 源目录、生产数据库或生产结果表。

## 验收记录

定向测试覆盖：新交易日追加、板块改名隔离、概念成员变更隔离、历史价量修订的全市场 RPS、RET60 `d+60`、市场更新、空/缺失成员、未知参数域、相同输入空计划、复权锚的市场/板块/成员末端传播。

- `pytest -q tests/upgrade_v3/test_p04_01_build_planner.py`：`11 passed`。
- `pytest -q tests/upgrade_v3/test_p04_02_incremental_writer.py`：`5 passed`。
- `pytest -q tests/upgrade_v3 tests/upgrade_m7/test_window_planner.py`：`62 passed`。
- `python -m compileall -q src/workbench_service scripts tests/upgrade_v3`：通过。
- `git diff --check`：通过。
- 本阶段没有生产数据库写入、TDX 访问、结果行写入或发布动作。

验收结论：**P04-01 补项 PASS**。R19-02/R19-03/R19-04 已有反例和修复证据；改名不重算 MA/技术域；概念成员变化不扩散到无关股票技术；历史价量修订规划全证券 RPS 横截面并包含 `d+60`，同时闭合市场/板块/成员下游；显式空成员不生成任务，缺失映射和未知参数域均 fail-closed；相同输入的待算域为空。

## 下一阶段

下一项严格是 `P04-02` 补项：关闭 R19-05/R19-06，验证完整目标快照、frame 业务键、逐域执行器矩阵和真实 daily 入口；在此之前不得把原 P04-02 的协调器 PASS 解释为完整生产增量。
