# V4-00H Capability / Performance / Rollback 阶段回执（2026-09-25）

| 字段 | 记录 |
|---|---|
| stage | `V4-00H / CAPABILITY_PERFORMANCE_ROLLBACK` |
| stage_contract | V4.2.2 REV2 §49A.2、§52A–52B、§74、§78、§79：冻结缺失/质量消费者策略与分能力切换/回滚合同；登记性能基线；完成当前 PG 可恢复性核对；签发 Phase 0 最终状态。 |
| consulted_upgrade | 最新 REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`；V4-00A receipt 及 V4-00G receipt 均重新核对。 |
| input_identity | HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`；cutover contract `CAPABILITY_CUTOVER_AND_ROLLBACK_V1`；performance record `V4_PERFORMANCE_BASELINE_V1`。 |
| execution_boundary | 只读核对已有回执/报告/源码；没有连接或写入生产 PG、没有生成/恢复数据库副本、没有触碰 TDX、未运行 pipeline/scanner/tests。策略、性能清单、阶段/审计报告原子写到项目目录。 |

## 能力门和回滚政策

新增 `config/v4_capability_cutover_policy_v1.json`（SHA-256 `b7bc8a7f67c813dfb5dfba76362c6eff7b145523cb8762fbf7c26458d4f3c8d2`）。生产权限必须逐 capability 同时满足 `SHADOW_STABLE_PASS`、对应 Forward Gate、`MIGRATION_REPLAY_PASS` 和依赖权限。20 个连续 accepted market sessions 及股票 Forward 的 5 个 signal dates/30 个不同 T5 OBSERVED 正向逻辑事件按 REV2 原样登记；样本修订不重复计数，历史重放不能代替实时会话。Sector、Rotation、Sector Risk 的阈值仍未赋值，因此这些 scope 保持 `SHADOW_ONLY`。共享源失败只降级依赖它的能力，不以全局 PASS 放宽门槛。

Forward 基准保持冻结 T0 权重，未知/缺失不 carry、不填 0、不删成员、不重权。`OBSERVED`、单独的 `MARKED_ESTIMATE`、`PARTIAL_UNVALUED`权限严格分开。停牌估值 coverage 与 quote-age 数值缺少代表样本证据，标为 unset；对应 marked-relative consumer 不可用，不能臆定 95% 等阈值。

失败回执必须列明 capability、日期、实体、字段、reason、证据 digest、前一 accepted head 与回滚动作。候选 head 只在 capability gate 通过后以冻结 predecessor 原子接受；失败保留旧 accepted publication/Focus head，仅隔离失败 scope。

## 性能和恢复证据

- §74 指标采集不完整。`reports/releases/20260917/54afdb3b850f4ab7b4b6811b45ca5a1c/PERFORMANCE_AUDIT.json` SHA-256 `708cb560eaf4a4585c9c87fa37711322b29ef5aa480bde9e14ec550a64488b5e`仅作为旧版部分参考：从首个 precheck 至报告最终时间约 `625.641047 s`；normalization/adjustment `501.870053 s`，市场/合成板块 `53.230459 s`，sector scanner `2.417261 s`，stock scanner `49.248446 s`，candidate priority `1.891849 s`，写出 `19,696,532` 行。该记录是旧 pipeline，且报告无 hard SLA；不能作为 V4 性能验收。
- 峰值 RAM、CPU、独立因子耗时、V4 sector、Radar、Focus、PostgreSQL write、API P50/P95、首页 payload、DB growth 和 V4 全流程耗时均无证据。未据此决定 partition/materialized view/cache。逐项登记见 `reports/v4_00h/performance_baseline_20260925.json`。
- V4-00A receipt记录当前 PostgreSQL backup catalog 0 行且无匹配当前 PG 主库的恢复回执。`restore_20260921_report.json` SHA-256 `5803f0df5fbcf874c7877c0181eb6d6260661f2b55b7a40bd61af05b38ecd576`恢复的是 DuckDB 冻结副本。
- `scripts/pg_backup_service_catalog_rehearsal.py`构造 schema-only DuckDB probe，再检查 PostgreSQL backup catalog round-trip 并复制该 probe；`pg_backup_service_catalog_rehearsal_report.json`中的`restore_drill=true`不代表当前 PG 数据/模式完整恢复。无 `pg_dump`/`pg_restore`可用命令，也无可接受的当前PG备份 artifact。本阶段因此不自制导出格式，不动生产服务，当前 PG recovery audit 继续 `OPEN`。

## 阶段接受与 Phase 0 最终状态

00H 合同与已得证据已封存，但强制恢复演练、V4 source package acceptance、benchmark 数值门和 V4 数据因子 readiness 均未通过。为遵守 §0/§78/§79，签发：

- **V4-00H stage：`DEGRADED_PASS / POLICY_FROZEN_REQUIRED_EVIDENCE_OPEN`**
- **V4 Phase 0 final：`BLOCKED / SCANNER_PRECONDITIONS_NOT_MET`**
- **scanner authorization：`NONE`**

受阻 scope：TDX 完整包 overlap/身份门未接受（V4-00D）；当前 PostgreSQL 可恢复性未证明（V4-00A recovery audit）；Canonical Daily/adjustment/algorithm readiness 尚未完成（V4-00B/00E/00G）。V3 accepted publication 和 Focus head 保持原样，不因 V4 Phase 0 阻断被修改。旧 `FULL_PASS_TDX_NATIVE` 属旧生产链，不替代本回执。

下一步：先闭合 `V4-00A-PG-RECOVERY-01` 与 `V4-00D-OVERLAP-GATE-01`，再按 §78 进入 V4-01；Phase 0 为 BLOCKED 期间不开展 V4 scanner。每次开新阶段仍需重读届时最新升级合同。
# Repair addendum (2026-09-25): `FULL_PASS / PHASE0_FINAL_GATE_REPAIRED`

`config/v4_phase0_final_gate_v1.json` removes V4-01/V4-02 implementation and scanner implementation from Phase 0 prerequisites. The final gate separately grants V4-01 entry and RAW bootstrap, keeps adjusted bootstrap scope-dependent, BaoStock optional, scanner `NOT_APPLICABLE_UNTIL_V4_05`, and production cutover deferred. The performance field contract is frozen in `config/v4_performance_measurement_contract_v1.json`; actual V4 runtime numbers are assigned to V4-01/02/03/05 and first full performance acceptance to V4-05. Empty-schema drop/rebuild and PostgreSQL fresh migration passed; data rollback remains a future shadow/production gate.
