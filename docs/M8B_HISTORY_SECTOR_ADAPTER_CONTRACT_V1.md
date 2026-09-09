# M8B-01 历史基础板块适配器合同 v1

`HISTORICAL_SECTOR_ADAPTER_V1_0` 是独立于正式日发布 runner 的历史回算包装层。
它按固定顺序执行：技术因子 → 同日同范围截面 RS/RPS → `sector_base` → 既有板块
scanner 纯函数。它只返回内存中的派生 DataFrame，不写 `publication_heads`、
`observations` 或 `outcomes`。

- 技术输入必须按 `security_id + trade_date` 唯一；同一交易日的 RS 以纳入范围内的
  有限收益中位数为基准，RPS 使用平均并列名次除以当日有效 N，N<100 返回 NULL。
- 成员输入必须带逐日 `trade_date`、`sector_id`、`security_id`。技术日期若没有对应的
  成员日期即拒绝；不把截止日成员快照复制到更早日期。
- 历史适配器默认 `history_basis=RECONSTRUCTED`，输出同时保留
  `membership_basis`、`membership_snapshot_id`、语义版本、质量和覆盖字段。当前快照
  口径用于历史日期时明确拒绝。
- 基础板块行保留旧 scanner 需要的字段和 NULL；调用旧 scanner 后重新覆盖成员口径为
  `RECONSTRUCTED`，避免旧正式 scanner 的当前快照标签污染历史结果。
- `009_sector_base_history` 仅登记结构；本步骤不向正式生产库应用迁移，不创建历史发布
  绑定。失败输入不会通过去除旧 `snapshot_guard` 来“补齐”结果。
