# P11 V3 日增量激活（2026-09-13）

## 结果

P11-04 主入口交接后的 V3 日增量激活已完成，状态为 `FULL_PASS`。本次使用当前
V3 publication `m4-8a99c99719061f4f1f166d0b9184506c`，针对
`2026-09-10` 执行 `V3_DAILY_INCREMENTAL`：technical 由真实 normalized parquet
批量计算，strength/high/structure/summary/member_state 通过当前绑定快照显式复用，
全部完成后再绑定新的 V3 快照。

机器回执：[P11-V3-DAILY-ACTIVATION-20260913.json](../reports/upgrade_v3/P11-V3-DAILY-ACTIVATION-20260913.json)

## 验收边界

- 计划逻辑 task 只覆盖一个截止日 `2026-09-10`；协调器按域/日期合并计算，不逐 task 产生独立写入；
- 目标域严格为 `technical`、`strength`、`high`、`structure`、`summary`、`member_state`；
- 其它五个域通过既有 immutable slice 显式 `REUSE`，未静默跳过；
- 计划文件和增长回执已生成；生产库只发生本次 V3 result/snapshot binding 范围内的写入；
- 未访问或修改 TDX，未发在线请求，未删除旧表。

首轮外层执行器回执曾因目标域排序比较和内部 `report_artifact` 未回填而误报
`BLOCKED`；writer 事务实际已 `BUILT`。独立只读后置复核已纠正回执，最终以机器回执
中的 postcondition checks、落盘 build report 和当前 publication binding 为准。

后置复核又发现新 snapshot 初始遗漏了旧日期的 8 个 target-domain 引用，已通过
只补 immutable `analysis_snapshot_entries` 的兼容修复恢复；详见
`P11-V3-SNAPSHOT-COMPATIBILITY-REPAIR-20260913.json`。未删除旧 snapshot、旧表或业务行。

## 不变的限制

本次激活没有创造新的交易日，只是把当前 publication 的 V3 日增量入口真实跑通。
P10-03 仍为 `EFFECT_OBSERVATION_PENDING`；旧表继续保留，待 V3 开发和旧页面功能
迁移完成后再逐表复核。
