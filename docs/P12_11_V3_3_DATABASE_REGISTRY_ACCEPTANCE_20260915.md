# P12-11 V3.3运行及候选结果数据库落库验收

阶段合同为 `P12-11_V3_3_DATABASE_REGISTRY_ACCEPTANCE_V1`。执行前核对 `AGENTS.md`、[V3 v2.1升级方案](V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md) §16、§19，以及[P12-10独立审计](P12_10_V3_3_INDEPENDENT_AUDIT_20260915.md)。本阶段只登记已经完成哈希验证的活动V3.3 bundle及其候选结果，不重算算法，不进入Full LOO或历史物化，不修改TDX只读输入。

新增迁移 `035_v3_3_research_registry`，使用独立表 `research_runs_v3_3` 和 `research_candidates_v3_3`。旧 `research_runs` 结果模型继续保留，V3.3不会冒用旧运行身份。运行表绑定bundle摘要、逻辑run、交易日、publication、snapshot、membership、参数和依赖锁；候选表保存可查询的名称、类别、排名、支持状态和风险，同时完整保留factor、scanner及最终结果JSON证据。

导入器接受经过阶段登记的 `TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02` 及后续 P12-12 `TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO`，先复核活动指针、文件哈希、输出摘要、身份完整性、证券唯一性、日期一致性和证据结构，再用单事务写入。重复导入按bundle摘要幂等复用；已有运行若行数不一致则拒绝，不做静默补写。

生产登记对象为2026-09-15活动包，摘要 `a81dc08d2ecd1af3edea9a517bf4df13940153eaaf401b7c997500d9b4a8553e`，共58条候选。登记前使用DuckDB原生 `EXPORT DATABASE (FORMAT PARQUET)` 封存109张表及逐表行数清单，避免对正在使用的数据库执行不一致的普通文件复制。

机器回执见[阶段门](../reports/p12_11/p12_11_stage_gate.json)。逐行规范JSON与bundle完全一致，运行身份一致，重复登记无新增行，旧 `research_runs` 行数不变。阶段结果为 **`FULL_PASS`**。下一阶段是 `P12-12_FULL_LOO`，须等待用户验收后再开始。
