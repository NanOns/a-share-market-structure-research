# State Publisher 源码与输出

实现：`src/workbench_analysis/full_market_state_publisher_v1.py::build`。原算法 owner 生成位置为 `r43_focus_replay.py` 的 target_fact_producers_r4 → confirmation，模型由 `v4.confirmation.package` 校验冻结 legacy AST、参数及场景优先序。本发行器从 exact prewatch Owner 中的 target_values 实际重跑 confirmation，不读取已有 confirmation 分支状态作为判定输入。全市场范围来自 exact Lifecycle active_security_ids，成员版本来自 exact membership snapshot；每证券输出冻结模型的全部四场景。

输出运行合同 `FULL_MARKET_STATE_PRODUCER_OUTPUT_V1`，各行含 eligible/ineligible/unknown、具体失败/未知检查、源 Owner SHA、member 版本、model/parameters SHA、窗口和实际冻结时间。事实源不存在历史首次可用证明时，first_available 和 actual_cutoff 保留 null，而非用现在的机器时间冒充 T0 已知。源截止数据日为 T0；候选冻结时间为本次实际时钟。历史 Episode 无合法原件为 NO_PRIOR_EPISODE，事件和 benchmark 缺源为 SOURCE_PRODUCER_NOT_IMPLEMENTED。

10/09 真实历史研究输出：5,224 证券 × 4 场景 = 20,896，TRUE 300、FALSE 10,046、UNKNOWN 10,550。全部 eligible_at_T0=false、observed_count=null、RECONSTRUCTED_RESEARCH_ONLY。完整原始 JSON 使用确定性 gzip 持久化，不复制数据库。final/STATE_PUBLISHER_ISOLATED_RUN.json 同时记录压缩原件绑定和解压 JSON 字节 SHA。

`full_state_first_observed_v1.quarantine_publisher` 实际读取发布原件并隔离持久化；既有 freeze_first_observed 保留完整 PIT 输入检查。当前缺 Episode/event/benchmark 与独立入场，因此不伪造完整 PIT_INPUT 或 Writer Grant，不调用正式 capture。daily review 的可选 sidecar 接入发行及 quarantine；其失败不阻塞原主链。

合成反例实际覆盖缺信号、新 Universe、重复/异证券污染、未来窗口、缓存状态篡改不影响重算、独立 requested/received 时钟矛盾、历史升格拒绝、模型依赖变更另建版本、重试保留冻结字节。旧首获适配器测试另覆盖 Writer 合同前后边界；只在 G: 临时测试域产生明确 synthetic grant，不产生实际权限。

工程验收：PASS_SCOPED。权威 Source Owner 入场：INDEPENDENT_ADMISSION_REQUIRED；新日真实首次观测：FUTURE_REAL_OBSERVATION_PENDING。本实现是实际 scanner 发行者，不声称已经补出历史从未保存的权威 Episode 或 benchmark。
