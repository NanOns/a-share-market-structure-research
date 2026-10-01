# A05 Legacy Valid Member Exact Producer 候选收口

执行本轮总调度卡与 A05 R2 卡；基线 `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`。状态 `A05_EXACT_PRODUCER_RECOVERED_CANDIDATE`，批次状态 `CANDIDATE_READY_FOR_EXTERNAL_REAUDIT`；没有外部验收 PASS。

全仓 archaeology 找到了真正旧 producer：`src/sector/phase2.py::prepare`，版本 `sector-factor-contract-v1.1-correctness`。任务契约记录其实际 source SHA、完整 exact assignment AST、AST digest、regex 参数、排除 missing states、BOOLEAN 单位、CURRENT_SNAPSHOT_ONLY 时间角色。恢复结果见 `config/a05_legacy_valid_member_exact_v1.json`、`src/sector/legacy_valid_member_a05_v1.py`；没有使用有限 RET、tradable、上市天数或近似公式替代原判定。

旧规则严格是 identity 格式合法、missing_state 非空、且不在 FILE_MISSING/DELISTED_OR_INACTIVE。SUSPENDED 和 NOT_LISTED_YET 仍可为 true；未知但非空的字符串仍可为 true。这些是原 legacy 语义，不能解读成新的交易可用性或 PIT 保证。缺失 state 是旧规则 false；没有外部接受的新 observation 始终标 CANDIDATE，不能进入正式 legacy consumer。

真实 9/24 当日 6,188 个 input observations、75,367 个会员记录与 541 个旧 sector 的 total/valid/invalid/coverage/sector_valid/invalid_reason 全量重算零差异。旧 sector/membership 原 parquet、Phase1/2 原 receipts 与 24 份真实 golden CSV 已原字节归档；CSV 中 3,553 个实际 valid_member 输出逐值匹配。其余 valid/invalid/missing/suspended/new listing/regex 边界和 NaN 向量直接对照旧 pandas AST。

879MB 原 normalized 文件没有另复制一份；保留其原 SHA provenance 和当前实际观测的冻结 state 行。独立 checkout 可完整重读新冻结 state observations、原 sector/membership bytes、旧 receipt 输出 SHA 与全部真实 golden CSV。历史可比性仍限于 CURRENT_TDX_MEMBERSHIP 当前快照，不伪造 historical PIT。

最终核心证据：`reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json`。独立消费者图为 `reports/audits/A05_CURRENT_CONSUMER_GRAPH_R1.json`：semantic adapter、accepted input placeholder、legacy B2 和 materializer 仍存在 legacy 依赖；native primitives、B0/B1 rotation、V4 native rules 和 Stock PREWATCH 不消费该旧 denominator。既有 V4-08 head 原字节保持不变。确切 producer 已找回，当前无需 NON_EQUIVALENT replacement 或 B2 retirement；正式新 observation binding 与 B2 capability 仍待独立外部接受，不能借此自动解除 Amount-A 或其他 B2 门禁。

验证命令与本轮共享独立重读同 A02 收口文档。clean checkout/No-Symbol 由 root 批次统一执行，下一步仅为独立外部审计。
