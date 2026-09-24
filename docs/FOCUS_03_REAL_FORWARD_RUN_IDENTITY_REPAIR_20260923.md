# FOCUS REAL_FORWARD run 身份落库修复记录

> 状态：`FULL_PASS / EXACT_ROW_RECONCILED`。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 7、14、15、19 节；`FOCUS_03_FIRST_FORWARD_PUBLICATION_20260923.md`；`FOCUS_05_API_UI_PROGRESS_20260923.md`。 |
| stage_contract | `FOCUS_RUN_BASIS_RECONCILIATION_V1`；只把由 exact REAL_FORWARD manifest 生成的目标 run 上、与该 manifest 冲突的 `evaluation_basis` 列更正为 manifest 的原值。其他字段、episode、observation、anchor、head 不改；条件不匹配即回滚。 |
| evidence | 9/23 run `focus-run-f8ba1c4915d1c330506d9bc8954b0a2d` 来自 manifest `6828a567bc045df8d3e329d628ec24c61acb964e74847fe57f29170a75625464`，预检 basis=`REAL_FORWARD`，source digest=`1664f27800c0ebfc7ad836aee62ec90efdd2b9ec9ea6707c55eb82b3cf276fe1`，closure digest=`da138c462364988799cf9a4e555806158efc23869cf1066823393dc5ef1a6c56`，source rows=310。提交后只读 DB 查询显示相同 run/date/revision/source digest 已 ACTIVATED 且 head VALID，但 `focus_runs.evaluation_basis='HISTORICAL_RECONSTRUCTED'`。代码缺陷：writer 将该列硬编码成历史模式，无视 commit 模式；已修复 writer 绑定实际 basis。此身份矛盾禁止按历史数据显示本 run。 |
| acceptance_result | `FULL_PASS`。持 SERIALIZABLE 事务锁行前核对 run_id 由 `(manifest_sha256, closure_digest)` 确定、trade date/publication/revision/source digest、唯一有效 head 和 310 source items；单列从 `HISTORICAL_RECONSTRUCTED` 更正为 manifest 声明的 `REAL_FORWARD`，其余 run 内容未触碰。独立 run_id、source manifest、item count 只读再验通过。 |
| next_stage | 已核验线上默认及显式 9/23 API 返回 `AVAILABLE / REAL_FORWARD`，9/23 items total=310；下一步是独立技术 hash identity audit，不再更改此 run 的来源/观察事实。 |
