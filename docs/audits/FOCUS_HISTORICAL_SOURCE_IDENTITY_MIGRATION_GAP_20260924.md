# Focus 历史 publication 来源身份迁移审计项

| 字段 | 记录 |
|---|---|
| audit_item | `FOCUS_HISTORICAL_PUBLICATION_SOURCE_IDENTITY_MIGRATION` |
| scope | 复验已接受 publication 来源包，以版本化、不可覆盖的迁移记录向 settlement、manifest 和 PIT readers 提供精确 source identity。 |
| applicable_upgrade | `FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 的 outcome/source seal 条款；`docs/ADJUSTED_DATASET_CONTRACT_V1.md`。 |
| stage_contract | `FOCUS_PUBLICATION_SOURCE_IDENTITY_MIGRATION_V1`。验证 accepted publication/date、sealed bundle receipt SHA、package SHA 与 bundle id；登记 append-only identity overlay；不修改旧 publication 行。读取冲突或 digest 不匹配时 fail closed。 |
| evidence | `3a2f7a8d92e9313b7b2ad4b5120f9a57d82f5601`；迁移登记 receipt digest `1145b47f1021b83d103e9d25b7d73eaca44f2452576fd7cd5b0d40d85752478b`。2026-09-24 accepted publication 与 bundle 绑定通过复验；source package SHA `b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f`，sealed receipt SHA `fc71a9443414ac85212f503bd1f9fd4b2ca61ef2a496d5eee8279cad93cd0aba`。该身份用于 310/310 已到期 T+1 target seal。 |
| acceptance_result | `CLOSED / APPEND_ONLY_IDENTITY_MIGRATION_APPLIED_AND_READ`。历史 publication 原记录不变；310 个当前 outcome head 均已结算为 `OBSERVED`，PENDING 为 0。 |
| next_stage | 对未来 accepted publications 验证原生 SHA 路径；只对经过同等复验的旧 publication 使用版本化 overlay。更远 horizon 按目标日期自然到达后结算。 |

此跨切面迁移审计项独立关闭；不替代 07A/07B 的 Forward 阶段门。
