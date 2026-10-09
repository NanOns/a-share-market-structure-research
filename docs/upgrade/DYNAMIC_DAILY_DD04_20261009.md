# DD04 持久调度与事务发布

合同依据：V4-DYNAMIC-DAILY-R1.1 的 DD04，及 DD03 后继合同。Phase 0 保持 FULL_PASS；本阶段不增加 scanner。

已实现 SQLite WAL/FULL 持久 Job/Day/Event、默认 AUTO ON、官方日历全缺口顺序执行、时间门与退避、启动恢复、幂等与跨进程 worker 锁、取消安全边界、只重试失败日。本轮用户指令绑定只读策略，不复用旧一次性签收。

发布采用单日连续 successor、预期前驱 SHA CAS、精确前驱归档、六接口真实同 token HTTP 读回和失败回滚。事务 WAL 在 CAS 后进程崩溃时回滚精确前驱；COMMITTED 重启保持成功 Head。

证据：事务故障注入四例；队列测试十四例（含 1/2/5/10/20 日模拟源断档、实际 SQLite 重启与取消）；Windows 自启动注册读回与正式端口 28765 后台 worker 存活。系统任务为当前用户登录后运行，不冒充登录前系统服务；本轮未执行 Windows 重启。

阶段验收：后台队列与故障恢复 ENGINEERING_PASS；真实新增日期 CAS 待当天源完整后验收。独立外审 NOT_GRANTED。下一阶段：18:35 自动执行真实 10/09 源与 Owner、CAS 读回，再完成 DD05/DD07 的实际 UI 与完整归档。
