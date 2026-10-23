# V4 R9 全仓范围 UI 依赖图续修（2026-10-24）

本补充续接 [R9 独立外审实修报告](R9_INDEPENDENT_AUDIT_REPAIR_REPORT.md) 和 [R9 V4 续修报告](R9_V4_CONTINUATION_REPAIR_20261024.md)。用户已澄清，“全仓”指覆盖仓库内属于 V4 的功能模块及其实际依赖，不把 V1–V3 独立旧功能当作 V4 缺陷。本补充修正扫描器依赖边并更新可复现计数；严格扫描仍阻断，不能作为发布验收。

## 修复内容

此前扫描器把 `src/workbench_service/static/` 下的全部文件连到 V4 HTTP/桌面入口，使没有 V4 路由的 V2/V3 页面也被误判为运行依赖。扫描器现在按 `v4_server.py`、`v4_control_server_v2.py` 和桌面 Engine 的实际静态资源 allowlist 建边；当前联合发布包只在其 V4 UI 合同绑定路径、SHA 与文件均匹配时纳入扫描。控制适配器单独使用其 `app.js` 绑定。UI 文件的字面量模块引用继续传递到本地依赖。

当前发布包位于 `data/v4/ui_releases/`，原来不在代码扫描输入范围内。扫描器现在只添加 UI 合同精确绑定且 SHA 正确的文件，不扫入该目录的全部历史包。没有 V4 路由的 `online-events-v3.html`、`online-p09-v3.html`、`research-v3.html`、`operations.html`、`static/index.html`、`static/v2/index.html` 和 `focus-tracker.html` 均不再可达。实际 V4 服务 fallback、桌面资源及当前 SHA 绑定 UI 文件仍在依赖图内。

纳入当前 UI 后，两个六位 CSS 颜色码曾触发证券代码候选。扫描器只将 `.css` 文件中具备 `#RRGGBB` 语法边界的匹配归类为 `CSS_HEX_COLOR`；裸六位数仍是未裁定候选。非豁免候选基线测试现在排除已被精确语法判定的 `FALSE_POSITIVE` 项，不改写既有候选基线。

实现和回归覆盖见 [扫描器](../../../scripts/check_v4_business_literals.py)、[扫描器范围回归](../../../tests/v4_joint/test_r9_scanner_resolution.py) 和 [业务字面量基线回归](../../../tests/v4_policy/test_no_production_hardcoded_identities.py)。

## 验证结果

定向回归命令：

```text
pytest -q tests/v4_joint/test_r9_scanner_resolution.py tests/v4_policy/test_no_production_hardcoded_identities.py tests/v4_joint/test_r9_source_context.py tests/v4_joint/test_r9_market_cache_scope.py tests/test_r43_streaming_gzwrite.py
39 passed
git diff --check: PASS
```

严格扫描命令为 `python -B scripts/check_v4_business_literals.py --output G:/codex_tmp/R9_V4_SCANNER_UI_GRAPH_STRICT_20261024.json`，按未裁定项以 exit 1 结束。扫描输入 3,983 个文件，V4 活动入口 SHA 合同 7/7 通过，闭包 639 个文件；其中 2,215 个业务字面量命中有 2,198 个仍未裁定，自动确认违规为 0。闭包内还有 11 个未解析动态 `exec` 点，以及 9 个需继续做端点映射/契约核验的浏览器 fetch/import 位点。当前 V4 UI 依赖子图 31 个界面资源文件；上述 V2/V3 静态页面均不在闭包中。

扫描器整体状态仍为 `GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED`。其 5,003 个非活动维护脚本候选和 36 个全仓动态未解项包含 V4 运行闭包外的维护代码，不应报成 V4 业务缺陷；V4 活动闭包自身仍因未裁定候选和运行时边而阻断。旧续修报告中的 652/2,211/25/25 是修正 UI 图前的计数，被本补充中的 639/2,198/11/9 取代。候选数量净变化不是 13 个已修复缺陷：图边收窄移除未被 V4 服务的旧页，SHA 绑定后又纳入当前发布 UI。

本轮只读本地代码和 V4 UI 合同；没有查询业务 DuckDB 文件或表、没有 PG 读写、没有切换正式 Head、没有重启服务或 Windows，也未触碰 28765/28766。完整机器证据见 [R9 V4 UI 依赖图修复证据](R9_V4_UI_GRAPH_REPAIR_EVIDENCE_20261024.json)。

## 仍需处理

此项修复只纠正 V4 UI 依赖闭包，没有完成其余 R9 外审。D2 按用户指示留给下一轮 ChatGPT 独立审计；D0 source cutoff/seal、趋势参考路径和综合发布、breadth/SIGN 业务公式裁定、完整新日日更与 G1/G3/PG/CAS 失败恢复、Focus Priority 排序、Forward LIVE 首捕获、历史 Amount 差异与 10/09 回放证书仍未闭合。28766 未重载新版 UI，因此本轮没有浏览器端新版运行验收。旧续修报告中其他已修和待外部来源事项继续适用。

代码提交并推送到 `codex/v4-unified-development`：`0f5fdf9eade19dc54903d3e7d2592d5c1b7e8d5d`（包含 `a7a94ec923309efdd19ffaba66fec1b82950a697`）。严格重扫在该 HEAD 上执行，扫描输出 SHA-256 为 `75317c5df3c77b567d39f5807824f123177e8e3b0c7b6a9bc606060668e88bfc`，大小 41,619,418 字节；大清单仅保存在 `G:/codex_tmp`。当前远端分支头已包含代码提交；推送不代表独立外审或发布门禁通过。
