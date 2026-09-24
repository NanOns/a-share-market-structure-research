# Focus Tracker 07A / 07B / 07C 完成情况与线上验收说明

**核对日期：** 2026-09-24

**适用升级方案：** `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 以及 `docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md`
**当前整体状态：** 核心实现基本就绪，真实持续交易日验收仍进行中；不得标记为 Focus Tracker 完成，也不得放行自动提交或 07D。

## 验收摘要

| 阶段 | 完成情况 | 当前验收状态 | 未闭合的主要门 |
|---|---|---|---|
| 07A：每日构建与持续跟踪 | builder、daily runner、tracking union、context、路径与历史窗口、P12 接入、API 和显示合同等代码及静态门已实现；2026-09-23 → 2026-09-24 第二日 writer 已经回滚演练、正式提交并回读。 | `DEGRADED_PASS / REAL_NEXT_DAY_TRANSACTION_AND_CONTINUITY_ACCEPTED`；总阶段仍 `IN_PROGRESS`。 | 至少五个连续真实 accepted 交易日；退出后的持续 observation 与 EXIT+1/+3；真实重入多 episode 前向验收；310 个待结算 outcome 到期并产生终态。自动 apply 仍关闭。 |
| 07B：事实、失效与能力闭包 | 技术身份、首日冻结事实、predicate 窗口与逐日事实、路径能力、validity 三态及停牌/gap 路径均有版本化合同和实现。2026-09-24 technical identity、冻结事实、validity 新观察已有 accepted 数据回读。 | 代码与已知对象数据为 `DEGRADED_PASS`；真实复牌验收待样本。 | 后续新日对象继续产生并通过自动登记/全量回读；出现真实确认停牌及复牌行情后完成价格路径前向验收；部分缺 provider 路径仍明确为 `NOT_APPLICABLE`，不能解释为已实现。 |
| 07C：Path State V2 与 gap 语义 | UNKNOWN 优先级、`READY/PARTIAL/AMBIGUOUS/UNAVAILABLE` 解析、observation/API 接入和 session gap 合同均已实现。24 日 accepted publication 已做 397 条只读 V2 重建。 | `CONTRACT_AND_CODE_PASS / LIVE_V2_PUBLICATION_PENDING`。 | 24 日正式 observation 是旧 V1 运行；需要下一 accepted 交易日由新 assembler 写入并回读 V2 evidence、manifest、closure、head lineage 和 API。真实停牌复牌正样本仍待后续数据。 |

阶段 D 的入口由升级方案规定为等待 07A、07B 真实 Forward 验收。入口核对结果见 `docs/FOCUS_07D_ENTRY_GATE_20260924.md`；当前 07D 尚未开始。

## 07A 证据与实现范围

- 日构建、每日 preflight/apply 控制、多日 head 计划、tracking union、观察闭包、每日 context、path key、动态 history window 及 P12 post-sync stage 已加入实现和相应测试。
- 2026-09-24 的来源 publication 为 `m4-4c7e20b9b986cc6e193df851b764adce`。23 日 predecessor run 为 `focus-run-f8ba1c4915d1c330506d9bc8954b0a2d`；24 日接受 run 为 `focus-run-2a6378107492da723111cc78394a1248`。
- 24 日事务先以 `commit=False` 回滚演练，确认 14 张 Focus 表计数无变化且无 24 日残留 run/head，再正式提交。正式回读确认 predecessor lineage 有效、397/397 tracking key 均有唯一 observation、projection 397 行；transition 为 EXITED 280、NEW 87、PERSISTENT 30。
- 310 个 due outcomes 当日仍是 `PENDING`，因此不会被误记为结果验收通过。当前最少五日与退出生命周期门尚未通过。
- `config/focus_daily_pipeline_gate_v1.json` 将 `automatic_apply_enabled` 保持为 `false`，原因是多日 Forward 与到期 outcome 验收仍待完成。

详见 `docs/FOCUS_07A_01_DAILY_BUILDER_PROGRESS_20260924.md` 至 `docs/FOCUS_07A_09_TRACKING_CLOSURE_PROGRESS_20260924.md`、`docs/FOCUS_07A_CONTINUATION_PRE24_GATE_20260924.md` 和 `docs/FOCUS_07A_FORWARD_READINESS_20260924.md`。其中较早的 readiness 记录描述 24 日数据尚未发布；后续 `FOCUS_07A_CONTINUATION_PRE24_GATE_20260924.md` 记录了 24 日完成发布后的最新结果，应以该 continuation 记录为准。

## 07B 证据与实现范围

- Technical identity V2 在 2026-09-24 accepted object 上完成回滚演练、提交和全对象回读：6,188 行及 6,188 条当日 facts；canonical hash `838e2e71418def33722d967c244b7f66f730892c2bc48644346d156860c3f5b5`。未来每日登记路径仍需持续保留独立回执。
- 首日冻结的 V3.3 invalidation facts 已在 24 日接受 run 中验证：78 个新 episode，每个四个冻结事实键，共 312 条；缺失 source operand 保留 UNKNOWN，并由 `docs/audits/FOCUS_V33_MISSING_INVALIDATION_OPERANDS_20260924.md` 独立解释。
- Predicate requirements、facts-by-date、source capabilities、validity capability 均有版本合同；缺字段不会被推成 FALSE。无提供者的规则明确标记为 `NOT_APPLICABLE`，已存在值缺失则保留 `UNKNOWN/UNAVAILABLE`。
- 停牌路径只允许桥接两端实际行情之间且交易状态审计标记一致的 `CONFIRMED_SUSPENSION`；普通缺口不可桥接。全量标准化本地样本尚无 `CONFIRMED_SUSPENSION`，星帅尔 9 月 21～23 日的两个 `MISSING_DATA` 日仅构成失败关闭反例，不是复牌样本。

跨切面 provider gap、validity UNKNOWN 歧义、重入重叠、V3.3 source operand 缺失和停牌路径缺样本分别在 `docs/audits/` 下独立追踪，不以本阶段测试通过替代各自 acceptance。

## 07C 证据与实现范围

- V2 输出保留 `current_path_state` 原字段，新增解析状态、主状态候选、较低优先级确认事实、阻断 UNKNOWN 与逐谓词证据；V2 进入新 observation digest、core input closure 和 items API。旧 observation 不回填，API 以 null 表示无 V2 记录。
- Session gap contract 将主交易会话分为 `ACTUAL_BAR`、`SUSPENDED`、`DATA_GAP`、`SOURCE_UNAVAILABLE`。CONSECUTIVE 与 ROLLING 使用固定主日历窗口；路径只桥接证据一致的内部确认停牌。当前 AST 尚无 ROLLING 运算符，语义作为版本合同冻结。
- 对 2026-09-24 accepted publication 的新版 assembler 批次只读重建为 117 source rows、397 tracking keys、397 observations，closure 397/397；V2 分布为 READY 74、PARTIAL 243、UNAVAILABLE 80、AMBIGUOUS 0。manifest 为 `3ef5b6f4810968b6f9d68b88d0cdfd2c5ed17febf1830fe8f36ee6f6f68f5920`，写入 0，未改变 accepted head。
- 24 日已持久化 observation 是旧 V1 合同，故对它做只读 API 回查返回 V2 null。这证明兼容行为，不构成新版 observation 已正式落库的证据。

详细条款见 `docs/FOCUS_PATH_STATE_V2_DESIGN.md`、`docs/FOCUS_07C_01_UNKNOWN_PRIORITY_CONTRACT_20260924.md` 至 `docs/FOCUS_07C_05_SESSION_GAP_SEMANTICS_20260924.md` 和 `docs/FOCUS_07C_ALGORITHM_ACCEPTANCE.md`。

## 线上模型建议验收项目

1. 核对 daily writer 的 preflight、回滚和正式 apply 是否在单事务内绑定 predecessor、exact-date publication、tracking union、observation、projection 与 head 激活。
2. 核对同日 replay/revision、重入 episode 并存、退出后的 observation 以及 due outcome 的生命周期闭包；确认自动 apply 在真实总门通过前保持关闭。
3. 核对 technical identity、frozen invalidation facts、predicate requirements/facts-by-date、source capability 和 validity 三态的合同版本、digest 与 fail-closed 行为。
4. 核对 V2 path state 解析器三种最低反例：高优先级 UNKNOWN 保留低层 TRUE 但不给无保留主状态；高层 FALSE 允许低层 TRUE；高层 TRUE 优先于低层 TRUE。
5. 核对 session gap 状态冲突、连续谓词固定主日历、PATH 仅桥接有审计证据的内部停牌，以及真实 forward 样本缺失是否正确标为待验而非通过。
6. 将代码/合成/只读重建结果与真实 Forward 结果分开判定；当前 07A、07B、07C 的未闭合门不应被总括成 FULL_PASS。

## 本次提交范围与安全边界

本提交包含当前工作树中的 Focus 07A/07B/07C 代码、测试、contracts、progress/audit 文档和当日运行报告。`D:/new_tdx` 及其他 TDX 源目录是只读输入；本批更改和项目生成物均在仓库之外的 TDX 输入范围外。本说明描述截至 2026-09-24 的证据，不声称之后的交易日已运行。
