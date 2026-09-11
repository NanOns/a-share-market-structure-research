# M11-03 个股—板块关联合同 V1

合同 ID：`STOCK_SECTOR_ASSOC_V1`  
适用计划：`workbench-upgrade-plan-v2.1`  
阶段：M11-03（预览）

## 目标与数据边界

该合同只输出可解释的日级“个股属于哪些板块”的关联证据，不宣称复刻原软件算法，也不证明经济有效性。输入必须来自当前已发布且可追溯的本地分析快照；回算数据必须标记 `history_basis=RECONSTRUCTED`，不能伪装成历史时点事实。TDX 源目录只读，Forward 观察表不参与历史回算写入。

## 资格门

对每个“证券—板块—日期”关系同时执行以下门控，所有未通过的原因都写入 `rejection_reasons`：

- 语义桶必须是 `NORMAL_ATTRIBUTE`；行情标签、排除角色和无效板块不得进入关联排名。
- `coverage >= 0.70`，板块状态模式必须是 `CURRENT_STRENGTH` 或 `REACCELERATION`。
- 留一法后至少有 5 个有效成员，20 日收益中位数严格大于 0，20 日正收益广度至少 `0.60`。
- 目标股在板块成员 20 日收益中的百分位至少 `0.80`。
- `REACCELERATION` 额外要求留一法 5 日收益中位数严格大于 0 且正收益广度至少 `0.60`，有效样本至少 5 个。

合格结果按模式、板块强度、留一法广度、目标股百分位和覆盖率的确定性顺序排序；每只股票最多保留 1 个 primary 和 2 个 alternatives。拒绝结果默认不展示，但在 `days=1&include_rejected=true` 时返回原因详情。

## 存储与接口

日级结果存储于 `stock_sector_associations_daily`，由迁移 `019_m11_association` 建立。每行绑定 `slice_id`、`membership_snapshot_id`、`contract_id`、`history_basis` 和完整证据 JSON。

API28：`GET /api/stocks/{security_id}/sector-associations`。

- `P` 默认使用已发布分析；`days` 范围为 1–250，默认 1。
- `include_rejected=true` 仅允许 `days=1`。
- 默认只返回合格的 primary/alternatives；响应必须包含 `_analysis_meta` 以及回算/快照依据。

## 阶段状态

M11-03 仅在定向测试、迁移验证、API 冒烟和全量 M7–M11 回归完成后出具 `PREVIEW_PASS`。该回执不代表正式激活；M11-04 必须人工启动，并重新读取本合同和最新升级文档。金额 A 等跨阶段综合审计问题单独记录，不并入本合同的通过结论。
