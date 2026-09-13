# V3 P09-02-A-EXT01：事件头与成员 DTO

## 阶段合同

本小任务依据最新 V3 主文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §8.3、§19.4、§22.3 执行，合同版本为 `v3-online-event-dto-v1.0`，适配器版本为 `v3-lz-ext01-event-adapter-v1.0`。

范围仅限 EXT01 合法响应的内存标准化：

- `EventHeader` 单独承载源头计数、口径、分页范围和提示信息；不把头计数复制成成员行。
- `EventPoolRow` 单独承载涨停成员，固定 `pool_type=LIMIT_UP`、`event_state=LIMIT_UP`，并保留 `source_fields`。
- `source_code` 带市场命名空间；无法映射的 `security_id` 保持 `NULL` 并记录质量码。
- `seal_rate`、`broken_rate` 分开；当前不计算任何比率。
- 成交额、封单额、流通市值、换手率和涨幅倍率未由重复样本确认，统一保持 `NULL` 并记录原因；价格仅做无倍率 Decimal 解析。
- 首末封时间只接受明确 Unix 秒/毫秒，0 转为 `NULL`；连续板与 M 天 N 板不从 `high_days_value` 等字段推断。

本任务不做网络请求、不写数据库、不写 raw、不连接 API/UI，不改变本地 run 身份，也不访问或修改 TDX 输入。

## 验收证据

机器回执：[P09-02-A-EXT01_EVENT_DTO.json](../reports/upgrade_v3/P09-02-A-EXT01_EVENT_DTO.json)。验证命令：

```text
python -m pytest -q tests/upgrade_v3/test_p09_02_a_ext01_event_dto.py
python scripts/verify_p09_02_a_ext01_event_dto.py
python -m compileall -q src/workbench_online/event_models.py scripts/verify_p09_02_a_ext01_event_dto.py
git diff --check
```

验收为 `FULL_PASS`（仅 DTO/适配器范围）；源能力仍为 `DEGRADED`，分页、字段倍率和生产表/接口放行不在本小任务关闭。

## 下一步

下一小任务为 `P09-02-B-EXT01-BATCH-READ`：在不改变本地 run 身份、且不持久化禁止 raw 的前提下，建立同一 source/fetch/batch 绑定、分页边界和失败降级的读取合同。
