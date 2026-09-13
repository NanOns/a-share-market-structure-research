# V3 P07-01：板块四类成员角色

## 结论

依据最新 V3 主实施文档 §6.2、§18.10 与 C20-07，P07-01 验收结果：**FULL_PASS**。本轮只执行 P07-01，不进入 P07-02。

## 阶段合同

- 合同 ID：`SECTOR_MEMBER_ROLES_PREVIEW_1`；入口：`workbench_analysis.sector_attention.build_sector_member_roles()`。
- 完整绑定成员集先确定分母和同日排名，再独立判定 TODAY_LEADER、CURRENT_RESEARCH、EARLY_WATCH；ALL_MEMBERS 只作为完整成员查询结果，不复制拒绝关系到紧凑角色结果。
- TODAY_LEADER：有效当日 `ret1>0` 且在本板块有效报价平均秩分位不少于 .80；排序 `ret1↓, amount_vs_prior20↓, security_id↑`。它是事实榜，不要求 RPS20，EXTENDED 也可保留并标事实风险。
- CURRENT_RESEARCH：板块 CURRENT 且 BREAKOUT/RECOVERY，非 STRUCTURE_BREAK、位置完整、非 EXTENDED；排序 BREAKOUT 优先，再金额、RPS5 改善和证券 ID；每板块最多 5 条预览。
- EARLY_WATCH：板块 POTENTIAL 且 SETUP/RECOVERY，非 STRUCTURE_BREAK、位置完整、非 EXTENDED；排序 SETUP 优先，再 RPS5 改善、绝对 bias20、金额和证券 ID；每板块最多 5 条，允许为 0。
- 缺报价的 ALL_MEMBERS 行保留并带 `QUOTE_UNKNOWN`；未知条件不转成角色合格。没有提前成员时不从旧 RET20 龙头补位。

## 验收证据

定向测试 `tests/upgrade_v3/test_p07_01_member_roles.py` 为 3 passed：当日赢家与 RET20 赢家可不同；EXTENDED 保留在 TODAY_LEADER 但不进研究角色；EARLY_WATCH 独立且不补旧龙头；角色预览上限和缺失解释有效。

真实只读产物：[P07-01_MEMBER_ROLES_DISTRIBUTION.json](../reports/upgrade_v3/P07-01_MEMBER_ROLES_DISTRIBUTION.json)。输入为 2026-09-10 publication `m4-8a99c99719061f4f1f166d0b9184506c`，成员 75,028 条、股票信号 6,178 条、554 个板块。分布为 ALL_MEMBERS 75,028、TODAY_LEADER 2,316（覆盖 522 个板块）、CURRENT_RESEARCH 0、EARLY_WATCH 0。研究角色为 0 是当前 CURRENT/POTENTIAL 阶段事实，不以事实榜填充；不构成效果或概率结论。

未写生产数据库、未修改 TDX、未启动 scanner。角色结果仅在内存和报告摘要中验证，P07-03 之前不接入正式 writer/API。

## 下一阶段

进入 P07-02：在四类角色基础上实现 CURRENT/EARLY 分离的主关联、最多两条备选和两条独立短名单。本阶段不预先实现或验收 P07-02。
