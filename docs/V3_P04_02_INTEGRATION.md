# V3 P04-02-INTEGRATION / C20-16 阶段记录

## 结论

依据当前工作区最新 V3 主实施文档（SHA-256：`3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`），本任务在代码与临时数据库验收范围内：**PASS（SCOPED）**。

本任务把 V3 增量入口接入实际每日任务调用链：旧 `build_m8_m9_preview.py` 完成当前兼容发布分析后，由 `app.py::run_today` 调用 `run_v3_daily_entry`，从只读 normalized parquet 生成/消费 `build_plan`，计算技术域，显式复用已绑定的其他目标域，最后在同一事务中写入结果、切片、快照和 publication binding。失败时入口返回 `V3_ANALYSIS_BINDING_FAILED`，不报告 READY。

本阶段未写生产数据库、生产结果库或 TDX 输入；验收使用临时 DuckDB 和与生产 schema/列合同一致的 parquet 输入。生产日任务的真实上线执行仍需独立运维窗口批准，不能以本阶段测试冒充生产写入证据。

## 阶段合同

- `src/workbench_service/v3_daily_entry.py` 是 V3 P04-02 的每日入口。
- 新日计划默认目标为旧每日构建器已能提供的 V3 结果域：`technical`、`strength`、`high`、`structure`、`summary`、`member_state`、`sector_base`、`sector_cycle`。
- `technical` 由 `CALCULATE` 从 normalized parquet 计算并写入 P03 result-row writer；其他目标域必须从明确绑定的 source snapshot `REUSE`，缺 slice、缺 result binding 或域/日期不一致时 fail-closed。
- 旧快照中的 `coverage`、`membership_changes`、`representative` 等非 V3 目标条目通过 `preserved_entries` 原样保留到新快照，不能满足 V3 目标完整性门，只用于兼容旧 reader。
- `mainline` 不在默认入口目标集合中，因为旧每日构建器当前不产生该域；显式把它放入目标时，缺少源 entry 会失败，不静默跳过。该域仍由后续明确接入任务处理。
- 同域同交易日多个证券任务合并为一个完整 frame/slice，避免 `analysis_snapshot_entries(snapshot_id, domain, trade_date)` 唯一键造成只写受影响股票、丢失同日未受影响股票的问题。
- 快照绑定的 `expected_task_keys` 仍只由已验证 plan 决定；兼容保留条目不会扩大或伪造目标计划的完成范围。

## 已完成实现

- `src/workbench_service/app.py`：旧分析预览成功后调用 V3 daily entry，V3 失败则 fail-closed。
- `src/workbench_service/v3_daily_entry.py`：加载真实 normalized parquet、读取 membership、构建新日 plan、读取 source snapshot、组织复用、批量计算技术域、绑定新快照并原子写出 plan/report 证据。
- `src/workbench_service/incremental_writer.py`：支持 source snapshot 证据化复用、同域同日批量任务、兼容旧条目保留和完整目标绑定。
- `scripts/run_v3_incremental_build.py`：source parquet provider 支持同日多证券批量输入。
- `reports/v3/daily/{cutoff}.plan.json` 与 `.report.json`：入口级计划和增长/复用/绑定结果使用临时文件后 `os.replace` 原子落盘，位置在 TDX 根目录外。

## 验收证据

集成测试 `tests/upgrade_v3/test_p04_02_integration.py` 覆盖：

1. 新日：两证券同日技术计算、strength 复用、结果写入、完整 snapshot/publication binding。
2. 同输入重跑：业务结果新增为 0，既有技术对象和旧域对象复用，兼容条目仍保留。
3. 历史价量修订：仅受影响证券的 technical 任务计算，strength 按全横截面任务复用/绑定，任务日期从修订日开始，不扩散到 B 的 technical。
4. 关系变化：只执行关系下游的复用目标域，不生成 technical/strength/high 任务。
5. 缺失/旧格式 source scope：只有显式 source snapshot entry 才允许复用旧 basis；没有绑定证据则拒绝。

执行结果：

- `pytest -q tests/upgrade_v3/test_p04_02_integration.py tests/upgrade_v3/test_p04_02_incremental_writer.py`：`14 passed`。
- `pytest -q tests/upgrade_v3 tests/upgrade_m7/test_window_planner.py`：`74 passed`。
- `python -m compileall -q src/workbench_service scripts tests/upgrade_v3`：通过。
- `git diff --check`：通过。
- 未访问或修改 `D:/new_tdx`、配置的 TDX 源目录、生产数据库和生产结果表。

## 未在本任务执行的事项

- 未执行 P04-03 缓存回收、全库备份策略或任何删除动作。
- 未把 `mainline` 冒充为已接入；未补做其旧构建器计算委托。
- 未执行生产 daily job；生产激活证据仍需要独立运维窗口和回滚核验。

## 下一项

P04-02-INTEGRATION/C20-16 在上述范围内关闭；下一项按最新 V3 台账为 `P04-03`，但本阶段不提前执行。
