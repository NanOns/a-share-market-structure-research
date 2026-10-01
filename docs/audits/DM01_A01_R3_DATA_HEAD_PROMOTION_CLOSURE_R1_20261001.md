# DM01 A01-R3 外部接受正式化与 Data Head 推进收口

独立外部验收正式 authority 为 `docs/evidence/source_authority/V4_DM01_A01_R3_AND_A13_FORMALIZATION_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md`，审计基线 `ac811e210c66b7ee9446086659dee169ee0f81a8`；任务卡只定义执行范围。

Data Head 已原子推进至 2026-09-30。Accepted Chain 保留 9/24 → 9/28 → 9/29 → 9/30 全部父子指针、27 个组件及 source instances。旧 9/24 Data Head 原始 2478 bytes 已归档，SHA-256 未变化。V2 契约和独立 reader 使用明确归档绑定，不降低旧 hash gate。

Registry R10 清理 A12 当前矛盾状态并保留 R9 历史；DM01 连续链正式接受，A13 formalization 外部确认通过。Owner Registry Bootstrap 仍 OPEN。Stage Head 以及 V4-08/V4-09 字节保持不变，本轮未进行业务重建或重新接受。

最终组件中 ADJUSTED_DAILY、PERIOD_ADJUSTED、PRICE_LIMIT 保持 DEGRADED_PASS，其余六组件 FULL_PASS。权限及原因逐项来自最终 receipt；READY 行未用于升级 capability。

新 checkout `708c0228fbe47b4d86408568bfcfad829040e512` 独立重读完整链与最终九组件真实 source bindings。Disposable PostgreSQL 联合回归：1521 passed / 2 skipped / 1 既有授权 deselected / 0 failures / 0 errors。config/.env 未读取，production DB 未使用，No-Symbol PASS。详见 `reports/audits/DM01_A01_R3_PROMOTION_INDEPENDENT_READBACK_R1.json` 和 `reports/audits/DM01_A01_R3_PROMOTION_CLEAN_CHECKOUT_R1.json`。

production=false、shadow=false、focus=false。后续消费新 Data Head 须按各 stage 独立版本化合同执行；此次推进不授予生产权限或 global mandatory adoption。

跨阶段历史绑定问题独立记录于 `reports/audits/DM01_DATA_HEAD_HISTORICAL_BINDING_RESOLUTION_AUDIT_R1.json`，保留真实失败运行与修复证据。V4-09/V4-10 旧验证器未修改，新只读历史适配不授予当前业务重新接受或生产权限。
