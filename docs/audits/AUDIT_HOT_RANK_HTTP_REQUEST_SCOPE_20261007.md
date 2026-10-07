# 热榜 HTTP 请求锁范围独立审计项

状态：CANDIDATE_FIXED_SUBJECT_TO_EXTERNAL_REVIEW。

范围：`make_handler().Handler.do_GET()` 对 request-time 热榜接口的锁范围，与 IA05 总门禁分别验收。

证据：原 `test_hot_rank_route_skips_request_scope` 在补齐无操作服务 stub 的现行 `status()` 接口后仍失败，实际进入了 `Api.request_scope()`。这会把提供方网络等待包入本地数据库请求范围，违背已有并发隔离合同。

修复：`/api/hot-rankings` 与 `/api/v3/hot-rankings` 在通过现有数据库独占构建检查后，直接执行路由处理。原数据库独占期间的 503 阻断不变；热榜实现中的短时本地名称读取仍由自己的数据库锁保护。

不恢复 capture、raw payload、batch 或历史快照持久化，不修改数据权限、Forward 数值语义、accepted heads 或生产授权。原锁范围、网络等待并发、断开客户端测试及最终全量回归作为实际验收证据，计数见 execution 目录。
