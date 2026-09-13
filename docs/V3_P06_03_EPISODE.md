# V3 P06-03：潜在板块 episode 生命周期

## 结论

依据最新 V3 主实施文档 §5.3、§18.9，P06-03 验收结果：**FULL_PASS（纯函数与 10 日合成序列）**。

## 阶段合同

- 入口：`workbench_analysis.sector_attention.progress_potential_episode()`；输出保留 `first_seen_date`、`last_qualified_date`、`age_sessions`、`state`、`end_reason`。
- 状态包括 `QUALIFIED`、`CONFIRMED`、`INVALIDATED`、`MONITORING`、`CONDITION_LOST`、`EXPIRED`、`DATA_GAP`；CURRENT 先于潜在状态确认。
- 最长跟踪 5 个主交易日；最多 1 个有效日 MONITORING；第二个已知不满足日 CONDITION_LOST；至少 2 个已知非命中日后才允许新 episode。未来 CURRENT 不回写首日信号。
- W、`ma20_width<.35`、风险覆盖充分且过热成员超过一半时硬失效；缺失输入进入 DATA_GAP，年龄推进但不转为失败。

## 验收证据

定向测试 `tests/upgrade_v3/test_p06_03_episode.py` 为 `4 passed`，覆盖 CURRENT 确认、首日不可回写、MONITORING→CONDITION_LOST、两日重置、DATA_GAP、硬失效和完整 10 主交易日第 5 日到期。该任务只验证状态机与合成序列，不声称算法效果，不消费未来数据。

未写生产数据库、未修改 TDX、未启动 scanner；历史 episode 尚未接入持久化 writer，后续 P07/P08 只能消费带 contract 的只读状态结果。

## 下一阶段

G06 关闭，进入 P07-01：计算板块四类成员角色，并保持 TODAY_LEADER、CURRENT_RESEARCH、EARLY_WATCH、ALL_MEMBERS 的分母和语义分离。
