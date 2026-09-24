# Focus 重入与旧 episode 并存审计

| 字段 | 记录 |
|---|---|
| scope | 同一来源、同一实体退出后，旧 episode 的 follow-up/outcome 尚未完成，实体又重新入选时的双 episode 并存。独立于 07A-04 的来源实体 coverage 硬门。 |
| evidence | `tracking_union` 继续负责来源实体 coverage；旧 `PlannedDay.tracking_keys` 是 `FocusKey` 实体集合，单独不足以标识 episode。原 `plan_day` 只产生当前 lifecycle decision，导致重入时旧 episode 的 follow-up observation 被合并。 |
| risk | 旧退出 episode 的后续路径记录可能中断；旧 anchor 的到期结算仍可单独由 settlement 执行，但这不能替代逐日 observation。 |
| tracking_contract_decision | Observation、follow-up 和 outcome work item 以 `(FocusKey, episode_id)` 为身份；来源 coverage 仍按来源实体去重。accepted current projection 每个实体只显示一个 episode，优先显示当前活动 episode；所有 episode observations 和 anchors 独立保留。 |
| implementation | `FOCUS_EPISODE_TRACKING_PLAN_V2` 增加 episode-scoped tracking decisions；pending follow-up 与 due outcome 查询返回精确 episode refs；旧 episode 只使用其首日来源和冻结板块篮子，新重入 episode 使用当日 accepted 来源。同日写两条 episode observation，旧 follow-up 不虚构 membership transition。 predecessor reader 选择当前/最新 episode，projection 选活动 episode。 |
| acceptance_result | `CONTRACT_AND_SYNTHETIC_TRANSACTION_PASS / REAL_FORWARD_PENDING`。纯计划和上下文覆盖重入时旧、新 episode 双 observation identity、各自价格路径起点和来源上下文；writer 回滚/提交测试覆盖同一实体的双 observation。现有 accepted run/head 未回写。 |
| remaining_real_data_gate | 后续真实重入样本出现时，核对 accepted head 中旧 episode 继续观察、新 episode 正常开始、各自 outcome anchor 独立；退出—重入—再次退出的真实前瞻证据仍待自然市场样本。 |
| next_stage | 随下一 accepted session 运行 preflight / rollback / readback；重入现实样本出现后完成 forward gate。 |
