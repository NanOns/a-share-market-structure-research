# 大A V4｜2026-09-28～09-30 三日数据、Owner 与算法全链对齐专项任务卡 R1

- **基准仓库**：`NanOns/a-share-market-structure-research`，分支 `codex/v4-system-reform`
- **审查时 HEAD**：`2c136ac41937f216b9599429692ea885458a7631`（实际执行必须重新 `git ls-remote` 并冻结 SHA）
- **依据**：`AGENTS.md`；`docs/evidence/r2_data_algorithm_repair_20261008/R2_DATA_ALGORITHM_CLOSURE_FINAL.md`；`R2_CORE_BLOCKERS_AND_NONBLOCKERS.md`；`docs/evidence/r2_continuous_daily_20261008/TWO_DATE_SOURCE_QA.json`；当前真实生产 release/owner manifest。
- **本轮唯一目标**：把 **原始数据事实存在性 → 日期/身份/复权对齐 → Owner 日期输出 → 依赖算法结果 → UI/API 读取** 的真实断点逐个识别、修复、独立数值复核。**不得以严格 PIT 历史首获证明缺失，掩盖可修复的本地输入、日期或计算产物问题。**
- **非目标**：Edge、多分辨率兼容性、重新设计 UI、无限扩大历史训练、凭猜测填充 UNKNOWN、自动交易、假装旧日首获数据是在旧日捕获。

## 0. 当前审计已核实事实（并非本轮新执行结果）

| 业务交易日 | 现有可确定内容 | 尚未闭环 | 禁止作出的断言 |
|---|---|---|---|
| 2026-09-28 | 当前代码/证据能追到该日 `TRADING_STATUS` 来源；历史 Core 相关产物也出现过该日身份 | 该日完整 RAW、ADJUSTED、Universe、membership、Core/sector owner 的日级可用矩阵尚**没有**独立全量证明 | “9/28 完全没有数据”；“9/28 已完整 PIT 验收”均未证实 |
| 2026-09-29 | 两日回放中真实 RAW OHLC 核对 **20,844 项**，Focus **297** episodes；日级 states、价格与交易状态链可读取 | 当日归属的历史板块成员未绑定；原生 Focus Core 不完整；旧日 owner、Base/Seed、轮动阶段并未完整重建 | “缺 9/29 的全部行情”；“9/30 成员可直接当 9/29 成员” |
| 2026-09-30 | RAW OHLC 核对 **20,852 项**；当日 378 板块成员身份及多项 current strength；Focus **469**；117 Forward 入组 | 378/378 板块 `output_state=UNKNOWN`；5213/5213 基础突破状态未知；5037 缺精确前日 ATR/跨复权基准依赖，176 还缺接受复权；Base/Seed、LOO、条件 Owner 等缺口未闭 | “当日数据不存在”；“只补三根日 K 就能恢复完整结构算法” |

**时间戳边界**：9/30 两日回放中的 62,556 个 corrected 字段单元保留了晚于业务日的实际采集时间；`AS_RECORDED=false`。2026-10-08 捕获的 `first_observed_at` 不可倒签成 9/28～30 当时可知。严格 PIT 对旧三日仍 0/3，但不应阻断已验证的当期生产研究与注明为事后重建的历史比较。

**先区分五类问题**：
- `RAW_ABSENT`：实际原始文件/记录不存在或数据损坏；
- `SOURCE_PRESENT_NOT_INGESTED`：原始数据存在但 ETL/索引/缓存未载入；
- `OWNER_NOT_MATERIALIZED`：输入已具备但该日期计算及正式结果未生成；
- `IDENTITY_OR_COORDINATE_MISMATCH`：日期、证券/板块成员、来源头、参数或复权口径错绑；
- `HISTORICAL_FIRST_AVAILABLE_UNPROVEN`：能进行有标识的 corrected 重建，但无法证明 T0 当时已获知。**不得将最后一类混入前三类。**

## A. P0：三日源数据实物盘点与身份统一——先完成，不先改算法

1. 冻结 HEAD、生产联合指针、旧 accepted heads、完整备份摘要。TDX（例如 `D:/new_tdx`）及已冻结头只读，禁止直接修改或重命名。
2. 对 9/28、9/29、9/30 **逐日**盘点实际本地来源及保存路径：通达信 `.day` 原始日 K、已接受 RAW_DAILY、ADJUSTED_DAILY、交易状态、证券身份/代码迁移、停复牌、分红配股/GBBQ/复权因子、基准指数、所属行业/概念、板块成员、同日和历史价格序列、模型及参数版本、Owner 输出与接入时间。记录每项 `exists / covered_rows / expected_rows / checksum / trade_date / source_as_of / captured_at / first_available_proven / quality / upstream_digest / consumer`。
3. 做三日逐股票的 `(security_id, symbol_effective_date, trade_date)` 外连接；与 `(sector_id, membership_effective_date)` 分开匹配。识别转代码、停牌、未上市、退市、额外身份池与历史存在性；不要把 RAW 股票行数少于身份池数量一概视为缺失（9/30 已有 5224 身份 vs 5213 RAW 的范围差异）。
4. 分开校验原始不复权行情与每个目标日期的**原生 QFQ 坐标**：四价逻辑、量/额单位（股/元）、相邻日间调整、涨跌幅、涨跌停原始价与复权后价；不允许简单前复权跨不同目标日直接相除。
5. 对找不到的原始数据，**先搜索现有 local artifact store / accepted staging / TDX 读取缓存 / BaoStock 合规历史输入**，给出“真实缺哪一个文件/哪一天/哪只股票/哪个板块”的差集；确认不存在后再通过现有版本化数据源合同受控补采。已存在的不重下、已接受的不重写。
6. 最终生成 `THREE_DAY_SOURCE_INVENTORY.json`、`THREE_DAY_SOURCE_DIFF.csv`、`IDENTITY_AND_QFQ_RECONCILIATION.json`，并注明不能补齐的真实数据及替代可能。**无差集报告，不允许宣称“历史数据不足”。**

## B. P0：按交易日期重建缺失 Owner 输出——不能把三日视为孤立 K 线

1. 冻结 9/28、9/29、9/30 每日独立 data head、每日参数与模型实现版本；输出 `DATE_OWNER_BINDING_MATRIX`，严格检查每个消费字段的 `target_trade_date / input_digest / owner_contract / parameter_digest / price_basis_id / published_at / knowledge_lineage`。
2. 先解决 9/29 当日**历史成员的真实来源**：搜索历史 membership 事件、分类变更、官方成分记录、已冻结按日成员或能够按明确有效日重放的来源；不得拿 9/30 当前成员冒充 9/29 PIT。若无法取得，只能建立 **RECONSTRUCTED_CORRECTED** 解释性比较（注明存活偏差），不能提升为原生日期成员或 PIT 通过。
3. 运行行业/概念 `Base / Seed / Native / Rotation` 真正的上游输入检查与按日构建，不得绕开原模型直接发明 lifecycle。给出所有 378 板块 `output_state` 原因为何未知的逐项分布，区分：缺日前成员、缺 seed、缺参数、未执行算法、真实不可判定。
4. 核对 9/30 个股基础突破：前一个有效交易日 ATR、原生 QFQ 变换、所需窗口与前日 `core_profile`；对 5037 和 176 个失败家族按 **每个上游依赖** 给出实际可用度、修复计划。不能直接将 UNKNOWN→FALSE；真实指标完成后由原版规则重新计算。
5. 允许只读 corrected 历史算法链补算，但必须使用 **截至每个目标日** 的价格、成员与状态，锁死 owner 目标日；模型可能是后发布版时保留 `RECONSTRUCTED_CORRECTED`，不宣称 as-recorded。对历史真正失源应 fail closed 于该字段。
6. 检查 `breadth_delta3`、5/10/20 日生命周期、20 日均线及 ATR 等窗口依赖：**三日不是所有窗口的足够输入**。按公式向前递推所需**真实历史交易日**（包括可能的 9/25 等），只补必要窗口，避免无限回填全历史。价格序列可存在而阶段输出不存在，须分别生成和验收。
7. 对不含明确 Owner 公式的 `why_now / health / maturity / waiting_for / invalid_if / H` 等，先找原合同或已有 producer；没有规范则版本化新合同、独立测试、批准后再实现；不得靠 UI 文案填充算法含义。
8. 生成 `OWNER_REPLAY_PER_DAY.json`、`OWNER_DEPENDENCY_ROOT_CAUSE.json`、`REAL_FIELD_BEFORE_AFTER.json`，保留新旧 producer 行与 SHA，不覆盖旧冻结数据。

## C. P0：跨域对齐及真实数值验收

1. **市场**：三日对应大盘/全市场行情、市场四轴、涨跌宽度、量额与分母；逐项同日原始数值 oracle。
2. **板块**：行业/概念当日成员集合、结构变化、breadth、seed、amount、RS5/20、进入退出、状态迁移；至少 5 个板块在 T-1/T0 的成员增减、价格变化和阶段状态独立重算，区分当前/历史 corrected/严格 PIT。
3. **个股**：所有可用股票 `close/MA20/ret5/ATR/突破/支撑/相对市场和板块` 逐字段对账；每种 CORE 判定（趋势、突破、回踩、风险等）保留正例、反例、边界样本。历史窗口使用明确前日与同坐标价格。缺值清单必须附具体 source/owner 与 next action。
4. **Focus**：9/29 的 297 条 observation 的真实原生 Core 可用性单独核对；9/30 的 469 条 observation 检查相对前日的升级、减弱、退出、重入、Anchor、价格路径。原始 T0 不变；如果历史是后生成，标 corrected，不强制抹去 UNKNOWN。6 个特殊 affine 调整样本需与**原始调整系数**独立复算，不能只验证最终收益接近。
5. **Forward**：117 个真实入组、585 个期限，当前 due=0 应继续 PENDING；不可将 Focus 的 T+1 路径结果算作 Forward 到期收益。真正到期才执行按接受日历结算、缺价处理和样本完整性验证。
6. **数值范围**：除聚合计数和 SHA，要有跨源独立算式和原始输入；标注 `PASS/FAIL/NOT_VERIFIABLE`，不得把单纯单元测试或相同内核二次调用算独立复算。

## D. P0：发布、回滚与日更

- 构建 **仅针对已确证修复域** 的 successor 生产快照，CAS 前比较 `Owner 日期 / frozen head / params / 价格坐标 / 真实所有嵌入 publication / 新旧 source SHA`。
- 本地现行指针与旧 frozen manifest 全量保留；禁止破坏已接纳的 9/30 生产范围。尝试错误日期、错误复权、坏 owner、缺成员、新旧头冲突的候选必须拒绝并保留旧版本；具备可验证的场景必须回读与回滚成功。
- 真实日更入口执行单次增量和无新日 NOOP；输入缺失应局部报告，不能清空全部前端数据。发布健康核查的关注重点是数据与算法，而不是各种屏幕尺寸。
- 对无法回滚的历史邻接前驱继续登记独立风险，不得因尚未恢复远古前驱而禁止所有现行可用域升级；但本轮当前直接前驱必须可读、可逆。

## E. 分阶段门槛与完成定义

| 门槛 | 接受条件 |
|---|---|
| E1 源事实闭环 | 三日 RAW/ADJUSTED/身份/交易状态等各域完整逐日清单、实际缺失差集、哈希一致性；所有非停牌、有效交易且应有行情的记录均有明确去向 |
| E2 Owner 可用性 | 所有实际有输入的必需算法有按日 producer 输出；暂缺 Owner 的必须明确 `NOT_IMPLEMENTED`，而不是写成缺历史 PIT |
| E3 板块 | 当前真实成员与上游 Base/Seed 闭环；真实状态可计算的板块不再集体 UNKNOWN；不能证明日期成员的历史比较独立降级 |
| E4 个股 | 5037/176 两组的根因逐项处理，实源满足者输出可复核的结果，缺源者给精确原因；CORE 数值+语义反例抽测通过 |
| E5 Focus/Forward | 两日真实递进、旧 T0 不变、路径与结算区分、特殊复权样本原始系数校验；Forward 无到期仍为正常状态 |
| E6 运营 | 新旧 HEAD 绑定、fail-closed、no-new-day NOOP、精确回滚、最少浏览器功能路径成功；现有分域生产继续可用 |

不要求为了 9/28～30 事后补造无法证明的严格 PIT 证明；从**下一个实际输入日**起正确、自动、增量记录 `first_observed_at / owner/model published_at / source content SHA / full input freeze`，为未来真正的严格回放创造条件。长期样本成熟与所有可选第三方新闻/分钟行情不是这次全域修复的前置条件。

## F. 交付文件和 Codex 执行纪律

- `A_SOURCE_DISCOVERY_AND_MISSING_DIFF.md`
- `B_THREE_DAY_SOURCE_AND_OWNER_MATRIX.json`、`B_WINDOW_REQUIREMENTS.json`
- `C_SECTOR_STOCK_CORE_NUMERICAL_ORACLE.json`、`C_FOCUS_FORWARD_TEMPORAL_ORACLE.json`
- `D_HISTORICAL_CORRECTED_VS_PIT_SEPARATION.json`
- `E_POST_RELEASE_READBACK_AND_ROLLBACK.json`
- `F_INDEPENDENT_AUDIT_DISPOSITION.md`（逐问题 PASS/FAIL/NOT_VERIFIABLE、残余风险、下一步）

**执行顺序**：A 数据盘点 → B 按目标日重建真实上游 → C 数值审计 → D 受控准入发布 → E 独立验收。A 可以立即执行，不需要等待后续交易日。禁止一上来修改 50 个字段的展示或重新制作整套 UI；先恢复会影响主线判断的算法根依赖。所有正式阶段 MD/JSON、代码、测试及证据 commit + push，明确目标 SHA。**所有检查必须根据真实本地文件重新计算，不能把本卡列出的历史报告数字当作新完成的 QA。**

## 附：本轮审计引用入口

- `docs/evidence/r2_data_algorithm_repair_20261008/R2_DATA_ALGORITHM_CLOSURE_FINAL.md`
- `docs/evidence/r2_data_algorithm_repair_20261008/R2_CORE_BLOCKERS_AND_NONBLOCKERS.md`
- `docs/evidence/r2_data_algorithm_repair_20261008/SECTOR_OWNER_DEPENDENCIES.json`
- `docs/evidence/r2_data_algorithm_repair_20261008/FOCUS_DEPENDENCY_COUNTS.json`
- `docs/evidence/r2_continuous_daily_20261008/TWO_DATE_SOURCE_QA.json`
- `docs/evidence/r2_continuous_daily_20261008/OWNER_CHAIN_STAGING.json`
- `src/workbench_service/continuous_daily_release.py`
- `src/workbench_service/joint_release.py`

**审核备注**：这是针对最新仓库已提交证据的外部定点诊断，并非本地数据盘点已经完成。缺失数据到底是否存在于用户硬盘，须由 Codex 在本地执行 E1 才能正式定性。
