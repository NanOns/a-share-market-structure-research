# Focus SOURCE_MODEL_BOUNDARY writer/readback 审计项

| 字段 | 记录 |
|---|---|
| audit_item | `FOCUS_SOURCE_MODEL_BOUNDARY_WRITER_READBACK_E2E` |
| scope | 同一 source family/entity 相邻交易日 selection contract 改变时，核对 episode、首日来源事实、今日来源行、SOURCE_MODEL segment、observation、accepted head 与 settlement 可见性。 |
| applicable_upgrade | `FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md`；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 7、9 节。 |
| stage_contract | `FOCUS_SOURCE_MODEL_SEGMENTS_V2` 与 `FOCUS_SOURCE_MODEL_BOUNDARY_WRITER_READBACK_E2E_V1`。同一 episode 保留首日合同；selection family 边界追加 segment；后续日按当前 segment 继续；revision 行按 source run 保持不可变。 |
| evidence | 临时 PostgreSQL receipt `docs/evidence/FOCUS_SOURCE_MODEL_BOUNDARY_E2E_20260924.json`，所有 12 个 checks PASS：D2 boundary、下一日 persistent continuation、revision r1/r2/r3、旧 revision anchor 隐藏、旧 episode 延续、顺序 replay、乱序阻止及数据库 readback。V2 segment migration rehearsal 与 apply 均成功，397/397 既有 segment 获得 selection contract family。 |
| acceptance_result | `CLOSED / TEMPORARY_POSTGRES_WRITER_READBACK_E2E_PASS`。该项是可合成验收的 writer/schema gap；不代表真实 Forward gate 已通过。 |
| next_stage | 按 07A 真实 Forward 日历继续观察；保留每日 SOURCE_MODEL segment 和 head readback。 |

隔离 E2E 数据库由脚本创建并在完成后删除；receipt 不包含生产数据明细。
