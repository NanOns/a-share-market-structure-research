# 全系统代码审计当前入口

R3 B2 续行增量：[UI/传输/Shadow证据](r4_r3_integration_20261011/B2_UI_TRANSPORT_SHADOW_INCREMENT_R3.md)，提交 `b476e8de43388390892b6b01db8c4f56f42d4a02` 已推送；[Drive完整字节读回](r4_r3_integration_20261011/DRIVE_B2_INCREMENT_BYTE_READBACK_R3.json) SHA一致。48个合法局部节点通过，六路传输前后完整内容SHA一致，桌面/390浏览器及4项数据数量对照已补。旧基线失败保留，完整合法回归/全部消费者/56类及全语义门仍OPEN。Series全1,309,832行PG对照是另一个未提交增量，联合发布仍在修复，不构成总验收。

R3 续行工程检查点：[进度与未关闭门](r4_r3_integration_20261011/ENGINEERING_PROGRESS.md) / [Drive 检查点读回](r4_r3_integration_20261011/DRIVE_CHECKPOINT_READBACK.json)。实现提交 `2a7c6cb4d41822a1bed83e9abcfab11bba4deb90`，有界13项真实调度/控制与36项复权测试；合法全分母、所有消费者和全语义仍OPEN，完整基线重跑尚未绿。该检查点不替代下方R2与历史裁决。

最新用户指定复审 R2 隔离整改：[本轮报告](r4_external_repair_r2_20261011/REPAIR_REPORT.md) / [独立问题与继承处置](r4_external_repair_r2_20261011/R2_DISPOSITION.json)。206 项本轮能力重跑通过；四表/Series/Journal/Shadow 新内容身份、联合 PG CAS、五日期跨行业默认 HTTP/独立 oracle 已补证。完整合法分母、全真实消费者、容量、正式角色和生产准入继续 OPEN。总状态 EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE。

最新隔离工程：[R4 外审修复第二批](r4_external_repair_batch2_20261011/REPAIR_REPORT.md) / [有效阶段处置](r4_external_repair_batch2_20261011/BATCH2_DISPOSITION.json)。60项能力回归通过；正常authority产品HTTP、全字段差异溯源和旧出版物四表PG无损迁移已补证。正式外部验收/生产切换及全V4分母仍OPEN。

当前外审修复首批：[修复回执](r4_external_repair_20261011/REPAIR_REPORT.md) / [独立问题台账](r4_external_repair_20261011/AUDIT_ITEMS.json)。定向10/10通过；完整验收仍阻断。

当前 R4：EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE。隔离工程基线 fbd23a6ba08d0948fe7ad421d1765fe363648522；尚未完成总任务或集成在役目标分支。

- [R4 工程报告](full_system_r4_pg_only_20261011_fbd23a6b/REPAIR_REPORT_R4.md)
- [R4 有效问题视图](full_system_r4_pg_only_20261011_fbd23a6b/EFFECTIVE_AUDIT_ITEMS_R4.json)
- [R4 源版本限定](full_system_r4_pg_only_20261011_fbd23a6b/R4_SOURCE_BASELINE_QUALIFICATION.json)
- [历史 R3 报告](full_system_repair_r3_20261011_239fb9b5/REPAIR_REPORT_R3.md)
- [历史 R3 问题视图](full_system_repair_r3_20261011_239fb9b5/EFFECTIVE_AUDIT_ITEMS_R3.json)

范围 V4 / PostgreSQL-only；合法测试分母仍 OPEN，局部 PASS 不代替全量回归。历史原件保留，正式 PIT/H21/Cohort/FEP/Windows 与外部验收门禁未解除。
