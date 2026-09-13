# V3 P09-02-C-EXT01：收盘事件批次存储结构

## 阶段合同

本小任务依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §8.3、§19.4、§19.5、§22.3 执行，存储合同为 `v3-online-event-storage-v1.0`，迁移版本为 `033_v3_online_events`。

本轮仅建立允许归档的收盘事件结构：

- `online_event_bundles`：按交易日绑定来源批次、来源状态、覆盖和观察时间。
- `online_event_header`：按 `batch_id` 单独保存顶部计数、`seal_rate`/`broken_rate`/`source_rate` 分离的率字段和口径范围。
- `online_pool_entries`：按 `(batch_id,pool_type,source_code)` 保存事件成员，含 `float_market_cap`、`open_count`、`last_break_time`、`source_reason`、`source_fields` 和 `quality_codes`。
- 所有新表强制 `personal_research_only=true`；未知倍率、未知梯队语义允许为 `NULL`，不强制填 0/false。
- `source_code` 的市场命名空间由上游 DTO 合同负责，表结构不替换源身份；同日期修订通过新 batch，不覆盖旧 batch。

本任务不执行真实迁移、不采集网络、不写 raw、不写热榜表、不改变本地 run 身份、不访问或修改 TDX。迁移只在临时内存 DuckDB 中验证。

## 验收证据

机器回执：[P09-02-C-EXT01_CLOSE_BATCH_STORE.json](../reports/upgrade_v3/P09-02-C-EXT01_CLOSE_BATCH_STORE.json)。验证命令：

```text
python -m pytest -q tests/upgrade_v3/test_p09_02_c_ext01_close_batch_store.py
python scripts/verify_p09_02_c_ext01_close_batch_store.py
python -m compileall -q scripts/verify_p09_02_c_ext01_close_batch_store.py
git diff --check
```

验收为 `FULL_PASS`（迁移/结构范围）；EXT01 源能力仍为 `DEGRADED`，本任务未放行生产数据库应用、写入器或 API/UI。

## 下一步

下一小任务为 `P09-02-D-EXT01-CLOSE-BATCH-WRITER`：将已通过 DTO/批次读取的收盘批次以事务方式写入上述表，并校验 bundle/header/member 绑定、重复批次不覆盖和失败回滚。
