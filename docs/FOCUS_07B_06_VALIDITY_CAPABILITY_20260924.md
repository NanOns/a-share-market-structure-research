# 07B-06 Validity capability（2026-09-24）

## 阶段合同

依据修订方案第 22 节实施 `FOCUS_VALIDITY_CAPABILITY_V1`。`validity_state` 表示规则结果；`validity_capability` 表示规则是否适用及证据是否足够。V3 来源没有正式可执行失效规则，为 `NOT_APPLICABLE`；V3.3 结果未知为 `UNAVAILABLE`，结果已判定且 AST 证据完整为 `APPLICABLE`。

## 实施与证据

- `validity_capability.py` 输出三态、理由、规则合同和摘要；V3 不能声称已执行失效规则，V3.3 已知结果缺 AST 证据时失败关闭。
- `observation.py` 将该合同放入每条新观察的持久化证据，并校验它与 `VALID`、`INVALIDATED`、`UNKNOWN` 一致。V3.3 无当天来源时显式记录 `SOURCE_ROW_ABSENT`。
- 读取 API 在列表、板块成分及 episode 观察记录中返回能力字段；23 日既有 as-recorded 行不回写，故该字段为 null。独立审计见 `docs/audits/FOCUS_VALIDITY_UNKNOWN_AMBIGUITY_20260924.md`。
- Focus 测试 116 项通过。23 日已接受来源只读重建：310 条，`UNAVAILABLE` 273、`NOT_APPLICABLE` 37，validity 全为 UNKNOWN，写入 0，闭包摘要 `1d21000862a7e4198caa4cc5d7321cbb35262d3538744a6e1c439da2973cedb6`。读取 API PostgreSQL 临时表演练通过，持久化变化 0。

## 验收与下一阶段

07B-06 三态合同与新观察读写链路的代码及只读演练已完成。首个新正式交易日落库回查仍待 07A 连续日验收。下一阶段 07B-07：把停牌/缺口对价格路径和连续交易日谓词的影响分开处理。


## 2026-09-24 accepted-day readback

The new accepted day persisted distinct validity capabilities: V3.3 `APPLICABLE` with 27 `VALID` and 1 `INVALIDATED`; 80 V3.3 observations `UNAVAILABLE/UNKNOWN`; V3 sector (2) and V3 shortlist stock (7) are `NOT_APPLICABLE/UNKNOWN`. The 24-day data confirms the new observation contract is operational and does not claim V3 rule execution. Read-only database evidence: `reports/focus_07b/FOCUS_07B_20260924_ACCEPTED_DATA_READBACK.json`. Real subsequent-day persistence and due-outcome closure remain open.


Full 397-episode readback (including follow-up-only episodes): 28 V3.3 rows are evaluable (27 VALID, 1 INVALIDATED); 323 are UNKNOWN/UNAVAILABLE. The latter split into 243 EXITED episodes with SOURCE_ROW_ABSENT, 78 NEW episodes with insufficient history or a missing operand, and 2 PERSISTENT episodes with missing operands. Separate V3 rows (19 sectors, 27 stocks) remain UNKNOWN/NOT_APPLICABLE by contract. This confirms reasons are persisted; next accepted session must re-evaluate fresh and new episodes. Counts are in `reports/focus_07b/FOCUS_07B_20260924_ACCEPTED_DATA_READBACK.json`.
