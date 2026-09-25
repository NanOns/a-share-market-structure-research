# V4-00G Algorithm Contract Framework 阶段回执（2026-09-25）

| 字段 | 记录 |
|---|---|
| stage | `V4-00G / ALGORITHM_CONTRACT_FRAMEWORK` |
| stage_contract | V4.2.2 REV2 §10A0、§72–73、§49A.2、§78、§87A：冻结 Rule AST/schema/参数实例/producer 框架、三类窗口与缺失语义，登记基准缺失、retention、分能力切换参数及 Legacy 精确提取格式。 |
| consulted_upgrade | 最新 REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`；复审 `docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md` SHA-256 `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`。 |
| input_identity | HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`；`V4_ALGORITHM_CONTRACT_FRAMEWORK_V1`；`PARAMETER_REGISTRY_V1`。 |
| execution_boundary | 仅合同与登记框架；未改旧算法、旧输出、数据库、TDX 输入或 production head；未运行测试、scanner、历史重放或重算。新增文件在 TDX 根外原子写入。 |

## 证据盘点

- REV2 §10A0要求序列化 input/producer/time/quality、AST、窗口、舍入、互斥、输出身份及独立向量；Kleene UNKNOWN 不能通过 hard safety。§73要求字面数值映射参数 ID 或声明数学常数。
- `src/factors/registry.py` SHA-256 `c6486d571be26412ba841e1cf79cd14010079e79dfafc2e534afd1a90dd4d7b1` 是 `factor-contract-v1.0`，使用 `CURRENT_NORMAL_UNIVERSE_AT_OUTPUT_DATE`，不能当作 V4 PIT producer 合同。
- `config/history_windows.yaml` SHA-256 `8e4c728c6247857c46a0c99748ed68e370d6193dd49f8479b80db7ada4b0fec3` 是旧 lookback 清单，不能代替 V4 窗口语义和逐字段映射。
- `config/research_v3_schema.yaml` SHA-256 `8d22346245f1d364b9e775d1f327f1158799887eed548fd674dadb4e2857714e0` 是 V3 API preview schema。V3/V3.3 registry需在相应阶段按源码、hash、有序谓词、参数、窗口、缺失语义和 golden vector 精确抽取；“沿用思想”不算合同。
- §49A.2 固定 T0 benchmark 权重、不可删除/重权、停牌标记估值单独输出、`PARTIAL_UNVALUED`不得冒充完整相对收益。覆盖门、quote age 与完整质量权限矩阵由 V4-00H 验收冻结。

## 冻结项

机器合同 `config/v4_algorithm_contract_framework_v1.json` 冻结 AST/schema、版本与 digest 组成、三值逻辑、缺失传播以及三类窗口；文件 SHA-256 `53f42ab97a0af5f00a819f5285475728f9eb055e249f0524ef601974a5c7974a`。参数注册 `config/v4_parameter_registry_v1.json` SHA-256 `179f9d3561b7b8c8cef03ff6adfa979564c16a7e887783d751eae730c3e502e6`，登记基准覆盖/quote age、质量权限、Rotation retention、事件样本门及切换参数。未赋值项不给正式消费者权限。

- `TECHNICAL_BAR_WINDOW_V1`：最近 N 根已验证实际 bar；只允许跨过本地确认停牌；不明缺口令相关字段 UNKNOWN。记录起止日期、calendar span、actual/suspended count 和窗口身份。新股不缩短窗口。
- `CROSS_SECTION_SESSION_WINDOW_V1`：全证券同一市场会话起止日期；端点不因停牌平移。`retN`端点停牌/缺失为 UNKNOWN；中间停牌留质量注记，未知缺口使结果 UNKNOWN。波动率需要 N 个相邻市场会话收益，不能跳过停牌拼接。RPS限于同日 PIT 可评估成员，少于两个为 UNKNOWN。
- `FORWARD_SESSION_WINDOW_V1`：T+N固定为 T0 后第 N 个市场会话，不因个股停牌延长。MARKED_ESTIMATE只能在独立估值、覆盖和 quote-age 门接受后产生；未知数据不 carry/填零/删成员/重权。path 每日单独判断质量。
- `FORWARD_MARKET_BENCHMARK_MISSING_POLICY_V1`：冻结 T0 权重并记录互斥原因；OBSERVED、MARKED_ESTIMATE、PARTIAL_UNVALUED权限分开。未知覆盖/quote-age候选值留给 00H，不在本阶段臆定。
- 20个连续 accepted shadow sessions 是 REV2 工程候选，按 capability 计算；缺日不计，历史 replay 不替代真实观察。

## 尚未接受

框架冻结不等于 V4 模块算法冻结。每个模块仍须独立 AST、参数实例、字段 producer schema、正反向向量和适用 replay 证据。Legacy extraction manifest schema 已定义，精确抽取未完成。合同复审中的 MDD、结算顺序、事件前驱修订、AS_RECORDED、模块 AST 等冲突保持独立开放，未由此阶段静默裁决。

**接受结果：`DEGRADED_PASS / FRAMEWORK_AND_WINDOW_SEMANTICS_FROZEN_ACCEPTANCE_GATES_OPEN`。** 后续模块可以据此起草合同；没有 V4 因子、画像或 Seed 因此获得实现验收。受影响能力保持 `SHADOW_ONLY`。

**下一阶段：`V4-00H / CAPABILITY_PERFORMANCE_ROLLBACK`。** 依据缺失、停牌、退市、真实缺口和公司行为证据冻结能力门/切换政策、完成恢复演练并签发 Phase 0 最终状态。该回执前不得开始 scanner。