# V3 P09-03-EXT01：在线涨停简图产品切片

## 阶段合同

本小任务依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §19.5、§20.8、§22.3 执行，API 合同为 `v3-events-ladder-api-v1.0`。

本轮只交付 EXT01 涨停简图/梯队切片：

- 新增只读 `GET /api/v3/events/ladder`，读取已获准归档的 EXT01 收盘 batch，不启动网络采集、不启动本地 run。
- 顶部 counts/rates/scope 与成员 items 分开返回；`seal_rate`、`broken_rate`、`source_rate` 不混用。
- 默认排序为高度降序、末封时间升序（NULL 最后）、封单额降序（NULL 最后）、security_id 升序；`sort=FIRST_LIMIT_TIME` 提供首封时间升序。
- `consecutive_limit_days` 与 `m_days/n_boards` 分列，`9天5板` 不显示为 `5板`；缺字段显示未确认，不改写为 0。
- 分页先算 total，再切页；覆盖或批次缺失时返回明确 `UNAVAILABLE` 空态，不用本地梯队结果冒充在线事实。
- 新增 `/v3/events` 页面，显示来源、交易日、观察时间、覆盖、头统计、成员字段和空态；未确认字段保持“未确认”。

EXT01 当前源能力仍为 `DEGRADED`，因此即使已归档批次存在，切片也不会宣称 `FULL_PASS` 或完整线上能力；本轮不接 EXT02–09、题材、七池、热榜或报价附加列。

## 验收证据

机器回执：[P09-03-EXT01-LADDER-SLICE.json](../reports/upgrade_v3/P09-03-EXT01-LADDER-SLICE.json)。验证命令：

```text
python -m pytest -q tests/upgrade_v3/test_p09_03_ext01_ladder_slice.py
python scripts/verify_p09_03_ext01_ladder_slice.py
python -m compileall -q src/workbench_service/online_events.py
git diff --check
```

本切片代码/API/页面/空态验收为 `FULL_PASS`；数据源能力仍按 EXT01 证据标 `DEGRADED`。

## 下一步

下一小任务为 `P09-03-EXT01-LADDER-EVIDENCE`：补充 API 返回的字段证据/来源时间展示和单股事件下钻合同；仍不扩展其它在线源。
