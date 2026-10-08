# FP12 日期冻结回放与跨对象比较执行记录

授权范围：用户提供的 12_PIT冻结回放与跨对象比较_R1_20261008.md。阶段入口见 docs/evidence/fp12_20261008/ENTRY.json；Phase 0 FULL_PASS。遵循总任务卡、V4.2.2 REV2 的时间边界和 AGENTS.md；未进入下一任务。

阶段合同：config/v4_replay_compare_contract_v1.json。独立日期发布目录及逐文件 SHA 绑定于 config/v4_replay_compare_authority_v1.json，并纳入研究快照 manifest。旧日期原始、复权、交易状态、身份输入如修订，构建器拒绝隐式覆盖，要求显式发布。日期版本 token 冲突返回 409，未来日期拒绝。

| 任务要求 | 实现及验收 | 结果 |
| --- | --- | --- |
| T0 当时可知数据、日期与模型 | /api/v4/replay?as_of=；逐字段 effective_date、known_at、publication_date、model_namespace，模型可得时间与上海日界门禁 | 工程通过；真实严格 PIT 数据不可用 |
| 缺历史不得用当前成员补齐 | 9/28、9/29、9/30 独立修正截面；严格视图不展示重建状态；不存在日期 PIT_NOT_AVAILABLE | 通过 |
| 股票对股票、上一交易日、市场 | /api/v4/compare；同一 FP07 原生复权坐标、接受交易日、真实行情；前日状态取前日截面 | 已实现事后重建比较，非 PIT |
| 冻结板块基准与当前 LOO 分开 | 独立行和来源原因；不存在绑定篮子不产生收益 | 来源缺口，降级 |
| 板块与市场、三日前、生命周期 | 当前成员中位数仅诊断；历史成员和阶段输出不足返回不可用 | 当前诊断可读；历史比较未具备数据 |
| 图表、T+1/3/5 | RAW 图表截断至 T0；明确点击后独立后续区；未接受未来日期待数据 | 通过；不参与 T0 哈希 |
| URL 与身份 | 日期、资料视图、对象、比较方式进入 URL；SPA popstate；API 日期/版本绑定 | 浏览器前进恢复 9/30，后退 URL 恢复 9/29；刷新可读 |
| 未来数据攻击 | future outcome/member/state/time/model、未来行情/全库摘要变化 | 测试通过 |

真实数值：REAL_VALUE_ORACLE.json 核对 12 个真实股票行情端点收益与 Core kernel，误差 < 1e-12；浏览器 SH.600000 同窗收益 3.268%、市场参考 -0.136%。历史图终止 9/29，独立 T+1 实际 9/30 收盘 9.48，T+3/5 待数据。截图位于同目录。

真实数据的知识血缘是 RECONSTRUCTED_CORRECTED、AS_RECORDED=false；9/30 发布发生于 10/1，不能证明历史首次可用。严格 PIT 可用日期为 0。历史板块成员只绑定 9/30；已有 T0 冻结篮子示例 members=[]、UNKNOWN_UNAVAILABLE，也不能制造基准收益。独立审计项见 docs/audits/FP12_PIT_SOURCE_READINESS_20261008.md。

阶段验收：DEGRADED_PASS，仅限工程交付和诚实降级。未达到原卡完整生产 PIT 验收。证据而非测试单独建立此结论。后续为独立审计项补齐真实首获时刻、历史成员及阶段输出并重新验收；不自动进入 FP13。

TDX：本阶段没有访问或修改 TDX 根目录。872 个历史受保护引用最终摘要核验见 FINAL_ACCEPTANCE.json。相关代码与本阶段证据单独提交并推送，Git 推送不等于外部验收。
