# FEP R0 集成与架构独立审计 — 2026-09-30

状态：DESIGN_REVIEW_CHANGES_REQUIRED。只读检查设计稿、现行 REV2 与仓库合同/实现，不证明数据库运行或预测效果；未修改主合同或代码。

审计输入：桌面 `A_SHARE_RESEARCH_SYSTEM_V4_2_2_FORWARD_EXPECTANCY_PRIORITY_MODULE_R0_20260930.md`（下称 R0）；`docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`（下称 REV2）；读取时 HEAD `0581731c1284e82380fa115156f1dc0a16a38bd4`。R0 行8引用较旧 `68276e4...`，不能把该引用当当前实现验收证据。

## 结论及独立问题

| ID /级别 | 证据（文件、起始行） | 问题与修订要求 |
|---|---|---|
| FEP-I01 / P1 | R0:690、706；`config/v4_08_sector_membership_contract_v2.json`:4、19 | Sector Benchmark 被列全局 Mandatory，而 Sector Context 又 Optional。当前 accepted membership 尚有独立时间证据门。改成按 entity/target/model scope 的依赖矩阵；纯 Stock-Core 的 absolute/market/risk 不依赖 sector，Sector Excess 单独不可用，不把所有 FEP 或 Core 挡住。 |
| FEP-I02 / P1 | R0:3358；3290；REV2:6383 | E1→E2→E3→E4→E5→V4-16 字面顺序使 Tree Challenger 或训练样本不足阻止既有 Shadow。改旁路 DAG：V4-15 可用后 E1、E2；E2 可直接进入 E5 的 baseline Shadow，E3/E4为可选 challenger。原 V4-16/UI/Focus 的工程推进不等 FEP，只授权已就绪能力。 |
| FEP-I03 / P1 | R0:724；REV2:6311–6312 | “T0 accepted 时冻结”没有定义事务边界。State/Radar 必须先完成而 FEP不能阻断Core。Core accept 原子登记冻结输入引用与 outbox；独立 worker 按这些引用物化，不读 latest。接受后失败只产生 FEP PENDING/UNKNOWN；晚完成需按预测截止时刻降为 reconstructed，不能假冒当时已看见。 |
| FEP-I04 / P1 | R0:744、1933、2796、3732 | snapshot 主键只有 feature contract/publication/entity，无法同时表示同一 Core publication 不同 supplemental/context 修订；模型集合与prediction revision只有token名字，没有注册实体、完整FK与冻结关系。需 feature dependency manifest digest（或显式 enrichment/context revision），snapshot_id、model_set_id、prediction batch/revision完整唯一键和FK；校验publication日期/entity、target/horizon、model feature schema一致，禁止跨namespace拼接。 |
| FEP-I05 / P1 | R0:2917、2875；REV2:4834 | FIRST_OBSERVED/LATEST_CORRECTED仅覆盖源修订，不能防今天训练模型回推旧日被记为first预测。补 model accepted/activated_at、inference completed_at、prediction cutoff、first-accepted ledger及重跑用途；只有截止前真实发布的预测进入真实Forward预测评估，晚回填独立reconstructed。 |
| FEP-I06 / P1 | R0:1983；REV2:678、4681 | 现行产品边界明确“不直接回答明天上涨概率”，FEP展示正超额条件概率。必须明确修订§2/§50，而不是append后留下矛盾；定义研究条件分布/校准概率允许范围和禁止交易承诺。M14公开增强禁概率仍独立保留，不能据此误判所有独立FEP禁止概率。 |
| FEP-I07 / P1 | R0:2617、2640、3732、3786 | registry生命周期不足以保障并发切换和回退：需要accepted模型集合的不可变manifest、按scope/date生效的部署head、CAS切换、完整batch原子可见、部分target能力状态与幂等键。rollback仅切FEP head，保留预测/评估历史，不能回写Core或删除已见预测。 |
| FEP-I08 / P1 | R0:8、1269、3850；`data/v4/V4_07_ACCEPTED_HEAD.json`:121、138；`data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json`:72 | 不能把已accepted工程当可训练的历史PIT。现有V4-07明确 5222/5222 的rps5_delta3 UNKNOWN，prior-RPS审计OPEN；历史as-recorded调整价也有证据限制。数据集须逐字段/日期按真实accepted lineage和quality过滤或明确缺失模型，不能从旧staging补出“完整历史”。样本能力不足不阻断独立工程开发。 |
| FEP-I09 / P2 | R0:3710；REV2:1707、5989 | 两个token扩展字段不足以定义API：未规定首次查询如何取得已接受FEP head、publication不匹配、同Core多FEP版本、pagination/evaluation cutoff。保留完整既有context token，再引用FEP manifest。缺失/过期/错配返回结构化状态，不回落latest。现有token确为R0列的五字段，本审计不主张遗漏run_namespace。 |

## 当前存在的实现与可复用边界

| 已存在路径 | 可复用内容 | 不可据此声称 |
|---|---|---|
| `src/v4/accepted_input.py` | accepted head/hash-bound读取模式；检查代码中当前cutoff/路径固化限制后再抽象 | 已有通用FEP训练集resolver |
| `src/v4/profile_core.py`、`profile_primitives.py`、`profile_status.py` | Core计算、字段质量解释 | 可任意重算历史并冒充原T0快照 |
| `config/v4_04_field_registry_v2.json`、`config/v4_03_native_contract_registry_v1.json` | 实际字段/producer合同查表 | R0所有候选field均已实现或同义 |
| `src/v4/base_seed.py`、`data/v4/V4_07_ACCEPTED_HEAD.json` | 已接受Seed工程及UNKNOWN传播 | 当前历史拥有完整Seed/RPS/结构样本 |
| `src/workbench_db/migrations/v4_postgres/003_phase0_contract_alignment.sql`、`004_publication_head_revision_identity.sql` | publication_id为不可变revision身份、accepted head规则 | 应沿用001初始复合PK而忽视后续迁移 |
| 同目录 `015_v4_07_base_seed_results.sql` | append-only publication-bound sidecar模式 | 该表即FEP dataset或新预测ledger |
| 同目录 `016`–`018`及`config/v4_08_sector_membership_contract_v2.json` | membership temporal lineage、质量门和正式view | candidate已外审accept；历史当前成员可倒填 |
| `src/workbench_analysis/forward_outcome_v3_3.py`、`src/focus_tracker/outcome_math.py` | 旧实现可作为数学/迁移参考并逐项重新验收 | 已实现V4-15统一Label Authority；Focus outcome等于完整Validation Cohort |
| `src/workbench_service/app.py` | 当前HTTP接入位置可研究复用 | 已存在R0五个FEP API |

V4-15统一结算器在REV2:4610/6383是未来阶段交付要求，本次未找到已实现并验收的V4 FEP或V4-15结算模块。因此设计应写“消费将由V4-15交付的权威结果”，不是现成函数调用保证。

## 拟新增路径（设计建议，尚未创建/实施）

- `src/v4/expectancy/`：snapshot、target_projection、dataset、conditional、inference、evaluation、registry、priority_projection独立模块；训练及推理均不进入Core producer。
- `config/fep_feature_registry_v1.json`、`fep_target_registry_v1.json`、`fep_dependency_matrix_v1.json`、`fep_parameter_contract_v1.json`：逐字段映射单位/时间/nullable/quality/allowed scope，禁止只凭相似名字映射 `rotation_state` 到正式 `rotation_core_state`。
- `src/workbench_db/migrations/v4_postgres/<next>_fep_*.sql`：编号在实施时分配，不抢占并行阶段；包含依赖manifest、dataset成员、target revisions、model artifacts/deployments、prediction batch/rows、priority projection/evaluation及append-only约束。
- `src/workbench_service/expectancy_service.py` 与现有app路由：只读accepted FEP批次，参数化上下文，不现查现训。
- `scripts/run_v4_15e*.py`、`tests/v4_fep/`：按E1/E2/E5旁路先行，E3/E4可选；有重复消息、CAS冲突、崩溃恢复、late inference、optional缺失、跨publication混合、rollback不改Core的验收。

## 主合同必须显式同步的章节

§2（产品概率边界）、§3/§77B（Core接受后旁路）、§4.9/API（完整上下文）、§45/45A（prediction样本不改cohort）、§46/46A/49（复用价格权威与revision）、§50（事后验证和事前研究分离）、§51/51A/52A/52B（工程与真实证据/按能力授权）、§60及PRIORITY/DISPLAY相关段（仅授权后独立投影、不改风险事件或原rank）、§78（非阻断阶段DAG）、§80/81（时序/故障验收）、§83（回滚保留历史）、§84/85/86（术语与边界）、§87/87A（新增producer与字段登记）。

## 接受条件与下一步

以上问题作为跨阶段独立审计项追踪，不替代或污染当前V4-08门。下一步为R1设计修订、逐项处置及其他统计/PIT审计合议；通过设计审计后才并入主合同。字段和schema可在设计层完整提出，但真实源可用性、性能、样本量、阈值和预测质量必须保留待实施验收状态。本报告不授权修改accepted heads、运行scanner、训练或生产切换。