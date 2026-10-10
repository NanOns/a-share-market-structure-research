# D2 原资格口径事实复核

旧 phase2.prepare 与 legacy exact_value 的正则均正确：`(SH|SZ|BJ)\.\d{6}`。本轮不新增旧正则故障归因。prepare 在 merge 后要求代码匹配、missing_state 非空且不属于 FILE_MISSING/DELISTED_OR_INACTIVE。显式 None/NaN 为 FALSE；来源字段根本不存在则 V3 研究资格 UNKNOWN。SUSPENDED、NOT_LISTED_YET、RENAMED 和其他非空枚举不能无条件用 Lifecycle 生存状态替换旧口径。normal_universe 影响市场分母，不等于 valid_member；sector_valid 另受总人数、有效人数、70%覆盖和 role 排除约束。

本轮从 SHA 校验后的冻结原 CSV 读取 3,553 个实际成员样本，将原 valid_member、prepare 的独立 pandas 结果及 exact_value 三方对照，全部 PASS。prepare 比较中 MA/AMOUNT 非资格字段填入 synthetic 常量，明确只核对 valid_member，未宣称这些常量是实际数值。原 CSV 不带新 Lifecycle 的样本对 V3 映射记 UNKNOWN，不编造状态。原 parquet 的 541 板块及 6,188 资格观察使用原 receipt、成员和总数/有效数/coverage/sector_valid/invalid_reason 独立 oracle，0 差异。完整逐字段源引用见 final/D2_LEGACY_GOLDEN_FIELD_READBACK.json。

黄金历史范围仍为冻结 2026-09-24；不是 10/09 A05 准入。10/09 有真实新代码研究值，但 legacy missing_state 当时合法原件缺失为 HISTORICAL_NOT_VERIFIABLE。另有合成 None、缺字段、停牌、未上市、退市、重命名、错误代码、不同 normal 和小板块门槛实验，不和上述真实样本混淆。

六字段生成器 `sector/d2_research_source_matrix_v1.py` 从已冻结研究 candidate 的实际 CONFIRMED/WARM 生成两项研究三值，绝不使用非正式 Native 标签代替官方判定。无合法 prior Episode 的另外四项明确 NO_PRIOR_EPISODE；合法 prior 可继承 scenario/creation contract，当前 invalidation 缺计算原件记 UNKNOWN；due 未到记 PENDING，到期仍须 settlement Owner。final/D2_PRODUCER_SOURCE_MATRIX.json 为当前实际来源矩阵，非重复的六字段全 NULL 清单。

验收：历史 exact oracle PASS_SCOPED；申请独立入场的范围是研究输入/qualification 诊断。正式 D2、A05 跨日期与 Episode 正式准入均 NOT_GRANTED。
