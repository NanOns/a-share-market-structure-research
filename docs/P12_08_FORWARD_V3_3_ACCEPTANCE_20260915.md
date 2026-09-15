# P12-08 FORWARD_V3_3 验收

## 阶段合同

依据 `V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md` 的 P12-08：连续封存真实时点可得的研究结果，记录股票进入、退出、类别变化、选择模式变化与延续状态，并按场景和关系数量分层形成描述性前向报告。效果报告最低门保持为至少 20 个独立信号日、50 个具有明确身份的独立 episode；历史回放不得计入真实前向天数，达到门槛也不得自动关闭效果专项审计。

本阶段首轮合同为 `TODAY_RESEARCH_FORWARD_V3_3_CANDIDATE_02`。P12-08A 随后以 `CANDIDATE_03` 补全稳定 episode 身份，详见 `P12_08A_EPISODE_IDENTITY_ACCEPTANCE_20260915.md`。本阶段只建立前向封存和报告能力，不开展 V3 校准，不修改 TDX 输入，不写生产数据库。

## 实现与证据

- 每日观测绑定交易日、研究 run、活动 bundle digest 和逐股解释字段，以内容摘要命名并原子封存；同内容重跑复用，内容冲突拒绝。
- 状态迁移合同覆盖 `ENTERED`、`EXITED`、`CATEGORY_CHANGED`、`MODE_CHANGED` 和 `CONTINUED`。
- 报告按研究场景、关系数量 `1-2`、`3-5`、`6+` 以及选择模式分层。
- 首轮发现活动候选包未携带 `episode_id`；P12-08A 已通过新合同按首次进入/延续/类别变化生成稳定身份，旧封存不覆盖。
- 机器证据：`reports/p12_08/p12_08_stage_gate.json`、`reports/p12_08/forward_report.json`，以及 `data/forward_v3_3/observations/2026-09-14/6f6358cdae2b792dbe5fb5ec50d4bedca91e75c4680cf0196ae74f13c7cb35b2.json`。

## 验收结果

**DEGRADED_PASS**，工程阶段通过，效果观察继续待验。

已封存 2026-09-14 一个真实 PIT 信号日、113 条候选；104 条为 `LAUNCH_CONFIRM`，9 条为 `TREND_CONTINUE`。关系分层为：`1-2` 共 5 条，`3-5` 共 20 条，`6+` 共 88 条。首日迁移为 113 条 `ENTERED`。定向 P12-07/08 回归 9 passed，Python compileall 和 `git diff --check` 通过。

P12-08A 修订后最低报告门为 1/20 个独立信号日、113/50 个唯一 episode 身份；同日相关性仍按日期分组，不把113只股票当作113个独立交易日。1、3、5、10 日后验结果均为 `NOT_DUE`，历史诊断回放未计入前向门槛。效果状态保持 `EFFECT_OBSERVATION_PENDING`，独立效果审计保持开启。

## 下一阶段

P12-08 工程合同验收完毕。只有连续真实日观测达到 20 个信号日且显式独立 episode 达到 50 个后，才可独立评价并考虑 V3 校准；当前不得进入校准阶段。
