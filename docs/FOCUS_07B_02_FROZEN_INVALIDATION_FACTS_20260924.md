# 07B-02 V3.3 首日失效事实冻结记录（2026-09-24）

## 阶段合同

依据修订方案第 18 节和 `FOCUS_V33_FROZEN_INVALIDATION_FACTS_V1`，每个 V3.3 episode 在 `FIRST_FOCUS` 首日固定四个事实键。值只取自当日已接受来源；没有明确来源时记录 `SOURCE_OPERAND_UNAVAILABLE`。续日读取、校验首日来源摘要，不随当日候选事实改写。数据表在 PostgreSQL 的 `workbench.focus_episode_frozen_facts`，以 `(episode_id,fact_key)` 为主键，可单独查询。

## 证据与实施

- 23 日已接受来源的 273 个 V3.3 episode 可还原为 1,092 条事实；初次安装回滚演练与正式写入数量一致。
- 初次写入后发现 Focus 源事实以 `$binary64` 对象序列化浮点数，原提取器把 `phh20` 当作缺失。修正解码后，使用 `--repair-initial-encoding` 在事务内核对旧事实均为空，再重建 253 个 episode 的四键；任何旧非空事实都会拒绝覆盖。重跑回滚演练显示 `backfilled_episodes=0`、`repaired_initial_encoding_episodes=0`、`fact_rows=1092`。
- 源候选包含 253 个 `LAUNCH_CONFIRM` 和 20 个 `TREND_CONTINUE`。表内 `frozen_phh20` 有值 253 条、不可用 20 条；其他三个键均不可用 273 条。`trend_key_low`、`pullback_invalid_low` 在已接收因子键中不存在，不能从别的价格字段替代。当前 23 日候选没有另外两类 primary category。
- 新 episode 在核心事务内插入冻结事实；续日验证已持久化事实与首日已接受来源完全一致；日构建器读取冻结值提供给 AST。失效判断仍需 07B-03 的多日窗口和 07B-04 的逐日事实，当前不能据此宣称 validity 全面可用。
- `tests/upgrade_v3 -q -k focus`：96 passed。冻结事实定向测试覆盖原始数值与 `$binary64`、缺失阈值、恢复 MA 分支歧义。
- 23 日只读观察构建：310 条，V3.3 为 273 条；`validity=UNKNOWN` 310 条，符合后续多日窗口和事实供给未闭合的能力边界；写入数为 0。

## 验收与下一阶段

07B-02 的首日固化、独立查询、续日防漂移已完成。冻结事实缺失时维持 UNKNOWN；不使用 MA20、PHH20 等其他价格替代缺失的失效阈值。下一阶段 07B-03：predicate lookback planner。24 日正式连续运行仍由 07A 的独立验收门处理。


## 2026-09-24 accepted-day readback

The accepted 24 September Focus run contains 78 newly opened V3.3 episodes. Each has exactly four frozen invalidation fact rows (312 total); no new episode is missing a key. This confirms the freeze-on-entry path on a second accepted date. Read-only query evidence: `reports/focus_07b/FOCUS_07B_20260924_ACCEPTED_DATA_READBACK.json`. Later sessions must still confirm that continuation reads these exact frozen values without drift.

## Operand-gap audit closeout

The three `MISSING_OR_INVALID_OPERAND` observations in the 24 September readback were checked against their accepted first-source rows. All three are `TREND_CONTINUE` episodes, and none of those source rows supplies `trend_key_low`. Under the V2.1 thesis contract, an absent threshold must remain `UNKNOWN`; inferring a low or substituting another price would change the frozen thesis. The cases are closed as explained source gaps, with a separate versioned source-contract extension required before this predicate can become evaluable for such episodes. See `docs/audits/FOCUS_V33_MISSING_INVALIDATION_OPERANDS_20260924.md`.
