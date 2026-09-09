# M9 板块层级与周期排名合同 v1

合同 ID：`sector-hierarchy-contract-v1.0`

## 层级来源

- `INDUSTRY` 使用本地 TDX 行业编码的稳定前缀关系。细分行业编码的最长已存在父级前缀作为 `parent_sector_id`。
- 父级成员集合由子级成员并集物化，来源标记为 `tdxhy.cfg:DERIVED_PARENT`；这不是外部数据，也不修改 TDX 源文件。
- `THEME` 和 `STYLE` 当前没有可审计的父级编码，保持 `FLAT` 平级，不按名称相似度猜父子关系。
- 当前本地输入没有 `REGION` 板块数据，UI 不提供地区板块选项。

## 排名规则

- 行业一级大板块（`ROOT`）和细分行业（`LEAF`）分别计算名次和 RPS20 百分位。
- 概念、风格标签在各自类型内平级计算，不与行业混排。
- API 保留原始 `rank` 和 `sector_rs20_pct` 字段；页面使用 `hierarchy_rank` 与 `hierarchy_sector_rs20_pct`，防止破坏旧快照解释。
- 周期详情只把近 30 个可用交易日映射为本层级名次；无法映射的历史点不伪造排名。

## API 扩展

`GET /api/sectors/cycle` 增加可选 `hierarchy_level`：`ALL`、`ROOT`、`LEAF`、`FLAT`。`ALL` 表示分层展示，不表示把一级和细分放进同一个排名分母。
