# V4_R21_R5 全模块文件引用与 Workspace 集中实修收尾报告

- 执行分支：`codex/v4-workspace-cleanup`（基础 `4a69c4cd0841c9fbb83e730c2e4f9a910d8628d2`）
- 状态：`CODE_REPAIR_AND_PG_CANDIDATE_BROWSER_ACCEPTANCE; FORMAL_HEAD_CLOSURE_PENDING`
- 本次范围：现役 V4 的 PG 读取链、Owner/Membership、合同 Registry、股票历史、回放、研究 BFF/UI、开发候选服务及 Workspace 引用。

## 实际代码修复

改动 **15 个运行时代码文件、1 个 PostgreSQL 迁移、4 个聚焦测试文件**。按功能链计，实际修复 10 组：

1. V4 原生连接使用现有 `WORKBENCH_PG_DSN` 连接同一数据库；保留显式 V4 覆盖项，不再要求额外 Reader DSN。
2. 开发候选服务直接绑定 PG snapshot schema，`/api/v4/*` 经 PG reader/BFF 读取；该分支不构造文件型 accepted-Head reader，不读取 UI authority 文件来选入口，也不启动日更 worker。
3. 候选 reader 校验 PG snapshot identity、descriptor 和数据 manifest；股票、板块、Focus/Forward、市场、诊断和操作状态从 PG 投影读取。
4. Owner 与 Membership 运行路径移除本地快照回退；Membership schema 从 Head-bound binding 读取。
5. Product BFF 移除 R1 read-index、FEP `MODEL_CATALOG.json` 及单位注册表文件回退；缺少 PG 投影时显式降级。
6. Product 启动缓存减少对本地 authority、manifest 和 Owner/source 文件签名的二次依赖，改校验 Head-bound PG Catalog 与数据库身份。
7. 股票历史图在候选模式下按 T0、Head token 和 source digest 唯一匹配 PG history version；不再从 workspace 路径或本地指针选历史表，来源不唯一时明确返回缺口。
8. 回放/比较新增候选快照路径：正确标注事后重建、严格 PIT 证明不足时不显示为 PIT；后续观察保持独立区。
9. `/api/operations/status` 和诊断 Jobs 页面展示 PG snapshot 的 T0、记录数及“无日更 worker/无作业进度”真实状态。
10. 新增合同版本与审批事件 PG Registry 迁移，落实 append-only 约束及 Accepted publication 的合同绑定校验。

## PostgreSQL 实例操作

直接使用现有 `127.0.0.1:5432/market_research`，没有创建 Reader DSN 或新实例。已应用 `043_v4_contract_registry_approval_events_r1.sql`，登记迁移校验值，并写入及读回校验 7 个源文件合同版本为 **DRAFT**（逐字节摘要、版本及源修订一致）。审批事件、Accepted publication、正式 publication Head 仍均为 0；没有改动正式 Head。

候选快照为现有 PG snapshot，T0 `2026-09-30`：股票 5,213、板块 378、Focus/Forward 各 117、事件 33。它仍是候选快照，不构成 Accepted authority。

## 28766 内置浏览器验收

通过 Codex 内置浏览器在 `127.0.0.1:28766` 实际操作；候选服务使用真实 PostgreSQL 数据：

- 总览：5213 股票、378 板块、117 雷达及 117 Forward 显示；市场四轴与 33 条变化事件可读。
- 板块：检索“煤炭开采”返回真实 PG 结果；详情成员及字段可读。
- 个股：检索 `600675` 显示“中华企业”；详情、行情值可读。历史图在 Head/source 不匹配时显式停止拼接。
- Focus/Forward：显示 469 条关注锚点、117 条样本、585 条期限计划、5 条已发布结果及 0 个成熟样本；未宣称胜率或收益分布。
- 市场：2344 涨、2712 跌、155 平、13 未知，实际行情分母 5213；指数、涨跌停和事件区域显示。
- 诊断：health 4 项真实记录；Jobs 页显示 `PG_CANDIDATE_SNAPSHOT`、T0 和计数，并明确没有启动日更 worker。
- 回放：真实操作选择中华企业和“事后重建对照”，显示实际收盘 2.520、成交额 323885760、成交量 135013893；页面明确声明这不是 PIT。严格 PIT 可用日为 0，且未伪造 PIT 结果。
- 比较：真实操作运行“股票 vs 市场”，中华企业收益来源标为不完整；同窗 Universe 基准显示 -0.136%，并标注共同起止日。

以上为候选 UI 功能验收，不是生产验收。开发服务端口为 28766，未触碰 28765。

## 验证与准入

- 聚焦验证先前执行结果：29 passed；3 项被仓库测试隔离插件以 `DISPOSABLE_PG_CLUSTER_REQUIRED` 拒绝连接共享实例。未绕过隔离器；真实数据库行为已通过本任务授权的迁移/读写读回和浏览器链路核验。
- `git diff --check`：通过（已统一相关源码换行）。提交前仍执行暂存区仓库准入策略。
- 未运行 GitHub CLI 流程测试、重复全仓基线扫描、大型 pytest 或 GitHub Actions。

## 未完成项与单独授权边界

- 任务卡原始稳定 ID 总数 **266**，正式关闭数仍为 **0/266**。既有矩阵最新保存计数为 PG-only code pending **54**、ingress adapter open **9**、OPEN **203**、未映射引用边 **22**；任务卡冻结摘要为 53/10/203，差异是一行已在既有矩阵中从 ingress-open 归入 code-pending。本轮没有重复全仓扫描或逐 ID 关闭核销，因此上述存量均作为未关闭处理。被明确识别的活跃点包括 `core_product_server_r1.py` 的 accepted API/Head 签名装载、`producer_bootstrap_v1.py` 的 Head/producer 输入、`operational_successor_release_v1.py` 的 Head JSON 写入和 `v4_current_stage_authority.py` 的 authority 文件读取。非 V4 引用仅登记。
- 7 份导入合同均为 DRAFT，没有批准事件；publication/head 表仍为空。不得将其称为正式接受或 Head 切换。
- 仍需单独授权：正式 Head CAS/切换、生产 28765 部署、物理删除及 Git 强推/历史重写。正常提交和推送不包含上述操作。
- GitHub Issue/PR 状态更新连接器此前返回 HTTP 403，本轮不通过 GitHub CLI 绕过。

本报告如实区分代码层修复、真实 PG 候选验收与正式 authority closure；提交/推送不代表生产发布。