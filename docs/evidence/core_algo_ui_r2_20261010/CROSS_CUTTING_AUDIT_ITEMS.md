# 独立综合审计登记

均为OPEN，不能因本轮页面/接口修复而关闭；没有新授权的自动写入或下阶段准入。

| ID | 独立范围 | 当前证据 | 独立接受条件 |
|---|---|---|---|
| AUDIT-CORE-R1-01 | Rotation全递归、阶段改变与同形异因 | dated 5点、原contract/前态、4板块median与breadth；完整reducer未复跑 | 至少3连续真实点，独立前态+新增F→新态/失效/UNKNOWN，真实反例 |
| AUDIT-CORE-R1-02 | 信号完整阈值、锚点失效、重入、LOO | 29股票技术窗、D2 failclosed、真实画像；全部detector未独立计算 | 官方每阈值、T-1依赖、递归prior、终止重入、假设反证逐项闭合 |
| AUDIT-CORE-R1-03 | M10 Amount A及native/BaoStock不同来源口径 | 本轮只显示既有TDX raw CNY及amount ratio；不更改a04权威 | 独立样本/单位/adjustment源合同对账，原审计单独接受 |
| AUDIT-CORE-R1-04 | 严格PIT、历史成员、首次可用与存续偏差 | 当前成员重建且PITfalse；corrected compare有5日 | 有真实首次可用事件且符合原权限和PIT合同，不以后来采集当T0知识 |
| AUDIT-CORE-R1-05 | Validation Cohort、FEP、Forward成熟结算 | Focus路径到期算术不等同Cohort；缺T0合法model/enrollment Owner | 权限/enrollment/baseline/censor/benchmark/成熟分母/实际模型源齐全 |

责任：上述领域各原版本化Owner维护轨道与独立外审；本轮修复不任命新生产Owner、不自授任何原BLOCKED门通过。

## R2 追加证据（不关闭旧审计）

- 01：4 个板块原生算术、5 日 AST/前序计数复核已补；篮子/保持输入生成仍 OPEN。
- 02：125 个股日的确认/PREWATCH 阈值独立求值；实际 INVALIDATED 退出修复，完整 D2/LOO 全递归仍 OPEN。
- 03：金额集中度与市场 CNY 换算有样本；原 M10 Amount A 跨来源独立验收保持 OPEN。
- 04/05：没有新增严格 PIT 首获或合法 cohort/FEP 源，保持原门。

具体独立范围和接受条件见 REMAINING_WORK_LEDGER.json。
