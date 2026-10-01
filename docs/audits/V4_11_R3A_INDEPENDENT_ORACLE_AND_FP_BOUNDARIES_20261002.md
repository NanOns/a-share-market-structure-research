# V4-11 R3A 独立算术与源类别复核｜2026-10-02

最终工程核验：`PASS_INDEPENDENT_ACCEPTED_SOURCE_ORACLE`。5,224 个 target entities、141,048 个 prior/target master-session slots 从 accepted parquet 与 dated RAW / ADJUSTED / IDENTITY / STATUS artifacts 重读一致；36 个数值、风险、信号与资格字段独立重算，最终 mismatch 为 0。独立核验不调用被测 producer、feature builder 或 classifier；calculation payload 仅为窗口引证，逐字段与 accepted source rows 对照。

AMR20 使用 target raw amount CNY / prior 20 master sessions mean，target 排除。LIQ20 使用同一 prior 20 的 median。CLV、MA、slope、returns、risk、reclaim、prior-high 等直接重算。V3 signal 的输入由 accepted source arrays 重构，原 101-session basis gate 保留；滚动均值使用原合同指定的 pandas 数值 primitive，未调用被测业务函数。RPS 以 exact accepted current / t-3 publication binding 重读，独立做 revision gates 和 fraction delta。

源资格复核中，11 个 target 无 RAW 行均有 accepted SUSPENDED 记录。55 个不足以从近 130 slots 证明 lifetime >=120 的实体重新打开全历史 accepted parquet：45 个真实 history <120，32 个 recent120 coverage <0.75，11 个 latest raw absent（原因可以重叠）。这些是原 normal-universe eligibility 条件的事实 FALSE；没有 missing fact cast to FALSE，没有 provider unavailable 推断，当前文件缺失未当成 provider 证据。

发现及归档：

- 首轮 R1 的 114,435 个历史 READY slots 坐标 Decimal 数值相等而表示不同（如零的 exponent）；初始 candidate 保留为 FAIL。主线使用 R2 append-only candidate 修正坐标等价判断。
- 初次独立 oracle 的 7 条严格 BOOL 差异已归档。因子 `statistics.mean` 使用 binary-float exact-sum / round-once，原 feature 使用 pandas rolling IEEE；独立 verifier 分别保留相应数值执行。
- 另 1 条 prior5 count 差异已归档：该冻结 projection 使用 left-to-right `sum / 20`，与 factor mean 的执行顺序不同，独立 oracle 保留这一区别。

历史 FAIL 与浮点边界诊断保留原 bytes，含理想 Decimal、binary-float exact sum、naive sum、原 accepted IEEE 因子和 rolling 数值。生产者输出、legacy 阈值、比较符均未因 oracle 调整；没有 epsilon 改写业务 TRUE/FALSE。

46 项定向测试通过，覆盖 positive / negative / boundary / missing、AMR target exclusion、mean/median 区别、CLV 0/1/zero denominator、MA/slope/returns、RPS exact t-3 与 wrong binding、master session gap、future / same-day feedback / missing fabrication 拒绝、no-symbol，以及源类别和 FP 执行回归。Synthetic vectors 明确仅为 oracle-only，未创建真实业务 TRUE。

证据入口：`reports/v4_11_r3a/INDEPENDENT_ORACLE_CLOSURE_R1.json`，绑定最终 oracle、46-test XML、全部历史 FAIL/诊断。测试及此工程核验均不授予外部接受，不推进主 Heads，不授权 V4-12 runtime；下一步仍由总调度卡控制 R3C，并在本批统一提交推送后 STOP 等独立外部验收。
