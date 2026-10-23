# 通达信市场结构扫描器——实现基线

采用的基线文档为 `TDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md`，日期为 2026-09-04。

用户提供的权威设计文档位于：

```text
E:/codex work/大A交易/requirementTDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md
```

本工作区实现阶段 0 至阶段 0.2C。必须执行的约束如下：

- 本地通达信文件是只读输入；
- 解析确定的源根目录为 `D:/new_tdx`；
- 不允许使用网络或外部复权来源；
- 阶段 0 的输出决定后续扫描器属于正式模式还是实验模式；
- 当前板块成员关系不代表历史时点的成员关系；
- 所有产物都必须在通达信源根目录之外，以原子方式写入。

已实现的合同和当前判定见 `docs/DATA_FACTOR_SPEC.md`、`docs/ADJUSTMENT_CONTRACT_V0_3.md` 和 `reports/phase0_2c/PHASE0_2C_RELEASE_SEAL.json`。较早阶段的收据作为历史证据保留。

阶段 0.1 新增了主交易日历、近期窗口证券全集规则、最小板块角色划分，以及初步复权审计。阶段 0.2 独立实现本地 GBBQ 解码器和仿射前复权/后复权（QFQ/HFQ）引擎，并验证了三段完整的本地历史数据。该阶段的历史最终状态为 `DEGRADED_PASS`，原因是要求执行的通达信桌面端前复权对照仍待完成；因此，该阶段项目价格口径仍为 `RAW`，正式趋势扫描器保持禁用。

阶段 0.2A 曾临时允许使用公开前复权数据，但严格限定为验证参考。
其历史门禁判定替代阶段 0.2，状态为 `BLOCKED_FOR_FORMAL_ADJUSTMENT`，原因是四个固定点位不匹配，且保留的批次证据不完整。根本原因尚未解决，因此该阶段不允许进入正式因子或扫描器阶段，继续执行 `RAW` 和 `LOCAL_TDX_ONLY` 限制。请求数量限制和证据覆盖方面的缺陷已在阶段 0.2A 报告中披露，并在验证层修复。

## 当前发布状态——阶段 0.2C

本节替代上文及较早阶段文档中关于原始价格（`RAW`）、手工界面核验和外部精确匹配的历史发布限制。历史研究结论保持不变。生产输入仍限定为 `LOCAL_TDX_ONLY`；此前已授权的数据提供方快照仅作为验证参考。

```text
CURRENT_DATA_STATUS = TDX_NATIVE_ADJUSTMENT_RELEASED
PHASE_0_STATUS = FULL_PASS
PHASE_0_CLOSED = TRUE
ADJUSTMENT_IDENTITY = TDX_NATIVE_AFFINE_QFQ
PROJECT_PRICE_BASIS = FORWARD_ADJUSTED
ADJUSTMENT_STATUS = VERIFIED_REPRODUCIBLE_TDX_NATIVE
FORMAL_TREND_SCANNERS_ALLOWED = TRUE
NEXT_PHASE = PHASE_1_NORMALIZATION_AND_FORMAL_FACTOR_ENGINE
```

当前发布依据为 `Phase0.2C`、`adjustment-contract-v0.3`、`adjusted-daily-contract-v0.3` 和 `known-limitations-v0.3`。阶段 1 可按各自合同生成 `adjusted_daily.parquet` 和正式因子。本次发布封存本身并未实现数据生成、因子或扫描器。不同数据提供方之间的前复权差异，以及对数据提供方口径敏感的较早历史数据，属于已知限制，不构成当前生产阻断项。

## 当前生产状态——阶段 1

PHASE1_STATUS = PASS
PROJECT_PRICE_BASIS = FORWARD_ADJUSTED
ADJUSTMENT_IDENTITY = TDX_NATIVE_AFFINE_QFQ
NORMAL_UNIVERSE_COUNT = 5461
NEXT_PHASE = PHASE_2_MARKET_REGIME_AND_SYNTHETIC_SECTOR_FACTOR

本节状态替代先前阶段 0.2C 的下一阶段指向。详见 `docs/PHASE1_REPORT.md` 和 `reports/phase1/PHASE1_FINAL_RECEIPT.json`。

## 当前生产状态——阶段 2

PHASE2_STATUS = PASS
SNAPSHOT_BASIS = CURRENT_SNAPSHOT_ONLY
SECTOR_MEMBERSHIP_BASIS = CURRENT_TDX_MEMBERSHIP
NEXT_PHASE = PHASE_3_SECTOR_SCANNER

本节替代较早的下一阶段指向。本节对应阶段尚未实现阶段 3 扫描器。

## 当前生产状态——阶段 3

PHASE3_STATUS = PASS
SCANNER_RULE_VERSION = sector-scanner-ruleset-v1.2-evidence-binding
SNAPSHOT_BASIS = CURRENT_SNAPSHOT_ONLY
SECTOR_MEMBERSHIP_BASIS = CURRENT_TDX_MEMBERSHIP
NEXT_PHASE = PHASE_4_FORMAL_STOCK_SCANNER

## 当前生产状态——阶段 4

PHASE4_STATUS = PASS
RULE_VERSION = stock-scanner-ruleset-v1.0
NEXT_PHASE = PHASE_5_CANDIDATE_POOL_AND_RESEARCH_PRIORITY

## 当前生产状态——阶段 5

PHASE5_STATUS = PASS
RULE_VERSION = research-priority-ruleset-v1.1-correctness
NEXT_PHASE = PHASE_6_DAILY_PRODUCTION_CLOSURE_REPORTING_SMOKE_TEST

## 全市场通用性、临时测试与中文默认要求（2026-10-23）

本节是现役项目的强制实现约束，并与根目录 `AGENTS.md` 第18至22条一致。

- 业务运行代码、正式维护脚本和运行配置必须适配全市场及任意有效交易日。不得把正常个股证券代码、具体板块/行业/主题代码或指定交易日期写入业务分支、默认参数、查询条件、页面选择或计算范围。身份从本次输入、证券/板块目录、成员关系或明确的运行参数读取；日期从请求上下文、市场交易日历或来源事实读取。相对窗口和算法阈值按有版本的参数合同配置。
- 固定股票、板块和交易日只允许出现在测试代码及明确标记的测试脚本中，作为隔离的样例输入。优先用合成身份；真实样例只可验证通用解析、映射或展示，不得让业务算法形成个股或单日特判。
- 一次性诊断、取证、验收和临时测试脚本/测试文件放在 `G:/codex_tmp`，执行后立即删除且不提交。正式回归测试仅在有重复验证价值时保留；正式维护脚本需有持续用途和通用参数，不保留一次性过程工具。
- 系统默认简体中文（`zh-CN`）。用户可见的前端页面、提示、命令行帮助、报告、文档及 Git 提交说明、标签说明和 PR 文案使用中文和 UTF-8。程序接口、数据库字段、代码标识、协议常量、供应方原生值和工具固定前缀按兼容性保留原样，不直接作为面向用户的文案。
- 每个业务代码阶段扫描新增/修改的运行代码，检查证券代码、板块代码、指定交易日期字面量、动态输入绑定和用户可见文本语言；扫描结果与阶段验收一起记录。测试夹具和正式代码分别判定。
