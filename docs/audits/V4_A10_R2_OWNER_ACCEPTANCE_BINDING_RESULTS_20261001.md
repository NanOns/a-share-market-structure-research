# A10 R2 Owner Acceptance Binding 执行结果

任务：WP-A10-R2-OWNER-ACCEPTANCE-BINDING。任务卡原始字节保存在 docs/evidence/source_authority；阶段入口为 reports/audits/A10_R2_STAGE_ENTRY_R1.json。业务基线为外部审计 HEAD 1655f84，阶段入口在 R3 正式化 seal ddeaee2 后冻结。

正式 CORE_AUTHORITY/FIELD_AUTHORITY 消费必须通过独立 governance head 的 registry path/SHA/version、registry 的 owner path/SHA、contract/field/consumer/date/mode、EXTERNALLY_ACCEPTED 和严格布尔 formal authorization 校验；owner 的已接受 role binding 必须与调用规则完整一致。任何不足返回 AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED，保留 Core 值。未声明的消费者不会取得 formal PASS，也不会阻断其它 capability。diagnostic 路径显式标记 PASS_DIAGNOSTIC_SCOPE，不授予 formal authority。

新增 SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V1 和独立 SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V1。真实 accepted owners = 0。新 R2 配置中的 formal owner 均待接受；TRADING_STATUS/ISST 明确 PENDING_EXTERNAL_ACCEPTANCE、enabled_for_formal_consumer=false。没有注册 A10 R1 或 A12 R1 为 accepted owner。原 R1 config 保留，旧 self-declared rule 同样会被当前通用门拒绝。正式 owner 注册必须等待 A10 R2 与 A12 R2 独立外部接受后的新任务。

DM01 私有防线复用相同的 accepted owner verifier，对两个字段采用同样的 target/mode/consumer/binding 校验。旧 global_head 参数仅为调用兼容保留，不能代替独立 authority head。原 R1 九适配器、其 contract 和 accepted builder registry 字节不变；本任务未执行 DM01 final all-nine，也未重新抓 BaoStock。缺失 supplemental 不影响本地 Core preflight，canonical adjustment 仍为 GBBQ。

107 项定向检查全部通过。新增 39 项 owner 检查涵盖 self declaration、外部接受缺失、formal false/错误类型、field/consumer/target/mode 越界、owner/registry 哈希错误、缺失 governance binding、role 修改、重复 owner、路径越界、supplemental 自升权、实际 A12 pending 拒绝、CORE 正向证明及 DM01 两门一致性。正向接受只使用 SYNTHETIC_FIXTURE_ONLY 测试目录，不向真实 registry 写 owner。原历史时间、availability、role 校验函数 AST 保持与审计基线一致。

新版治理 scanner 扫描 1195 个文件、保留 76 条独立 findings，新增 FIELD_AUTHORITY_WITHOUT_ACCEPTED_OWNER_BINDING、FORMAL_CONSUMER_USING_PENDING_OWNER、SUPPLEMENTAL_ROLE_PROMOTED_WITHOUT_ACCEPTED_OWNER；实际 status/ST 标记 PENDING_OWNER。扫描完成不代表所有 findings 已解决。

全新 detached checkout 测试 commit：fa07b6f。无 config/.env 及其读取；临时 PostgreSQL 应用 001–025 migrations，结束后清理。全局回归包含 A10、A12、DM01 R2、A08/A09 accepted replay smoke 和 R3 formalization 检查：1375 passed、2 skipped、1 个既有授权 deselect，没有新增 skip/deselect。NoSymbol PASS。XML 按原始字节提交，证据 SHA exact。

所有 business Accepted Heads 和 Registry R1/R2 的 Git blobs 与 1655f84 完全一致，主工作区原始 SHA 同样保持。R3 registry 与其已接受 sidecar/amendment 也未修改。先前独立登记的历史 CRLF/LF 表示问题仍 OPEN，分别检查原始工作区与 Git 基线；本阶段不修写任何业务 head。production、shadow、focus_cutover 全部 false。

证据：A10_R2_CLEAN_CHECKOUT_R1.json、A10_R2_OWNER_GATE_AND_PENDING_SOURCE_EVIDENCE_R1.json、A10_R2_ENGINEERING_GATES_R1.json、A10_R2_STAGE_CLOSURE_R1.json，以及 work_packages/WP-A10-R2-OWNER-ACCEPTANCE-BINDING/STATUS_R1.json。A10R2-G01–G13 为 PASS_ENGINEERING；G14 为 PENDING_INDEPENDENT_EXTERNAL_AUDIT。

最终状态：A10_R2_OWNER_ACCEPTANCE_BINDING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT。R3 中上一轮 A10/A12 外部 BLOCKED 裁决保持；本工程完成并不关闭该 audit。A12 real dated owner semantics 与 DM01 final all-nine 继续受独立验收门约束。
