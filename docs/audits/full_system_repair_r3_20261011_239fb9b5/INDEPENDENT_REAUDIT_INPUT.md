# 大A V4｜全系统代码审计续审 R2 独立复核及下一轮处置建议

> 文档版本：R1 / 2026-10-11  
> 性质：独立交叉复核报告 + 下一轮修复/审计任务说明；**不是生产验收许可**  
> 仓库：`NanOns/a-share-market-structure-research`  
> 审计目标分支：`codex/v4-fp14-r2-repair`  
> 本轮远端 HEAD：`239fb9b545ac25305af02a645a77d82246cbb71a`  
> 本轮 R2 实际审查的代码基线：`58faf74e0a108bff74dcafd4e2bbca854fc67cd3`（继承 R1 业务代码基线 `a2eadda9151b37b4cc463bd5c6a7e540be85741a`）  
> 总结论：**INDEPENDENT_RECHECK_PASS_WITH_CRITICAL_OPEN_ITEMS**（仅代表本次所核对的文件、逻辑和证据合理性；全系统正式总状态继续 `AUDIT_INCOMPLETE`，不签 `EXTERNAL_ACCEPTANCE_PASS`）

## 一、审计范围与证据边界

按用户约定，先对照 Drive 中现行的 V4 全系统审计主任务书、最新项目任务记录，再核对目标 Git 分支及 `docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md`。最新提交 `239fb9b` 的差异为审计目录新增文件、勘误、报告和入口索引，**没有业务源码修复**。所以 R2 中所有声称“发现缺陷但未修复”的条目应保持 OPEN。

本次独立读取并交叉核对：
- `docs/audits/full_system_audit_r2_20261011_58faf74e/V4_FULL_SYSTEM_CODE_AUDIT_CONTINUATION_REPORT_R2_20261011.md`
- `.../NEXT_REPAIR_EXECUTION_BATCHES_R2.md`、`.../ERRATA_R2.md`、`.../INDEPENDENT_AUDIT_ITEMS_R2.json`
- `.../b2_full_native_oracle.json`、`.../b2_rounding_counterexamples.json`、`.../b2_small_scope_vectors.json` 和 B3 部分收据
- `src/adjustment/tdx_adjustment.py`、`src/workbench_analysis/full_loo_v3_3.py`
- `src/workbench_service/core_product_bff_r1.py`、`src/workbench_analysis/fep_e2/registry.py`、`src/workbench_analysis/fep_e3/protocol.py`、`src/workbench_service/static/core-product-r1/replay.js`
- `src/workbench_analysis/market_source_acquisition.py`、`src/v4/factors/core.py`

**独立性限制**：本次没有连接用户 Windows 生产进程，没有取得本机的 551MB TDX ZIP、GBBQ 原件和完整 Owner 数据并从头执行上千万条复算，因此对于 R2 声称的全部历史数值计数，给的是**证据一致性与源码可解释性复核**，不是声称我本人独立重跑所有 1,297 万+比较。小数舍入反例使用独立 Decimal 局部复算确认。

## 二、总体裁决

| 子项 | Codex R2 结果 | 本次外部复核判断 | 是否全量关闭 |
|---|---|---|---|
| B1 全合同与 §87A | 29族→157行、156明确字段、1,413 scoped schema atoms、33 FEP 表 286列 | 确有范围内分解，仍非全需求与全版本 producer→consumer 语义验证 | **否** |
| B2 原生数据及 QFQ | 全原生比较通过，QFQ 发现7股16格错误 | 数值异常机制由实际源码独立支持；不能把大样本一致误认零错误 | **否；FA-016成立** |
| B2 LOO/状态 | 15正例、1失败 | 源码先调 `build_sector_current()` 后处理空 sector 分支，边界问题成立 | **否；FA-017成立（候选域）** |
| B3 环境与回归 | 151个不同测试PASS | 仅是经过恢复精确依赖和历史夹具后的选择性测试通过，不能等价全库回归全绿 | **范围内通过** |
| B4 Amount A | 5210金额和量、5201股票比率；378板块H21未知 | 计数加总和解释一致；正式历史 H21 / producer 授权尚未完成 | **仅表示/窗口范围可认可** |
| R1旧问题 | A1/A2/A3等仍OPEN | 逐条对照源码，确实未修复 | **否** |
| 正式 PIT、Cohort、FEP、Windows | 仍在相应数据/权限/现场门 | 未见能解除这些门的独立新证据 | **否** |

**正式总状态继续 `AUDIT_INCOMPLETE`**。未在本次可核范围发现必须宣布正在发生的 P0 线上事故，但不等于全系统零 P0。

## 三、最重要的新确认缺陷

### FA-016｜P2｜QFQ 精确舍入偏差，建议以数据正确性高优先处理

源文件 `src/adjustment/tdx_adjustment.py`：
- `build_affine_factors` 中临时 `localcontext(prec=40)` 用来生成 Decimal 仿射系数；
- `AdjustmentFactor.qfq_price` 后续以 `self.qfq_mul * raw + self.qfq_add` 算价格，在**默认 Decimal 上下文**完成乘加并 `ROUND_HALF_UP` 到分；
- 有限精度系数和乘加在恰好五厘的精确分界值附近产生略小的数，因此按 half-up 舍入可能少一分。

例：SH.688553，2025-04-14，open。用户冻源的精确有理数结果 `391/40 = 9.775`，HALF_UP 应为 **9.78**；以当前有限精度系数运算得到 `9.774999999999999999999999997`，生产记录为 **9.77**。本轮独立 Decimal 复算确认相同的舍入方向；即使将已有有限精度系数的乘加上下文从 28 增加到 40 位，仍可得到略低于 9.775 的值，**不能把简单提高精度视作正确修复**。

R2 清单列出的 16 格横跨 7 只股票、2025-02-12 至 2025-06-20，每格记录与精确半分结果差 0.01 元。当前五个冻结运营日的 ret/RPS 端点未被这16格触及，但历史图、均线/ATR/突破阈值、事件与候选路径的间接影响需要重新评估。不得覆盖已接受旧 Owner；须建新版本算法、候选重算和影响图，对全部消费者做 delta 核对。另须确认基于原始记录金额/股本等事件的经济复权口径与主合同完全一致。

**本项裁决：`CONFIRMED_CODE_LEVEL_NUMERIC_DEFECT / FIX_NOT_APPLIED`。**

### FA-017｜P2｜单成员板块 LOO 全空的边界异常

`src/workbench_analysis/full_loo_v3_3.py` 将目标从板块成员集合剔除后，立即执行：

```python
recomputed = build_sector_current(without_target, market_without_target, config).set_index("sector_id")
```

只有返回 `recomputed` 后才有 `SECTOR_EMPTY_AFTER_EXCLUSION` 判断。如果市场仍有其它股票，但本次选入的全部板块只有目标一个成员，`without_target` 为空，下层抛出 `CURRENT_REQUIRES_ONE_TRADE_DATE`；因尚未进入内层循环，预期的显式 UNKNOWN/空集合分类未产生。R2 15/16 静态反例与这段源码吻合。

本缺陷属于 V3.3 candidate 的明确构造边界，**不等于已经确认当前V4正式板块 LOO 日更事故**；必须区分候选与正式消费者。修复应先冻结空成员行为合同，再对无相关成员、单成员、有其他不相关板块、n=2、多成员、跨多个板块，以及市场本身全空进行独立验证。

**本项裁决：`CONFIRMED_CANDIDATE_BOUNDARY_DEFECT / CURRENT_PRODUCTION_IMPACT_NOT_PROVEN`。**

## 四、上一轮问题尚未修复的源码证据

1. **FA-001，P1，风险事件被覆盖**：`core_product_bff_r1.py` 先按 `INVALIDATED(0)…NEW(5)` 升序排列，又 `{entity_id: row for row in changes}` 去重，字典保留较晚行；同股票多个事件时，NEW 可覆盖 INVALIDATED。源码明确成立，仍需修。
2. **FA-005，P1，G盘合同冲突**：`fep_e2/registry.py` 和 `fep_e3/protocol.py` 仍以 `.startswith(('e:\\','f:\\'))` 限制目录；即使用户现行隔离要求为 G 盘，也会被拒。修复不能随便把整个 G 盘放行，应仅 allowlist 精确隔离根和已解析子路径，阻止路径穿越及对生产/TDX根写入。
3. **FA-013，P2，比较身份别名**：`core_product_bff_r1.py` 比较入口仍以字符串对照 `entity_id/symbol/symbol末6位`，没有调用按日期别名解析器。搜索与详情能识别 300114→302132，比较却可能失败。
4. **FA-014，P2，比较字段映射**：`static/core-product-r1/replay.js` 对股票和板块统一读取 `sector_rs5/sector_rs20`，股票已有 `rps5/rps20` 无法展示。必须按 domain 使用正确字段并写明单位。
5. **FA-004，P2，性能问题**：R1 观察到首页6.31MB和历史首次读取8秒级。R2未提供正式并发/容量门的新验证，保持OPEN。

## 五、审计记录质量与勘误

- **FA-015 合格订正**：R1误写 CLV `(2C-H-L)/(H-L)`，正式源码 `src/v4/factors/core.py` 的 CLV 为 `(C-L)/(H-L)`，范围0..1，H=L返回UNKNOWN；这属于审计正文勘误，不是产品源码改错。
- **新增一个独立审计证据治理问题 `AR2-E01`（P2）**：`INDEPENDENT_AUDIT_ITEMS_R2.json` 的历史 `issues` 部分仍保留 FA-012 的旧 `location=config/amount_authority_audit_brief_v1.json`，而 `ERRATA_R2.md` 明确该路径不存在，现行来源应是 `config/a04_amount_a_go_forward_r3.json` 等配套。虽然 `continuation_updates` 有说明，自动消费者若只读 `issues` 仍会拿到错误位置。建议改为 `effective_location`、`superseded_by` 或逐问题 versioned disposition，不覆盖历史 R1 原件。
- R2 中 `FULL_SYSTEM_AUDIT_CURRENT.md` 指向新的R2报告是正确做法；更新 `issues` 主记录与续审项之后再校验统一入口，防止人读报告与程序读JSON裁决不一致。
- 24个 named-symbol 命中中，源码 `market_source_acquisition.py:233` 的 `'sh.600000'` 是 `smoke = codes[:1] or [...]` 采集 smoke fallback，不能归为纯 QA 文本，也没有证据说明是股票评分捷径；须按采集策略单列审核，原硬门保持。

## 六、仍未证明的系统能力

- 完整逐原子需求→版本化因子→真实 producer→consumer→quality/time/permission→API/UI 的全量分母与语义审计（FA-009）。当前 39 模块 PARTIAL 仍不能升级。
- 正式历史 PIT、逐日前序状态、D0/D1/D2合法 source/LOO，当前成员重构不能冒充历史 first-observed（FA-002）。
- 生产 Radar、Validation Cohort、Forward 真正完整可消费 Owner（FA-003）。Focus 2805 个对象不能代替 Cohort 全分母。
- Amount A 的严格历史 H21：378 板块当前明确 UNKNOWN，不能从 5210 当日金额表示一致跳到正式 Amount A 成熟验证（FA-012）。
- 全库绿色回归、M14 原始probe档案、部分孤岛实现及代码静态符号原政策（FA-006）。151 选定测试通过是正面增量，但不是重置全库基线。
- 2026-10-12 或其后的真实采集/首次可用/自动日更/后继成熟，截止本报告的2026-10-11尚未发生（FA-008）。
- FEP成熟标签/OOS、正式model/Grant以及Windows真实安装、登录重启、托盘、卸载/回滚与最终加载图（FA-007/FA-011）。

## 七、下一轮面向 Codex 的执行建议

**优先级与并行原则**：可立即执行的A类修复与B类深度审计并行，不要因为等10/12真实交易日或Forward 20日成熟而阻塞其它项。每个工作包独立冻结 HEAD、源码SHA、测试原件、影响矩阵和验收口径；不得修改 accepted/strict/operational Head、TDX原始根、真实Grant或既有 T0 冻结数据，未经明确授权不执行生产接管。

| 批次 | 立即执行内容 | 强制交付与验收 |
|---|---|---|
| A1 | FA-001：事件优先级字典覆盖 | 组合排列的优先级不变性，失效优先，风险计数，五日真实 Focus 只读重放 |
| A2 | FA-005：FEP E2/E3 工程目录合同 | G隔离根正负例、symlink/path traversal、非工程和生产根拒绝、原子语义不变 |
| A3 | FA-013/014：比较别名及字段 | 300114/302132日期别名、未知代码/不同实体、股票与板块四mode、真实HTTP+DOM |
| A4 | FA-016：复权精确HALF_UP | 有理数规则+7股16格反例、非tie多事件、全股候选数据重算、所有消费影响；不得旧Owner原地覆盖 |
| A5 | FA-017：LOO空集合 | 为空原因或受控拒绝的唯一合同、n1/n2/multi/overlap，市场为空与非空；candidate/formal隔离 |
| A6 | FA-004：实测服务性能 | 同Head/token下吞吐、延迟、内存、读写隔离，合同阈值，非全局锁改造前后数值一致 |
| B1 | 继续全字段全版本需求原子化 | 除157行已有范围外补controls/Focus/profile/FEP多版本；逐字段真实路径、公式、source、quality、消费者和反例，建立最终合法总分母 |
| B2 | 继续状态与数学深度审计 | 旧日合法prior、D0D1D2、LOO、FIRST/ANY分母与label生成，非仅复算既有数值；识别因复权新版本而受影响字段 |
| B3 | 完整回归与遗留证据治理 | 修复fixture版本与自动PG测试隔离、M14原件不可取如实记录、24个symbol用途不全局豁免、全库测试分门 |
| B4 | Amount A/H21 正式资格 | 精确跨源表示与窗口已过域复用，不重复重跑；等待合法20个PIT观察的真实/历史已证明数据，正式consumer未成熟则UNKNOWN |
| C | 下一实际交易日首获与日更 | 只在真实来源可用后执行，不脑补新日数据；来源时间、SHA、正式issuer、CAS、故障回滚与六入口同头 |
| D | Forward/FEP成熟长期检验 | 完整候选与未入选分母、后继T+1/3/5/10/20、右截尾、OOS；不解锁未授权预测 |
| E | Windows真实验收 | 仅经用户明确授权进行实体安装、重启、托盘、回滚与生产切换 |

**任务卡执行出口**：A类修复分别提交 `REPAIR_RESULT`、不可变反例集、隔离回归、真实只读消费验证；B类补证提交逐原子完整索引与差异报告。任何批次只有工程PASS仍不能代签独立外部验收；R2 原报告与 JSON 问题总账不得静默覆盖。

## 八、引用定位

- 统一入口：`https://github.com/NanOns/a-share-market-structure-research/blob/239fb9b545ac25305af02a645a77d82246cbb71a/docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md`
- R2报告：`https://github.com/NanOns/a-share-market-structure-research/blob/239fb9b545ac25305af02a645a77d82246cbb71a/docs/audits/full_system_audit_r2_20261011_58faf74e/V4_FULL_SYSTEM_CODE_AUDIT_CONTINUATION_REPORT_R2_20261011.md`
- R2补证批次：`https://github.com/NanOns/a-share-market-structure-research/blob/239fb9b545ac25305af02a645a77d82246cbb71a/docs/audits/full_system_audit_r2_20261011_58faf74e/NEXT_REPAIR_EXECUTION_BATCHES_R2.md`

## 九、结论

**R2是有价值的深度续审，尤其把“全量抽样通过”推进到“全证券历史复权的细小但真实差异已被查出”，但仍只是审计与证据阶段。** 立即启动A类定点修复，B类逐需求和正式全链审计持续推进，C/D/E维持各自真实数据和授权边界。

**当前唯一有效总状态：`AUDIT_INCOMPLETE`。**
