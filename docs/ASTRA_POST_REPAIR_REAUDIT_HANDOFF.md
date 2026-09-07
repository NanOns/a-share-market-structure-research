# Astra 修复后独立复审交接单

当前状态：`READY_FOR_EXTERNAL_REAUDIT`。这不是 Astra PASS，也不声明 V2 已具备生产资格。

## 当前绑定

- 截止交易日：`20260904`
- V1 发布：`695c7ae5affd4abbb3d86eddb4b154e0`
- V1 计算身份：`41f4030eaff55b041bcbb05ce0bc39ed3d8736f438d5aa24eb4c14cdac5db51b`
- V2 集成身份：`cb3bdd356f01dfaad5990a393a44d10149cf81f9805c533219124d773aad8c94`
- 全量回归：`471 passed / 0 failed`
- 外部复审前 Forward 防护：`MODEL_IDENTITY_PREFLIGHT / BLOCKED`
- TDX 输入：只读，未使用网络或外部行情

## 当前实际结果

- V1 候选板：`1015` 行，逐股主键唯一
- V2 研究候选：`628`
- CORE / SUPPORTED / DIAGNOSTIC：`403 / 225 / 387`
- 队列：`{"BREAKOUT_QUEUE": {"CORE": 37, "SUPPORTED": 11}, "EARLY_QUEUE": {"CORE": 0, "SUPPORTED": 17}, "LEADER_QUEUE": {"CORE": 217, "SUPPORTED": 115}, "PULLBACK_QUEUE": {"CORE": 116, "SUPPORTED": 100}, "STEADY_QUEUE": {"CORE": 89, "SUPPORTED": 89}}`

## Astra 必须独立重跑

1. 校验 `POST_REPAIR_REAUDIT_EVIDENCE.json` 内每个文件的 SHA256。
2. 独立执行全量测试，不以本交接单中的测试数字替代。
3. 独立重放默认 V1 与七个 V2 模块，并核对 1015 行逐股唯一性及上述分类数量。
4. 重跑 `run_r3_integrated_seal.py`，确认收据链、Parquet、优先级身份和当前 V1 发布完全一致。
5. 重跑模型身份变更、发布故障、Forward 状态、两股票 Outcome、零队列等边界验证。
6. 只有 Astra 给出 `EXTERNAL_AUDIT_PASS` 后，才允许更新 `SEALED_MODEL` 并恢复 Forward。

机器证据入口：`reports/shadow/v2/20260904/integrated/POST_REPAIR_REAUDIT_EVIDENCE.json`
集成封存收据：`reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json`
