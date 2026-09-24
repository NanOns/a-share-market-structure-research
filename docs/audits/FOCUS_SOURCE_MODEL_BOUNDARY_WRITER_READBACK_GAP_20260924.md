# Focus SOURCE_MODEL_BOUNDARY writer/readback 验收缺口

| 字段 | 记录 |
|---|---|
| audit_item | `FOCUS_SOURCE_MODEL_BOUNDARY_WRITER_READBACK_E2E` |
| scope | 同一 source family/entity 在相邻交易日 selection contract 变化时，核对既有 episode 身份、首日来源事实、今日来源行、SOURCE_MODEL segment、observation、accepted head 与 API/readback。 |
| evidence | `resolve_tracking_contexts()` 已允许仅 selection contract 不同的 `SOURCE_MODEL_BOUNDARY`，并新增 old first source + current source context 单测。尚无覆盖正式 continuation writer、PostgreSQL segment/observation/head 及 readback 的隔离数据库端到端测试。 |
| acceptance_result | `OPEN / CONTEXT_UNIT_PASS_WRITER_READBACK_UNVERIFIED`。本次不能称 SOURCE_MODEL_BOUNDARY 全链路通过。 |
| next_stage | 在临时 PostgreSQL schema 准备 D1 contract A accepted head 与 D2 contract B accepted source，运行 rollback 和 commit；断言同 episode 延续、首日冻结事实不变、D2 SOURCE_MODEL segment 和 observation 正确、head lineage VALID、API 返回旧/新合同边界证据，且未制造退出/重入。 |

该项不依赖未来市场自然样本，与连续交易日 Forward 门分开验收。
