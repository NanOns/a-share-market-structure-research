# 成员有效日来源处置

`sector_membership_daily.parquet` 包含 753636 行，日期 2026-09-11 至 2026-09-24，覆盖目标日行数为 0/0/0；其来源标记为 CURRENT_TDX_MEMBERSHIP，historical_backtest_safe=false。V4-08 accepted membership artifact 是 9/30 快照，不外推至 9/28、9/29。已检索 accepted V4-08 head/artifact、V4-01 membership interval artifacts、仓库 membership Parquet、source_evidence 与备份数据库 memberships。当前找到的资料不足以证明目标日前两日的完整历史行业/概念身份；这属于 EFFECTIVE_MEMBERSHIP_UNKNOWN，和 first_available 未证明分开。维持 9/28、9/29 corrected membership NOT_VERIFIABLE、strict PIT 0/3。

本次搜索限仓库 data 与已配置 `D:/new_tdx` 目标证券日 K；未扫描整个磁盘，也没有把“没找到”外推为所有可用数据源不存在。
