# M8B 历史结构合同 v1

## 范围与身份

历史板块、队列结构与覆盖率属于 `LOCAL_RECONSTRUCTED` 分析数据，不是实盘观察，
不得写入 observations、outcomes 或替换正式发布头。所有结果以 `slice_id`、交易日及
业务实体组成不可变键；相同键只有全部内容一致时才允许幂等重放。

## 持久化

- `sector_base_daily`：板块/日期基础、覆盖率、强度、形态及成员口径。
- `historical_structure_daily`：证券/日期/队列命中、层级、排名、证据和质量码。
- `stock_structure_summary_daily`：证券/日期的队列汇总与研究分层。
- `historical_coverage_daily`：逐日技术、行情、成员及结构能力覆盖率。

历史成员口径必须显式标记；当前成员快照不得伪装成点时历史成员。未知结构保持
`NULL`，不能折叠成未命中。

## 只读接口

- API13 `GET /api/stocks/{security_id}/structure-history`：返回绑定快照内的逐日结构。
- API14 `GET /api/queues/{name}`：`include_analysis=1` 时读取历史结构，保留稳定
  `queue_rank`，另给出筛选后的行号。
- API15 `GET /api/evidence/{queue}/{security}`：`format=groups` 返回摘要、分组历史
  证据和合同身份；默认格式保持旧接口兼容。

所有接口仅解析所选发布显式绑定且状态成功的分析快照；无绑定返回
`ANALYSIS_NOT_BUILT`，不得回退到未来数据或未封存输入。
