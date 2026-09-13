# V3 P09-02-D-EXT01：收盘批次事务写入

## 阶段合同

本小任务依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §8.3、§19.4、§19.5、§22.3 执行，存储合同为 `v3-online-event-storage-v1.0`。

本轮只写入已通过 DTO/批次读取的完整收盘事件批次：

- 复用 `data_sources`、`online_fetch_runs`、`online_batches`，并在同一事务绑定 `online_event_bundles`、`online_event_header`、`online_pool_entries`。
- 只有 `complete_pagination=true`、无失败页、无重复冲突的批次允许归档；部分分页或 `UNAVAILABLE` 在写入前拒绝。
- 原始响应不落 `online_payloads`，`online_fetch_runs.raw_hash` 保持 `NULL`；成员的未确认金额/倍率/梯队字段保持 `NULL`，来源字段与质量码按 JSON 保存。
- 相同 `batch_id` 且内容一致时返回 `ALREADY_STORED`，不覆盖；同 ID 内容不一致或已有半写入状态则失败。
- 任一 source/fetch/batch/header/member/bundle 写入异常均回滚，不留下孤儿行。

本任务使用临时内存 DuckDB 验证，不应用真实数据库，不采集网络，不接 API/UI，不改变本地 run 身份，不访问或修改 TDX。EXT01 源能力仍为 `DEGRADED`。

## 验收证据

机器回执：[P09-02-D-EXT01_CLOSE_BATCH_WRITER.json](../reports/upgrade_v3/P09-02-D-EXT01_CLOSE_BATCH_WRITER.json)。验证命令：

```text
python -m pytest -q tests/upgrade_v3/test_p09_02_d_ext01_close_batch_writer.py
python scripts/verify_p09_02_d_ext01_close_batch_writer.py
python -m compileall -q src/workbench_online/event_store.py scripts/verify_p09_02_d_ext01_close_batch_writer.py
git diff --check
```

验收为 `FULL_PASS`（事务写入合同范围）；未放行生产应用、API/UI或全市场覆盖声明。

## 下一步

下一小任务为 `P09-03-EXT01-LADDER-SLICE`：基于已存收盘批次提供涨停简图/梯队最小产品切片，单独完成数据范围、空态、API、页面和回归验收。
