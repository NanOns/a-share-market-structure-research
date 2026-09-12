# V3 P04-02 阶段报告

## 结论

`P04-02`：**PASS**。

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

下一项严格是 `P04-03`：只处理解包缓存、源包引用与回收预览边界。本阶段不执行缓存删除、备份策略改造或物理空间回收。
