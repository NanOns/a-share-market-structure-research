# Source Authority / Cross-stage R2 阶段执行结果

本轮范围由用户“按照文档执行”的持续授权及“本轮也执行 A08/A09”的明确回复确定：A10、A11、A12、A08、A09、DM01 A01 R2。Master R2 已追加 12 项独立 OPEN audit；A02–A07 本轮未关闭。阶段执行后提交、push 代码和证据，push 不代表独立外部接受。

## 工程候选与验证

| 工作包 | 本轮工程结果 | 干净 detached 回归 | 证据 |
|---|---|---:|---|
| A10 | Source Authority Governance 候选；角色、可用性、错误分类与能力门，静态问题分别归属 audit | 1274 passed / 2 skipped | [阶段封存](../../reports/audits/A10_STAGE_CLOSURE_R1.json) |
| A11 | 完整 required-universe 身份字段权威矩阵，Result C；身份不重键，来源/历史语义不能证明的字段明确降级；官方 600018 锚点案例独立核对 | 1278 passed / 2 skipped | [阶段封存](../../reports/audits/A11_STAGE_CLOSURE_R1.json) |
| A12 | Path A 状态/ST producer 工程冻结，完整历史修复、独立逐行 oracle 与原算法下游真实回放 | 1299 passed / 2 skipped | [阶段封存](../../reports/audits/A12_STAGE_CLOSURE_R1.json) |
| A08 / N01 | repair freeze 的身份、authority、binding set、consumer、原 freeze 与 amended parent 自验证；接受版本回放字节/逻辑身份不变 | 1312 passed / 2 skipped | [阶段封存](../../reports/audits/A08_STAGE_CLOSURE_R1.json) |
| A09 / N02 | 新增 V4 PostgreSQL migration 025，publication/result 显式 consumer；旧 payload 保留、冲突拒绝、独立 SQL 精确回滚 | 1313 passed / 2 skipped | [阶段封存](../../reports/audits/A09_STAGE_CLOSURE_R1.json) |
| DM01 A01 R2 | runtime/date 解耦、实际历史补抓、精确 SDK 适配、required/supplemental preflight 和独立源核对完成；最终 all-nine 未执行 | 1333 passed / 2 skipped | [部分工程封存与阻断](../../reports/audits/A01_R2_PARTIAL_ENGINEERING_CLOSURE_R1.json) |

各回归均使用临时 PostgreSQL、无 config/.env 读取、无配置/生产数据库使用，No-Symbol PASS。仅沿用原已授权的一项 V4-09 acceptance assertion deselect；未新增 deselect。测试证明工程范围，不能替代 source semantics 或独立外部接受。

## 关键业务结果

A12 使用已接受 R7 去重后的 4,035,729 条 required membership；旧审计中的 4,036,121 是去重前口径，旧文件和旧统计保留。独立 oracle 直接核对已接受本地 bar 日期，4,026,611 条为 ACTUAL_TRADED，9118 条缺 bar 从 provider-derived SUSPENDED 改为 UNKNOWN。未恢复可接受的逐证券历史 ST/停复牌权威池；ST 和依赖它的 price-limit 明确 UNKNOWN，禁止当前 TNF 名称或 BaoStock 回填。

V4-03 的技术窗口和 market-regime price-pressure 确实受到影响，已真实重算。V4-04、V4-05 各回放 5222 条；算法/阈值 AST 保留，仅输入/输出绑定替换。Base Seed 的业务记录变化 36 条，PREWATCH 变化 33 条；V4-08 保留 9/30 目标与 9/28 Core 的日期缺口，实际回放证明其业务等价、来源身份重新绑定。详见 [完整级联与差异](../../reports/audits/A12_DOWNSTREAM_CASCADE_AND_FULL_BUSINESS_DIFF_R1.json)。这些均是候选，不是 amended accepted heads。

A08 接受版本的 5222 条回放与旧接受 artifact 字节、逻辑摘要完全一致。首次 clean regression 暴露旧 promotion validator 把“当前源码”与“过去接受源码”混为同一校验；原失败证据保留。新增 Git audited commit 锚定的原源码 archive，历史接受记录仍可精确验证，当前 runtime 明确 PENDING_INDEPENDENT_EXTERNAL_AUDIT。新 promotion 仍要求当前源码逐字节符合接受版本，不以 archive 放行新 runtime。

A09 在真实临时 PostgreSQL 中对 5222 条旧接受 payload 检验 14 个独立 SQL/迁移断言；迁移 001–024 字节保留。025 rollback 在存在非 legacy consumer 记录时拒绝丢失身份治理；事务撤销新 consumer 后，旧行、publication、逻辑 schema、migration ledger 均精确恢复。

## DM01 R2 尚未完成的前置门

实际发起 6 次有界 BaoStock 请求，包含登录、两日 smoke/target 的两种 query 和退出。9/30 smoke 与 9/28 target 独立；9/28 返回 5222 条 daily 和 16 条 factor，observed/received 为 10/1 实际时间。TDX 当日 5210 个实际 bar 的收盘价逐条吻合 BaoStock，12 个目标成员无本地 bar。provider presence/status/ST 仅作 cross-check，factor 为 audit fact，不是 canonical QFQ authority；不会证明 9/28 first-availability 或 AS_RECORDED。

SDK 0.9.3 的实际源代码/哈希绑定用于精确适配：daily 对象无 date 属性，以所有返回行日期证明目标日；factor SDK 截断末列名 `adjustFacto`，仅允许声明的 header alias。初次离线归一化同名文件导致 smoke nested binding 被 target 响应覆盖；原始捕获和诊断均保留，新增 V2_1 purpose-scoped immutable response 文件，独立 nested binding 校验通过，额外网络请求为零。当前有效报告是 [R2 归一化报告](../../reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R2.json)，R1 仅为未接受诊断历史。

A12 任务卡第 15 节要求最终 all-nine 绑定 A12 的 accepted owner contract。当前 A12 为 FROZEN_ENGINEERING_CANDIDATE_EXTERNAL_PENDING，formal_consumer_authorization=false，Global Head 没有接受该 owner。最终门实际返回 A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED。因此，未重写已通过的 R1 九个 adapters，未执行最终 R2 all-nine，也未宣称 DM01_A01_R2_REAL_TARGET_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT。

待独立外部接受 A12 owner，并单独执行正式 owner promotion/binding 后，继续 R2 runtime integration、真实 all-nine candidate、独立 period/price/special-phase 与 parent/source/calendar postcheck，以及真实 candidate retry/revision 检验。当前 source preflight 是单独工程范围，不替代上述未完成门。

## 接受与下一阶段

五项工程候选均等待独立外部 reaudit；DM01 最终候选被上述 owner 接受依赖阻断。12 项 audit 均 OPEN，external_acceptance=null。所有受保护 accepted heads、Global Stage/Data/Dev Head 与历史 R1 registry 保持原 SHA；TDX 输入未修改。Production、shadow、Focus 权限不变，不自行推进后续 gated stage。
