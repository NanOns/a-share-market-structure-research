# V4 R21-R4 BaoStock runtime ingress PG 接线 R88

- 日期：2026-10-17
- 范围：`accept_v4_dm01_baostock_runtime.py` 与 `accept_dynamic_daily_baostock_v2.py` 的 runtime acceptance 来源路径、交易日 authority、SDK schema contract。
- 代码结果：两种入口的验收 receipt/manifest 均写入 `BAOSTOCK_CACHE_ROOT` 配置缓存；连续验收入口通过 PG-only `official_sessions` 校验目标交易日，并从 PG 合同注册表读取 `BAOSTOCK_DM01_SDK_SCHEMA_ADAPTER_V2@2.0.0`。保留 download root 现有项目内路径边界和 TDX root 写保护。
- 验证：受控离线测试仅验证配置路径和 PG reader 调用边界，不代表外部 BaoStock 数据验收、PG 写入/读回、Head 更新或日更业务验收。实际 PG 读写身份未提供，本轮未执行 live ingress。
- 原 266 项账：原始稳定 ID 真正完成 `0/266`，剩余 `266/266`；其中 53 项已有 PG-only 代码路径但待库存/线上核对，213 项仍 OPEN 或 ingress-open，22 项没有可映射引用。R88 没有可精确映射到本批入口的原始稳定 ID，因此不改计数、不关闭项目。
- 后续：继续按原始 ID 将 Head/Authority/descriptor、其他业务读取与 Owner 读取接到真实 PG 调用链；补齐 DM-01 编排的 PG 状态迁移、采集路径配置及在线读回证据；持续检查 CI，并更新 Issue #2 和 PR #3。
