# Focus 同日修订与顺序回放独立审计项

| 字段 | 记录 |
|---|---|
| audit_item | `FOCUS_SAME_DAY_REVISION_ORDERED_REPLAY_GAP` |
| scope | `07A` same-day source revision writer、accepted head 切换、anchor/outcome 可见性及 downstream ordered replay。 |
| evidence | `3a2f7a8d92e9313b7b2ad4b5120f9a57d82f5601` 实现同日 revision 原子写入、每 revision 独立 run/observation/anchor、按日期 head 过滤结算，以及从最早 replay date 顺序重建。临时 PostgreSQL E2E `docs/evidence/FOCUS_SOURCE_MODEL_BOUNDARY_E2E_20260924.json` 验证同日 r1→r2→r3、旧 anchor 隐藏、D2 修订后 D3/D4 失效、拒绝跳过 D3、依次重放 D3/D4 并清空 backlog。Focus 回归 153 passed。 |
| acceptance_result | `CLOSED / REVISION_AND_ORDERED_REPLAY_E2E_PASS`。关闭代码、事务和合成数据库验收缺口；真实连续交易日 Forward gate 仍独立待验。 |
| next_stage | 07A 按自然交易日收集真实 Forward 证据；Auto Apply 继续关闭，07D 继续等待 07A/07B 的真实阶段门。 |

旧 run、观察、anchor 和 outcome 保持追加式历史；修订 head 决定当前有效版本。此审计项不替代真实多日 Forward 验收。
