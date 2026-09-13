# V3 P07-02：主关联、备选与双短名单

## 结论

依据最新 V3 主实施文档 §6.3、§7、§18.10，P07-02 验收结果：**FULL_PASS（合同、合成验证与真实零候选门）**。

## 阶段合同

- 关联合同：`RESEARCH_ASSOCIATION_PREVIEW_1`；短名单合同：`RESEARCH_SHORTLIST_PREVIEW_1`。
- `select_associations_and_shortlists()` 只消费真实成员、P07 角色和 V3 板块状态；旧 `association`、`strength_association`、`candidate_daily` 不在输入路径。
- CURRENT/EARLY 分开做 LOO：CURRENT 要求剔除目标股后至少 5 个有效成员、其他成员 `b1>=.55` 且 `m1>0`；EARLY 要求至少 5 个有效成员、至少 2 个其他 SETUP/RECOVERY，并有 `b_delta3` 或 `ma20_delta3>=.05`。LOO 不通过只标注“单股/小样本”，不删除真实成员关系。
- 每只股票每条轨道选择 1 个 PRIMARY、最多 2 个 ALTERNATIVE；主关联按轨道资格、角色、LOO 支持、板块稳定排序，不固定一级行业。CURRENT_FOCUS/EARLY_FOCUS 分别最多 20，每板块最多 3；双轨同时合格时 CURRENT 优先，提前清单不重复占位。
- 选择原因、等待条件和失效条件均显式保存；RECOVERY 提前成员等待“板块当前强势确认”，SETUP 等待 BREAKOUT 或 RECOVERY。

## 验收证据

定向测试 `tests/upgrade_v3/test_p07_02_association.py` 为 3 passed，覆盖主关联不固定第一板块、弱 LOO 不删除关系、两轨清单独立、双命中不占 EARLY、RECOVERY 等待条件。

真实 P07-01 绑定输入报告显示 CURRENT_RESEARCH=0、EARLY_WATCH=0，因此本阶段真实候选行严格为 0；机器门报告：[P07-02_ASSOCIATION_DISTRIBUTION.json](../reports/upgrade_v3/P07-02_ASSOCIATION_DISTRIBUTION.json)。这是零候选安全通过，不生成虚假主关联、备选或短名单。

未写生产数据库、未修改 TDX、未调用旧 association/candidate、未作效果或概率声明。

## 下一阶段

进入 P07-03：只在 P07-01/P07-02 纯计算合同通过后设计完整 research run 的事务封存、幂等 input_key 和已有 job 接入。
