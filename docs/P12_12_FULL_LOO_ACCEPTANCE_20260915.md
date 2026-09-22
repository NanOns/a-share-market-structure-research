# P12-12 完整 Full LOO 验收

阶段合同为 `P12-12_FULL_LOO_ACCEPTANCE_V1`，算法合同为 `TODAY_RESEARCH_FULL_CURRENT_LOO_V3_3_CANDIDATE_01`。执行前核对 `AGENTS.md`、[V3 v2.1升级方案](V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md) §10、§12、§19，以及[P12-11验收](P12_11_V3_3_DATABASE_REGISTRY_ACCEPTANCE_20260915.md)。P12-11内部复核通过后开始本阶段；本阶段不进入5—10日历史物化。

Full LOO 对每只初筛候选执行完整 CURRENT 轨道重算：目标股从全市场收益基准及其全部重叠行业/题材关系中同时剔除，随后重新计算532个板块的成员数、覆盖率、M1、B1、市场中位数、REL1、同类型横截面覆盖、P1、正收益成员数、最大正贡献和全部 CURRENT 谓词。输出逐板块保存已知失败项和未知项，明确 `full_track_recomputed_without_target=true`。处理范围限定于初筛后的58只候选，没有对全市场逐股运行。

在剔除前，使用与生产构建相同的5580只主市场范围、调整日线摘要、成员revision及实际bar规则重新构建基线。532个板块的 CURRENT、M1、B1、REL1、P1、成员数和有效报价数与生产 `research_sector_states` 全部一致，差异数为0；该门通过后才执行剔除计算。

完整重算结果为TRUE 9只、FALSE 49只、UNKNOWN 0只。旧局部成员宽度LOO曾确认14只，其中5只在完整轨道下不再成立：`SH.600110`、`SZ.001223`、`SZ.002585`、`SZ.002846`、`SZ.301389`。前两类处理中，只有延续场景的 `SH.600110` 和 `SZ.301389` 从正式候选移除；其余3只仍满足独立启动条件，改列个股独立候选。

新活动包合同为 `TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO`，共56只，其中板块确认9只、个股独立47只，摘要 `45ae278c97d7a4fdec844fe52158ad0f85a39a76ac72adde69092588161fa4d7`。每行保存完整 `full_loo_audit`，新包已原子激活并通过P12-11注册器落库。一键生成流水线已加入Full LOO重算和新版包步骤，同publication/date重复点击直接复用。

机器证据见[Full LOO计算回执](../reports/p12_12/p12_12_full_loo.json)与[新版bundle回执](../reports/p12_12/p12_12_full_loo_bundle_gate.json)。阶段结果为 **`FULL_PASS`**。下一阶段为 `P12-13_HISTORY_MATERIALIZATION_PILOT`。
