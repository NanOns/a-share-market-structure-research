# FEP 候选状态合同订正 R2

修复P2：errors非空不再返回 CANONICAL_AUTHORITY_CANDIDATE_VERIFIED。contract_id升级 FEP_CANONICAL_AUTHORITY_READ_R2。

- db_facts_status=DB_FACTS_READ_VERIFIED 仅表示只读 repeatable-read 查询完整结束。
- status=CANDIDATE_INCOMPLETE 表示源、身份、授权窗口、预测、成熟标签或schema有缺口；candidate_complete=false。
- 仅余独立approval/engineering CAS问题时 status=FORMAL_APPROVAL_MISSING，仍 candidate_complete=false。
- 缺valid_from/expires_at明确 GRANT_VALIDITY_WINDOW_SOURCE_MISSING，过期 GRANT_TIME_INVALID；不修改业务模型或写accepted Head。
- production_authorized恒false；完整typed工程预测可保留 READY_ENGINEERING_EVIDENCE_ONLY，但不能供生产显示/排序授权。

实际隔离PostgreSQL31项零失败/跳过。首次未登记cluster被隔离保护拒绝（1通过、30 setup错误），登记G盘exact cluster manifest后31通过；保护始终启用，数据库已停止。D_REAL_SQL_SUCCESS_FAILURE_READBACK.json保存完整工程正向与expired/missing prediction真实SQL负向返回；这些是合成行的真实查询，不是正式生产源。

真实消费者前置与实际缺源详见 D_EXACT_TRUSTED_PRODUCTION_REQUIREMENTS.json。当前28765仍加载R1；本修复为离线DB候选入口R2，未声称该进程加载新代码。下一阶段：独立可信原件/能力审批及受控加载审查；生产预测保持BLOCKED。
