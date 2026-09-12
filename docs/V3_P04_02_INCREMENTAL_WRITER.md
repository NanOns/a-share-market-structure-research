# V3 P04-02 阶段报告

## R19-05/R19-06 追加补验（当前权威结论）

当前主实施文档 SHA-256：`3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`。

追加补验结论：**PASS（限定在已注册能力和目标域范围内）**。本次修复关闭了 R19-05/R19-06 的对象完整性门：

- `SnapshotBinding.expected_task_keys` 必须显式给出，并且必须等于整个目标 plan；仅提交部分 objects 不能绑定 publication。
- 计算对象和复用对象都必须覆盖计划任务；复用必须声明旧 `source_slice_id`，且旧 slice 必须已有结果绑定、域和交易日一致。
- `PreparedBuildObject` 的 `security_id`/`sector_id`/日期业务键会与 covered task 逐项交叉核验，错误声明不能把 A 任务写成 B。
- 执行器矩阵逐域显式标记 `CALCULATE`、`REUSE` 或 `UNSUPPORTED`；未支持的 quote/market 不会静默跳过，也不会伪造结果。
- `execute_daily` 和 `run_v3_incremental_build.py` 的 `source_parquet` 入口已覆盖“只读输入→技术指标计算→P03 writer→slice/result binding→snapshot/publication binding”完整链路；prepared frame 仍保留为显式 hand-off 入口。

当前能力边界必须保留：默认矩阵只有 `technical` 走真实 `CALCULATE`；`strength`、`high`、`member_state`、`structure`、`summary`、`sector_base`、`sector_cycle`、`mainline` 明确要求 `REUSE`；`quote`、`market` 为 `UNSUPPORTED`。因此本补验不把局部技术域闭环冒充为全域每日生产已接入，C20-16 的 `P04-02-INTEGRATION` 仍是下一项任务，P04-03 不提前开始。

追加证据：P04-02/P04-01 定向测试 `22 passed`；V3 与 M7 窗口回归 `68 passed`。测试只使用临时 DuckDB；未写生产数据库、结果库或 TDX 输入。用户工作区对 V3 主实施文档的未提交修改未触碰。

## 结论

原 `P04-02` 协调器报告的 `PASS` 作为历史证据保留；按最新主实施文档复核，完整每日生产入口仍为 `SCOPE_PARTIAL`，以上 R19-05/R19-06 追加补验单独记录，不覆盖历史记录。

本阶段只实现“严格消费 P04-01 build plan 的增量 writer 协调层”和增长记录，不执行 P04-03 的解包缓存回收、备份调用链改造或任何删除动作。执行依据为当前工作区 V3 主实施文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` §17.6、§17.10、§17.12、§18.7 P04-02。

## 阶段合同

- `src/workbench_service/incremental_writer.py` 只接受通过 `v3-build-plan-v1.0` 内容 hash 校验的计划。
- `PreparedBuildObject` 为计划任务准备稳定 slice 身份；同一域同一交易日的多个证券任务可以覆盖到一个输出 slice，避免违反 `analysis_snapshot_entries(snapshot_id,domain,trade_date)` 唯一键。
- 已注册的 P03 result-row writer 在一个 DuckDB 事务内执行；未注册域 fail-closed，不静默回退到旧全量 writer。
- 所有对象成功后才创建/校验 `analysis_snapshots`、`analysis_snapshot_entries` 和 `publication_analysis_snapshots`；任一 writer 异常时结果行、slice、快照和发布绑定一起回滚。
- 指标按实测值记录：`new_fact_rows`、`reused_rows`、`reused_result_objects`、`identity_rows_added`、`cache_bytes_added`、`db_file_growth_bytes`，并保留每个 task 的覆盖范围。没有用固定“每行字节数”估算增长。
- `scripts/run_v3_incremental_build.py` 接收已准备好的 JSON frame hand-off，原子写出增长报告；输出路径拒绝落在 `D:/new_tdx` 下。

## 实现范围

- 默认复用 `technical`、`strength`、`high`、`member_state`、`structure`、`summary` 的 V3 writer，以及既有 `sector_base`、`sector_cycle`、`mainline` writer。
- `quote` 与 `market` 没有被伪造为已实现 writer；若调用方未显式注册对应合同，协调器返回 `WRITER_NOT_REGISTERED`，不写旧表、不绑定半成品。
- 不修改 `build_m8_m9_preview.py` 的旧全量入口，不把旧全量脚本冒充为增量入口。

## 真实输入证据

只读实际 `data/normalized/adjusted_daily.parquet`，未访问或修改 TDX 输入目录；抽取真实证券 `BJ.430017` 的 65 行，日期范围 `2023-05-31` 至 `2023-08-31`，通过现有 `calculate_technical_daily` 和 P03 technical result writer 写入临时 DuckDB。

- build plan 识别技术域 60 个受影响日期任务。
- 实际执行其中两个相邻日期对象，连续重复同一计划三次。
- 第一次：`new_fact_rows=2`、`identity_rows_added=2`、`reused_result_objects=0`、`db_file_growth_bytes=7077888`。
- 第二次：`new_fact_rows=0`、`identity_rows_added=0`、`reused_result_objects=2`、`db_file_growth_bytes=0`。
- 第三次：`new_fact_rows=0`、`identity_rows_added=0`、`reused_result_objects=2`、`db_file_growth_bytes=0`。
- 真实验证使用临时数据库，不改变生产数据库的行数、发布头或快照绑定。

## 失败与回滚证据

定向测试注入第二个域 writer 失败，首个 writer 已产生的 slice/result rows 与快照/发布绑定均回滚为 0；计划外对象在任何数据库写入前拒绝。

## 测试与验收

- `pytest -q tests/upgrade_v3/test_p04_01_build_planner.py tests/upgrade_v3/test_p04_02_incremental_writer.py`：`11 passed`。
- `pytest -q tests/upgrade_v3 tests/upgrade_m7/test_window_planner.py`：`57 passed`。
- P03 technical/strength/high/member_state/structure/summary 定向回归：`15 passed`。
- `python -m compileall -q src/workbench_service scripts tests/upgrade_v3`：通过。
- `git diff --check`：通过。
- 未写入生产数据库、生产结果表、TDX 输入或在线数据；真实验证只写临时 DuckDB。

验收结论：**PASS**。同输入三次重跑业务内容新增为 0；相邻日期只产生对应计划对象；对象不在 build plan 时拒绝；失败不改变首页/发布绑定；实测增长指标已记录。

## 下一阶段

原报告中的 `P04-03` 仅对应旧范围。当前权威下一项是 `P04-02-INTEGRATION`：把 plan、失效范围、复用、计算、写入和绑定接入实际每日生产调用链并完成新日/历史修订/关系变化/同输入验收；在该项完成前不执行 `P04-03`。
