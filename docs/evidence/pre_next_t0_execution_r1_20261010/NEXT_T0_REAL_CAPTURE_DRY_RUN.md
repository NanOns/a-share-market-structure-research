# 真实新日首获流隔离预演

本轮未请求 2026-10-12 行情，未改机器时钟，未触发实际未来日任务，也未重启 28765。测试中 synthetic 输入所在交易日期及 clock 仅用于合同实验，不输出生产授权。

`test_pre_next_t0_executor_chain.py` 从真实 `execute_sources` 开始，使用模拟 transport 原件，经真实 freeze/first_capture_source_candidate、derive_ready_sources、ready adapter 的 build/seal、review builder 和 SAME_DAY_SOURCE_SCOPE_RECONCILIATION_V1。外部 transport、SDK normalization、数值 replay/audit 与 Owner 准备输入明确标 synthetic；本演练证明控制链和数据形状，不宣称重新验收全市场数值内核。readback_url 未提供则以 QA_BLOCKED 收尾，无实际 CAS/Grant。

readiness 失败时先保存原字节与 request/receive/captured 时间，Owner 未运行；成功时继承旧 Head 临时预范围，随后按新 Owner 成员对账。跨日测试真实调用 capture/strict/reconcile，观察到新增 NEW/RENAMED、移除 OLD、B0→B1 板块成员变化及 SUSPENDED。缺新证券、成员 SHA 改变、未来窗口、来源内容冲突及中断后重试分别归于 SOURCE_GAPS 或精确拒绝。

原 `test_operational_successor_release_v1.py` 单独验证隔离 CAS 冲突及回滚，绝不在本机实际 Head 做冲突写。Source 后到和旧日冒充由 source_capture/bootstrap/strict 与 first_observed 反例验证。未到真实日只准备采集手册，不以演练 PASS 替代实际 first-observed。

运行手册：服务已有 DailyJobs 后台调度，first_check=18:35（北京时间），重试 19:05、19:35、20:05、20:35、21:05、22:05。到真实交易日先通过合法日历及实时时钟门，读取当时 BaoStock/TDX/成员原字节，检查 requested_at ≤ received_at ≤ captured_at、target 日期及独立 first_available；缺 request time 明示缺源，不能写成 15:00 已知。初次 capture 的 scope=PRELIMINARY_PREVIOUS_HEAD_SCOPE；新 Lifecycle/身份/membership Owner seal 后再 same-day reconcile。

新增身份、停复牌、更名、成员新增删除都必须有当日范围原件与 Owner，不靠旧 Head 补齐。源失败只保存候选诊断；可用日更主流程保持其已有门和 last-good。候选发行/quarantine 无权改变运营或 strict Head。新版本内容另建 slot；同 revision 重试保留首冻字节，冲突拒绝覆盖。每日真实原件与候选单独持久化后进行独立 Source Owner 入场；正式 Cohort 写入仍需精确日期/版本 Writer 合同。

验收：PASS_SCOPED_SYNTHETIC。实际下一 T0 首获为 PENDING，唯一实时阻断是 FUTURE_REAL_OBSERVATION_PENDING；Source/正式消费者的独立准入不阻止本轮工程。
