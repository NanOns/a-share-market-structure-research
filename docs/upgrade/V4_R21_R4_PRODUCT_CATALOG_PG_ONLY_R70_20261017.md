---
stage_id: V4_R21_R4_PRODUCT_CATALOG_PG_ONLY_R70_20261017
branch: codex/v4-workspace-cleanup
status: TWO_OWNER_READ_CALLS_PG_ONLY_CODE_LIVE_RECONCILIATION_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 50
open_callsite_rows: 208
ingress_adapters_open: 8
remaining_open_or_ingress: 216
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# V4 R21-R4 product catalogue PG-only runtime reader R70

日期：2026-10-17（Asia/Shanghai）。本批将两个原 Owner P1 调用点的运行时读取改为只接受 Head 内嵌 PG catalogue authority。

## 实际调用链

- `native_product_catalog_v3.load` 现在必须收到 `native_product_read_authority_pg`，然后通过 `_load_pg` 读取精确日期的 product manifest 与 Head scope Owner facts。
- 删除 runtime 从 `native_product_read_authority` 本地 authority JSON 读取并递归打开 manifest/source 文件的回退。缺少 PG authority 时 fail closed。
- 首次准备仍使用独立的 `prepare_pg` ingress 路径；它不会被 runtime load 用作隐式 fallback。
- 这对应原清单两条 Owner 读取：`V4-BCA-R2-96a1db02fb06bc6096e1`、`V4-BCA-R2-ca45d459cf05da9b3d97`。矩阵已标为代码级 PG-only、待 live inventory/readback；不标正式完成。

## 验证与边界

- Product catalogue、Head-bound Owner、BFF 与 authority-preparation 选定回归：**17 passed**。
- 测试使用受控 PG fact-store 替身；验证没有读取本地旧 authority、manifest 或 source binding。没有 live PG readback、Head CAS、服务启动或业务验收。
- 暂存区仓库策略与差异空白检查通过。

## 原 266 项核对

原 P1 **正式完成仍为 0/266**、正式剩余 **266/266**。代码级矩阵状态从 48 增至 **50**，OPEN 从 210 减至 **208**，Ingress 仍为 **8**；OPEN/Ingress 合计 **216**，未映射 reference edge 仍为 **22**。Owner 子集现为 **46** 代码级待对账、**147 OPEN**、**7 ingress-open**；其他业务 28 项仍为 4 代码级待对账、23 OPEN、1 ingress-open。

## 后续

对这两条 Owner 调用点执行真实数据库身份、Head authority 绑定、manifest/scope 与源分母逐 ID 对账；继续同类 Owner/Head/BFF 消费者以及 DM-01 stage PG 交接迁移。
