# V4 UX R4 收口报告

**结论：`V4_PRODUCTION_CUTOVER_BLOCKED`。** 本轮完成并推送了 R1 首页兼容修复和 R2 索引修订隔离代码，但同版 R2 索引、业务生产者、全量真样本、六入口双视口及切换验收没有完成。28765 保持原服务，未切包。

## 阶段合同与现场

- 执行依据：用户指定的 R5 任务卡（2026-10-14）；同时核对最新适用的 [`V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`](../../../../docs/upgrade/V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md)。阶段合同为修复 B-01/B-02，使用 2026-10-13 已接受数据做只读 PG/API/UI 验收；不得伪造 Cohort/FEP，不得启用自动日更或更改 Head；所有核心门通过才切换 28765。
- 代码基线：`d2f9dfb99221e9fe1cd78b302b5b4b135f380ecf`。本轮代码提交：`54abe9f1ef33d9d2836790c405ec7b43a5af3afa`，分支 `codex/v4-r4-closeout-20261014`。
- 在役保底：`127.0.0.1:28765`，PID `34284`，包 `V4_PACKAGE_1.0.0_88cc19deae3b`，路径 `G:\codex work\v4-production-20261012\versions\V4_PACKAGE_1.0.0_88cc19deae3b\DaAV4\DaAV4.exe`。未停止、未修改。内置浏览器显示 T0 `2026-10-13`、引擎 RUNNING、自动日更暂停、该日已发布。`auto_daily` 状态保持暂停。
- PG/上下文：生产根的受保护角色配置可供只读服务使用；HTTP context 在 `2026-10-13` 返回可用上下文。为避免将上下文值写入报告，token 已脱敏；本轮未封存精确 Data/Research/Joint Head SHA、cluster system identifier、R1 schema 名称，**PG 身份门未验收**。R2 authority/index 在生产根缺失；R2 schema 因未准入生成而不存在。
- 禁止修改的 TDX 根未触碰；测试临时目录仅在 `G:\codex_tmp`。浏览器验收仅使用 Codex 内置浏览器，没有调用外部浏览器。

## 已完成修复与证据

1. **B-01 代码修复**：仅当 BFF 返回允许的 R1 legacy 状态且带精确 capability 标记时，HTTP `/api/v4/home` 跳过只适用于 R2 摘要的 512 KiB/字段形状校验；未标记或 R2 响应仍运行校验，R2 读取/摘要错误仍 fail closed。
2. **B-02 代码修复**：R2 producer digest 修订写入以 workspace 与完整内容 digest 派生的新 schema；旧未加修订 schema 只读兼容。Authority 更新保留旧/新 revision history，不覆盖旧 PG schema 中的 sealed 对象。此次只验证合同与命名逻辑，**未在正式 PG 生成索引或改 authority**。
3. 定向测试：`tests/test_v4_ux_r2_contract.py` 11/11、`tests/test_v4_ux_r3_routes.py` 9/9 通过；覆盖 R1 明确降级标记、R2 大响应仍受限、digest schema 隔离及路由合同。完整 pytest 配置先前因当前 checkout 缺少 `src/common/disposable_paths.py` 所需模块而无法完成加载；这不视作完整回归通过。
4. 只读 HTTP 观测使用 28766 的 R5 分支 Python 服务和生产 R1 PG authority，静态资源仍由生产根提供：`/api/v4/home` 8 次均 HTTP 200，identity 响应 **5,060,827 B**，P50 **279.43 ms**、P95 **370.04 ms**；复现首页旧 R1 超大响应兼容场景。该数据仍高于目标 R2 摘要体积，不满足 B-04。
5. API 分页列表（n=8）结果：stocks 200，54,849 B，P50 227.39/P95 350.86 ms；sectors 200，88,175 B，P50 169.49/P95 341.69 ms；focus 200，64,019 B，P50 207.82/P95 351.12 ms。详情仅各取 1 次：stock 200/6,575 B/260.71 ms，sector 200/20,745 B/1,112.65 ms。没有取得有意义的详情 P95。
6. Radar p1/p2 各试 3 次均 HTTP 400、77 B，响应为 `PRODUCT_READ_FAILED`；当前没有 R2 authority/index，不能验真实 SQL 过滤、第二页或计数对账。错误体不含可据以认定业务原因的细节。
7. 内置浏览器在 28765 实际看到：首页 stocks 5,225、sectors 400；Focus 变化 177 条/展示 30 条、风险 14 条；Radar/Forward 首页数值均为“来源未接入”。直达 `/v4/research/radar` 显示“没有找到该入口”。生产版本号仍为旧包 `1.0.0_88cc19deae3b`，不能代表本轮 source commit 的前端验收。另以 28766 打开时 API 来自 R5 源码服务，但静态 JS 仍来自生产根，故未将其当作同版 UI 通过。

## U01–U16 唯一状态

只使用任务卡允许的状态值；`NOT_VERIFIABLE` 表示本轮没有同版、足够的真实业务证据。

| ID | 状态 | 证据摘要 |
|---|---|---|
| U01 | `FAIL` | 生产首页 Radar 来源未接入；直达 Radar 无入口；R2 API p1/p2 返回 400。 |
| U02 | `FAIL` | Forward 首页为“来源未接入”，无合法样本数/首次冻结来源。 |
| U03 | `NOT_VERIFIABLE` | 首页显示前序状态，但没有完成所需两个可比日谓词与真值复算。 |
| U04 | `FAIL` | 可见风险列表仅有 Focus 类变化；三族 risk owner 与改善/持平/不可评估分母未验。 |
| U05 | `FAIL` | 400 板块成熟度/健康度来源不可用，缺独立 D2 lifecycle 生产者与 20 例复算。 |
| U06 | `NOT_VERIFIABLE` | 未完成真实板块详情、时间序列及 NONE/UNKNOWN 区分验收。 |
| U07 | `NOT_VERIFIABLE` | 未取得 R2 个股详情字段对账。 |
| U08 | `NOT_VERIFIABLE` | 未完成资格四态证据清单与详情 Owner 对账。 |
| U09 | `NOT_VERIFIABLE` | 未按任务卡完成 `SZ.301660`、普通旧股、无报价、别名核验。 |
| U10 | `FAIL` | 已见 Focus 集中度行业标签为 `INDUSTRY:T...` 原始标识，非中文名称。 |
| U11 | `NOT_VERIFIABLE` | 未按 observation/episode/最新观察逐字段对账。 |
| U12 | `NOT_VERIFIABLE` | 未完成 Focus 第 2 页、同日多事件及筛选证据验收。 |
| U13 | `FAIL` | 真实未来成熟样本客观未到期；但当前采集/准入/结算/FEP 显示与可测生产管道也未完成，不能只归为未来条件。 |
| U14 | `NOT_VERIFIABLE` | 未完成五指数、5/20 会话与图表双视口验收。 |
| U15 | `NOT_VERIFIABLE` | 未完成真分母、UNKNOWN 与规则负例核验。 |
| U16 | `NOT_VERIFIABLE` | 未完成精确连板分类及真实分页验收。 |

## 浏览器、部署与下一阶段

- 本轮检查了 28765 Radar 空入口及首页，并查看一张内置浏览器画面；**保存到仓库的截图：0 张**。六入口截图数量因此为 0；任务卡要求的宽/窄两视口没有完成。当前可用 CUA 接口没有公开 viewport 覆盖设置，本轮未用外部浏览器或模拟缩放冒充窄视口。
- 真样本门：没有完成至少 20 个分层 owner 样本对账；不以本地合成单测充数。自动日更继续暂停，未运行盘中任务，未改变 Head。
- 回滚点：上述仍在运行的旧 EXE/28765 服务与 `V4_PACKAGE_1.0.0_88cc19deae3b`。未部署本轮代码，故不需要执行回滚。
- **验收结果：`V4_PRODUCTION_CUTOVER_BLOCKED`**。第一阻断点为生产 R2 authority/index 缺失，导致 Radar p1/p2 真实 API 失败；此外首页 R1 仍为 5.06 MB，业务生产者、真样本及前端同版双视口/P95证据未满足门槛。已修的 B-01/B-02 只在代码提交中，未在生产安装/启用。
- 下一阶段唯一动作：在隔离、可审计的 PG schema 中，用本提交构建 2026-10-13 只读 R2 revision，保留旧 authority/schema，并先完成 R1/R2 缺失、错误、准备中、READY 四种首页路径及 Radar 真数据分页对账；随后补齐 U01–U16 的真实 Owner/页面验收，再评估切换。切换前必须重新封存 PG cluster/schema/Head/token 证据及同版前端双视口截图和完整响应 P95。
