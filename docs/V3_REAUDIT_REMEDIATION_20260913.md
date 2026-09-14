# V3 全栈复核整改记录（2026-09-13）

## 阶段合同

- task_id：`V3-RA-REMEDIATION-20260913`
- contract：`V3_FULL_STACK_REMEDIATION_V1_0`
- 适用文档：V3 主规格 §2、§5–§12、§18.13–§18.14、§20–§22，以及用户裁决 `V3-UC-20260913-01`
- 前置：Phase 0 `FULL_PASS`；全栈复核结论 `BLOCKED`

## 实施与证据

1. V3 启动时从 DOM 移除本地收盘梯队/晋级、旧 M14 热榜和含本地涨跌停的结构图；V3 市场页不再调用本地 `limit_ladder`、`limit_promotion` 或旧热榜请求。旧 `/v2` 和旧 API 保留历史兼容；功能矩阵 `LEGACY-13` 标记 `V2_HISTORY_ONLY_REMOVED_FROM_V3`。
2. V3 市场页增加 `/v3/online`“完整在线工作台”和 `/v3/events`“涨停简图与证据”显式入口；在线失败不回退本地估算。
3. 首页板块卡携带 `sector_id/context_id/member_role` 进入联动成员视图；个股条目携带 `security_id` 打开个股透视路由。
4. V3 页面残留的 M7/M7A 标识改为 V3；共享模板的 V2 品牌仍为 M7。
5. 修复研究构建器：从原始日线用同证券前一交易日 `raw_close` 生成 `quote_prev_close`；历史技术读取绑定当前 analysis snapshot slice，避免跨 slice 重复/缺失污染。
6. 按当前日与 t-3 的历史成员交集计算 `b_delta3`；同时要求共同有效成员不少于 5 且覆盖率不低于 70%，不直接相减不同成员集。
7. 算法版本升级为 `RESEARCH_V3_PREVIEW_3`，参数哈希同步冻结。真实生产重建完成：run `research-5674cf88ba024738bf3dc066c2e57155`，5932 个股票状态、554 个板块状态、2366 个角色、20 条 CURRENT_FOCUS、47 条关联。
8. 当前结果为 12 个 CURRENT 板块；页面按合同显示前 6 张卡、CURRENT_FOCUS 前 10 条。554 个板块均为 `READY`，不再出现 `UNKNOWN_MARKET_COVERAGE`。
9. 浏览器实测：V3 市场页 `local-limit-panel=false`、旧 hot-rank panel=false；完整在线工作台和涨停证据入口可见；板块卡打开指定 `sector_id` 的 11 条成员结果；个股条目打开指定 `security_id` 的透视弹窗。
10. 完整回归：`355 passed in 121.03s`；`node --check` 与 `git diff --check` 通过。
11. 收尾复核：矩阵与统一入口针对性测试 `5 passed`；共享 V2 模板品牌占位符按路由分别替换。最终代码再次完成 V3/M7/M14/M15 完整回归：`355 passed in 79.66s`；两个脚本语法及 diff 检查通过。

## 接受结果

| 项目 | 结果 |
|---|---|
| 移除 V3 本地收盘梯队与晋级 | `FULL_PASS` |
| 完整在线入口可见 | `FULL_PASS` |
| 首页对象级联动 | `FULL_PASS` |
| CURRENT / CURRENT_FOCUS 数据恢复 | `FULL_PASS` |
| POTENTIAL / EARLY_FOCUS | `EMPTY_BY_CURRENT_RULES`；当前真实日无合格项，不用旧候选填充 |
| 在线来源实时可用性 | `DEGRADED_PASS`；外部来源失败仍按数据集 fail-closed |
| P10-03 效果 | `EFFECT_OBSERVATION_PENDING`；不因本次修复提前宣称效果通过 |

阶段结果：`DEGRADED_PASS`。代码和本地核心数据缺陷已关闭；剩余限制是当前日没有 POTENTIAL 合格项、在线外部来源可用性和效果观察样本不足。

下一阶段：继续积累真实交易日，核查 POTENTIAL 分布和 P10-03 的 20 信号日/50 episode 门槛；在线源按各数据集独立复测，不恢复本地梯队回退。
