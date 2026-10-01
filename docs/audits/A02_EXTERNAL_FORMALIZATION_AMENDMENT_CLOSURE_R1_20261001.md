# A02 正式接受与下游 Amendment 收口

本轮正式 authority 为 `V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md`，审计 `66ef2e342dd339cc9795c2d1fd774b8edec4c345`；原字节 SHA `7d6c8d3faf64a948d206a318d122d41baf757613d0beb88e6d5bd54fcff96bb3`。总调度卡和 A02 卡提供执行调度；独立外部报告提供生产者接受，范围仅 `PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE`。

`A02_EXTERNAL_ACCEPTANCE_FORMALIZED = PASS`。建立独立不可变 `data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json` 及 `reports/audits/next_round_r2/A02_EXTERNAL_ACCEPTANCE_RECORD_R1.json`，精确绑定已经审计的 9/22、9/23、9/24、9/28、9/29、9/30 六日 publication、source input 与 delta 文件。Reader 同时 pin 原审计 producer evidence SHA，不允许把另一个候选串入已接受链。历史仅 `RECONSTRUCTED_CORRECTED`，没有 AS_RECORDED 或历史 first-availability。

从独立 RPS Head 重读实际 prior publications，重新执行原 Accepted V4-05 受影响 projection、原 V4-07 Base Seed 和 V4-09 Stock PREWATCH，未使用运行时 prior rank 重算。新的 profile/factor/seed publication namespace、新实际可用时间、新 source digest 与 Seed bytes 全量绑定。新 Core 与 Factor RPS 元数据逐字段一致，V4-09 精确绑定本次新 Seed 产物。

真实 fresh replay 的 V4-05/V4-07 各 5,222 个身份业务变化，V4-09 2,811 个身份业务变化。Seed 从 FALSE 2,443 / UNKNOWN 2,779 变为 FALSE 3,755 / TRUE 976 / UNKNOWN 491。与上一轮独立接受的 producer 数字一致；接受正式化只改变 lineage/namespace，不改变实际 score/delta，因此没有 source 数值变更需要新 expected。保留全量 old/new 输出与 15,666 行 full business diff。

分别生成 `V4_05_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE`、`V4_07_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE`、`V4_09_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE`；最终证据 `reports/audits/next_round_r2/A02_DOWNSTREAM_AMENDMENT_REPLAY_R1.json`。独立重读逐一检查 delta 来源、全部新 seed/stock 重算、全量业务 diff、旧 Head 和算法参数原字节一致。下游 business amendments 尚未独立接受，状态 `A02_DOWNSTREAM_AMENDMENTS_READY_FOR_EXTERNAL_REAUDIT`。

旧所有业务 Accepted Head 与历史 source/evidence 保留，Data Head 9/30、Stage Head V4-00→10 未动。未开启 V4-11 real confirmation、Production/Shadow/Focus、global mandatory，未执行 V4-12。本轮 root 统一 clean checkout/No-Symbol、提交与 push 后 STOP。
