# Focus 历史 publication 来源身份迁移缺口

| 字段 | 记录 |
|---|---|
| audit_item | `FOCUS_HISTORICAL_PUBLICATION_SOURCE_IDENTITY_MIGRATION` |
| scope | 对已接受 publication 的来源包进行身份复验，并以版本化、不可覆盖的迁移记录为 settlement 和 manifest reader 提供精确 source identity；禁止直接静默回填 publication 字段。 |
| evidence | 修复后的 `verify_source_bundle()` 对 2026-09-24 bundle 返回 PASS；sealed bundle SHA 为 `fc71a9443414ac85212f503bd1f9fd4b2ca61ef2a496d5eee8279cad93cd0aba`，官方输入包 SHA 为 `b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f`。当前该日 publication 仍为 `PUBLICATION_ID_ONLY`；因此 310 个 T+1 outcome 仍因 `TARGET_INPUT_UNSEALED` 保持 PENDING。 |
| acceptance_result | `OPEN / SOURCE_REVERIFIED_OVERLAY_NOT_REGISTERED`。本次只读诊断没有变更 accepted publication 或 settlement 历史。 |
| next_stage | 定义带迁移合同、publication id、bundle id、receipt SHA、package SHA、验证器版本、接受时刻和证据 digest 的 append-only identity migration；让 settlement/source manifest 明确读取原生身份或已验收迁移身份。先在隔离 PostgreSQL schema 测试冲突拒绝、幂等重放和审计读回，再通过显式操作登记生产身份并预览 T+1 结算。 |

该修复属于跨切面审计项，接受结果独立于当前 Focus 阶段门。
