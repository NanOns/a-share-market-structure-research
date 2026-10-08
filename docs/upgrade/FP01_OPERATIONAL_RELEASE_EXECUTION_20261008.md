# FP-01 生产语义与版本化发布合同｜阶段执行报告｜2026-10-08

阶段合同：V4_OPERATIONAL_PRODUCTION_RELEASE_POLICY_V1。开始基线 a247a25d47a892042711efe2d3b2c3a0be9e52b4，与远端一致；最新用户提供总卡和 FP-01 为本轮权威，全部14卡按原始字节归档。已核对 AGENTS、REV2 §62A–§69/§81.2、页面缺口审计与最新生产切换文档。现有 Phase 0 回执 DEGRADED_PASS；未运行 scanner 或进入后续阶段。

## 本阶段结果

PASS_LOCAL_SCOPED_READY_FOR_INDEPENDENT_REVIEW。此结论只覆盖 FP-01 合同、来源盘点、准入实现和定向QA；不声称独立外审已通过，不宣称 FULL_PRODUCT，也不宣称所有领域已经投产。

新 config/v4_operational_production_release_policy_v1.json 将运行准入、历史验收/长期样本证明、数据质量分为三个独立维度。旧 production_permission=false、20会话Shadow、Forward成熟门和原收据完整保留；新运营发布走真实输入/产物/生产代码/合同的精确绑定、独立QA、依赖范围、CAS和回滚收据。样本不足不再是全局前端阻塞；真实身份/来源/复权/PIT/字段质量缺陷仍影响对应范围。自动交易、杠杆和TDX写入继续禁止。

src/v4/operational_release.py 已实际实现准入及不可变蓝绿发布目录 runtime/operational_release_v1，支持并发串行CAS、后交换回查、失败恢复、精确前版本回滚和旧日期继续显示。只在该新项目受控目录写发布指针，不改历史 accepted heads、Focus路由或旧HTTP默认入口。config/v4_production_runtime_authority_v2.json 是版本化的新研究运营注册权威；完整HTTP切换仍按 FP14 执行。

## 盘点与真实来源

producer_inventory.json 覆盖 V4-03…22、A02…A13、FEP E1…E5、M14、Focus、Market Regime、轮动和Forward，共42个范围；1126个代码声明包括helper，不当作1126个真实已投产算法。按明确owner绑定盘点输入/产物/代码/历史工程QA/长期债务/API/页面；保留薄amendment的传递精确引用，完整来源图以 producer_inventory_full.json.gz 归档，不按mtime猜最新权威。元数据图有明确深度/文档上限，原owner原始绑定是完整复核入口；不是全量运行所有生产器。

本轮独立文件oracle全量扫描 V4-13 已保留真实高级画像5224条，核对owner产物、当时封存生产代码、活动合同族、数据head、日期/截止时点、身份、来源和字段质量。新运营注册准入 V4_13_PROFILE_ADVANCED；这是已有真实投影的合法研究消费，不是新造行情、重新运行所有算法或将历史engineering flag改为PASS。20782个KNOWN、62688个UNKNOWN、5224个DEGRADED、114个NOT_APPLICABLE保持原值；knowledge_lineage=RECONSTRUCTED_CORRECTED，未声称AS_RECORDED或真实历史PIT收益证明。5224条 sector_context_state 缺直接reason文本，独立列 AUD-FP01-FIELD-REASON-GAPS；来源身份仍保留，不变成KNOWN。

未接入新域的矩阵运行状态指新域发布适配/QA未就绪，不是“所有旧算法未实现”。这些域的未评估质量是null及明确NOT_ASSESSED标识，不能从缺QA推断来源不存在。具体已有产物待接入、真实来源/工程缺口、合同-only运行缺失分别进入 TARGETED_REPAIR_BACKLOG.json；FEP的fixture/reconstruction/真实观察通道不得混为生产样本，M14热榜不采集或持久化raw/row/batch/history。

## 验收证据

- 最终定向回归：123 passed，0 failed/error，见 REGRESSION.json、regression.txt。覆盖新准入反例及既有Phase0、V4-19/20、current reader和daily refresh；不冒称全仓回归。
- REAL_RELEASE_ROLLBACK.json：使用真实保留画像的运营注册发布，陈旧CAS拒绝、注入发布后回查失败恢复、green发布和精确rollback均PASS；旧服务指针未修改。
- PROTECTED_READBACK.json：入口冻结合同、heads、历史证据逐字节一致。TDX前后24493文件、5242354968字节聚合SHA完全一致。
- OPERATIONAL_PUBLISH_RECEIPT.json、OPERATIONAL_RELEASE.json、QA_V4_13_PROFILE_ADVANCED_*.json：来源绑定和准入收据。独立oracle源代码及QA收据使用内容寻址存档，避免后续QA文件更新损坏前版本证据。
- 真实浏览器兼容截图 browser_compatibility.png / AX：旧V4页面及最后日期仍可访问；Shadow入口保留、真实样本缺失仍如实显示。当前只连接Codex内置浏览器/MCP Apps，无Edge控制连接；本证据只覆盖FP-01兼容性，FP13真实Edge六页验收未执行。

实施过程的早期测试断言预期不一致已修正；E临时根缺失导致的隔离插件启动错误已修复。准入oracle修改期间一次回查按预期拒绝变更后的校验器字节，最终改为内容寻址校验器与不可变QA收据后重新发布并通过完整定向验收。这些中间尝试不作为最终PASS证据，最终有界发布源和日志以上述收据为准。

## 版本迁移与复跑

旧V4只读切换/Shadow诊断/Focus历史/Forward cohort保留；不恢复V3数据库。新运营注册权威在FP02读取真实产物、FP03统一API三维状态、FP04六入口框架之后接入，FP08独立验证Focus路由/事务，FP14完成完整生产服务原子切换。当前服务仍显示旧七区块是本轮未执行页面任务的事实，不能把FP01准入当成页面修复完成。

复跑只读校验与测试：python -B scripts/verify_fp01_real_admission.py；python -B scripts/finalize_fp01.py。后者在E受控临时目录运行123项并对新的运营注册做失败注入/回滚，恢复原指针。build_fp01_inventory.py / run_fp01_admission.py prepare/publish 是发布构建工具，只在明确的新阶段版本中使用；冻结后的policy v1、runtime authority v2和本轮不可变证据不得原位改写，未来用successor版本。

下一阶段：FP-02 / FP-03 / FP-04，等待各卡独立调度；本轮未执行。独立外审与长期统计验证分别记录，Git推送不代表外部接受。
