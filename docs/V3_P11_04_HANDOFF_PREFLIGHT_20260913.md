# P11-04 主入口交接预检（2026-09-13）

## 结论

P11-04 交接预检为 `FULL_PASS`，当前状态为
`READY_FOR_EXPLICIT_P11_04_SWITCH`。V3 本地双轨页面、已验证的在线卡片页面、旧入口回退、
P11-01 存储止增长门、P10-01/P10-02 和诚实的 P10-03 效果状态均已核对。

机器回执：[P11-04-HANDOFF-PREFLIGHT-20260913.json](../reports/upgrade_v3/P11-04-HANDOFF-PREFLIGHT-20260913.json)

## 入口状态

当前正式入口仍是：

- `OPEN_UNIFIED_WORKBENCH.cmd` → `/v2`；
- `OPEN_RESEARCH_WORKBENCH.cmd` → `/view`，并继续使用 `CURRENT_WORKBENCH.json` 回退；
- 服务已提供 `/v3`、`/v3/online` 和 `/v3/events`，旧 `/view` 仍由服务保留。

目标 P11-04 入口为 `/v3`，但本次预检没有写 `runtime/workbench_entry.json`，没有修改
`OPEN_UNIFIED_WORKBENCH.cmd`，也没有执行重启或入口切换。`switch_executed=false`。

## 已核对门

- `P11-01-STORAGE-STOP-GROWTH-GATE`：`FULL_PASS`；
- `P10-01`、`P10-02`：`FULL_PASS`；
- `P10-03`：工程链通过，效果仍 `EFFECT_OBSERVATION_PENDING`；
- P09 已验证在线卡片可按数据集状态进入并 fail-closed，不把不可用源伪装成本地事实；
- 旧页面/旧 API 和旧表均未因预检删除，旧表继续按用户决定保留。

## 安全边界

本次只读入口 JSON、启动脚本、路由源码、静态页面和既有机器回执；未写生产数据库、未访问
或修改 `D:/new_tdx`、未创建备份、未执行清理。

## 下一步

若执行 P11-04 的入口变更，需要单独授权/确认把默认入口从 `/v2` 切到 `/v3`，随后执行
启动脚本和 `/v3`、`/view` 的 post-switch smoke，并登记最终交接回执。该动作不改变旧表
保留决策，也不改变 P10-03 的效果观察状态。
