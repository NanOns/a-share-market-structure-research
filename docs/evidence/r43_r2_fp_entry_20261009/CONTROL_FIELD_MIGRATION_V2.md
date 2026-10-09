# 控制面 V2 迁移

`/api/operations/status` 使用 `V4_CONTROL_STATUS_NAMESPACES_V2`。`operational_context` 表示当前运营研究，`legacy_strict_pit_context` 表示旧严格 PIT；各自拥有 context_token、data_head_digest、as_of 和 capability_permissions。没有运营 Head 时 operational_context 为 null，当前展示回到实际旧 Head。

顶层 accepted_trade_date、last_accepted_trade_date、trade_date、data_head_digest、source_revision、data_updated_at、stage、namespace 统一属于当前读取权威。运营 source_revision 使用运营 publication token，表示该 Head 身份；不是旧 Git 修订。data_updated_at 为该冻结成员来源的 observed_at，不冒充今天价格发布或下一交易日采集完成。

顶层 production_permission 保留旧五域原值，明确 deprecated，范围为 LEGACY_STRICT_PIT_PROOF_ONLY。新消费者须读取两个命名空间的 capability_permissions；研究读取 true 不表示交易授权。兼容字段没有立即删除，废弃期限以所有已登记消费者迁移和独立审查完成为门，不虚构日期。

已扫描静态 research、r43-compat、旧 workbench/operations 客户端及 Python 消费路径。六入口头部使用 `/api/v4/context` 的实际 accepted_trade_date；旧运维页只消费 service_state 等运维字段。本轮没有将旧 permission=false 文本全局替换成 true。冻结 Head 绑定代码完整保留；修复服务位于 `v4_control_server_v2.py`，入口为原 run_workbench_service.py，适配器和 app.js 的独立摘要位于 config/v4_control_adapter_v2.json。

回滚：将服务进程入口恢复到冻结 `workbench_service.v4_server.serve_v4`；无须改任何数据 Head。恢复旧实现会恢复旧混合字段语义，不能因此称控制面修复完成。数据回滚与适配器回滚是独立操作。
