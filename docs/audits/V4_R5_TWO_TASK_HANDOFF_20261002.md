# V4 R5 两卡交接｜2026-10-02

工程候选完成，STOP 等待独立外部验收。未创建正式 V4-11 Accepted Head。

四份本轮 MD 原字节归档于 docs/evidence/next_round_r5。外审基线 1dee36ae83fb63b6a7fe57e05ccb63bb1e0c5099，实际 clean tested source commit a8635c6802dc31e3c879207cd470bd63021e35ca。最终提交只追加回执与交接文档，已测代码和业务产物保持不变。

## R5A

严格按 R5A → 9/28 exact owner parity PASS → seal → R5B 执行。5222 行 V4-07 Seed / V4-09 PREWATCH 的业务、质量、waiting/UNKNOWN 原因均零差异。所有 target formal close_t_minus_1 与 ma20_t_minus_1 为 UNKNOWN(ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE)，没有扩展 t-1 capability。actual_bar 从 accepted dated status 三值投影；price identity 验证 canonical security、source symbol、board、target date、candidate publication 和 AS_RECORDED=false；research_universe 绑定 sealed target membership。

两日 owner publications 为 accepted=false、formal_consumer_enabled=false、RECONSTRUCTED_CORRECTED、AS_RECORDED=false。复用 unchanged accepted owner projection/evaluator/parameters；accepted RPS delta 保留原 contract identity，未为通过 PREWATCH provenance gate 改标签。独立 oracle 未调用 R5 adapter helper 生成 expected。14 项 owner 边界测试与 10 项 D2 authority/AST 测试通过。首次 oracle 假设所有 universe identity 有效的错误已修正，失败记录保留；产物已正确保留无效 identity 的 UNKNOWN。

## R5B

D2 只能从 R5A sealed owner publications、冻结 R4 D0、accepted dated status / RPS history、V4-10 reducer/provenance、R3B diagnostic seal、calendar identity 读取。serialized input 的 self-reported authority 不足以 admission；没有 raw/calculation fallback。独立 oracle 重开这些 publications，对两日 10447 行的 SEED/PREWATCH/core_price_damage/risk/delta3/suspended/CONFIRMED/scenario 共 83576 项实际输入核对 entity/date/contract/parameter/publication/output digest/quality/value，并独立验证 Core/profile 算术与 accepted pure owner 结果。

9/30 D0 冻结为 TRUE/FALSE/UNKNOWN=166/4671/387；Launch=124/4872/228，Recovery=63/4769/392，multi=21。D2 FRESH/STALE=868/4356，eligibility TRUE/FALSE/UNKNOWN=117/751/4356，maturity CONFIRMED/NONE/PREWATCH=135/4925/164。Event NEW_CONFIRMED/NONE/UNKNOWN=33/508/4683；quality KNOWN/UNKNOWN_CURRENT/UNKNOWN_PRIOR=541/4356/327。

9/29/30 分别有 5046/5047 行至少一个 reconstructed-known t-1 恢复为 accepted-UNKNOWN；Seed 值变化 365/459 行，Seed quality 1297/1404 行，PREWATCH 3953/3939 行，D2 business 3852/3893 行，9/30 Event 3244 行。数量改变不是通过标准；标准是 owner authority exact parity。全部 STALE 有 required UNKNOWN、精确 publication 与 source root cause，producer wiring missing / unsealed helper / generic coefficient gate / raw fallback 均零。

Reducer normalized business AST、rule order、threshold、parameter set exact；Event predicates 保持。UNKNOWN/stale prior 不当 FALSE、UNKNOWN current 不发确定 NEW_CONFIRMED、same-day revision 不伪造 predecessor。9/29 prior 为 reconstructed left-censored，AS_RECORDED=false，未冒充历史 forward evidence。scenario lineage 的新 metadata matrix 绑定真实 R4A parent path/sha256/contract_id/status 和 R3B seal，原 D0 bytes 未修改。

## Clean 验证及限制

Clean tested commit a8635c6802dc31e3c879207cd470bd63021e35ca：2067 passed，2 skipped，0 failures/errors。保留原必需回归族及唯一原有授权 deselection，无新增 deselection。no-symbol PASS；数据完整性、scoped heads、accepted history、R4/R5 DAG readback 和 protected heads 验证通过。新建隔离 PostgreSQL 执行 migrations 001–027；config/.env 读取被审计钩子禁止，未访问生产/configured database。

全仓 collection 的 M14 removed API import 和 M2 ignored local publication dependency 与外审基线源码相同，分类 PREEXISTING_NON_MAINLINE；没有声称修复，也不声称 full repository runtime PASS。独立 audit overlay R17 保留父 R16，最终工程状态由本交接和 clean 回执记录；external acceptance 仍 pending。

## 关闭边界

R4A adjustment basis/9/24 parity/两日 facts、D0 detector、V4-10、R3B、A02/A05/A04、A03/A06/A07/Owner/Reader 均 KEEP。V4_STAGE_ACCEPTED_HEAD KEEP V4_00_TO_V4_10_ACCEPTED；V4_DATA_ACCEPTED_HEAD KEEP 2026-09-30；无 V4-11 Accepted Head，无 V4-12 runtime；Production/Shadow/Focus/Global Mandatory Adoption 全 false。阈值和优先级不变。

统一 commit + push 后 STOP，等待独立外部复验。任何主 Stage promotion / V4-12 entry 需下一轮授权。
