# V4-UX-R3-FIX-THEN-VERIFY 阶段报告

- 日期：2026-10-14（北京时间）
- 输入任务卡：`D:\Users\lps\Desktop\阶段任务\V4_85E5A58FE493A1E7ACABE596AEE59A82E4AEA4E48EAAE6B6_20261014.md`
- 任务卡 SHA-256：`C2261A59C9DB4469CF89E0A3E213B601E6B6866C37C3DC170C58458CED7592ED`
- 基线：`codex/v4-ux-r2-integration-20261014` @ `6cf1464d00873537c0aa9c017f351aeec9d326f7`
- 项目门禁：Phase 0 receipt `reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json`，状态 `FULL_PASS`，SHA-256 `313304495faee8c081794ec1bf4f19803ed8a634ac98187347d9190b5ebe5b59`
- 本阶段合同：只修复 R3 卡列出的 UI/R2 读取代码路径；不部署，不启动日更，不修改 Head、端口 28765、auto_daily、PG 正式 schema 或 TDX 源。下个门禁须先完成同版隔离 PG/HTTP/浏览器验收。

## 修复内容

1. Radar 与 Focus Events 的空 `event` 现在等同于无筛选；浏览器 API 不再发送空 query 参数。事件枚举和路由范围仍严格校验。
2. 路由专属 `event`、`validity`、`limit_state` 在调用旧 BFF 基础路由时被移除。旧 Context 白名单未被全局放宽；无关路由依旧拒绝这些参数。
3. 股票画像详情由 R2 PG `detail()` 按 token/T0 读取并验证逐行 SHA；股票/板块分页继续使用 PG summary。R2 当前 token/date 缺项会精确报错，只有 R2 Authority 不存在的旧版仍走 R1；历史缺项会标注兼容能力。Focus 实体返回同 token/T0 的 R2 detail。缺 Owner 字段保留 `SOURCE_INCOMPLETE`、字段名与原因，不推断结果。
4. R2 Authority 的 JSON、contract/schema、token、date、PG database identity、版本 digest 和详情 digest 有不同的失败分类。HTTP server 将 R2 Authority 纳入签名与变更检查，并禁用有索引 Authority 时的旧首页响应缓存。
5. Focus Events 与涨停梯队通过 R1/R2 PG 索引做批量身份/名称联接，只查当前返回或搜索涉及的身份，不在 HTTP 请求期重新投影全市场；保留证券代码、名称 Owner/source、质量、未知原因。
6. R2 生产器仍受原发布链控制。本轮没有修改 exact-daily policy、运行时来源 SHA 合同、Head、日更任务或发布逻辑。

## 代码验收

- 定向测试：`15 passed`（新增 8 个 R3 路由/Authority 用例 + 原有 7 个 R2 合同用例）。覆盖 Radar 默认/空/NEW/无效事件，Focus Events 空/NEW/PERSISTENT/validity/第二页，UNKNOWN 21 行分页和跨路由拒绝，个股详情经 `CoreProductBFFR1.get()` 读取完整 R2 detail，Focus detail，名称/source 与缺名原因，Authority 缺 token/date/schema、PG digest 冲突。
- Python：四个变更运行模块 `py_compile` 通过。
- JavaScript：`api.js`、`app.js` 的 `node --check` 通过。
- `git diff --check`：通过。
- 这些是源码和模拟 PG binding 的定向验收；不是 HTTP listener、真实 PG、真实 Owner 行或浏览器验收。

## 真实验收与阻塞

本候选工作区中没有 R1/R2 read-index Authority 文件或可复核的隔离 PG schema receipt；本轮未连接 PG、未请求用户的 28765 服务，也没有真实 Owner 数据。因此以下 R3 条件仍未验收：

- D2/identity 至少 20 条真实 Owner 行逐字段对账（需要包含 `NONE+UNKNOWN`、真实情景、未观测、旧股、`SZ.301660`）。
- Focus 的 3,151 唯一分母、行业 Top 5 和真实事件、梯队中文名称逐项源对账。
- R2 PG 写读、R1/R2 恒等对账、真实第二页/UNKNOWN 21 行、Authority 丢日期与现场 digest 冲突。
- 六入口双视口浏览器截图、实际 API 响应体积与 P50/P95。

发布链源码复核确认 `operational_daily_executor_v1.py` 与 `operational_sealed_resume_r1.py` 均先准备 R1/R2 索引，后进入候选 readback / `promote()`；`promote()` 继续调用 `verify_policy()`。`operational_runtime_acceptance_r1_1.py` 把 R1/R2 Index、BFF、server、sealed-resume 列为受限 IO-only 改动。旧 R2 报告记录的现场阻塞为 `EXACT_DAILY_POLICY_REQUIRED`。该校验要求 exact daily policy V2 合同、候选与 policy 的 accepted algorithm bindings 相同、exact generation contract/来源收据通过，并要求运行时算法/组件 SHA 只能在已批准 IO-only 范围内漂移。本轮未关闭或绕过该门；由于没有同版 frozen candidate/运行时 receipt，无法得出旧现场具体哪一个 binding 不同，最小可检验差异仍须在合法候选根目录生成。

## 阶段结论与下一阶段

**结论：`CODE_PASS / REAL_RUNTIME_BLOCKED / PRODUCT_ACCEPTANCE_OPEN`。** R3 指定的 P0 源码缺陷已修复并经定向测试覆盖；不能据此宣称当前页面可用或 R2-03 部署门通过。后续先在获得合法 policy 和隔离 schema 的同版候选上完成 Owner/PG/HTTP/浏览器/性能验收，并输出 exact-daily policy 的实际 binding diff。若该门仍失败，继续报告精确错误与受阻 source；保持 28765、Head、`auto_daily=false` 不变。六个正式生产者审计项仍按 `PRODUCER_AUDIT_ITEMS_R1.json` 独立跟踪，不混入本阶段验收。
