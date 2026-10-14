# V4 UX R4 收口报告

**验收结论：`V4_PRODUCTION_CUTOVER_BLOCKED`。** B-01/B-02 修复已提交并推送；在隔离 R2 schema 上，本轮源码版 API 和内置浏览器预览可工作。正式 28765 未切换，R2 authority 未写入生产根。业务生产者、20 个 owner 样本、六入口宽/窄双视口和截图门仍不满足，禁止宣称 FULL_PASS 或完成切换。

## 阶段合同与环境

- 执行依据：用户指定 R5 任务卡（2026-10-14）及最新适用升级文档 [`V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`](../../../../docs/upgrade/V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md)。阶段合同：修复 B-01/B-02；用 2026-10-13 已接受输入做只读验收；不得伪造 Cohort/FEP、不得启用自动日更/变更 Head；所有核心门通过后才允许切换 28765。
- 代码基线 HEAD：`d2f9dfb99221e9fe1cd78b302b5b4b135f380ecf`。提交：`54abe9f1ef33d9d2836790c405ec7b43a5af3afa`（代码），`664d310077ebf8912302585d0c3371396238cba5`（唯一收口报告），均已推送到 `origin/codex/v4-r4-closeout-20261014`。
- 28765 回滚点：PID `34284`，旧包 `V4_PACKAGE_1.0.0_88cc19deae3b`，EXE `G:\codex work\v4-production-20261012\versions\V4_PACKAGE_1.0.0_88cc19deae3b\DaAV4\DaAV4.exe`。进程未停止、包未修改、未切换。内置浏览器原先读到 T0 `2026-10-13`、engine RUNNING、`auto_daily` 暂停；本轮未运行盘中日更、未改变正式 Head/token。TDX 只读输入未改。
- 受限只读 PG 准备的 R2 schema：`v4_f05334ead7664a2b939a283bb3ac15ed1200ea2138fa93ccd8cbb58c`；database `market_research` / OID `646711`，host identity `127.0.0.1/32`，port `5432`，T0 `2026-10-13`。cluster `system_identifier` 和 R1 schema 名未封存，故 PG 身份证据不完整。投影计数 `{focus:3151, radar:177, sectors:400, stocks:5225}`；summary 110,096 B；producer SHA `9b37c0dd46a8480925e5848317e186ec1eadb999da21c639bf9805ea45da173d`；content digest `c5b0efd2a21afbeb17e6cca5ba56e21a8fe805853826de0d3b47871e0954492d`。隔离 authority 仅位于 `G:\codex_tmp\r5_v4_r2_shadow_prodsrc_20261014\config\v4_read_index_authority_r2.json`；验证了生产根未产生 R2 authority。该 schema 使用隔离名称，不覆盖 sealed schema。
- 浏览器验收只使用 Codex 内置浏览器（28765 生产页及 28768 隔离预览）；未调用外部浏览器。28768 是源码版静态资源 + 生产数据 owner 只读读取 + 独立 PG schema 的预览服务，不是生产部署。

## 修复、测试及 HTTP 证据

1. **B-01**：新增精确 R1 legacy capability 检测。仅当响应明确标记为允许的 R1 legacy 状态时，HTTP 层跳过 R2 专用 512 KiB/字段形状检查；未标记响应和 R2 仍受 guard 约束，错误保持 fail closed。
2. **B-02**：R2 content digest 采用按 workspace + 完整 digest 派生的版本化 schema 名，旧 schema 保持只读兼容；binding 校验 producer SHA；authority 更新保留 revision history，不覆盖旧修订。
3. 定向合同测试：`tests/test_v4_ux_r2_contract.py` 11/11、`tests/test_v4_ux_r3_routes.py` 9/9 通过，`git diff --check` 通过。全仓 pytest 未成功加载，因该 checkout 缺少 `src/common/disposable_paths.py`；不计为全量回归。
4. R1 兼容复现：28766 旧 R1 `/api/v4/home` n=8 HTTP 200，5,060,827 B，P50 279.43 ms、P95 370.04 ms。修复防止旧 R1 被 R2 guard 误拒绝；5.06 MB 本身不满足 R2 首页体积目标，因此此数字仅证明降级兼容，不代表首页性能验收通过。
5. R2 隔离预览（28768，n=8；耗时 ms）：

| 路由 | 响应字节 | 冷请求 | P50 | P95 | 结果 |
|---|---:|---:|---:|---:|---|
| home | 115,462 | 216.60 | 217.24 | 340.38 | 8/8 HTTP 200 |
| stocks | 67,167 | 112.48 | 114.95 | 225.69 | 8/8 HTTP 200 |
| sectors | 88,043 | 214.82 | 214.80 | 217.99 | 8/8 HTTP 200 |
| focus | 82,807 | 358.99 | 249.61 | 377.03 | 8/8 HTTP 200 |
| radar p1 | 49,605 | 215.45 | 211.22 | 330.77 | 8/8 HTTP 200，总数 177 |
| radar p2 | 49,716 | 347.41 | 220.01 | 347.41 | 8/8 HTTP 200，总数 177、offset 30 |
| stock detail | 158,677 | 153.74 | 214.77 | 363.32 | 8/8 HTTP 200 |
| sector detail | 56,969 | 1,082.27 | 1,085.01 | 1,198.83 | 8/8 HTTP 200 |

   P95 展示了首页/API 列表与关键详情的真实差异；板块详情超过 1 秒，R4 延迟门未通过。性能请求仅代表 28768 隔离预览，不代表现役 28765。

## 内置浏览器验收

- 28765 生产页：旧首页读取 stocks 5,225/sectors 400、Focus 变化 177/展示 30、风险 14；Radar/Forward 首页仍显示来源未接入，直达 `/v4/research/radar` 提示“没有找到该入口”。生产包版本仍为旧 `1.0.0_88cc19deae3b`。
- 28768 源码预览：Home 加载真实摘要（stocks 5,225/sectors 400/radar 177），清楚说明 Radar 是事件雷达、正式优先级未发布，Forward 正式样本未准入且不伪造计数。Radar p1/p2 均渲染真实事件、有效性/路径/场景/资格及来源字段，第二页显示共 177 条、offset 30。
- 28768 六入口逐项检查：Home、板块研究、个股研究、关注跟踪、市场与事件、数据与诊断。板块列表展示 400 行规模、代理指标与成熟度/健康度 Owner 缺失原因；煤炭详情可见成员数据、时间变化解释及“非严格 PIT”标记。个股列表显示 5,225 行，三一重能详情显示真实成交行情图及来源/周期操作。Focus 显示分母 3,151、行业未映射 0，Top5 中文名称为电气设备/化工原料/软件服务/汽车配件/专用机械；观察页标出 3 条真实状态变化、27 条来源不足观察，并未把来源不足计作事件。Forward 各栏明确显示未授权 Cohort owner、首次捕获来源未验证、结算 owner 缺失、FEP 模型未准入。市场页显示四轴值及风险环境；诊断页提供生产源健康、来源版本、日更失败状态入口。
- 双视口任务未完成：当前内置浏览器可见接口没有公开 viewport override。没有用缩放模拟窄屏。保存到仓库的截图为 **0 张**；六入口宽/窄截图门未通过。DOM/AX 检查也未代替视觉截图要求。
- 真样本门未通过：有代表性浏览器观察但没有按任务卡完成至少 20 个分层真实 owner 样本字段对账。浏览器检查到了部分页面，不构成完整 UI/业务验收。

## U01–U16 唯一状态

状态值依任务卡限定。`FAIL` 表示有可复现的生产失败或明确缺失；`NOT_VERIFIABLE` 表示没有满足完整 owner/跨日期/样本验收证据。

| ID | 状态 | 证据摘要 |
|---|---|---|
| U01 | `FAIL` | 生产首页 Radar 源未接入且直达入口 404；隔离预览事件 Radar 真数据/第二页可读，但正式全市场优先级 producer 未发布，未部署。 |
| U02 | `FAIL` | 生产首页无 Forward 来源；预览候选未验证、无授权 Cohort Owner，正式样本数合法留空。 |
| U03 | `NOT_VERIFIABLE` | 板块页标为验证中；未按至少两个可比日重算轮动前序及 NONE/UNKNOWN 真例。 |
| U04 | `FAIL` | 市场页有风险环境，但个股结构、板块生态、市场压力三类独立风险 producer/分母/改善和持平证据未齐。 |
| U05 | `FAIL` | 400 板块页显示成熟度/健康度 owner 未发布；D2 lifecycle producer 和 20 个样本复算缺失。 |
| U06 | `NOT_VERIFIABLE` | 煤炭详情可打开，生命周期及非严格 PIT 标示可见；历史序列的 NONE 与 UNKNOWN 不等价验收未做。 |
| U07 | `NOT_VERIFIABLE` | 三一重能详情及行情图可见；scenario/status/detector/unknown predicates 与 R2 owner 未逐字段核对。 |
| U08 | `NOT_VERIFIABLE` | Focus 真实观察显示资格、成员、有效性和 operational owner 未知；四态证据清单与 D2 owner 对账未完成。 |
| U09 | `NOT_VERIFIABLE` | 个股详情有 SH.688349 身份与行情；未按任务卡验 `SZ.301660`、旧股、无报价及别名样本。 |
| U10 | `FAIL` | 源码预览集中度已显示中文 Top5 且 unmapped=0；现役 28765 仍是旧包、未安装此修复，不能算生产通过。 |
| U11 | `NOT_VERIFIABLE` | Focus 表展示 owner-reported unknown membership/validity、operational owner unknown；observation/episode/最新观察逐字段一致性未核验。 |
| U12 | `NOT_VERIFIABLE` | 观察事件中文名/原因/来源不足可见；Focus 第 2 页、同日多事件反例及过滤证据未验。 |
| U13 | `FAIL` | 已实现缺源显式状态，但候选捕获、Cohort 准入、结算/FEP 管道缺授权 owner，超出仅等待未来样本成熟。 |
| U14 | `NOT_VERIFIABLE` | 市场四轴与真实风险环境可见；五指数 5/20 会话、OHLC 图和单位未双视口核对。 |
| U15 | `NOT_VERIFIABLE` | 本轮未核验可交易分母、规则未知证券样本与 UNKNOWN 筛选/负例。 |
| U16 | `NOT_VERIFIABLE` | 本轮未核验精确连板分类、逐类中文详情及真实分页。 |

## 切换门与下一步

- 验收：`V4_PRODUCTION_CUTOVER_BLOCKED`。生产 R2 authority 保持缺失；28765 上 Radar 仍失败。源码预览成功不替代生产部署；D2、风险、Cohort/FEP、20 真样本、六入口宽/窄截图及板块详情性能门均未通过。
- 生产保护：28765 与旧 EXE 保持运行；未部署、未回滚、未更改旧包；`auto_daily` 仍暂停；正式 Head/T0/token 未变。
- 下一步继续在该已授权阶段任务内修复并验收缺口；只有任务卡核心门通过后才切换 28765。该报告不是外部接受或进入下一阶段授权。