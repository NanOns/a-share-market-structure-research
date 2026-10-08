# R2 连续日更修复验收

验收：DEGRADED_PASS。原 R2 修复授权持续有效。本次关闭连续 journal 与候选日更编排的工程缺口，不能据此关闭全产品、严格历史 PIT 或剩余字段准入。

- 实源两日：2026-09-29 → 2026-09-30。Focus 297 → 469；实际锚点到期观察 0 → 297。未到期维持 PENDING。
- 9/30 原生 FP05、FP06、FP07、FP09、FP10 在新目录全部重建，通过接受日、输入 head、RAW 逐项核对后形成快照；修复 FP06 从在线旧日期取目标日的问题。
- 9/29 仅使用该日真实 RAW、states 与截止当日的价格路径；板块成员、板块生命周期等没有已接受历史源的领域明确降级，不倒灌 9/30 数据。因此两日全域 FULL_PASS 不成立。
- 41,696 次实际 RAW OHLC 比对，653,526 个字段单元检查；未发现未来业务日期或 literal UNKNOWN 被标为 KNOWN。62,556 个 corrected 单元保留晚于业务日的真实捕获时间，未伪称 AS_RECORDED。
- 同一不可变 UI 在 IAB 完成两日验收；跨日旧 token 被拒绝，刷新正常恢复；联合切换失败精确回滚，成功切换及重复 NOOP 均通过。104 项相关回归通过，正式 HTTP 六域 readback 通过。
- 正式入口 `python -B -m scripts.run_fp02_research_snapshot --daily`：无新完成会话时零请求 NOOP；新接受输入依次构建原生 owner、连续 Focus journal、候选快照，完成来源/RAW/时间边界 QA 后走联合 CAS 与 HTTP 健康回滚。代码和 UI 版本受 admission 哈希约束。
- 自动能力范围是受门禁约束的日更候选生成与联合发布；没有开通任意 Focus 写接口或交易能力。新算法或同日输入修订必须新命名空间；失败保留正式联合指针。
- 真实两日没有 Forward 到期任务。未来出现到期计划但没有已接受结算 owner 时明确阻断该次日更发布，不能把 Focus 观察冒充 Forward 结算；该缺口另列审计。
- 首获冻结保留真实 2026-10-08 时间。严格历史 PIT 仍不获准，缺失原始首获、历史模型/成员证据不能补造。

证据：CONTINUOUS_REPLAY、OWNER_CHAIN_STAGING、TWO_DATE_SOURCE_QA、TWO_DATE_JOINT_SWITCH、QA_FINAL、REGRESSION、RELEASE_FINAL、ADMITTED_DAILY_NOOP、POST_RELEASE。

下一阶段：独立审计剩余 110 字段的 source/UI/oracle/browser 准入，及 Forward 到期结算 owner 接入；不覆盖本阶段冻结证据。
