# B2 增量工程证据：UI、无损传输、Shadow 域隔离

依据 DRIVE_TASK_CARD_R3.md 的 P0-2 DB03、P0-5 与 B2 出口执行。
本包为有界工程增量，不签署完整分母、全消费者、全语义或外部验收通过。

## 代码与实际运行

`product_http_transport_r2.py` 在默认产品 handler 协商 gzip，保留完整 JSON、未知状态和来源字段。10 个协议/内容负例通过，原始 JUnit 为 TRANSPORT_JUNIT.xml。真实六 API 的 identity/gzip 解压 SHA 全部一致：首页 6,313,877 字节压缩为 1,129,951 字节。TRANSPORT_ACTUAL_ORACLE.json 保存原数据与 1/4/8 并发结果。

`core_product_bff_r1.py` 先按已有事件优先级/对象稳定顺序去重，再复制大字段投影。TRANSPORT_HOME_SELECTION_R3_ORACLE.json 六路完整解码 SHA 与修改前全等，原始日志与 PG SQL 意图另存。并发 P95 未明显改善，不宣称性能闭合。

`shadow_server.py` 将损坏 Shadow 合同限定为该域 409，保留 V4 页面服务与写请求 405。两个原 shared HTTP 节点改用当前原生 Shadow handler，不启动旧 V3 DuckDB 工作台；没有将数据库 mock 成可用。`test_fp06_sector.py` 使用真实不可变四表 PG SnapshotR2，保留独立集合手算交集2、并集4、成员3、Jaccard1/2、唯一份额1/3。

SHADOW_DOMAIN_ISOLATION_R3.xml 实际 48 PASS / 0 FAIL / 0 ERROR，另 1 个旧 V3 全 AST 固定节点明确 deselect，原失败仍在基线。该单节点的合法性由 scope 台账独立复审，其他 Shadow 节点均执行。代码/source SHA 在 SOURCE_BINDINGS_UI_TRANSPORT_SHADOW_R3.json；实际运行并非当前全部工作树的单版本完整回归。

## 浏览器与独立对照

UI_BROWSER_INCREMENTAL_R3.json 保存实际浏览器数据状态、390/1440 宽度、D/W/M 和 RAW/QFQ 切换、筛选/空结果、分页、来源抽屉、历史日期跨页保持及 Forward/FEP 来源不足提示。UI_DESKTOP_DIAGNOSTICS_R3.png、UI_MOBILE_DIAGNOSTICS_R3.png 是实际截图。窄屏观察 document_width375 <= innerWidth390。

UI_HTTP_COUNT_ORACLE_R3.json 的原始实际 API 对照为板块400、概念268、历史个股5223、空筛选0，四项相等。第一脚本尝试参数拼写错误的 HTTP400 原始日志保留，修正为正式 type/q 后重跑；这不是业务失败删除。UI_SOURCE/assets 绑定见 UI_SERVER.json。预览 PID51880 命令行确认后关闭释放内存，生产 PID22956 未操作。

## 关闭条件与仍开门

- 本包已满足局部无损传输、独立完整内容 SHA、48节点 PG/负例、UI真实数据与4项数量对照。
- 全分母清账、同冻结 SHA 全回归、全部真实消费者、56类与全语义仍依赖其他工作包，不以局部结果替代。
- 性能仍需双T0冷/热、RSS、内容全校验开销及批准容量阈值；已有1/4/8并发不自签容量 PASS。
- 默认完整生产型 handler 的损坏 Shadow 合同隔离集成仍需与全链 publication 同版本补证。
- 旧 accepted 产物、生产权限、在役端口/DSN/Head未切换。真实交易日、成熟样本及部署授权单列，不能豁免工程缺口。

Drive旧检查点2487a6ff...的远端1,261,356字节重新下载后 SHA256 与本地完全一致，见 DRIVE_CHECKPOINT_BYTE_READBACK_R3.json；该检查点仍是历史中间产物。
