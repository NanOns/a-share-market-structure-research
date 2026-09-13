# V3 P09-03-EXT01：涨停简图来源证据与单股下钻

## 阶段合同

本小任务依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §12、§19.5、§20.8、§22.3 执行。上一阶段的 `P09-03-EXT01` 已完成简图列表；本轮只补 EXT01 已归档收盘批次的字段证据、来源时间和单股事件下钻，不重新采集网络数据。

合同版本为 `v3-events-ladder-evidence-v1.0`，路由为：

```text
GET /api/v3/events/ladder/{security_id}?event_bundle_id=...&trade_date=...
```

## 实施范围

- 复用 `GET /api/v3/events/ladder` 的固定 bundle、批次和 `LIMIT_UP` 成员边界；支持规范 `security_id` 或对应 `source_code` 查询。
- 返回 `source_id`、数据集、bundle/batch、交易日、`observed_at`、`source_as_of` 和明确的 `source_time.basis`；缺少 `source_as_of` 时保留 NULL，并提示观察时间不是逐股成交时间。
- 返回规范字段→来源字段映射、字段值和状态；未知倍率/缺失字段保持 `UNCONFIRMED` 或 `OBSERVED_VALUE_SCALE_UNRESOLVED`，不补 0、不猜单位。
- 页面在每行增加“证据”按钮，使用居中弹窗显示来源时间、身份、字段证据和事件摘要；支持 X、遮罩、Esc 关闭并回焦触发按钮。
- 缺失批次或个股返回 `UNAVAILABLE` 与明确空态，不用本地梯队或本地估算补齐在线事实；不落 raw、不启动本地 run。

## 验收证据

机器回执：[P09-03-EXT01-LADDER-EVIDENCE.json](../reports/upgrade_v3/P09-03-EXT01-LADDER-EVIDENCE.json)。验证命令：

```text
python -m pytest -q tests/upgrade_v3/test_p09_03_ext01_ladder_evidence.py
python scripts/verify_p09_03_ext01_ladder_evidence.py
python -m compileall -q src/workbench_service/online_events.py src/workbench_service/app.py scripts/verify_p09_03_ext01_ladder_evidence.py
git diff --check
```

本阶段只对代码合同、内部 API、页面入口和临时数据库查询验收；EXT01 来源能力仍为 `DEGRADED`，不代表生产数据已放行。

## 下一步

下一小任务为 `P09-03-EXT01-EVIDENCE-UI-REGRESSION`：对弹窗交互、来源时间/空态展示和列表分页做独立页面回归；仍不扩展其它在线源。
