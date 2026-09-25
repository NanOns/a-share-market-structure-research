# V4-00A 基线冻结回执（2026-09-25）

| 字段 | 记录 |
|---|---|
| stage | `V4-00A / BASELINE_FREEZE` |
| stage_contract | V4.2.2 REV2 §78：冻结当前 HEAD、数据库备份/恢复回执、accepted/Focus head、旧输出和继承审计；本阶段只读，不要求未来算法 AST。 |
| consulted_upgrade | 桌面正式 REV2 文档 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`；REV2 QA `963d574d0e1c1fb654a6c64cf157ed1efd54dcf4f6b32c321a877bcc2b7bd269`（references/fences PASS，implementation NOT_VERIFIED）；修订差分 SHA-256 `1943f828b20742d3fd7bc516f813e48b0bcd43086a3fce9c1f11f19198c6a859`；复审 `docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md` SHA-256 `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`。 |
| repo_identity | 分支 `codex/v4-system-reform`；HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`。开始盘点时只有既存未跟踪的 `artifacts/`、`docs/audits/V4_2_1_CONTRACT_REAUDIT_20260925.md`、`docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md`；均未改动。 |
| execution_boundary | 仅执行只读文件盘点及 PostgreSQL `BEGIN READ ONLY` 查询；未运行 scanner、数据生成、下载、迁移、数据库写入或 TDX 访问。 |

## 基线证据

- **生产发布与旧输出：** `reports/current/CURRENT_RELEASE.json` SHA-256 `3c6fef7cbf3e0e2fa2dba6ebd0fcfe7e31b1f57b9086ccbd89d496beb804ccf1`；当前生产 `daily-production-v1.2`，cutoff `2026-09-24`，release/run `c3bd3117fc5e41109cee21f5a7299137`，revision 1，`production_ready=true`。既有边界：当前 membership 非 PIT，未审计本地状态证据时 trade status 为 unknown。该旧 release 仅作为迁移前输出身份冻结，不等于 V4 算法认可。
- **实时 PostgreSQL accepted head：** 只读查询得到 `workbench.publication_heads` 最新日期 `2026-09-24`，publication `m4-4c7e20b9b986cc6e193df851b764adce`；前一日为 `m4-51729396603ef27a36e4b0390302766d`。数据库标识 `market_research`，连接到 primary。
- **实时 Focus head：** `workbench.focus_trade_date_heads` 最新日期 `2026-09-24`，authority `FOCUS_SOURCE_AUTHORITY_V1`，run `focus-run-2a6378107492da723111cc78394a1248`，revision 1，predecessor `focus-run-f8ba1c4915d1c330506d9bc8954b0a2d`，lineage `VALID`；前一日 run 为该 predecessor。与 `docs/FOCUS_07A_CONTINUATION_PRE24_GATE_20260924.md` 的正式提交/回读相符。该 Focus 阶段总体仍为 `DEGRADED_PASS`、真实持续观察未完成。
- **Phase 0 既有封存：** `reports/phase0_2c/PHASE0_2C_RELEASE_SEAL.json` SHA-256 `d14050590dd5fae0be424e2d60c4968acbfc757b1bd9b38c1c6f8d99d09b8639`，记录 `FULL_PASS_TDX_NATIVE`、`phase0_closed=true`、TDX source unchanged。它是 V0.3/旧生产扫描链的封存，不代替 V4-00H；V4.2.2 §78 将本轮 Phase 0 最终能力回执安排在 V4-00H。故本阶段明确不放行 V4 scanner。
- **备份/恢复证据边界：** 当前 PostgreSQL `workbench.backup_catalog` 与 `legacy.backup_catalog` 均为 0 行。存在的 `runtime/postgres_migration/20260922/restore_20260921_report.json` SHA-256 `5803f0df5fbcf874c7877c0181eb6d6260661f2b55b7a40bd61af05b38ecd576`，证明的是 2026-09-21 DuckDB 冻结副本的 `latest-publication-pg-sync` 恢复演练，不能证明当前 PG 主库已备份并恢复。2026-09-22 PG backup catalog/service 演练为 `DEGRADED_PASS`，属服务/目录演练，不是当前生产库恢复回执。
- **Phase 0 / 升级门：** 历史 Phase 0 有 FULL_PASS 封存；V4 Phase 0 尚未完成 V4-00B–00H。复审要求先处理合同冲突；基线盘点可继续，但当前 REV2 仍为 `IMPLEMENTATION_NOT_VERIFIED`，合同复审总判定 `CONTRACT_INCOMPLETE`。

## 继承审计与独立跟踪

1. `docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md` 中 V422-B01–B10 保持 OPEN；其中 B01、B03 为 P0，阻断其影响的正式能力。REV2 文档 QA 不构成算法实现或独立审计关闭证据。
2. `AUD-AMOUNT-A-06` 保持 OPEN；Amount A 的 provisional 值/质量/合同及正式消费权限需独立裁定，不由本阶段或其他能力的 PASS 关闭。
3. PostgreSQL 全库身份/摘要审计 `PGM-IA-02` 保持 OPEN。此次实时确认了当前 publication/Focus heads，但没有完成所有表的逻辑摘要与 active artifact 引用核对。
4. 新增独立审计项 `V4-00A-PG-RECOVERY-01`：范围为当前 PostgreSQL 生产库可恢复性；证据为 PG backup catalog 0 行、当前主库无匹配备份/恢复回执；历史 DuckDB 副本演练不可替代。接受条件：建立绑定当前 PG 实例/时间点/备份身份的备份，并在隔离位置完成恢复和摘要/readback 核验；保留原库不变。状态 `OPEN`，独立于阶段门跟踪。

## 阶段接受与下一步

**接受结果：`DEGRADED_PASS / BASELINE_IDENTITIES_FROZEN_RECOVERY_EVIDENCE_OPEN`。** 代码基线、旧 release、当前 publication/Focus heads、Phase 0 历史封存及开放审计已记录；当前 PG 可恢复性和全库逻辑摘要仍缺证据，不能宣称完整基线冻结。该降级只说明 V4-00A 的基线证据范围，不授权 scanner 或 V4 数据/状态发布。

**下一阶段：`V4-00B / SECURITY_LIFECYCLE_UNIVERSE_PIT`。** 执行前重新核对当时最新适用 REV2/修订及审计回执，冻结日期有效身份、knowledge-time、历史覆盖与不支持范围；V4-00H 前不启动 scanner。`V4-00A-PG-RECOVERY-01` 与 `PGM-IA-02` 并行独立跟踪。
# Repair addendum (2026-09-25): `FULL_PASS / CLEAN_DATABASE_BASELINE_REBUILT`

The project PostgreSQL database was physically backed up at the user's explicit request, then only `market_research` was dropped and recreated with its original owner, encoding, and locale. Its former 244 project tables contained 5,308,402 rows, read from a disposable clone of the verified backup; none were restored. Hash-checked V4 migrations rebuilt the empty `v4`/`v4_meta` schema. See `docs/audits/V4_00A_DATABASE_RESET_AUDIT_20260925.md` and `reports/v4_phase0/V4_DATABASE_RESET_RECEIPT.json`. Historical database rows are not a V4 migration input.
