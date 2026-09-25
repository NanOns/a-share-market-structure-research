# V4-00A-PG-RECOVERY-01 独立审计状态更新（2026-09-25）

| Field | Record |
|---|---|
| audit_id | `V4-00A-PG-RECOVERY-01` |
| status | `OPEN` |
| scope | 当前 PostgreSQL production instance 在隔离位置恢复至可查询状态、核验数据库/必需 artifact 身份及逻辑摘要，且确认源库与 accepted heads 未改变。 |
| evidence | V4-00A基线回执：`workbench.backup_catalog`与`legacy.backup_catalog`均为0条；无匹配当前PG实例/时间点的backup及restore/readback回执。2026-09-21 restore report SHA-256 `5803f0df5fbcf874c7877c0181eb6d6260661f2b55b7a40bd61af05b38ecd576`只恢复DuckDB冻结副本。2026-09-22 catalog repository/service reports的恢复对象为临时schema-only DuckDB probe，PG rehearsal source明确没有替代当前PG物理/逻辑备份。 |
| impact | 不得宣称V4 Phase 0具备恢复就绪；V4 scanner授权为NONE。既有V3生产heads保持不变。 |
| independent_from | V4-00H阶段 `DEGRADED_PASS`、TDX overlap、V4算法/Forward门、旧Phase0 seal。 |

## 关闭条件

1. 在受控维护窗口依照当前正式PG备份合同生成绑定实例、时间点、版本、数据库/依赖artifact的不可变备份；记录大小和SHA-256，确认路径位于TDX根以外。
2. 恢复到隔离目标而不是生产实例，完成数据库连接、schema/version、关键表逻辑摘要、publication/Focus heads和被引用artifact回读核验。
3. 对照恢复前冻结的源实例/head identity，证明演练未更改生产数据或heads；保留可复现命令、失败回执、时长和恢复资源预算。
4. 由独立验收更新状态。DuckDB副本恢复或PG backup catalog CRUD不能替代该证据。

本阶段没有合适PG备份/恢复工具与当前实例专用备份artifact，因此未执行不安全的自制导出或生产库操作；保持 `OPEN`。