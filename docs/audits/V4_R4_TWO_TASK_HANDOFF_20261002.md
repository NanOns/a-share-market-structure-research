# V4 R4 两张任务卡交接｜2026-10-02

状态：两卡工程实现及必需回归完成，等待独立外部复验。不是外部接受，不创建正式 V4-11 Accepted Head。

依据：本轮四份原始 MD 已逐字节归档于 `docs/evidence/next_round_r4/`；R4 总调度卡为最高执行调度依据，R3 独立外审 R1 为复验依据。审计基线 `65774de20108beafaa15c0b557b4cd2ee58edb29`，clean tested source commit `fc4d204012bca642d1b0beed7f2f098d6efea86c`。最终提交仅追加验证回执与交接证据，不改变已测代码或业务产物。

## R4A

formal adjustment basis 已绑定接受的 V4-03 `price_basis + adjustment_source_revision`。qfq_mul/qfq_add 保留为系数证据，不作为 basis identity。9/24 对接受的 V4-03 5222 行、39 个 Stock Core 字段 exact parity PASS；数值、质量、UNKNOWN、窗口与 digest 差异均为零。真实同 basis 系数变化与不兼容/缺失 revision 反例已单独验证。先完成 parity 与 R4A seal，再执行 R4B。

9/29、9/30 真实 Target Facts 独立算术核验均 PASS；全部 129/130 源窗口共 1,352,887 个 source slots 独立重开比对，零差异。active producer contract 为 `config/v4_11_target_fact_producers_r4a_v4.json`；active repair seal 为 `reports/v4_11_r4a/R4A_SEALED_REPAIR_R4.json`。reason-only 修正与旧版本均保留，事实值及质量没有因减少 UNKNOWN 而调整。

## R4B

重新生成两日真实全市场 Target Facts → D0 → D2 → Event。9/30 共 5224 行：D0 TRUE/FALSE/UNKNOWN = 166/4671/387；Launch = 124/4872/228，Recovery = 63/4769/392，multi = 21。D2 FRESH/STALE = 3614/1610，eligibility TRUE/FALSE/UNKNOWN = 501/3113/1610。Event NEW_CONFIRMED/NONE/UNKNOWN/CONFIRMATION_INVALIDATED = 88/3498/1637/1。该 invalidation 来自已接受 V4-10 Core，不是 V4-12 执行。

所有 STALE 均有 required-fact UNKNOWN 归因；producer wiring missing 为零，错误系数 generic reasons 为零。完整窗口恢复遵循既有技术计算语义；MA60 未新增为 D2 required input。9/29 是 reconstructed left-censored prior，AS_RECORDED=false；事件不冒充 forward publication。当前/前日 freshness、UNKNOWN 安全及 same-day revision prior invariance 已读回验证。

## 验证与限制

Clean checkout `fc4d204012bca642d1b0beed7f2f098d6efea86c`：2043 passed，2 skipped，failures=0，errors=0。原必需回归族完整保留，新增 R4 回归纳入；无新增 deselection。PostgreSQL 001–027 在新建临时隔离集群执行，config/.env 读取被审计钩子禁止，未使用生产数据库。Stage/Data/其他受保护 heads 保持原字节或原先明确 pin 的字节表示证明。

全仓 `pytest --collect-only tests` 仍有两个审计基线已存在的阻断：M14 测试导入已移除的 `_commit_raw_and_batch`；M2 测试在导入时依赖未入库 publication heads，在 clean checkout 的空 ignored DuckDB 中索引失败。两者作为独立 audit items 登记，相关源码与基线相同；没有重建持久化接口、造 publication 或增加跳过项。本次不声称全仓所有测试 runtime PASS。

第一次 clean 预检发现本轮新增测试与 R3 同名，已重命名修复并保留失败日志；第二次 clean 为当前交付回执。早期 R4 admission 配置指向与过量重复 IO 的中止记录、reason-only 原始产物也作为 inactive evidence 保留。

## 边界和下一步

R3B、A02/A05/A04、A03/A06/A07/Owner/Reader 与 V4-10 已接受内容保持。`V4_STAGE_ACCEPTED_HEAD` KEEP V4_00_TO_V4_10_ACCEPTED，`V4_DATA_ACCEPTED_HEAD` KEEP 2026-09-30。没有 V4-11 Accepted Head，没有 V4-12 runtime；production/shadow/focus/global_mandatory_adoption 全部 false。阈值、优先级及 UNKNOWN 的正式语义保持。

统一提交并推送代码与 evidence 后 STOP，等待下一轮独立外部验收。待外部验收通过且新一轮授权后，才可考虑主 Stage promotion 或 V4-12 entry。
