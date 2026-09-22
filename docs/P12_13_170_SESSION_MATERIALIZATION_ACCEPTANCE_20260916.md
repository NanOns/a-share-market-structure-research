# P12-13 170个交易日历史物化验收

阶段合同为 `P12-13_170_SESSION_MATERIALIZATION_V1`，数据集合同为 `TODAY_RESEARCH_HISTORY_BASE_170_V3_3_RECONSTRUCTED_01`。执行前核对 `AGENTS.md`、[V3 v2.1升级方案](V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md) §14、§16、§17、§19，以及[P12-13八日试跑](P12_13_HISTORY_MATERIALIZATION_PILOT_ACCEPTANCE_20260916.md)。八日试跑为 `FULL_PASS` 后才开始本阶段；八日数据集保持不可变。

物化范围固定为截至2026-09-15最近170个交易日，即2026-01-06至2026-09-15。每个目标日独立使用生效日不晚于该日的本地GBBQ除权事件建立目标日复权锚，没有使用最新日调整值倒灌历史。通达信目录全程只读，生产数据库只读，结果写入项目独立内容寻址目录。

最终数据集包含1,050,940条股票基础事实和90,440条板块CURRENT截面，对应170×6,182股票和170×532板块。股票层包含V3.3窗口、均线、趋势、位置、prior额量、波动、回撤、风险、质量及RAW收益；板块层包含成员/报价覆盖、市场中位数、M1、B1、REL1、P1、正收益成员、集中度、完整谓词和原因。股票 `trade_date/date` 与板块 `trade_date` 均为原生Parquet `DATE`。

历史身份保持 `RECONSTRUCTED_CURRENT_MEMBERSHIP`。关系和市场范围采用当前冻结来源，市场合同为 `TDXHY_CURRENT_A_STOCK_IDS_V1`、5580只统计股票。因此这批数据可直接用于基础因子、横截面、筛选器输入和重构诊断，不能冒充历史实际发布结果、历史PIT成员关系或独立效果证据。完整历史episode、历史换手率和参数校准不在本数据集内。

生产一致性硬门使用2026-09-15对账：532个板块的CURRENT、M1、B1、REL1、P1、成员数和有效报价数与生产 `research_sector_states` 差异为0。170日股票与板块复合主键均唯一；日期覆盖、行数、文件哈希、非有限值、日期类型和TDX只读边界全部通过。READY股票事实924,371条，PARTIAL 126,569条，缺口原样保留，没有补0或删除。

股票Parquet为230,642,093字节，板块Parquet为3,048,869字节，连同manifest总计233,694,707字节，约222.9 MiB。相同输入完成第二次全量计算后，仍得到摘要 `35b083cc6654c7fccf0f70a70102d7036725fc4774221ce2b40bf01eb0747417`，返回 `reused=true`，没有创建重复可见数据集。

机器证据见[170日阶段回执](../reports/p12_13/p12_13_170_stage_gate.json)。阶段结果为 **`FULL_PASS`**。下一阶段为 `P12-14_OPTIONAL_TURNOVER_SOURCE`，本阶段没有执行东财请求或换手率增强。
