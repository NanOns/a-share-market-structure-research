# FOCUS-07D 入口门核对（2026-09-24）

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 30～34、38～41、50.4、52 节；`docs/FOCUS_07A_FORWARD_READINESS_20260924.md`；`docs/FOCUS_07A_CONTINUATION_PRE24_GATE_20260924.md`；`docs/FOCUS_07B_07_SUSPENSION_GAP_PATH_20260924.md`。 |
| stage_contract | 07D 的变化驱动首页、研究优先级、详情页和图形，须等 07A、07B 通过真实 Forward 后推进。入口未通过前，只允许修复已确认的真实 UI 缺陷；不提前进行 07D 功能实现或大规模界面调整。 |
| evidence | 07A 已有 2026-09-23 至 2026-09-24 两个连续 accepted REAL_FORWARD 日；记录要求至少五个连续真实交易日、真实退出后的持续 observation 和到期 outcome。310 个待结算 outcome 尚无终态。07B 合成与现有数据验收完成，但技术对象新日回查及真实确认停牌复牌样本仍待后续正式数据；本地标准化行情没有 `CONFIRMED_SUSPENSION` 行。07C 算法合同和代码验收完成，V2 observation 正式落库也仍待下一日 accepted publication。 |
| acceptance_result | `NOT_STARTED / ENTRY_GATE_PENDING_REAL_FORWARD_07A_AND_07B`。当前没有证据证明 07A 与 07B 的真实前向总门均通过，因此 07D 入口条件不成立。本记录不把已有单元测试、合成样本或只读回算记作真实 Forward 通过。 |
| next_stage | 后续 accepted 交易日到达时继续执行 07A writer、readback 和 outcome 结算，并完成至少五日及退出生命周期验收；出现可用新日对象和真实确认停牌复牌样本时完成 07B 前向核验。两个阶段各自达到真实 Forward 验收后，再启动 07D-01～04，并按 07D 合同记录变更与验收。 |

## 07D 预定交付范围

- 07D-01：默认首页呈现值得复盘的变化，并折叠 `PERSISTENT` 稳定对象。
- 07D-02：只定义页面研究优先级，不改变 V3.3 `category_rank`、score、候选资格或来源成员关系。
- 07D-03：详情页呈现最初关注原因、后续变化和当前解释三段证据。
- 07D-04：价格图展示 K 线、MA5/MA10/MA20，并标记关注、升级、首次支持、失效、退出生效及重入事件。

以上为升级方案定义的目标范围；本轮入口检查未修改产品界面或业务数据。
