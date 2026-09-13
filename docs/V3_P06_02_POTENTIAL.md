# V3 P06-02：板块 POTENTIAL 三分支

## 结论

依据最新 V3 主实施文档 §5.2、§18.9 与 C20-15，P06-02 验收结果：**FULL_PASS（工程合同与真实只读分布）**。

## 阶段合同

- 合同 ID：`SECTOR_POTENTIAL_PREVIEW_1`。
- `aggregate_early_width()` 直接消费 P05 全量股票 SETUP/RECOVERY，分母为两类信号均可判定的成员，不读取最终 shortlist、旧 candidate 或 member_state。
- `build_sector_potential()` 实现 BREADTH_BUILD、BASE_BUILD、RECOVERY_BUILD 三条分支，所有基础条件与分支条件为三值逻辑；CURRENT 为 true 时 POTENTIAL 强制 false；当前强度或风险覆盖缺失时不静默放行。
- 主标签顺序固定为 RECOVERY_BUILD、BREADTH_BUILD、BASE_BUILD；`q20` 只作 BASE 背景，不作为全局潜在排序替代。

## 测试与真实证据

定向测试 5 passed，覆盖：全量成员早期宽度、不从 20 只截断；低 q20 的扩散改善可入；单一强 dq5 但宽度恶化不入；CURRENT/POTENTIAL 互斥；风险或共同历史缺失为 UNKNOWN。

真实只读产物：[P06-02_POTENTIAL_DISTRIBUTION.json](../reports/upgrade_v3/P06-02_POTENTIAL_DISTRIBUTION.json)。输入绑定 2026-09-10 publication `m4-8a99c99719061f4f1f166d0b9184506c`，成员 75,028 条、P05 股票信号 6,178 条；早期宽度可计算板块 548/554。严格当前/风险/共同比较条件下，真实分布为 POTENTIAL true 0、false 554、unknown 0，三个分支均 0。零命中是当前输入的事实结果，不据此调整阈值；它不代表效果或概率结论。

全量回归、编译和 diff check 在本阶段收口时执行；未写生产数据库、未修改 TDX、未启动 scanner。

## 下一阶段

进入 P06-03：实现潜在 episode 的首次、持续、暂停、确认、失效、到期和 DATA_GAP 生命周期，不回填未来结果。
