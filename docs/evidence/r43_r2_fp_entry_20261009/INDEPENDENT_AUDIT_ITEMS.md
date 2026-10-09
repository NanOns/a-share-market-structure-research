# 独立审计事项

以下事项的范围、证据和验收独立于本轮控制面工程门，commit/push 与测试不能关闭外审项。

| 项 | 范围 | 本轮证据 | 状态 | 独立关闭标准 |
|---|---|---|---|---|
| R43-R2-AUTH-001 | 直接用户权限原始来源 | 原始 user-role 事件、会话 ID、UTC 时间、行号与抽取 SHA | LOCAL_ORIGIN_FOUND_EXTERNAL_REPLAY_PENDING | 外审从原会话独立回读身份、上下文及逐项范围 |
| R43-R2-CTRL-001 | 新旧控制面语义 | 68 隔离 HTTP、37 生产 HTTP、两个 namespace、并发回归 | ENGINEERING_FIXED_EXTERNAL_REVIEW_PENDING | 外审复核 V2 字段合同、consumer 迁移与实际运行 |
| R43-R2-UI-001 | FP 全产品覆盖 | 真实六入口 DOM/截图、实际缺失 owner 与每包下一卡 | FP_ENGINEERING_ENTRY_AND_GAPS_RECORDED | FP01–FP14 逐卡按原合同完整验收，不以 200/截图替代功能 |
| R43-R2-DATA-001 | 全域数值与 Rotation oracle | 冻结四日 owner 原字节复用；VALIDATION_ONGOING 保留 | FULL_INDEPENDENT_NUMERIC_NOT_GRANTED | 全状态机竞争路径、递归 oracle 与源覆盖独立审查 |
| R43-R2-DAILY-002 | 后续日期日更 | 官方日历绑定、动态 next-session preflight、last-good 保留反例 | BLOCKED_SUCCESSOR_AND_SOURCE_QA | 独立日增量、身份/生命周期/GBBQ、Source QA、successor/CAS/失败回滚、真实读回 |

数据身份与成员 S 未改；本轮不是重新执行 10/08 切换，也不是 FP14 完整产品发布。
