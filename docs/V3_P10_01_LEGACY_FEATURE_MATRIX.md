# V3 P10-01：旧功能去留矩阵

## 阶段合同

本阶段执行前读取最新适用升级文档：`docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，适用范围为 §2、§18.13 P10-01、§20.3–§20.8；阶段合同为 `v3-p10-legacy-feature-matrix-v1.0`，主文档 SHA-256 为
`52536035f82d4754eda13241181f2aa8563b9d37e280e2ae39bfbd3a5a6c9d5b`。

目标是逐项处理 §2 的旧功能：每一项都必须有保留/替换/排除/后置决定、V3 新入口、旧 API 或历史入口、可执行查询证据和解释。矩阵是纯只读注册表，不创建迁移、不写生产数据库、不访问或修改 TDX。

## 实现

- `src/workbench_service/legacy_feature_matrix.py` 提供 19 行完整矩阵和版本化合同。
- `GET /api/v3/legacy-matrix` 返回矩阵；带 `publication_id` 时校验并绑定该发布日，发布身份或日期只传一项会 fail-closed。
- `/v3` 页面展示完整矩阵，并把旧入口链接带上当前 `publication_id/trade_date`；支持用 `?publication_id=...` 打开指定历史发布。
- `/v2` 保留旧 API 和页面；强势板块改标为“历史强势板块参考”，主线改标为“中期主线背景”，代表改标为“历史代表个股”，旧候选明确为“全部结构候选”。
- 本地涨停/连板/晋级仍是“本地估算/历史切换”；在线事件和热榜保持 P09 的独立来源与请求时边界。P10-02 的名称选择、集合筛选和跨页关联不在本阶段实现。

## 矩阵结果

| ID | 功能 | 决定 | 当前入口/语义 | 旧兼容与查询证据 |
|---|---|---|---|---|
| LEGACY-01 | 首页市场概况 | 保留 | V3 本地双轨；本地收盘和在线事件分源 | `/v2?page=overview`；`/api/dashboard` |
| LEGACY-02 | 首页强势板块 | 替换 | CURRENT/POTENTIAL 双轨，不再作为旧强势榜 | `/v2?page=sectors`；`/api/sectors/cycle` |
| LEGACY-03 | 首页优先研究 | 替换 | CURRENT_FOCUS/EARLY_FOCUS 双清单 | `/v2?page=overview`；`/api/candidates` |
| LEGACY-04 | 全板块 | 保留 | 板块研究/全部板块 | `/v2?page=sectors`；`/api/sectors`、`/api/sector-library` |
| LEGACY-05 | 板块周期矩阵 | 保留 | 周期矩阵，5/10/20/30 日指标保持原义 | `/v2?page=sectors`；`/api/sectors/cycle` |
| LEGACY-06 | 主线周期 | 保留并改标 | 中期主线背景，不作双轨必需资格 | `/v2?page=sectors&subpage=mainlines`；`/api/mainlines` |
| LEGACY-07 | 成员留存/龙头更替 | 保留并改标 | 原结构强成员/历史代表，与当日领涨分开 | `/v2?page=sectors`；成员历史/代表历史 API |
| LEGACY-08 | 板块—个股联动 | 保留 | V3 详情和旧联动页；集合增强留到 P10-02 | `/v2?page=linkage`；`/api/linkage` |
| LEGACY-09 | 属性库与交并排除 | 保留 | 联动/属性库；角色过滤按 P10-02 扩展 | `/v2?page=linkage`；`/api/sector-library`、`POST /api/sector-intersection/query` |
| LEGACY-10 | 五类结构 | 保留并改标 | 全部结构候选/结构证据；CORE 不等于今日重点 | `/v2?page=overview`；`/api/candidates`、`/api/queues`、`/api/evidence` |
| LEGACY-11 | 新高/RPS/MA/量额/换手 | 保留 | 个股研究/技术状态；换手缺可靠输入则显式缺失 | `/v2?page=stocks`；`/api/stocks/technical`、`/api/stocks/new-highs` |
| LEGACY-12 | 个股证据与透视 | 保留 | V3 个股详情/证据；旧抽屉继续可达 | `/v2?page=stocks`；`/api/stocks/{security_id}/insight`、`/api/evidence` |
| LEGACY-13 | 本地涨停/连板/晋级 | 保留并显式切换 | 在线事件和本地估算分源 | `/v2?page=market`；`/api/limit-ladder`、晋级历史 API |
| LEGACY-14 | 最强题材/分布/简图/速览 | 保留 | 在线事件页；按来源状态降级 | `/v3/events`；`/api/v3/events/overview`、`/api/v3/events/distribution` |
| LEGACY-15 | 人气热榜 | 保留 | 在线总览/热榜，请求时读取 | `/v3/online`；`/api/v3/hot-rankings` |
| LEGACY-16 | 板块精选 | 替换 | CURRENT/POTENTIAL 主体叠加在线证据，不造第三套榜 | `/v2?page=sectors`；`/api/sectors/cycle` |
| LEGACY-17 | 数据状态/运维 | 保留 | 数据能力/运维中心，不占研究主导航 | `/operations`；`/api/operations/status` |
| LEGACY-18 | 导出/会员/投资日历/外部跳转 | 明确排除 | 本版不提供，无空壳入口 | 无 API；用户取舍和 V3 §20.3 为显式处置证据 |
| LEGACY-19 | 龙虎榜/新闻原因 | 明确后置 | 后续独立需求和来源证据再立项 | 无 API；V3 §20.3 为显式处置证据 |

机器返回还保留每行的 `status`、`legacy_compatibility.apis`、`evidence.path` 和 `note`，以上表格为便于人工核查的摘要，不替代机器合同。

## 证据与验收

阶段脚本：`scripts/verify_p10_01_legacy_matrix.py`。

| 检查项 | 结果 |
|---|---|
| P10-01 定向测试 | `4 passed` |
| 矩阵覆盖 | 19 行、ID 唯一、每行有决定和状态；排除/后置行有明确原因 |
| API 查询 | `GET /api/v3/legacy-matrix` 返回 200、19 行、合同正确 |
| 只读边界 | API smoke 前后测试库未创建 `research_runs`；报告标记 `database_written=false` |
| 历史发布查询 | 只读查询发现已有 SUCCESS 发布，可按 `publication_id/trade_date` 生成上下文链接；不修改发布数据 |
| 页面/脚本 | `/v3` 矩阵入口、V2 语义标签存在；Node `vm.Script`、compileall、`git diff --check` 通过 |

机器回执：`reports/upgrade_v3/P10-01-LEGACY-MATRIX.json`。

## 阶段结论与下一步

P10-01 结果为 **FULL_PASS**：旧功能没有静默消失，替换、保留、明确排除和后置项均可定位；旧 API/历史入口仍有兼容路径；本阶段未声称前瞻效果，也未实现 P10-02 集合筛选和跨页联动。

下一阶段：`P10-02`。

