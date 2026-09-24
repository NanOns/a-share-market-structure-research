# FOCUS-00 身份、状态与路径合同阶段回执

> 阶段：`FOCUS-00`；合同基线：`DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1` 第 14–20 节；日期：2026-09-23。

| 字段 | 结果 |
|---|---|
| prior_phase_0 | `FULL_PASS_TDX_NATIVE`（既有 release seal） |
| migration_precondition | `FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED`；见 `POSTGRES_MIGRATION_INDEPENDENT_REACCEPTANCE_20260923.md` |
| stage_contract | `FOCUS_SOURCE_AUTHORITY_V1`、`FOCUS_EPISODE_ID_V2_1`、`FOCUS_EPISODE_LIFECYCLE_V2_1`、`FOCUS_MODEL_SEGMENT_V1`、`FOCUS_ANCHOR_CONTRACT_V1`、`FOCUS_INVALIDATION_AST_V1`、`FOCUS_PATH_STATE_V1`、`FOCUS_PATH_PRICE_BASIS_V1`、`FOCUS_ANCHOR_OUTCOME_V1`；revision/head 与 tracking union 以最终设计第 15、19 节为权威 |
| evidence | `src/focus_tracker/{contracts,lifecycle,predicates,price_path,states,outcomes}.py`、`tests/upgrade_v3/test_focus_00_contracts.py`；18 个反例通过，含冻结 normalized 系数对较晚调整的共同锚点消除；源码检视确认该包不读写 TDX、DuckDB、PG 或在线数据 |
| acceptance_result | `FULL_PASS / FOCUS_00_SEMANTIC_KERNEL`；仅通过纯算法和合同阶段，不代表 PG schema、真实来源接入、页面或正式发布完成 |
| next_stage | `FOCUS-01`：PostgreSQL Focus schema、约束/索引、迁移 ledger、备份恢复演练；随后 FOCUS-02 真实来源与事实物化 |

## 本阶段冻结的边界

- 每来源族能力必须显式给出；只有 COMPLETE 的空行集能造成退出。
- 不同来源族的同一股票是不同 episode；同日行情事实可复用。
- 同日 revision 在相同前一 accepted head 上重算，不推进一次额外交易会话。
- validity、membership、followup 和 path 独立；INVALIDATED 不制造 EXIT。
- 缺 actual BAR 不参加连续谓词、价格路径或观察结果。
- 价格路径以目标日共同 affine 锚点重算，结果期限按主交易日历固定。
- 退出后的观察池由所有未终结的必需 anchors 决定；完成后停止日计算，历史不删除。
- 源事实缺少冻结阈值时 AST 返回 UNKNOWN，不能由页面或实现代码补猜。

## 反例证据与剩余门

测试覆盖跨来源身份、两次升级、板块完整掉榜与来源失败日、退出重入、模型边界、场景切换与同日确定性、仍在榜但失效、先独立后获支持、推断缺口使连续谓词 UNKNOWN、共同复权锚点、固定 T+N、停牌/退市/缺口终态及完成门。编译检查通过。`FOCUS-01` 前已复核最终设计及迁移验收；本阶段没有触碰生产库或用户现有未提交文件。PG 表、真实 head、来源行和恢复演练仍须各自验收，不能以本次单元测试替代。
