# FOCUS-05 API 与页面阶段记录

> 日期：2026-09-23；当前结果：`IN_PROGRESS / CONTRACT_FROZEN`。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 11、12、13、19 节；FOCUS-00 合同回执、FOCUS-03 输入 manifest 阶段记录、FOCUS-04 outcome 结算阶段记录 |
| prior_stage | FOCUS-00 `FULL_PASS / FOCUS_00_SEMANTIC_KERNEL`；FOCUS-01 schema 已验收；FOCUS-02 `DEGRADED_PASS`；FOCUS-03 与 FOCUS-04 仍 `IN_PROGRESS`，当前无 REAL_FORWARD Focus head |
| stage_contract | `FOCUS_READ_API_V1`；只读路由 `/api/v3/focus-tracker/{summary,items,episodes/{id},stocks/{id},sectors/{id},transitions,statistics,runs}`；`FOCUS_TRACKER_UI_V1`；`FOCUS_STATISTICS_MATERIALIZATION_V1`；回放子验收 `FOCUS_STATISTICS_REPLAY_PROBE_V1`；HTTP 冒烟子验收 `FOCUS_HTTP_ROUTE_SMOKE_V1`；`FOCUS_ITEM_CONTEXT_V1`；本次详情查询子合同 `FOCUS_ENTITY_DETAIL_BATCH_V1` |
| stage_boundary | API 只从 PostgreSQL 已激活 Focus run、head 与物化表读取；每请求在一个只读一致性事务内固定单一 `focus_run_id`，子查询必须复用该身份；PG 不可用一律返回 503，禁止 DuckDB、文件 pointer、行情或扫描器回退。没有有效 head 时明确报告无数据/不可用，不伪造空池或历史结果。列表补充首次关注日和会话数只能来自 episode 首日及 AS_RECORDED observation 行数；收益/回撤、entry sector、waiting_for、invalid_if 只读来源事实，不在页面重算/推断。实体详情证据必须按 episode 批量取数而非逐 episode 往返，且锚点、observation 和 target 日期均限制在所选 run 交易日以内。统计物化任务按指定 run 交易日截断锚点及结果目标日，按来源族、实体、选择/来源/状态合同、锚点、期限、evaluation basis、价格口径隔离；只在至少 30 条完整结果且 5 个独立信号交易日时写描述性分位值，不作概率表述；页面请求只读取该 run 显式 statistics head，不扫描 outcome 历史 |
| evidence | 设计阶段门规定 FOCUS-00 十项语义硬门和核心数据合同通过后开始页面工作；FOCUS-00 回执为 FULL_PASS。PG Focus schema 与 outcome schema 已应用并只读核验。数据库当前无有效 Focus head；上阶段结算 preview 返回 `NO_VALID_ACCEPTED_FOCUS_HEAD`。统计物化 schema `FOCUS_STATISTICS_MATERIALIZATION_V1` 已应用，SHA-256 `8c7d453f46dbb8f95e87b703cc0780b8612cf44aa3362f34c2f7349d40aa970`，3 表、20 项约束，真实批次/行/head 均为 0；rollback rehearsal 与只读 verifier 通过。物化 preview 返回 `NO_ACTIVATED_FOCUS_RUN`，未写批次。`FOCUS_STATISTICS_REPLAY_PROBE_V1` 通过：30/5 样本 READY 且分位指标存在；29 完整行或 4 信号日不出指标；incomplete 单独计数；REAL_FORWARD/HISTORICAL_RECONSTRUCTED 与 SOURCE_A/SOURCE_B 分组隔离；未来 target 被截掉；同输入批次 ID 稳定；接受新 outcome revision 后 digest 和批次 ID 改变，显式 head 转向新批次。API probe 验证物化 head 缺失和无 run 时响应结构安全、历史详情隐藏未来结果。新增 HTTP 层 probe 访问 `/v3/focus-tracker` 得 200、真实无 head 响应 `NO_ACCEPTED_RUN`、PG 不可达响应 503 `PG_UNAVAILABLE`，`fallback_used=false`；临时 DuckDB 在系统临时目录，退出后删除。`FOCUS_ENTITY_DETAIL_BATCH_V1` 已落地：股票/板块实体详情最多读取 50 个 episode，先查 episode 元数据，再分别批量读取 transitions、anchors、observations、accepted outcomes；所有关联保留 episode_id 映射，观察/锚点/target 截止所选 run 交易日。rollback API probe 在 2 个 episode 和 52 行候选历史（接口返回上限 50）fixture 下均测得固定 6 条查询（1 次 run 解析 + 1 次元数据 + 4 组批量证据读取）；episode 与证据映射正确，超上限时显式 `episodes_truncated=true`；查询数不随 episode 数增加。FOCUS 测试 `56 passed, 350 deselected`；HTTP smoke 通过；Python compileall、内嵌 UI JavaScript 语法检查通过；`git diff --check` exit 0（仅仓库既有换行格式提示）。IAB 浏览器打开 localhost 被 `ERR_BLOCKED_BY_CLIENT` 拦截，当前没有其他连接浏览器，因此这轮未完成浏览器视觉验收。所有 fixture 持久化业务数据写入数为 0。真实 run 统计、真实数据浏览器视觉及目标硬件 P95 尚未验收 |
| acceptance_result | **`IN_PROGRESS`** |
| next_stage | `FOCUS_ENTITY_DETAIL_BATCH_V1` 回滚 fixture 子验收已通过。下一项需要 FOCUS-03/04 产出真实 activated Focus run/head；届时执行真实页面列表/筛选/股票与板块详情/统计读数验收、浏览器视觉检查和目标硬件 P95 测量。当前数据库无 activated head，且本地浏览器 localhost 被拦截，因此这些验收有明确前置依赖；FOCUS-05 保持 `IN_PROGRESS` |

## 冻结响应公共字段

每个成功响应携带 `api_contract`、`focus_run_id`、`trade_date`、`revision`、`source_authority_contract_id`、`state_contract_id`、`evaluation_basis`、`data_status` 和本请求实际读取的 `source_family` 能力。日期字段始终使用交易日，不混入自然日或本地文件时间。无 head 为 `NO_ACCEPTED_RUN`，不能映射成 COMPLETE 空集合。PG 连接/查询失败返回 HTTP 503、`PG_UNAVAILABLE` 和 `retryable=true`。

## 总览与板块成员交互修订（2026-09-23）

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 8、15.3、19.2 节；`FOCUS_TRACKER_UI_V1`、`FOCUS_READ_API_V1` |
| stage_contract | 页面主视图为最新 VALID accepted Focus head 下的持续观察总览，不提供用户按日切换的主视图。各行读取该 head 下在榜 source items 与 `ACTIVE_FOCUS` episodes 最新已记录状态；详情和变化记录仍保留交易日事实。板块名打开按需分页弹窗；成员列出强势判定、同 head 下个股观察状态及已记录路径/表现。证券名称按当前 run publication_id 从发布绑定名称表解析。 |
| stage_boundary | 不改变每日 observation、episode、anchor、outcome 的时间序列数据合同；不把多 source episode 合并为单一证券 episode；板块强弱只读取同 trade_date/publication/domain 的 accepted `member_state` result，且限定 `MEMBER_STATE_RESULT_V3` 与 `SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC`。缺证据保持 UNKNOWN。成分依冻结篮子，按页返回；不从研究页面或行情临时推断成员/强弱。 |
| evidence | 页面移除重复页内头部、交易日选择和每日批次 tab；观察板块与独立个股表移除来源/实体类型列；证券名称/代码分行；板块改为 `<dialog>` 交互，调用新增分页参数，先强势后非强势/未知排序。`FOCUS_READ_API_V1` 板块成员路由回滚探针覆盖 publication-bound 名称、强弱排序、个股 episode 状态、分页及 503 fail-closed；Focus 定向测试 `59 passed, 355 deselected`，HTTP route smoke、Python compileall、内嵌 JS 语法通过。 |
| acceptance_result | `FULL_PASS / FOCUS_OVERVIEW_AND_SECTOR_DIALOG_UI`（自动化/API 子验收）；工作台部署后的实际交互视觉验收待服务重载后补记。FOCUS-05 总阶段仍 `IN_PROGRESS` |
| next_stage | 重载本地 workbench service 后确认真实 REAL_FORWARD run 的板块弹窗与股票名称/状态响应；进行浏览器视觉和分页操作验收。后续继续 outcome/统计与目标硬件 P95 门禁。 |

“总览”定义为截至最新有效交易日的当前持续观察状态，而不是跨日合并原始状态或抹去日期。详情时间线保留逐日证据供解释状态变化；页面不再要求用户每天选择日期来查看持续观察池。

## 当前实现与门禁证据（2026-09-23）

## 用户反馈 UI 修订阶段（2026-09-23）

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6、7、15.3、19.2 节；当前 UI 合同 `FOCUS_TRACKER_UI_V1` |
| stage_contract | UI 展示修订：工作台内联入口；来源/实体分栏；状态值仅展示中文映射；路径、场景、板块筛选必须从可见数据生成；详情只用可读字段呈现。数据库状态、身份、观察期限和 episode 语义不变 |
| stage_boundary | 不删减 V3.3 今日 membership；不改变 source contract、tracking union、episode 终态、长期留存和历史可查合同；不以界面分页/折叠充当数据库限量；不在客户端重算业务状态 |
| evidence | 用户截图与九项反馈；2026-09-23 已接受 `REAL_FORWARD` run `/items` 返回 310 条：V3.3 个股候选 273、V3 板块 17、V3 个股观察 20。页面已改为工作台内联入口、纯中文可读标签、板块/个股分区及板块成分展开、字段分行、自然语言详情/状态变化、来自已加载数据的筛选项。实际 run 板块目录返回 17 个中文名称；板块成分从该 episode 冻结篮子读取。HTTP/API 实测可按板块名过滤个股，V3.3 来源支持状态筛选可返回 121 项。完整 Focus 测试 `59 passed, 355 deselected`；只读 API probe、HTTP fail-closed smoke、Python 编译、内嵌 JavaScript 语法和浏览器页面加载检查通过。`git diff --check` 通过（仅 `v2/index.html` 换行格式提示）。 |
| acceptance_result | `FULL_PASS / FOCUS_UI_FEEDBACK_REPAIR`（此 UI 修订子阶段）；FOCUS-05 总阶段仍 `IN_PROGRESS` |
| next_stage | UI 反馈修订已通过。FOCUS-05 后续继续完成真实 outcome/统计展示与目标硬件 P95 等设计阶段门；V3.3 累计存储增长另开版本化留存/压缩合同。 |

### 数据增长优化议题（独立于本 UI 修订）

用户已指出每日 200+ V3.3 候选带来的累计增长，并明确具体方案待定。当前冻结设计不允许随意限量、按固定天数删除活动 episode 或物理清理历史。需在独立版本合同中比较并量化：保留逐日轻量 membership/状态摘要，同时将大体量 immutable `source_facts` 改为内容寻址共享 blob；统计每日新增/重复/净增长与 episode/outcome 到期退出率；定义历史压缩、备份恢复、引用完整性和审计验收。候选展示折叠只降低页面拥挤，不视为存储优化。本 UI 阶段不执行该议题。

- 新增 `src/focus_tracker/read_api.py` (`FOCUS_READ_API_V1`)；`summary/items/episodes/{id}/stocks/{id}/sectors/{id}/transitions/statistics/runs` 均为 GET 只读查询。连接进入 `REPEATABLE READ READ ONLY` 事务，请求只解析一次 run，之后 SQL 绑定同一个 run ID；只接受已激活 run，默认 head 必须 VALID，若存在 replay backlog 则不回显较旧 head。显式历史 run 会标注 `HISTORICAL`；请求 run 落在 `REPLAY_REQUIRED` 返回 409。观察池将当日 source item 与仍处于 `ACTIVE_FOCUS` 的退出后 episode 合并查询，但保留 source family 与 episode 独立身份；所有动态筛选值参数化，页大小上限 100。
- `PostgreSQL` 错误映射到 HTTP 503 / `PG_UNAVAILABLE`，不会经过 Workbench DuckDB API connection provider；API 的 DSN 读取服务环境变量或项目 `config/.env`。请求日期无效返回 400，路径未知返回 404，无有效 head 返回 `NO_ACCEPTED_RUN`（或 `REPLAY_REQUIRED`）且 `data_status=UNAVAILABLE`，不把空行包装成 `COMPLETE`。
- 新增 `src/workbench_db/focus_statistics_schema_v1.sql`：不可变 `focus_statistics_batches`、分组 `focus_statistics_rows`、每个 Focus run 显式指向的 `focus_statistics_heads`。应用器默认回滚演练，`--apply` 才安装；真实 schema 只读验收为 3 表、20 约束、0 数据行。
- 新增 `scripts/materialize_focus_statistics.py` (`FOCUS_STATISTICS_MATERIALIZATION_V1`)。默认 preview，只读取显式或最新 activated run 的 accepted outcome heads；锚点日与 target 日都截断到 run.trade_date；仅 OBSERVED 且 forward return/MFE/MDD 齐全记为完整，其余计 incomplete。分层字段固定为 source family/entity/selection contract/source model contract/state contract/anchor type/horizon/evaluation basis/price basis。`percentile_disc` 计算 P25/中位数/P75；30 完整结果且 5 信号交易日双门通过才物化统计数字，否则只记录计数和 `INSUFFICIENT_SAMPLES`。批次 digest 包含有序 outcome 身份、状态、结果和 input digest；同输入同批次 ID，可重复插入；行、批次和 head 在单一事务写入。无 activated run 返回显式状态，不造空批次。
- 物化器抽出 `materialize_in_transaction`，生产与探针共用同一选择、分组、样本门、摘要、写入逻辑。新增 `scripts/probe_focus_statistics_materializer.py`：临时表中构造 30/5 正样本、29 行和 4 日期负样本、不同 evaluation basis/source model 合同、SOURCE_REVISED 不完整项、未来 target 和 accepted revision 更新；相同输入连续 apply 两次后仍为一批/一组一行；更新 accepted revision 后新摘要与新 batch 生效；最后回滚确认批次/行/head 持久写入均为 0。
- `statistics` API 已接只读物化表：先以请求固定的 `focus_run_id` 查显式 head，再读该 batch 分组；无 schema / 无 batch 都明确不可用，绝不聚合 outcome。新增 rollback-only 统计 fixture 验证 batch/head/group 映射与 READY 样本门，探针结果 `persisted_changes=0`。
- Episode outcome 详情额外限制 anchor.trade_date 和 target_trade_date 均不晚于所选 run.trade_date，避免历史页面泄露未来结果。
- 统计页面对无 run/物化表/物化批次的响应提供安全空数组与明确状态；门状态读取 `gate_status`，避免接口真实字段与 UI 列绑定不一致。
- `FOCUS_ITEM_CONTEXT_V1` 扩充 `/items`：episode 首次关注日、所选 trade_date 截止的 distinct AS_RECORDED observation 会话数、first-supported anchor、entry/current sector、首日收益/峰值回撤以及来源原始 `waiting_for`/`invalid_if`。退出后 follow-up 行从该 episode 的 first-focus run 恢复来源条件，source 事实缺失时保留 observation facts，不构造条件。session count 对无 episode 返回 NULL，不把缺关联误报为 0。
- 观察池 UI 现在显示首次关注、已记录会话、六维状态/连续性与比较缺口、原/当前支持板块、收益/回撤、等待/失效条件和质量；会员筛选增加 `NONE/UNKNOWN`。HTTP smoke 校验这些列表合同标记，PG rollback fixture 对 CURRENT 与退出后行验证首次日、会话数、收益、回撤、entry sector 与来源条件值；`persisted_changes=0`。
- FOCUS 定向测试首次运行 55 passed、1 failed，失败点是旧 FOCUS-00 单测漏传 gap audit digest 却预期 DATA_GAP。已按 V2.1 的审计终态边界更正测试，并独立登记 [FOCUS Outcome 测试漂移审计](FOCUS_OUTCOME_TEST_DRIFT_AUDIT_20260923.md)；该修复不更改运行时 outcome 分类，FOCUS-04 settlement integration audit 仍独立开放。
- 可复现命令（仓库根目录 PowerShell）：`$env:PYTHONPATH='src;scripts'; python -m scripts.apply_focus_statistics_schema_v1` 做回滚迁移演练；已验收后 `python -m scripts.apply_focus_statistics_schema_v1 --apply` 持久化 schema；`python -m scripts.verify_focus_statistics_schema_v1` 只读核验；`python -m scripts.materialize_focus_statistics` 默认 preview，需物化时对已激活目标 run 使用 `--focus-run-id <id> --apply`；`python -m scripts.probe_focus_read_api` 做 rollback-only API 映射/未来 outcome/缺 head 检验；`python -m scripts.probe_focus_statistics_materializer` 做物化算法回放验收。
- 新增 `scripts/probe_focus_http_routes.py`：用临时 DuckDB 仅初始化工作台 HTTP 外壳，验证关注跟踪页面路由、真实 PG 无 head 响应及 PG 不可达 503 fail-closed；临时目录由脚本自动清理。
- 可复现命令（仓库根目录 PowerShell）：`$env:PYTHONPATH='src;scripts'; python -m scripts.apply_focus_statistics_schema_v1` 做回滚迁移演练；schema 通过验收后，`python -m scripts.apply_focus_statistics_schema_v1 --apply` 才持久化安装；`python -m scripts.verify_focus_statistics_schema_v1` 只读核验；`python -m scripts.materialize_focus_statistics` 默认 preview，需物化时对已激活目标 run 使用 `--focus-run-id <id> --apply`；`python -m scripts.probe_focus_read_api` 做 rollback-only API 映射/未来 outcome/缺 head/实体详情批量查询上限检验；`python -m scripts.probe_focus_statistics_materializer` 做物化算法回放验收；`python -m scripts.probe_focus_http_routes` 做 HTTP 路由与 PG fail-closed 验收。
- 新增 `src/workbench_service/static/focus-tracker.html`，可在工作台“关注跟踪”入口打开。包括交易日 head 选择、观察池筛选、状态变化、run 历史、episode/股票/板块详情和样本门统计；子请求显式携带固定 `focus_run_id`；PG 503 显示不可用且不回退。
- `python -m compileall -q src/focus_tracker/read_api.py src/workbench_service/app.py`、Node `new Function` 校验内嵌 UI 脚本通过。新增 `scripts/probe_focus_read_api.py`，用 PG session temporary schema 和 rollback-only fixture：构造同证券的新 episode 与退出后仍活跃的旧 episode，验证观察池返回两条独立 episode、SOURCE/退出后状态筛选、板块过滤、股票详情两段历史、episode outcome 与 transition 映射、历史 run 标注及 replay backlog fail-closed；探针报告 `persisted_changes=0`。另在只读事务执行 summary、items（含全部筛选）、transitions、runs、episode 全部详情子查询、entity 查询，SQL 均通过。当前真实库 API 返回 `NO_ACCEPTED_RUN`，统计返回 `STATISTICS_NOT_MATERIALIZED`；使用不可达端口验证 `503 / PG_UNAVAILABLE / retryable=true`，无效交易日为 400、未知路径为 404。事务结束 rollback，没有写入。
- 回滚 fixture 已覆盖列表行上下文与筛选、episode/outcome 映射、统计 30/5 正反样本门、未来日期隐藏、实体详情 50 条上限和固定查询数；这些合同不再列为待办。当前真实库仍无有效 run，因此真实业务行验收、真实统计物化结果检查、浏览器视觉检查和目标硬件 P95 尚未执行。真实验收的阶段门依赖 FOCUS-03/04 生成合格 REAL_FORWARD accepted Focus head；本阶段不改动 TDX 输入目录。

## 列表与详情约束

- `items` 默认只读请求固定 run 的 immutable daily items 并关联同一 run 的状态观察/当前投影；source family、日期、membership、validity、path、sector、scenario、quality 筛选均参数化；页大小上限 100，筛选/排序不得改变身份。
- `episodes/{id}`、`stocks/{id}`、`sectors/{id}` 的 transition、anchor、observation、outcome、target outcome head、source facts 都限制在明确的 run 或 episode 身份，并把历史与当前 head 状态分开标注。

## 首个真实 run 后续验收（2026-09-23）

FOCUS-03 首个 REAL_FORWARD run 已激活：`focus-run-f8ba1c4915d1c330506d9bc8954b0a2d`，head `VALID`，日期 `2026-09-23`。受控重启后线上 `/summary` 默认及 `?trade_date=2026-09-23` 均返回 `AVAILABLE / REAL_FORWARD`；`/items` 共 310 行，分组为 V3.3 今日候选 273、V3 板块跟踪 17、V3 个股观察 20。关注跟踪页浏览器验收通过，页面显示 9/23、REAL_FORWARD 和 310 条。

因此本文件前文“当前数据库无有效 Focus head”仅描述 FOCUS-05 开发期间状态，已由该 9/23 run 更新。9/22 未生成 REAL_FORWARD Focus head，显式查询仍是 `NO_ACCEPTED_RUN`，按“不回退/不伪造”合同保持空态。技术结果哈希仍 fail-closed，310 项 validity 为 `UNKNOWN`、path 为 `DATA_UNAVAILABLE`；真实 outcome 仍未到期且统计物化无数据，因此 FOCUS-05 总体状态保持 `IN_PROGRESS`。
- `transitions` 与 `runs` 按交易日、revision 稳定分页；统计只读取当前请求 run 所绑定的 outcome head，并应用样本门与来源族/评价 basis/合同版本分层，不合并不同 authority。
- UI 页面不得自行推导 validity、membership、follow-up、path 或 outcome；缺失值展示 UNKNOWN/UNAVAILABLE 原状态。PG 503 时展示不可用和重试入口，不切换至 DuckDB 或文件缓存。

## 工作台内嵌总览与强势成分交互最终复核（2026-09-23）

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 8、15.3、19.2 节；用户 2026-09-23 界面修订要求 |
| stage_contract | Focus 菜单沿用工作台同页切换模式，内容在主区域内嵌显示；总览固定读取最新 VALID accepted Focus head 当前观察池，不要求用户选择某一天；历史详情仍按真实交易日呈现。观察板块和独立个股分表；行内不重复展示来源/实体类型；证券名在上、代码在下；板块成员用分页 API 按需加载到弹窗。 |
| stage_boundary | 不合并来源 episode，不改每日持久化身份与时间线；总览日期只用于标明数据截至时间，不构造跨日合成状态。板块成分的强弱只在强度证据摘要与当前冻结观察值精确一致时显示，否则为未知。个股独立状态仅取同一个 accepted head 的记录。 |
| evidence | 本地工作台浏览器实际点击“关注跟踪”后，页面在主工作区内嵌出现，URL 保持工作台根路径；显示 2026-09-23 当前总览 310 条，17 个板块、20 只独立观察个股、273 只 V3.3 候选分组折叠分页。列表的板块名/股票名与代码分行、无来源和实体类型列。点击“玻璃基板”弹窗分页读取 62 只冻结成分，`三峡新材 SH.600293` 首行显示“强势”，其他成员显示各自强弱、个股观察状态、路径/规则状态、已记录表现与数据质量；“复合铜箔”弹窗验证分页总数 48。总览点击板块与弹窗均在原工作台页面内完成。修掉详情按钮下仍残留的来源标签。Focus 定向测试 `59 passed, 355 deselected`；API 回滚探针通过且 `persisted_changes=0`；HTTP route smoke、Python compileall、`git diff --check` 通过。 |
| acceptance_result | `FULL_PASS / FOCUS_OVERVIEW_AND_SECTOR_DIALOG_UI`（本次工作台内嵌与真实 2026-09-23 数据交互复核）；FOCUS-05 总阶段仍 `IN_PROGRESS` |
| next_stage | 继续处理 FOCUS-05 尚未完成的真实 outcome / 统计发布验收与目标硬件 P95；UI 总览及板块弹窗已不再阻塞。 |
