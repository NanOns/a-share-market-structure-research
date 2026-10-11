# R1审计报告版本化勘误 R2

原包 `full_system_audit_r1_20261011_a2eadda` 字节保留；本勘误优先解释以下范围。

1. 原报告第89行及字段登记 CLV 公式 `(2C-H-L)/(H-L)` 错误。主合同第2767行、`src/v4/factors/core.py:238` 和实际R1 oracle 均为 `(C-L)/(H-L)`，0..1，H=L UNKNOWN。改正的是审计文字/登记，不是生产算法；原 executed numeric PASS 不因这项正文错误失效。
2. FA-012 的实际合同是 `config/a04_amount_a_go_forward_r3.json`、namespace/source-admission 配套；`config/amount_authority_audit_brief_v1.json` 并不存在，不再用它作证据位置。独立总审计条目仍OPEN。
3. named-symbol 的24命中不能统称审计脚本命中：含 `src/workbench_analysis/market_source_acquisition.py:233` 的 smoke fallback。其余逐上下文分类见 b3_symbol_triage。分类不免除现行政策，也不证明存在股票资格/评分特例。
4. 本轮发现7股票/16cell QFQ HALF_UP反例，之前8证券抽样不能代表全股复权无差异；R1数值PASS仅保持原抽样范围。
