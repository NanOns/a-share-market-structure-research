# FOCUS-07B-01 Technical Identity 阶段记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 17、38、40 节；`docs/audits/TECHNICAL_RESULT_HASH_RECONCILIATION_20260923.md`。 |
| stage_contract | 旧 `TECHNICAL_RESULT_V3` 物理 hash 不变；`TECHNICAL_RESULT_CANONICAL_IDENTITY_V2` 先解析 JSON，再对全对象排序规范化计算新 hash。迁移记录明确绑定原对象、旧/新 hash、行数、证据文件摘要、迁移原因、合同和接受时间。Focus reader 在旧 hash 不匹配时仅接受与全对象实时复算一致的已登记迁移；任何不符仍拒绝。 |
| evidence | 22 日原始 DuckDB 备份 SHA `793dae0682a79aaf7b21366baad39ab899a5b043e9cde06e14fdeb1e92650cac`；22 日两侧 6186 行 canonical hash 同为 `6127166c6e7c49590d2f8f2949e7ea76149e5533c544d1d3784addbdcb53c915`。23 日使用原生产者 JSON serializer 重建并精确重现登记 legacy hash，内容寻址证据 SHA `ce101e6869493fac53c324d63b92508e65539d0e446bb9d597d36cd35577de39`，canonical hash `6fcb56d22e01c628b2d082f7e5324043196c22fa36386a82d7fd661c2be5bca2`。DDL 与插入先完成回滚演练再提交；22、23 日 readback 分别得到 6186 行，23 日 6186 条当日 technical facts 可用。篡改迁移 hash 的临时事务被 reader 拒绝并回滚；旧结果对象及行未改。测试 `91 passed, 355 deselected`。收据见 `reports/focus_07b/FOCUS_07B_TECHNICAL_IDENTITY_RECEIPT.json`。 |
| acceptance_result | `DEGRADED_PASS / KNOWN_ACCEPTED_OBJECTS_RECONCILED`。22、23 日已知对象修复通过；未来新增技术对象尚无自动证据导出与版本化登记路径，仍按设计 fail closed，故 07B-01 长期生产闭环未宣告完成。23 日已接受的 Focus run 不重写。 |
| next_stage | 为后续 accepted publication 加入独立、可审计的 technical identity 登记步骤，再做 24 日对象的真实验证；随后进入 07B-02 冻结 V3.3 invalidation facts。 |

本阶段数据库新增一张迁移记录表和两条记录；未修改 `analysis_result_objects`、`technical_result_rows`、Focus 已接受 run/head 或 TDX 输入。23 日证据导出写在 `runtime/focus_evidence`，采用内容摘要命名与原子写入。

## 新对象自动登记路径（2026-09-24）

| 字段 | 记录 |
|---|---|
| stage_contract | PostgreSQL 同步 `FULL_PASS` 后，按精确 `trade_date` 与 `publication_id` 唯一解析已接受技术 snapshot。登记程序重建原生产者 JSON 表示并精确比对旧 hash，原子导出内容寻址证据，再以独立事务登记 V2 canonical hash。登记失败写入 Focus 阶段的 `technical_identity`，不重标已完成的 P12/PG sync，技术 reader 仍拒绝无登记或不匹配对象。 |
| evidence | 新增 `scripts/register_focus_technical_identity.py`，扩展导出器核验 publication head、SUCCESS snapshot 和精确日期绑定。`focus_daily_stage.py` 在 Focus preflight 前独立运行登记并保存报告。23 日 accepted publication 重复 `--apply` 返回 `ACCEPTED`，原两条迁移记录不冲突；错误 publication 返回 `BLOCKED`。真实 23 日 post-sync 阶段再运行得到 `technical_identity=ACCEPTED`；同日 Focus preflight 因已有 head 返回 `REVISION_REQUIRED_WRITER_PENDING`，没有提交 Focus。测试覆盖登记先于预检、独立登记失败后 Focus preflight 仍执行；Focus 定向测试 `93 passed, 355 deselected`，编译与差异检查通过。 |
| acceptance_result | `DEGRADED_PASS / AUTO_REGISTRATION_CODE_READY`。已在 23 日真实 accepted 对象上验证幂等与错误 publication 拒绝；24 日新对象尚未生成，首次自动登记和日任务端到端证据待真实运行。 |
| next_stage | 24 日 PG 同步后核对 `focus_stage.technical_identity`、新对象迁移行及技术 reader 的全对象 readback；之后继续 07B-02。阶段 A 自动提交门仍按其独立验收条件关闭。 |


## 2026-09-24 accepted object verification

The new registration path was exercised against the exact accepted publication after PG sync. Rollback rehearsal returned `ROLLBACK_READY`; registration then committed as `ACCEPTED`. PostgreSQL readback through `read_accepted_technical` verified the complete 6,188-row object, all 6,188 same-day facts, the normalized artifact SHA, and exactly one immutable migration receipt. Canonical hash: `838e2e71418def33722d967c244b7f66f730892c2bc48644346d156860c3f5b5`; evidence SHA: `edfacdd0f2e38af1fa44fd980ec8df98483bb83480d2a8df137b7f2c7c988763`. Receipt: `reports/focus_07b/FOCUS_07B_TECHNICAL_IDENTITY_20260924.json`.

Acceptance advances to `DEGRADED_PASS / NEW_OBJECT_AUTO_REGISTRATION_AND_20260924_READBACK_PASS`. The accepted 24 September Focus run predates the later 07C observation V2 integration and remains unchanged. Automatic registration is verified for this object; future daily executions must continue to show the independent stage receipt.
