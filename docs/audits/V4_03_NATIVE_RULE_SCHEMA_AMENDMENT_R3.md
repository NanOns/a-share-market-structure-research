# V4-03 native machine contract amendment R3

状态：**候选修订，待独立外部接受**。治理任务为 `V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md`。

现有 `RULE_AST_V2` 适合单字段标量、技术窗口和横截面表达式。Native 合同还需要集合身份、一个规则同时输出数量和质量、以及跨日 `UNKNOWN` 后缀状态。将这些状态压进单字段表达式会丢失成员集合及链式路径语义，因此本轮采用版本化 `V4_03_NATIVE_DETERMINISTIC_RULE_SCHEMA_R3`。既有 1.1 股票字段合同不变。

机器规则文件为 `config/v4_03_native_rule_contracts_r3.json`，独立执行器为 `src/v4/contracts/native_rule_r3.py`，验证器为 `scripts/verify_v4_03_native_rule_contracts_r3.py`。四个 operator 对应四个 native 合同：PIT 等权市场参考、未知后缀市场路径、市场轴阈值规则、板块字段局部质量原语。每个合同有具名正反向向量，执行器不导入生产 `native.py` 或 `relative.py`。R3 回执记录合同和向量数及每类覆盖。

板块合同的合成向量只验证算法语义，不提供已接受历史板块成员。缺少成员身份时执行器拒绝发布；`SECTOR_NATIVE` 仍为 `BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP`。本修订须由独立外部验收确认，不能因机器向量通过自动升级为正式阶段 PASS。
