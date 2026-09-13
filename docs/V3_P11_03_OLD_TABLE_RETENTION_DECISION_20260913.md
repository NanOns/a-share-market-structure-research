# V3 旧表保留决策登记（2026-09-13）

## 决策

根据用户明确指示，以下旧表在 V3 全部功能开发完成、页面旧功能全部迁移完成之前统一保留，不执行删除、清空或 VACUUM：

- 6 张迁移域旧结果表
- 4 张关系历史表
- 7 张尚未纳入首轮迁移的辅助结果表

本次是保留决策，不是删除授权；生产数据库未修改。

机器回执：[P11-03-OLD-TABLE-RETENTION-DECISION-20260913.json](../reports/upgrade_v3/P11-03-OLD-TABLE-RETENTION-DECISION-20260913.json)

## 保留范围

### 迁移域旧结果表

`stock_technical_daily`、`stock_strength_daily`、`stock_high_daily`、`sector_member_state_daily`、`historical_structure_daily`、`stock_structure_summary_daily`。

### 关系历史表

`membership_snapshots`、`membership_entries`、`sector_membership_changes`、`stock_sector_associations_daily`。

### 辅助结果表

`sector_base_daily`、`historical_coverage_daily`、`representative_state_daily`、`sector_cycle_daily`、`mainline_daily`、`market_cycle_daily`、`market_reference_daily`。

## 重新判断条件

只有同时满足以下条件后，才逐表判断是否删除：

1. V3 功能开发完成；
2. 页面旧功能全部迁移到 V3 入口；
3. 每张表的 API、页面、兼容读取和脚本引用关系完成盘点；
4. 每张表完成等价性和兼容回归；
5. storage reference audit 已关闭或有独立处置结论；
6. 重新形成明确的逐表删除决策和删除前回执。

在此之前，旧表的状态统一为 `RETAIN_UNTIL_V3_AND_UI_MIGRATION_COMPLETE`，实际动作 `NONE`。

## 当前验收

| 项目 | 结果 |
|---|---|
| 保留表数量 | 17 |
| 生产库 | size/mtime 未变化 |
| 数据库表删除 | 未执行 |
| VACUUM | 未执行 |
| TDX | 未访问、未修改 |

下一阶段关注 V3 完成和旧页面迁移门，不提前进行旧表回收。
