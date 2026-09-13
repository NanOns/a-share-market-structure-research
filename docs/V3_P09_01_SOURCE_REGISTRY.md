# V3 P09-01-A：公开来源静态登记

## 结论

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`、§19.3–§19.4、§20.6，本小任务结果为：**FULL_PASS（静态登记范围）**。

本任务只登记已知公开端点、七个事件池、字段线索、转换待确认项和请求边界；未执行网络请求，未启用任何在线能力，未访问或修改 TDX，未写生产数据库。

## 阶段合同

- 合同：`V3_ONLINE_SOURCE_REGISTRY_1` / `v3-online-source-registry-v1`。
- 实现：`config/online_source_registry_v3.json`。
- 来源范围：EXT01–EXT11；EXT11 来自 §20.6 已有 `eastmoney_quotes.py` 的实际模板。
- 能力状态：所有来源 `STATIC` + `NOT_VERIFIED` + `enabled=false`。
- 请求边界：未来复测总预算 12 秒、单源 8 秒、响应 2 MiB、最多 4 个并发源；事件页初始上限 20，报价批次上限 50。
- 热榜/报价：保持请求时直取，禁止原始载荷、行、批次和历史快照持久化。

## 验收证据

| 检查项 | 结果 |
|---|---|
| 静态登记校验 | 通过；EXT01–EXT11 顺序、HTTPS 模板、GET 方法和 fail-closed 状态均匹配 |
| 七池登记 | 通过；`super_stock`、`limit_up`、`limit_up_broken`、`yesterday_limit_up`、`limit_down`、`new_stock`、`nearly_new` 均有独立语义和禁止推断 |
| 字段合同 | 通过；已知字段映射已登记，字段代码、倍率、数组结构和单位未确认项保留为待复测 |
| 网络请求 | 0 次；本小任务范围内明确 NOT_RUN_BY_SCOPE |
| 定向验证 | `python -m pytest -q tests/upgrade_v3/test_p09_01_source_registry.py` |
| 机器回执 | `reports/upgrade_v3/P09-01-A_SOURCE_REGISTRY.json` |

## 约束与下一步

本小任务的 FULL_PASS 只覆盖静态来源登记，不代表来源当前可用，也不放行在线 API/UI 消费。`P09-01-B-CURRENT-PROBE` 作为独立审计项保持 OPEN；下一步必须人工启动 P09-01-B，复用项目既有有界 HTTP 能力，按 `STATIC/HISTORICAL_PROBE/CURRENT_PROBE` 分列记录成功、失败、字段倍率、日期能力和分页范围，并保持 fail-closed 降级。
