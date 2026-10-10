# State Publisher → FirstObserved 源码实际字段差异

阶段合同：TASK A / 最新 V4.2.2 §78 V4-11、V4-15、V4-16。exact_BASE=c0b9903fe596c1884c04f5529d6699034548850e。Phase 0 继承现有分范围 gate；未执行新的 scanner 算法或重算市场。

Publisher 原件为 gzip；freeze_first_observed 输入为普通 JSON。桥接必须生成新候选接口，保留原 gzip 身份。

| State 字段 | 当前原件 | FirstObserved 必需 |
|---|---|---|
|publication_id|STATE_PUBLISHER:47323b91704a49f0ec616b826ca0a6eef64f2ab6d48b6ef356b8e02574efd70f|版本身份/完整绑定及合法值|
|revision|delivery-r1|版本身份/完整绑定及合法值|
|state_lineage_id|MISSING|版本身份/完整绑定及合法值|
|frozen_signal_version|MISSING|版本身份/完整绑定及合法值|
|capture_deadline|MISSING|版本身份/完整绑定及合法值|
|first_available|None|版本身份/完整绑定及合法值|
|frozen_at|2026-10-10T10:00:45.899277+00:00|版本身份/完整绑定及合法值|
|membership|{'bytes': 2281, 'path': 'data/v4/dynamic_daily_owners/2026-10-09/6c04ca70243fb34e33adef9e472fa229fab57aa8968a1b93db70d72105021917/MEMBER_SNAPSHOT_S.json', 'sha256': '11d1c790c6dbd0|版本身份/完整绑定及合法值|
|model|{'bytes': 1292, 'path': 'docs/evidence/state_publisher_models_v1/cdb53fa2507bda4f49975490898a8fec5cd4e2c472dec2aa17a42261c28e3277/model.json', 'sha256': 'a6093f8561dcc7497713014ffb|版本身份/完整绑定及合法值|
|scope|ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS|版本身份/完整绑定及合法值|
|evidence_class|RECONSTRUCTED_RESEARCH_ONLY|PIT_OBSERVED + 当日合法时钟|
|T0|2026-10-09|版本身份/完整绑定及合法值|

完整实际顶层 schema：`T0, adapter_gap, adapter_ready, candidate_head, contract_id, evidence_class, first_available, frozen_at, frozen_computation_dependencies, membership, model, next_gate, observation, observed_count, production, production_write_authorized, publication_id, revision, scenario_outputs, scope, source_owner_admitted, source_owners`。
完整实际 model schema：`dependencies, model_contract_id, parameters_sha256, scenarios, window_version`。
完整实际 row schema：`actual_cutoff, benchmark, checks, eligible_at_T0, episode_id, event_type, exclusion_reasons, first_available, frozen_at, membership_version, model_sha256, parameters_sha256, qualification, scenario, security_id, source_owners, source_window, state, unavailable`。

Model 缺 first_available / frozen_at；membership 是当前 TDX snapshot，必须另供 true AS_RECORDED / PIT_ELIGIBLE 的完整当日 stock universe，不能把 current 标签替代原件。每行 episode_id/event_type/benchmark=null，eligible_at_T0=false。首次接口要求完整事件身份、benchmark.id、逐行 first_available/frozen_at，以及全 universe×scenario ledger。FALSE/UNKNOWN必须有排除原因；输出全部保留，不仅Top-K。

这份完整差异同时满足指定 STATE_PUBLISHER_TO_FIRST_OBSERVED_FIELD_DIFF.md 内容；没有为不具备的历史 PIT 补时钟。
