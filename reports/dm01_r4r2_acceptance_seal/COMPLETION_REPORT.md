# DM01 R4R2 Acceptance Head 封印执行记录

机器接受头已按正式外部审计创建，真实 accepted_envelope()、审计原文与全部扩展字节绑定通过。仅更新用户明确授权的旧测试缺席断言；运行时源码、算法、依赖配置、Data/Stage Head 和权限均未改动。

专项结果：R4 25、R4R1 15、R4R2 18 全部通过；封印检查 2 通过、1 被治理门拦截。完整范围：2136 通过、45 失败、3 跳过、0 错误。保留 43 项历史债务，另外 2 个失败节点因授权测试修正触发 HISTORICAL_PROTECTED_BYTES_CHANGED；未宣称全绿或最终通过。

阻塞原因：validate_r25_preflight.py::protected 将上述历史测试路径锁定到旧字节；该脚本自身又被外部审计接受的 runtime_dependencies_v4 精确绑定。治理门与本轮授权修正冲突，修复会涉及禁止修改的运行时和审计绑定，已单独登记。原始失败与修正后回归证据均保留。

未来会话桥接仍 WAIT_MARKET_CLOSE、零源请求、无桥接产物。真实 R25/Shadow 未启动，无真实 DB 和计数增加。

状态：BLOCKED_GOVERNANCE_PROTECTION_CONFLICT，未签发 PASS_LOCAL_READY_FOR_FINAL_READBACK，未设为活动恢复入口。交付授权单点修改和阻塞证据；STOP_WAIT / final readback。推送不构成该治理冲突的验收。
