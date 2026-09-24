# FOCUS-07A 第二日连续写入验收记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 7、14、15、38、39 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md`；`docs/FOCUS_07A_08_P12_INTEGRATION_PROGRESS_20260924.md`。 |
| stage_contract | NEXT_DAY writer 在单事务中重读 predecessor、来源身份和 run slot；延续及退出复用旧 episode，重入创建新 episode；写 observation、transition、anchor、projection 并通过最终核验后才提交。失败回滚不得留下新 head。 |
| source_acceptance | 24 日官方日线包由官方 `HSJDAY_SOFT_TIME=2026-09-24 15:57:21` 确认已更新。裸 ZIP URL 返回 23 日缓存对象；同一官方 HTTPS host/path 加唯一 query 后返回 24 日对象。下载包验证为 `2026-09-24`，M3 `FULL_PASS`，publication `m4-4c7e20b9b986cc6e193df851b764adce`。 |
| artifact_catalog_repair | M4 更新本地规范化行情后，PG catalog 仍引用 23 日旧 SHA，导致 Focus fail-closed。同步器现按 parquet cutoff 验证日期并登记当前 SHA；24 日 SHA `c6fc7b5455355390b0740b46e4bf24a2c5f458084cd6155478eae6c0be75c05a` 已注册，旧引用失效。 |
| rollback_evidence | 2026-09-24 manifest `262aa39416b9402704627091c0110e9979295cb0bc0c3b3b81c7af5bc3258e2d`；`publish_next_day(commit=False)` 返回 `ROLLBACK_READY`。117 source rows、397 tracking keys、397 observations；14 张 Focus 表事务前后计数完全一致，23 日 head/run 身份相同，24 日无遗留 run/head。 |
| apply_readback | 同一 manifest 正式提交，run `focus-run-2a6378107492da723111cc78394a1248` 为 `ACTIVATED`，head lineage `VALID`，predecessor 为 23 日 run `focus-run-f8ba1c4915d1c330506d9bc8954b0a2d`。23 日 head 保留；24 日 397 个 tracking key 均有唯一 observation；projection readback 397 行。transition：EXITED 280、NEW 87、PERSISTENT 30。 |
| outcome | 结算独立执行并返回 `READY`；310 个 due outcome 均为 `PENDING`，终态 0。此项作为真实前向结果待后续交易日到达后继续结算，不视为数据生成失败。24 日可评价 observation 中 READY 74、DATA_UNAVAILABLE 323，未知/不可用事实继续保留为显式状态。 |
| acceptance_result | `DEGRADED_PASS / REAL_NEXT_DAY_TRANSACTION_AND_CONTINUITY_ACCEPTED`。本次确认 23→24 连续写入、事务回滚和 projection；多日延续、到期 outcome 终态和数据可用性仍需后续阶段验收。 |
| next_stage | 继续阶段 C 的路径状态和未知值审计，并跟踪 310 个 outcome 到期结算；补足 DATA_UNAVAILABLE 的事实来源闭合。自动提交配置暂保持关闭，待多日和到期结果门通过后单独评估。 |

结果证据：`reports/upgrade_m3/FOCUS_20260924_CONTINUATION_ACCEPTANCE.json`。正式提交仅修改应用数据库与项目生成产物，没有写入任何 TDX 源目录。
