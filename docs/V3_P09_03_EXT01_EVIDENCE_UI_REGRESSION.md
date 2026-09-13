# V3 P09-03-EXT01：来源证据弹窗 UI 回归

## 阶段合同

本小任务依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §12、§19.5、§20.8 执行。合同版本为 `v3-events-evidence-ui-regression-v1.0`，页面为 `/v3/events`。

本轮只回归已交付 EXT01 简图的证据弹窗、来源时间、失败空态和分页状态：不新增源、不发上游请求、不写生产库或 TDX。

## 实际页面证据

使用临时 DuckDB 合成批次启动本地页面并通过浏览器检查：

- 首行“查看”打开 `事件证据 · SH.600005`；来源、数据集、交易日、观察时间、源截止“未确认”、事件批次和覆盖均可见。
- 字段证据表正确展示 `price → latest`、`ret1 → change_rate → UNCONFIRMED` 等映射；没有把未知倍率改写为数值。
- 点击弹窗内容后弹窗保持打开；按 `Esc` 关闭；再次打开后点击 `X` 关闭；两种关闭方式均将焦点返回触发“查看”按钮。
- 无事件批次页面显示 `UNAVAILABLE · 当前没有可读取的 EXT01 收盘事件批次。`，观察时间、源截止、覆盖保持明确未确认，返回计数为 `0 / 0`，没有使用本地数据替代。

## 自动验收

机器回执：[P09-03-EXT01-EVIDENCE-UI-REGRESSION.json](../reports/upgrade_v3/P09-03-EXT01-EVIDENCE-UI-REGRESSION.json)。验证命令：

```text
python -m pytest -q tests/upgrade_v3/test_p09_03_ext01_evidence_ui_regression.py
python scripts/verify_p09_03_ext01_evidence_ui_regression.py
python -m compileall -q src/workbench_service/online_events.py src/workbench_service/app.py scripts/verify_p09_03_ext01_evidence_ui_regression.py
git diff --check
```

结果：定向 UI 回归 `2 passed`，机器回执 `FULL_PASS`。`source_status=DEGRADED`、`release_ready=false` 保持不变；本地临时服务已关闭。

## 下一步

下一小任务为 `P09-03-EXT01-CLOSE-OUT`：汇总 EXT01 简图/证据链的范围、缺口和独立能力状态；不将 `DEGRADED` 源能力改写为生产 `FULL_PASS`，也不扩展其它在线源。
