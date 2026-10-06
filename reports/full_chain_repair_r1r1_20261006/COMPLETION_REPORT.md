# P0-02 R1R1 修复候选完成报告

状态：CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。

本轮只修 activation_head 精确重启和队列 exact idempotency。重启通过只读事务读取唯一 singleton head，然后精确读取相应 activation fact，并校验 digest、authority_id、authority binding、external acceptance、grant、V5 dependency digest 和 storage identity。A/B 多 activation 历史合法保留，Head 指向哪项就选择哪项；不使用末项、日期或文件排序。

enqueue 在同一事务内 INSERT OR IGNORE 后逐字段核对 queue_key / evaluation_source_digest / due_kind / due_id，再从持久 due 和 enrollment 重新计算冻结身份。相同重试保持原行；冲突报 QUEUE_IDEMPOTENCY_CONFLICT 并回滚，校正 source digest 仍可生成新 evaluation revision。不新增或修改 migration。

定向验收 103 次通过，定向失败和跳过均为 0。包括 A01–A06、Q01–Q05，以及已有 queue、双连接 CAS、V3 rejection、V5 stop/restart、publication rollback、未知 due calendar extension、P0-01 capability 和 P1-03 DB integrity 测试。入口回归 43 次通过，1 项既有 R25 F12 历史夹具绑定债务与基线一致，单独审计跟踪；新增失败为 0。完整六项实现、合同、旧证据和迁移按入口字节核对保持不变。初始夹具失败保留原始 XML。

已实际复现旧 selector 在 Head=A 时错误选择 B，以及旧 enqueue silent ignore；候选实现均拒绝或精确选择。所有新执行数据来自隔离 ACTIVATION_SIMULATION，真实观察计数仍为 0。A08 保持 OPEN_EXTERNAL_REAUDIT；PURE_CORE_STOCK 阻断、R25 WAIT、First Real Shadow 未授权。生产、Focus、Default UI、FEP_PRODUCTION、MODEL_DISPLAY、PRIORITY_USE、CHAMPION、REAL_OOS 保持原状态；V4-16–22 formal Accepted Head 仍缺失。TDX 输入未写入，未执行 scanner。

下一步：独立定点验收 P0-02。代码提交和 push 不代表外审通过或开启运行权限。
