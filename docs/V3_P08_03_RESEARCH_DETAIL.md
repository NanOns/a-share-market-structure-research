# V3 P08-03：全局双清单、个股详情与旧入口兼容

## 结论

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`、§10、§18.11，P08-03 结果为：**FULL_PASS（清单、个股证据与兼容入口）**。

本阶段完成 P08 本地研究预览的收口，不进入 P09 在线数据任务；未访问或修改 TDX，未写生产数据库。

## 已实现边界

- `/v3` 页面新增 CURRENT_FOCUS/EARLY_FOCUS 全局双清单，各自最多 20 条/页并保留 `total`、`has_more` 和分页。
- 清单行可打开个股详情 modal，详情绑定同一 `context_id`，展示基础信号、质量、风险码、板块角色、主备清单和等待/失效信息。
- 证据 modal 按 `selection/risk/sectors/technical` 分节按需请求 `/api/v3/research/stocks/{id}/evidence`，不预取无关深度数据。
- 个股后端详情只消费当前 COMPLETE run 的 stock state、member roles 和 shortlist；不读取未来结果，不回接旧 candidate/association 作为 V3 排名。
- 旧 v2 入口标题改为“全部结构候选”，说明其仍是兼容旧 API31 的结构候选排序；`/api/candidates` 和旧页面保留，未删除或改写旧字段语义。
- modal 关闭、清单分页和上下文切换均保持在当前页面；请求使用 AbortController/序列号，迟到响应不能覆盖当前个股。

## 验收证据

| 检查项 | 结果 |
|---|---|
| P08-03 定向测试 | `6 passed`（含 P08-01 API 回归） |
| 清单边界 | CURRENT_FOCUS/EARLY_FOCUS 各独立分页，最多 20/页；个股详情返回角色与清单绑定 |
| 证据分节 | selection/risk/sectors/technical 按需读取，风险分节只返回对应证据对象 |
| 兼容入口 | v2 显示“全部结构候选”；旧 `/api/candidates` 调用路径仍存在 |
| 前端脚本 | Node `vm.Script` 解析通过 |
| 完整回归 | `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：`217 passed in 78.21s` |
| 静态检查 | `python -m compileall -q src scripts`、`git diff --check`：PASS |

## 真实数据范围与下一步

当前生产环境没有被本阶段伪造激活的 COMPLETE research run，因此清单和个股页在真实访问中继续显示 `NOT_BUILT/EMPTY` 安全状态；定向合成 run 只验证绑定和分节合同，不冒充真实效果或截图。P08 阶段完成，下一阶段按计划进入 P09-01 在线来源逐数据集验证。
