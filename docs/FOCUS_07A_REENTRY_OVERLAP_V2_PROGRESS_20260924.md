# FOCUS-07A Reentry Episode Overlap V2

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 13、14、15、38、39 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6、7、10 节；`docs/audits/FOCUS_REENTRY_OVERLAP_AUDIT_20260924.md`。 |
| stage_contract | 来源实体 coverage 仍按 `FocusKey` 去重；episode observation/follow-up/outcome 按 `(FocusKey, episode_id)` 保持独立。旧 episode 继续持有其退出后观察和 outcome，重入创建独立新 episode。当前投影每个来源实体仅呈现一行，并优先呈现活动 episode。 |
| implementation | `FOCUS_EPISODE_TRACKING_PLAN_V2` 将 pending follow-up 与 due outcome 精确到 episode。上下文解析按 episode identity 读取对应的首日来源；旧 episode 不继承同日重入来源行。库存股票路径按每个 episode 的起点建立；板块观察按 episode 使用冻结篮子和 strength。核心闭包按 episode 校验 observation 集；写入器可在一个交易日为同一实体保存多条 episode observation；predecessor reader 与 current projection 各自采用单一实体展示规则。 |
| evidence | 合成计划验证旧 `POST_EXIT` 与新 `REENTERED` 同时存在、实体 coverage 仍只有 1 个 key、股票路径各用各自起点；板块测试验证旧/新 episode 使用各自冻结篮子；上下文测试验证旧 episode 继续读首日来源而新 episode 读当天来源；writer 回滚演练验证同实体两条 observation 入批、旧 episode 不重复写 transition。按 V2 合同对 2026-09-24 执行只读 assembler 重建：117 来源行、397 实体 key、397 episode decisions、397 observations、closure 完整；V2 manifest `bf7b5ae3cdc1e260b765c0a8eab8fcdcd064d9e23c2676120a010e5abb02577e`，closure `0f6deffaa08b52e66870970a93d7b2993778f16a3c5b981a4bb6599def751f97`。当前 accepted 日没有重入重叠样本，所以额外 episode observations 为 0。Focus 定向回归测试：144 passed（按 `pytest -q tests/upgrade_v3 -k focus`）；新增 runner/transaction/plan/context 定向回归 24 passed；compileall 与 `git diff --check` 通过。未对数据库执行写入。 |
| acceptance_result | `CONTRACT_AND_SYNTHETIC_TRANSACTION_PASS / REAL_FORWARD_PENDING`。合同和实现收尾；真实 accepted 重入日读回以及退出、重入、再次退出的真实样本仍需市场自然出现。 |
| next_stage | 下一 accepted session 执行 versioned manifest preflight、rollback rehearsal、apply/readback；实际重入发生后验收旧、新 episode observations、projection 选择和独立 anchors/outcomes。 |

本次只修改代码、测试和审计/阶段记录；未改 accepted Focus run/head、数据库记录、V3/V3.3 来源或 TDX 输入。
