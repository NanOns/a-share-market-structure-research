# FOCUS-02 冻结篮子与成员强度阶段回执

> 日期：2026-09-23；阶段结果：`DEGRADED_PASS / FIRST_ACCEPTED_DAY_INPUTS_READY`。

| 字段 | 证据与结论 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6、14、15、17、19、20 节；`FOCUS_02_SOURCE_FACT_PROGRESS_20260923.md` |
| Phase 0 / migration | `FULL_PASS_TDX_NATIVE`；`FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED`；TDX 来源未写入 |
| stage_contract | `FOCUS_EPISODE_BASKET_V1`、`FOCUS_BASKET_RESOLUTION_V1`、`FOCUS_ACCEPTED_MEMBER_STRENGTH_V1` |
| basket_schema | 加法迁移 SHA-256 `3b5f037911aa86d2dd7465d5e9535cee56d045745d845c994545225700daa7a4`；默认 DDL rollback 演练、隔离 schema 恢复演练、事务安装及只读复核通过；新增 1 表、10 约束、2 索引、0 业务行 |
| persistence_rehearsal | PostgreSQL rollback-only 演练：冻结篮子插入、同键同摘要幂等、同键不同摘要拒绝、按 accepted head 读回、同日 revision 切换到新版篮子均通过；演练后 Focus run/head/篮子业务行仍为 0 |
| member_predicate_authority | 同 publication 的 `LOCAL_RECONSTRUCTED` accepted analysis head，member-state result object 75,361 行；结果合同 `MEMBER_STATE_RESULT_V3`，成员谓词合同 `SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC`；当前 publication 绑定关系与 `member_present` 集合逐键一致，缺失与多余均为 0 |
| full_day_probe | 2026-09-22：393 来源行、80 新 episode 冻结篮子、301 唯一股票事实 READY、80 板块相邻会话收益 READY、80 板块宽度 READY；最低板块价格覆盖率 `0.9782608695652173913043478261`；来源摘要 `4160454e07471b27c418a6d4c48b508585a32fb8a708f5b814785963f5352279`；计划摘要 `2ad1f1ba3c281b58aafb83966a956b30fb2274c91d44a3d43a3f8f6c8b6b1b62`；事实集合摘要 `ef167d21c8dc027ea52d6fc3c2aa919a2dd1a7601835eacdaedf2354583fee91` |
| tests | FOCUS-00 与 FOCUS-02 相关 34 项通过；含旧篮子不随当代篮子漂移、同日 revision 选择、强势成员留存率缺证据时为 U |
| acceptance_result | `DEGRADED_PASS / FIRST_ACCEPTED_DAY_INPUTS_READY`：首次正式日输入链和持久化篮子结构可进入 FOCUS-03 rollback-only writer 演练。历史多日 Focus head 尚不存在，无法做真实历史 episode 读回与连续前瞻验收；不代表模块可上线 |
| next_stage | `FOCUS-03`：冻结完整 input manifest、组装六维 observation 与 evaluation，事务内插入 run/items/episodes/baskets/anchors/observations/projection/head；先回滚演练，验证真实数据备份恢复后再接受正式激活 |

## 明确的质量边界

- entry-frozen basket 按 episode 首日 **accepted Focus head** 选择；同日修订保存两份不可变篮子，head 决定当前接受版本。后续 contemporary basket 单独保存并计算，不能覆盖 entry basket。
- 当前成员强度必须来自匹配日期与 publication 的 accepted analysis snapshot。结果行数、合同、成员集合及每板块可评价覆盖均验真；`strong_state=NULL` 不当作 false。`SWIDTH=强势数/可评价数`，不足 80% 时 U。
- `RETENTION` 只在前后篮子 Jaccard≥0.90、两日强度 READY、所有前日强势成员在今日可评价时计算；否则 U。没有前一 Focus 接受日时不能伪造留存率。
- `matched_categories` 和 `matched_stock_only_categories` 已从 V3.3 结果中按白名单纳入来源事实摘要；热榜请求时原文仍不保存。
- 本回执没有正式写入 Focus 业务数据。加法迁移只扩展 schema；回滚演练不会产生持久化 run/head。`DEGRADED_PASS` 的降级范围限于历史连续性未能用真实 Focus head 验证。
