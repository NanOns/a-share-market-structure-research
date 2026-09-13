# P11-04 V3 主入口交接（2026-09-13）

## 交接结果

P11-04 已完成，机器状态为 `FULL_PASS`。默认入口已从 `/v2` 切换为 `/v3`，V3 本地双轨
研究页成为 `OPEN_UNIFIED_WORKBENCH.cmd` 的启动目标；旧 `/view` 和
`OPEN_RESEARCH_WORKBENCH.cmd` 继续保留为兼容回退入口。

机器回执：[P11-04-ENTRY-HANDOFF-20260913.json](../reports/upgrade_v3/P11-04-ENTRY-HANDOFF-20260913.json)

## 实际变更

- `OPEN_UNIFIED_WORKBENCH.cmd` 的 readiness/open URL 从 `/v2` 更新为 `/v3`；
- `runtime/workbench_entry.json` 更新为 `V3_P11_ENTRY_HANDOFF_V1_0`，主入口为
  `V3_LOCAL_DUAL_TRACK_WITH_VERIFIED_ONLINE_CARDS`；
- `docs/DAILY_OPERATION_GUIDE.md` 更新为 V3 日常入口说明；
- 旧 `/view`、旧启动脚本、旧发布读取路径和旧表均未删除。

## Post-switch smoke

使用本机临时端口和生产数据库连接执行 GET-only smoke：

- `/v3`：HTTP 200，V3、本地双轨 CURRENT/POTENTIAL 标记存在；
- `/v3/online`：HTTP 200；
- `/v3/events`：HTTP 200；
- `/api/v3/research/context`：绑定发布 `m4-8a99c99719061f4f1f166d0b9184506c`、交易日
  `2026-09-10`，返回 `READY`；
- `/api/v3/home/local`：HTTP 200；
- `/view?publication_id=...`：HTTP 200，旧回退入口可读。

smoke 前后生产数据库 size/mtime 不变；未提交 job、未调用外部在线采集、未写生产数据库、
未访问或修改 `D:/new_tdx`。

## 保留的明确限制

- P10-03 仍为 `EFFECT_OBSERVATION_PENDING`，入口切换不代表效果或收益保证；
- 在线卡片按数据集能力状态展示，不可用时 fail-closed；
- 旧表继续保留，只有在 V3 全部开发完成、旧页面功能迁移完成、逐表兼容回归完成后才重新裁决。

## 下一阶段

进入 V3 日常运行和效果观察；旧表按既定门槛等待重新逐表判断。
