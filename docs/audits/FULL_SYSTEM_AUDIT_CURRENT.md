# 全系统代码审计当前入口

当前修复与续审：**R3 / 2026-10-11 / AUDIT_INCOMPLETE**；执行基线 `239fb9b545ac25305af02a645a77d82246cbb71a`。

- [修复报告](full_system_repair_r3_20261011_239fb9b5/REPAIR_REPORT_R3.md)
- [有效问题视图（自动消费者入口）](full_system_repair_r3_20261011_239fb9b5/EFFECTIVE_AUDIT_ITEMS_R3.json)
- [本轮独立复审输入](full_system_repair_r3_20261011_239fb9b5/INDEPENDENT_REAUDIT_INPUT.md)
- [历史 R2 报告（字节保留）](full_system_audit_r2_20261011_58faf74e/V4_FULL_SYSTEM_CODE_AUDIT_CONTINUATION_REPORT_R2_20261011.md)

本轮审计范围为 **V4 / PostgreSQL-only**。旧版DuckDB混合回归不计入V4验收；FA-018调度SQLite、FA-019图表SQLite派生索引分别OPEN。

各批次工程结果见报告和独立 REPAIR_RESULT。正式PIT/H21/Cohort/FEP/Windows门未解除；提交和push不代签外部接受。

B3已完成245模块冻结清单、4,568用例的执行及独立夹具重跑；清单内回归未绿，合法全需求分母仍OPEN。详见本轮B3_V4_FULL_REGRESSION_RESULT.json。FA-020治理扫描性能独立OPEN。
