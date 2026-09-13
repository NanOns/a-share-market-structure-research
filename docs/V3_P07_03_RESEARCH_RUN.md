# V3 P07-03：研究 run 事务封存与任务合同

## 结论

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`、§8、§10.4、§18.10，P07-03 本阶段结果为：**FULL_PASS（事务封存与任务合同）**。

本阶段只处理完整研究 run 的持久化边界、幂等身份、完成可见性和 `BUILD_RESEARCH_V3` 请求合同；没有启动生产研究 job、没有写生产数据库、没有访问或修改 TDX，也没有进入 P08。

## 阶段合同

- run 合同：`RESEARCH_RUN_PREVIEW_1`。
- job 类型：`BUILD_RESEARCH_V3`；请求字段只允许 `publication_id`、`trade_date`、`algorithm_version`、`parameter_hash`、`snapshot_id`、`membership_snapshot_id`、`dependency_bindings` 及 `job_type`。
- `input_key` 对输入日期、发布身份、快照/成员快照、算法版本、参数哈希和依赖绑定做规范化 SHA-256；同输入只复用原 run，不新增业务 run。
- `research_runs` 只允许 `BUILDING`、`COMPLETE`、`FAILED`。只有 `COMPLETE` 可被 `visible()` 查询；构建中或失败的 run 一律返回 `RESEARCH_RUN_NOT_VISIBLE`。
- 股票、板块、episode、成员角色和短名单在同一个事务中写入，最后才把主 run 标为 `COMPLETE`；任一子表写入失败整体回滚，旧发布身份不被原地修改。

## 实现与基线保护

- 新增 `src/workbench_service/research_runs.py`，集中实现请求校验、`input_key`、启动、完成、失败和可见性边界。
- 新增 `src/workbench_db/research_runs_schema.sql`。它由 `ResearchRunStore` 显式、幂等安装，不加入旧迁移序列。
- 这样保留了已明确属于 V3 基线的 M7 迁移尾端 `032_v3_contract_fields.sql` 及其哈希/依赖测试；没有伪造 `033` 迁移，也没有改写已执行迁移身份。
- `research_shortlist` 仅接受 `CURRENT_FOCUS`、`EARLY_FOCUS`、`INDIVIDUAL`；JSON 字段由 writer 统一规范化，旧 association/candidate 结果不作为输入。

## 验收证据

| 检查项 | 结果 |
|---|---|
| 定向 P07-03 + M7 migration executor | `7 passed` |
| 同输入重复启动 | 同一 `run_id`、`reused=true`，无新增业务 run |
| BUILDING/FAILED 可见性 | 均不可见；仅 COMPLETE 可见 |
| 中途失败 | 子表重复键触发回滚，run 保持 BUILDING；显式 `fail()` 后转 FAILED |
| 紧凑结果封存 | sector、member role、shortlist 与 COMPLETE 同一事务提交 |
| 完整回归 | `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：`209 passed in 76.13s` |
| 静态检查 | `python -m compileall -q src scripts`、`git diff --check`：PASS |

## 范围说明与下一步

本阶段交付的是可复用的 run writer 和 `BUILD_RESEARCH_V3` 合同边界；生产 HTTP worker、真实绑定上下文的完整 builder 和正式 GET 研究 API 不在本阶段伪造激活。下一阶段按台账进入 P08-01，读取端必须继续只消费 `COMPLETE` run。
