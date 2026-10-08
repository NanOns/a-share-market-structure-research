# FP-03 BFF 与字段合同执行

依据：本轮总卡、03 卡、完整合同 §69 和 FP-01 运营语义。合同：`config/v4_research_bff_contract_v1.json` / `V4_RESEARCH_BFF_V1`。

新 API 提供 context、home、股票/板块列表与详情、完整成员、画像/证据/未入选字段、结构/锚点字段、雷达/事件、Forward/结算、数据源及来源/字段/规则/参数/旧模块诊断。原 `/api/v4/current/*` 不改变。

统一返回发布身份、交易日、model namespace、来源/版本、知识谱系与 token。字段分别提供 value、quality、reason、来源摘要/字段、单位、分母、窗口、复权基础、source_as_of、计算域。原 owner 未声明的元数据保持明确空值或 `OWNER_UNIT_NOT_DECLARED`，不猜测；未知值不变成零。

服务端支持代码/中文名称前缀、历史代码归一、分页、状态与多键稳定排序。搜索分别使用身份、代码、名称、alias 索引后合并，拒绝任意 SQL 字段。每页 1–200 条，搜索最多 80 字符，最多 4 个排序键；末位加身份排序保证稳定。参数重复/越界/未知为 400，上下文、日期、发布、模型冲突为 409；不存在与身份存在但不在当日池分别标识。每客户端每分钟 240 请求，超限 429。

JSON Schema 定义统一 envelope、字段 cell 与列表 item；字段字典记录实际适配来源，并另列需重算/接线的字段。历史 timeline / chart 以及 Replay / Compare 保持有合同的 501 状态，由 FP-06/07/12 完成，不返回伪造历史数据。

证据：`REAL_READBACK_AND_ROLLBACK.json` 的逐路由覆盖、`HTTP_READBACK.json` 的实际 HTTP 200/400/409 检查；新增 22 项定向合同测试覆盖分页排序、别名、上下文冲突、边界、数据库篡改、NULL/来源投影与限流。与旧发布/Phase 0/当前 reader/日更等回归加上 UI 权限回滚测试合计 146 项通过。

验收：**PASS（BFF 基础合同与当前真实字段接入范围）**，不表示后续历史图表、Replay/Compare 或未接入业务域已完成。下一阶段：FP-04 六入口框架消费该合同；业务字段缺口按已登记任务推进。
