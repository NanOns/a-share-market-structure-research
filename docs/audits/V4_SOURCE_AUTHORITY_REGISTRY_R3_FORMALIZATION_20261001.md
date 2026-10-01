# Source Authority Registry R3 正式化

基线与独立外部审计 HEAD：`1655f84d1a47faca43c281d66e7704f2fa56b1b8`。原始审计与任务文档按字节归档并绑定 SHA256。

本阶段仅追加治理元数据。A08 N01、A09 N02 的 audit 状态为 ACCEPTED；A11 为 PASS_RESULT_C_WITH_CAPABILITY_DOWNGRADE。A08 的 historical validation scope 保持 ACCEPTED_PUBLICATION_HISTORY_ONLY，当前 runtime 未自动接受。A09 的 migration 025 为 accepted future schema hardening，未部署生产数据库。A11 保留全部 identity 业务字节、stable IDs 和 go-forward official identity authority；历史 legal lifecycle/type 仍未证明为 local-TDX authority，正式追加 HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED 能力限制，不重跑业务 stage。

A10、A12 继续 OPEN / external BLOCKED；DM01 继续 PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED，依赖 A10-R2 与 A12-R2 独立外部接受。没有 accepted owner 注册，也没有 business Accepted Head promotion。production、shadow、focus_cutover 全部 false。

验证 commit：`f268332`。全新 detached checkout，无 config/.env，使用临时 PostgreSQL，应用 001–025 migrations；1336 passed、2 skipped、1 个既有授权 deselect，没有新增 deselect。NoSymbol PASS。验证包括 5222 行 accepted PREWATCH 的压缩字节与逻辑 digest、A08 负向向量、A09 消费者 SQL 与精确回滚、A11 身份等价、R3 状态及历史保护绑定。

首次 clean entry 检查识别到两份历史 head 的主工作区 CRLF 与 Git LF 表示不同，测试尚未启动即停止。这是基线已有差异；未改 head。新增独立 OPEN 项 AUD-HISTORICAL-HEAD-GIT-BYTE-REPRESENTATION-R1，分别冻结工作区原始 SHA 与基线 Git SHA，并证明仅有换行差异。第二次全新 checkout 对 Git 基线字节进行严格检查，主工作区继续保留原始字节。

证据入口：reports/audits/R3_STAGE_ENTRY_R1.json、R3_CLEAN_CHECKOUT_R1.json、R3_ENGINEERING_GATES_R1.json、R3_STAGE_CLOSURE_R1.json 和 V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json。R1/R2 保持原字节。

最终工程状态：SOURCE_AUTHORITY_REGISTRY_R3_FORMALIZATION_CANDIDATE_READY_FOR_EXTERNAL_CONFIRMATION。下一项为本次已授权的 A10 R2 治理门修复；正式化本身仍等待外部确认。
