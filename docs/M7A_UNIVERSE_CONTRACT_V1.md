# M7A 股票范围合同 v1

合同 ID：`workbench-universe-v2.1`
适用步骤：`M7A / 7A-02`
状态：preview；不改变已封存发布，不触发正式入口切换。

M7 专用配置位于 `config/workbench_universe.yaml`；不得修改被 V1 计算身份封存的 `config/universe.yaml`。

## 范围规则

工作台的正常 A 股范围是沪深北三市场的六位证券代码前缀：

- SH：`600/601/603/605/688/689`
- SZ：`000/001/002/003/300/301/302`
- BJ：`4/8/92`

SH `900xxx` 与 SZ `200xxx` 明确分类为 B 股并排除。`NE/NQ/OC/OTC/SB/XSB` 市场明确分类为新三板并排除。其它合法 ID 可展示为 `OTHER`，但不能进入报价或结构范围。

## 三种资格

同一证券分别计算：

- `display_eligible`：身份格式和市场代码可解释即可展示；范围外证券保留排除原因，便于审计。
- `quote_eligible`：仅 A 股且没有明确报价缺失；状态未知不自动改成退市。
- `structure_eligible`：仅 A 股、状态可确认且属于正常结构范围；`UNKNOWN`、`UNAVAILABLE`、`DATA_INSUFFICIENT` 等状态不能参加结构扫描。

用户展示范围与统计范围分离：`display.show_star_stocks=false` 配合 `excluded_board_prefixes` 控制个股推荐、结构队列、个股技术、个股联动和个股透视等股票行；当前个股展示同时排除科创板和北交所。`statistics.include_star_stocks=true` 控制市场/板块/全市场汇总，仍纳入科创板和北交所。全市场股票查询是全量查询例外，保留这些股票行；任何市场聚合不得复用个股展示过滤。

显式 `DELISTED` 或 `is_delisted=true` 才能分类为 `DELISTED`。状态缺失或未知统一保留为未知/结构不可用，不能写成退市。

## API04 响应

`GET /api/universe/summary?publication_id=P` 返回 `item`，至少包含：`contract_id`、`publication_id`、`trade_date`、`display_count`、`statistical_count`、`display_quote_valid_count`、`quote_valid_count`、`structure_eligible_count`、`classified_counts` 与分层的 `excluded_by_reason`。响应同时回显 `display_scope` 与 `statistical_scope`、来源身份哈希和 `source_revision_id`，使范围结果绑定到所选发布。

`excluded_by_reason` 分为 `display`、`quote`、`structure` 三层；每层只计对应资格未通过的原因，不把成员数、有效行情数和结构资格混为一个数字。

## 不变量

1. ID 前缀校验与身份元数据不一致时，结果为 `UNKNOWN/IDENTITY_*_MISMATCH`，不得凭名称或板块成员关系升级为 A 股。
2. 沪深北 A 股使用同一合同；BJ `4xxxx/8xxxx/92xxxx` 不得因只识别 `92xxxx` 而遗漏。
3. B 股、新三板、指数、基金、债券和未知市场不进入报价或结构资格。
4. 规则版本变更必须产生新的 `contract_id`，不得覆盖旧发布解释。
