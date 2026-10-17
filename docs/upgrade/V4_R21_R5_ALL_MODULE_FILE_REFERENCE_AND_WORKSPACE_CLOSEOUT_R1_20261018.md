# V4_R21_R5 全模块文件引用与 Workspace 一次性集中实修收尾报告

- 阶段：V4_R21_R5
- 执行分支：`codex/v4-workspace-cleanup`
- 基础提交：`4a69c4cd0841c9fbb83e730c2e4f9a910d8628d2`
- 状态：`CODE_REPAIR_PARTIAL; LIVE_PG_AND_BROWSER_ACCEPTANCE_BLOCKED`
- 范围：现役 V4 Owner / Membership PG 读链、Product BFF、启动缓存签名、FEP BFF 来源、Workspace 路径依赖及迁移矩阵精确行。

## 已完成的代码修复

1. Owner schema 选择改为读取 Head 绑定的内联 PG descriptor；移除运行时对 `r8_owner_read_origin_r1.json`、前序 Head 和 authority JSON 的 schema 选择依赖，并验证 schema 名称。
2. Membership authority 的 schema 从 Head-bound binding 读取，消除从本地 workspace root 派生 schema 的逻辑。
3. Product BFF 移除 R1 读索引回退和 FEP 本地 `MODEL_CATALOG.json` 回退；身份展示可在没有 R2 投影时从 PG identity / Owner 生成，FEP 缺少 PG projection 时显式降级为缺失。
4. BFF 单位展示改为使用已接受 Owner cell；不再读取三份本地 field registry JSON。
5. Product server 缓存启动链移除 Membership authority、旧 Product/Focus authority、Product Catalog 日期清单和 Owner/source 输入文件的二次读取/签名；以 Head-bound PG Catalog 校验及 PG database identity 校验为准。
6. 新增 FEP PG projection 回归测试；更新 Owner、Membership 和缓存回归测试；矩阵中一个精确 callsite 从 ingress-open 移入 PG-code-pending，未更改正式关闭计数。

**本轮实际修改：6 组运行时调用链，1 个矩阵稳定 ID 状态迁移，1 个新测试文件，3 个既有测试文件更新。** 该数字按具体代码路径归组，不表示关闭了 6 个正式基线 ID。

## 最小验证

- 指定 5 个焦点测试文件：`19 passed`。
- `git diff --check`：通过。
- 仓库暂存区准入检查：待提交前执行。
- 未运行 GitHub CLI 流程测试、全仓基线扫描或 GitHub Actions。

## PG 与浏览器验收

- 环境未配置 `WORKBENCH_PG_DSN` 或 `V4_NATIVE_PG_DSN`；未尝试 PG 写入，也未切换正式 Head。
- PostgreSQL 仍是共享实例 `127.0.0.1:5432/market_research`；未创建或复制测试数据库。
- 内置浏览器请求 `http://127.0.0.1:28766/v4?source=pg_candidate` 返回 `net::ERR_CONNECTION_REFUSED`。开发服务未运行；缺少 Reader DSN 和 Head-bound PG 身份也不能安全启动。
- 因此 7 个 candidate UI 模块（summary、radar、entity、sector、cohort、settlement、health）均未取得真实页面或 API 结果，浏览器功能验收状态为 **BLOCKED / 未通过**，没有使用 mock。
- `28765` 未触碰；`28766` 无监听。仅查询确认 PG 端口 `5432` 的现有实例。

## 仍未修调用点及授权边界

- `src/workbench_service/core_product_server_r1.py`：活跃 Product API 仍从 `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json` 通过 `accepted_api()` 装载运行 Head；R2 read-index、joint-authority 和 release-policy 仍有文件绑定/签名读取。它们需要逐项对照已批准的 Head/Registry 合同后迁移，本轮没有证据证明可安全删除这些权威绑定。
- `src/workbench_service/core_product_bff_r1.py`：legacy navigation/shadow policy 仍读两份版本化 config；dated manifest、Owner lifecycle/snapshot 仍读取 Head 指定的文件型来源。这些尚未迁为 PG 读者。
- 矩阵保持 266 个正式 P1 项全部未关闭；代码层 PG-only pending 54、ingress-open 9、OPEN 203，另有 22 条引用边未映射。正式关闭为 **0/266**；完成路径修复不能替代 live PG readback 与逐 ID 对账。
- 单独授权事项仍包括实际 PG 写入/合同注册、正式 Head CAS、生产 28765 部署、物理删除和强推/历史重写。

## 下一阶段

配置获批准且只读的 Reader DSN 与准确的 accepted PG identity 后，在唯一开发槽位 28766 启动现役服务，通过 Codex 内置浏览器逐模块验收真实页面/API；随后对未迁路径按稳定 ID 和版本化合同继续迁移并独立复核。当前代码与规范按任务卡授权提交、正常推送；推送不等于运行验收或生产发布。
