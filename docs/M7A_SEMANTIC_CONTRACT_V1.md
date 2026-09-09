# M7A 板块语义合同 v1

合同 ID：`workbench-semantic-v2.1`
适用步骤：`M7A / 7A-04`
状态：preview；旧发布语义不回写，正式入口不切换。

## 语义层

板块语义分为互斥的 `NORMAL_ATTRIBUTE`、`PRICE_BEHAVIOR_TAG`、`EVENT_TAG`、`STATUS_TAG` 和 `UNKNOWN_TAG`。`NORMAL_ATTRIBUTE` 才是行业、概念和风格等稳定属性；行情、事件、状态标签保留用于展示和筛选，但不参加正常强势板块排序。未知类别可展示，不能静默加入正常强势集合。

解析优先级固定为：同版本 `sector_id` 精确覆盖、输入已有的合法 `semantic_bucket`、合法 `sector_type` 默认属性、未知类别。`sector_id` 是带来源命名空间的精确 ID，不按同名自动合并。

## 关键词规则

旧版 `PRICE_WORDS`、事件词和状态词只产生 `keyword_hint`，并记录 `KEYWORD_CANDIDATE_REQUIRES_ID_REVIEW`；任意名称子串不能直接写成最终语义类别。需要把某个近期强势、昨日首板、涨停等板块纳入或排除时，必须提交该 `sector_id` 的新版本精确覆盖，并留下 `rule_id`、原因和来源。

## 输出字段

语义注册表输出 `semantic_version`、`sector_id`、`bucket`、`role`、`is_attribute`、`is_market_tag`、`normal_rank_eligible`、`override`、`rule_id`、`reason` 和 `keyword_hint`。属性和标签字段分开，不能用一个 `sector_role` 字段同时表达两者。

## 不变量

1. 近期强势、昨日首板等名称关键词默认不进入正常强势板块。
2. `EXCLUDE_FROM_THEME_RANK` 或无效板块即使属于属性类，也不具备 `normal_rank_eligible`。
3. 精确覆盖只对完全相同的 `sector_id` 生效，不能按名称、代码后缀或模糊匹配扩散。
4. 规则/覆盖变更必须产生新的 `semantic_version` 或覆盖版本，历史发布的语义不原地改写。
