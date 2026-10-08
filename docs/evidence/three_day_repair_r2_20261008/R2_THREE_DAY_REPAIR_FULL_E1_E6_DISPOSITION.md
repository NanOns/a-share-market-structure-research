# R2 三日数据与算法修复 E1–E6 阶段处置

- 阶段合同：`R2_DATA_ALGORITHM_REPAIR_V1`（按 `docs/upgrade/R2_DATA_ALGORITHM_REPAIR_EXECUTION_20261008.md`；当前结构连续任务另受 `docs/upgrade/R2_STRUCTURAL_FIELD_CONTINUATION_20261008.md` 约束）。
- 阶段结果：`SCOPED_OPERATIONAL_RELEASE_PASS / E1_E5_FULL_ACCEPTANCE_BLOCKED`。
- 目标日：2026-09-28、2026-09-29、2026-09-30；当前发布读域只落在接受目标日 2026-09-30。
- 本阶段 source/code/evidence commit：`7fe1ae009d4a0871011e3da19462b524da0e80be`；审计基础 HEAD：`d571b23aec1d93ea79f633fcf8a5ee644527b6f3`。
- Phase 0：沿用正式 `reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json` 的既有结果；本任务未启动 scanner。
- TDX：`D:/new_tdx` 仅只读；未写入、重命名或删除其中文件。

| E | 结果 | 本轮证据与数值 | 未解决边界 |
|---|---|---|---|
| E1 源事实闭环 | `NOT_VERIFIABLE`（分类子范围通过） | 563 差集复核：35 停牌无 bar、528（176/日）复权能力未证明；RAW 缺失 0，source-present-not-ingested 0；配置 `.day` 位于目标日之前而已验 ZIP 包可用。 | 9/28–9/29 有效成员日与 strict PIT 0/3 未证明；全源发现范围仅仓库与配置目录。|
| E2 Core→Profile→Structure | `FAIL` | 当前候选消费 5,213 股票；独立对照旧/新 snapshot 的 7 个关键结构字段均 0 known / 5,213 unknown。隔离 Core 不等于接受 Owner。 | Profile/Structure正式 binder 未物化；10 只真实正反边界与时间泄漏重算未运行。|
| E3 板块 | `NOT_VERIFIABLE`（当日事实子范围通过） | 378/378 当前 RS、breadth、MA20 width 可用；独立公式对照 2,646/2,646 PASS；修复了 MA20 adapter 的价格基准精确匹配门。 | Rotation 378/378 unknown；Base/Seed与历史成员生命周期未恢复；9/29不回填。|
| E4 个股数值/结构 | `FAIL` | 真实消费保留当前 Core/Profile 数值；个股图表 QFQ 可见，单股显示明确根因状态。 | 结构谓词、支撑、相对状态缺 Owner，不能据基础数值推断突破/回踩等状态。|
| E5 Focus/Forward | `NOT_VERIFIABLE` | Focus 有 297/469 observations 与 6 个仿射复核样本；Forward 117 enrollment / 585 plans 全部 PENDING，due=0。 | 仓库隔离向量 65/65 通过（退出/重入、失效、停牌/缺价、T0冻结、due缺价、幂等与迟到修订）；完整 episode/path/reentry 异常矩阵仍未全覆盖，真实 due=0 不是结算通过。|
| E6 运营发布 | `PASS`（受限范围） | 真实 joint CAS：`5204…`→`8d342…`；7类 API 同一 context token READY；IAB 首页/板块详情/个股详情/来源与诊断通过。健康失败的隔离精确回滚、坏日期/哈希/基准和并发拒绝均已验证。 | `full_product_release=false`；股票结构、板块轮动与 strict PIT债务仍显示为未知；生产成功后未执行实际反向切回。|

## 当前生产接受范围

已激活的 9/30 scoped successor manifest：`data/v4/research_snapshots/3a3f5d9074b646189ccfd830c15e7161/manifest.json`（SHA-256 `d9d052fdf912c0975f5bfca0cd1067fe4a47fde99d804ce356c266da960e72f3`）。联合发布范围为 stocks_daily、sectors_current_facts、market_current、focus_read_corrected、forward_read、diagnostics、compare_corrected；它不是全产品通过，也不改变历史 PIT 许可。

## 独立审计项

金额 A 等跨阶段审计债务继续由 `docs/evidence/three_day_repair_r1_20261008/CROSS_CUTTING_AUDIT_ITEMS.json` 独立跟踪，不并入本阶段 E1–E6 接受。保留原始 R1 外审结论，不覆盖。

## 下一阶段

按最新结构连续合同，对接受快照完成完整 5,213 股票实源结构核验和关系展示核验；先补齐版本化结构 Owner/谓词与 positive/negative/boundary/leakage vectors，再重跑独立 Oracle。9/28–29成员有效日期缺权威时继续 `NOT_VERIFIABLE`。不因本次 push 自动推进该门。
