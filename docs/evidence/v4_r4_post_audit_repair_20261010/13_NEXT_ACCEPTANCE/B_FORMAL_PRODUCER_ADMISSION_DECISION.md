# 板块正式 Producer 入场决策 R1

T0=2026-10-09。真实 Native、Core、运营 Head、9/24 legacy 原件字节 SHA 已在 B_CURRENT_SOURCE_BYTE_READBACK.json 回读；本轮无新正式原件。

| 六字段 | Producer / 必须原件 | 10/09 首获与 accepted binding | 窗口/成员版本 | 当前决策 |
|---|---|---|---|---|
| CONFIRMED | exact legacy valid-member publication + 冻结 AST | SOURCE_NOT_PRESENT | 当日 legacy 成员、观察截止、AST 版本 | BLOCKED |
| WARM | q20/dq5_3 rank + SETUP/RECOVERY 原 publication | SOURCE_NOT_PRESENT | 原排名窗口、成员版本；Amount 分支独立 H21 门 | BLOCKED |
| frozen_invalidation | 原始 prior SECTOR Episode 创建冻结 Owner | SOURCE_NOT_PRESENT | 创建时成员集与首次可用 | BLOCKED |
| episode_invalidation_contract_id | 原 Episode 合同 ID/version/SHA | SOURCE_NOT_PRESENT | 创建冻结版本，不用当前配置替代 | BLOCKED |
| followup_complete | 原 due_plan + 已成熟 settlement Owner | SOURCE_NOT_PRESENT | 冻结市场会话与真实到期 source | BLOCKED |
| scenario | 正式 confirmation/scenario + 原 priority publication | SOURCE_NOT_PRESENT | 当时成员版本、first_available、prior state | BLOCKED |

A05 只接受 2026-09-24 原证据；10/09 仍 A05_CURRENT_SNAPSHOT_TARGET_NOT_ACCEPTED。9/24 TRUE/FALSE/UNKNOWN 金样本只为诊断候选。

合法新原件路径：由获准正式 Producer 在真实新 T0 从只读源生成完整观察、原始窗口/成员清单、first_available、cutoff、source SHA 和合同版本；在 G 盘以不可变 publication 发布。独立审查当日 source/Owner 合同、Head binding、AST 黄金输入覆盖、Episode 前驱、能力 grant，之后才可通过 prepare_entry 输入六个逐字段 SHA 绑定 receipt。候选字节校验不替代 SECTOR_D2_FORMAL_OWNER_PASS。不得扩写9/24授权日期或改 as-recorded 标签。

Native 非 H21 事实继续按既有获准显示。正式 reducer 与消费者保持关闭；下一阶段为真实原件及独立准入审查。
