# V4 PostgreSQL 一次性迁移/权限批次授权申请 R1

状态：仅供审阅与一次性授权；本轮未执行 DDL/DML、迁移、角色创建、隔离库复制、Head 更新、28765部署或调度。真实对象的SQL文件SHA以同目录 `V4_PG_MIGRATION_CATALOG_DIFF_R1_20261016.md` 逐项列表为准。新增Universe前向迁移：`042_market_universe_persistence_r1.sql`。

## 请求批准范围（必须填写目标/窗口/角色与备份恢复证明后方可执行）

- 目标：明确区分共享库 `127.0.0.1:5432/market_research` 与经单独批准的隔离演练目标；本申请默认不复制、不执行。
- DDL批次：仅批准后按显式 runner 注册顺序执行已确认 SHA；迁移文件正文和 SHA 在批准后需再次核对。任何SQL SHA漂移即停止该批。
- 重复010：分别以 `010_security_lifecycle_history_r5.sql` 与 `010_source_manifest_contract_r1.sql` 的完整文件名、各自 contract/version 和catalog对象验证；不能将一条 010 ledger 当两条都完成。不得自动改名或重写历史ledger。
- 授权身份：reader / business writer / migration operator 分离；reader只读且非特权；writer仅对批准的现役append-only表写；migration身份只在批次窗口临时/审批授权，角色职责和撤权责任人需填入。
- 备份与恢复：执行前记录目标 DB OID、schema/catalog 快照、迁移ledger、目标表行数/关键摘要和一致性快照；列明可恢复备份标识、最近恢复演练时间、验证查询、回滚顺序。042含表、约束、函数、触发器，事务失败可回滚；提交后需按依赖逆序进行经批准的补偿/恢复，禁止盲目 DROP。
- 锁与容量：先对静态 SQL 做风险审查；隔离PG编译/回放/rollback作为一个批准窗口。生产执行另开审批；评估现存 publication 数、预期 Universe 行数与每版对账行数、索引增长、锁等待、应用兼容和读服务影响。当前容量/锁估算 `NOT_VERIFIABLE`。
- 回读：只读事务核实ledger全SHA、对象定义/约束/函数/trigger/grants、Universe snapshot行数/摘要；由独立Reader执行；任意不符停止，不接受writer自证。
- 批次回滚：事务内失败整体ROLLBACK；若后续版本已依赖提交后的042，先停写入并按备份恢复演练方案回滚，不直接删除业务表或历史事实。

## 单独批准边界

本批不包括 accepted publication/Head CAS、生产服务 28765、自动日程、不可逆重算、DROP/DELETE/TRUNCATE、权限扩张到生产 writer，也不批准将测试Issuer写入生产 authority registry。真实 source/issuer/calendar 的签发流程需由独立Owner批准。

## 当前阻断

- `V4_NATIVE_PG_READER_DSN` 与 `WORKBENCH_PG_DSN` 当前均未配置；未执行catalog查询。
- 没有 `V4_NATIVE_PG_DSN`；没有任何 PG 实际写入/迁移。
- 需要项目Owner补充批准目标、独立Reader/Writer/Migration角色、备份恢复记录、可用执行窗口及针对生产的单独范围。
