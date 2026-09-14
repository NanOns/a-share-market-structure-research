# P12-01 基线冻结与阶段验收（2026-09-14）

阶段合同：`P12-01_BASELINE_V2`。本阶段只冻结输入、旧结果、字段覆盖、依赖和资源基线；未执行 P12-02 因子实现、扫描、生产重建或参数效果评价。

## 咨询版本与输入身份

执行前核对 `AGENTS.md`、`V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md` v2.1、对应审计修改说明、`ALGO_R1_CORRECTNESS_RECEIPT_20260914.md` 和 Phase 0 封存。各文件 SHA-256 及完整机器证据见 [P12-01 基线](../reports/p12_01/baseline_v2.json)。Phase 0 封存为 `FULL_PASS_TDX_NATIVE`，调整日线获准用于本地结构研究；这不是新算法效果验收。

目标交易日 `2026-09-14`；绑定 publication `m4-f787bac7863fa3409d45f75a8b7b5c30`、snapshot `m10-mainline-preview-4067dec5315150dc`、research run `research-59677a66206c4314b0b2b4b9e88046d0`、membership snapshot 与参数 hash 均在机器证据中逐字封存。`adjusted_daily.parquet` 当前 SHA-256 与该 run 的依赖 hash 相等。统计全程只读打开 DuckDB，未写 TDX 源或生产数据库。

## 冻结事实与漏斗边界

| 基线面 | 冻结结果 | 解释 |
|---|---:|---|
| 当日调整日线 / 实际 bar / 正常 universe | 6,182 / 5,553 / 5,458 | 三种分母不得混用 |
| 旧 candidate_daily | 1,045 | 旧合同候选，不能充当新四类的候选全集 |
| 全量 P05 股票状态 | 6,182 | SETUP 405、BREAKOUT 163、RECOVERY 87、TREND_BACKGROUND 1,113、STRUCTURE_BREAK 2,622；标签重叠 |
| P05 字段覆盖 | bias20 5,514；sigma20 5,512；rps5_delta3 5,453；liquidity20_amount 5,515 | 详细字段覆盖见机器证据；不能把缺值当零 |
| 板块状态 | 531；CURRENT 72；POTENTIAL 0 | `dq5_3`、`b_delta3`、`ma20_delta3` 均 0 个非空 |
| 既有 shortlist / LOO 原因 | CURRENT_FOCUS 20 / 20 条有 `LOO_COMMON_SUPPORT` | 只覆盖已截断预览；**全量 LOO 漏斗尚不存在**，不能据此关闭漏检或泄漏审计 |
| COMPLETE run 独立日期 | 2 | 多个同日 run 不当作连续历史或效果样本 |

固定反例以主方案 §18 的 25 项及主方案 SHA-256 冻结。本阶段登记它们作为 P12-02～P12-08 的验收输入，不宣称已执行新合同反例。资源基线：生产 DuckDB 261,894,144 B，调整日线 876,958,215 B，DuckDB 1.5.5；只读查询约 0.96 秒，完整文件 SHA 校验另行完成。`dependency_lock` 草案已绑定现有 run、参数和调整日线摘要；新合同源码及数值运行环境锁在 P12-02 定稿，不能用草案复用未来结果。效果最低报告门预登记为至少 20 个独立信号日、50 个独立 episode，并逐场景报告样本数；当前为 `EFFECT_PENDING`。

## 能力门与独立审计

接受结果：**`DEGRADED_PASS`（P12-01 基线冻结范围）**。Phase 0 和当前文件身份通过；缺口为历史成员 `UNAVAILABLE`、跨日派生三项变化全空、新四类全量资格/LOO尚未实现、完整依赖锁和效果样本尚未建立。它们不阻止下一阶段在已验证本地日线上的因子开发与单日反例验收，但不得放行 PIT 回放、提前轨道或新研究发布。

`AUD-HIST-01`、`AUD-AMOUNT-A-06`、`AUD-EFFECT-09`、`TR-AUD-LOO-01`、`TR-AUD-PRICE-TIME-02`、`TR-AUD-PUBLISH-03`、`TR-AUD-UNIVERSE-04` 及主方案 §20 其余专项继续独立跟踪，均未因本次基线关闭。下一阶段：`P12-02_FACTOR_V3_3`；进入前须再次咨询当时最新适用升级文档并核对本基线身份。
