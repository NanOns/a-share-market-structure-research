# TASK B · 上线前工程预检

合同：NEXT_T0_OLD_HEAD_IDENTITY_PREFLIGHT_V1；依据 2026-10-10 总调度 TASK B、整体外审、V4.2.2 REV4 第78节、PRE_NEXT_T0 STAGE_CONTRACT 与 AGENTS。基线 c0b9903fe596c1884c04f5529d6699034548850e。

裁决：ENG_PREFLIGHT_PASS_SCOPED；真实 10/12 首获为 PENDING；EXTERNAL_ACCEPTANCE_NOT_GRANTED。12 项真实 pytest 通过，是合成隔离函数行为，不是交易样本或生产许可。

DailyJobs 调用 execute_sources；实际 TDX package/target 与 BaoStock raw/runtime 原件先冻结。源不齐时已取得的 TDX 字节保留；合并源齐后 daily_freeze 和 capture_daily_sources 在 verify_source_gate 前执行。测试覆盖后续 gate 失败不会丢弃源字节，也不产生 Owner/CAS。

verify_source_gate 读取原始SHA、target bars、BaoStock目标日期和数值、factor同日或明确无变化证明；仍从 previous accepted Head 的 life.identity 产生 expected_codes，仍读取只读 GBBQ SHA。新 code 即使 TDX/BaoStock 相符也仍 WAIT_BAOSTOCK_DAILY。新 old_head_identity_preflight 明确区分 NATIVE_BYTES_CAPTURED_RECONCILED 与 PREVIOUS_HEAD_IDENTITY_SCOPE_MISMATCH。旧依赖源 gate 未放宽。

identity_authority_candidate 仅为新合法日期审源形态（当日原字节 binding + observed codes）；没有签发新 Identity Owner，没有借用代码列表作为合法身份；eligible_as_authority=false，PIT=false。真实新的 Identity/membership Owner 仍需独立合同与审查。

门通过后的现有真实链：derive_ready_sources → ready_owner.build/seal → 数值oracle → producer sidecar → SAME_DAY_SOURCE_SCOPE_RECONCILIATION_V1 → Publisher/quarantine → 独立准入。隔离测试真实执行控制/适配层，SDK/network/kernel/CAS 使用明确 synthetic IO；生产 28765 本轮未加载。旧/新Head和两种成员版本、源缺失、成员变化、日期错配、首次时钟以及重试幂等由对应测试覆盖。

源时钟 requested_at 缺失保留 null；received_at 若源没有独立字段，回退 observed_at，不能据此声称更早 provider publication。first_available_at 在本诊断仅指原始 native receipt 的实际 observed_at，不授予 State/PIT first_available。10/09 输出不重算；没有构造真实 10/12 原件。

下一阶段：10/12 现场采集后逐字段审源；旧闸修订必须独立批准。TASK B 不要求生产重启，需加载事项见 B_SAFE_SCOPE_DEPLOYMENT_PLAN.md。
