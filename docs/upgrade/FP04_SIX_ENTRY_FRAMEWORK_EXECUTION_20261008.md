# FP-04 六入口框架与设计系统执行

依据：本轮总卡、04 卡、完整合同 §62A–§69。合同：`V4_SIX_ENTRY_SHELL_V1`；UI authority 明确 `full_product_release=false`。

采用现有静态页面体系，拆分 `index.html`、`style.css`、`app.js`、`api.js`、`components.js`、`labels.js`。没有引入 npm 构建链或另一套服务；浏览器原生 ES modules 加载。这样保持当前 Python 启动和简单回滚，同时避免继续扩张七摘要单文件。

| 路由 | 入口 / 当前框架内容 |
|---|---|
| `/v4/research/home` | 今日总览、真实数据规模、当日事件、领域缺口 |
| `/v4/research/sectors` | 完整板块分页、名称搜索、字段详情、完整成员 |
| `/v4/research/stocks` | 全市场分页/筛选/排序、代码及名称搜索、画像字段详情 |
| `/v4/research/focus` | Focus 投影缺口与独立 Forward 生命周期区 |
| `/v4/research/market` | 市场四轴接线状态与真实事件分页 |
| `/v4/research/diagnostics` | 源健康、版本/来源/缺口、历史诊断入口 |

导航高亮、深链接、面包屑、详情返回/浏览器返回、股票到所属板块和板块成员到股票链接均接入。全局显示真实处理日、数据更新时间（北京时间）；来源摘要与长 ID 放在证据抽屉，中文枚举集中映射。列表不展示整批原始 JSON。

公共组件：ResearchHeader、AcceptedDate、SourceBadge、StatCard、DataTable、FilterPanel、Timeline、Kline（真实 OHLC 蜡烛图绘图接口）、EvidenceDrawer、QualityStatus、EmptyState、LoadingState、ErrorState、ComparePanel、Pagination。历史行情尚未由 FP-07 接入时，Kline 不造数据；Compare 的生产数据入口由 FP-12 完成。请求取消和加载序号避免旧响应覆盖新页面；错误/无结果/能力缺口分别显示。原生 dialog 支持键盘关闭，导航/筛选具备可访问名称。

启动：`python -B run_workbench_service.py --v4-default --host 127.0.0.1 --port 28765`。当前服务已重启至本批版本。UI 回滚将 `config/v4_research_ui_authority_v1.json` 的 mode 原子更新为 `LEGACY_SUMMARY`；旧摘要也始终可通过 `/v4/legacy-summary` 访问，旧 API 保留。索引回滚独立于 UI 回滚。

浏览器证据在 `docs/evidence/fp02_20261008/*_1366.png`、`home_1920.png`、`mobile_390.png` 与 `BROWSER_READBACK.json`。实际可用的是 Codex 内置浏览器，已验证六入口、中文名称检索、下一页、详情、返回、来源抽屉，以及 1366/1920/390 视口。**当前没有连接的 Edge 自动化会话，不能将上述证据声称为 Edge 独立验收；Edge 检查仍保留为明确限制。**

验收：**DEGRADED_PASS（框架与已连接浏览器范围）**。下一阶段为 FP-05–11 业务页和实际算法链闭环；FP-13/14 全站独立验收及正式全产品发布尚未执行。
