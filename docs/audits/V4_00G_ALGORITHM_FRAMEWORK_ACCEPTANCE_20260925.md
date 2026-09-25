# V4-00G-ALGORITHM-FRAMEWORK-ACCEPTANCE-01

| Field | Record |
|---|---|
| audit_id | `V4-00G-ALGORITHM-FRAMEWORK-ACCEPTANCE-01` |
| status | `OPEN` |
| opened_at | `2026-09-25` |
| scope | 独立验收框架/AST可执行性、V4模块合同、producer登记、benchmark估值门、Legacy精确提取与golden vectors，以及影响消费者的跨章节合同冲突。 |
| stage_result | `DEGRADED_PASS / FRAMEWORK_AND_WINDOW_SEMANTICS_FROZEN_ACCEPTANCE_GATES_OPEN` |
| impact | 三类窗口与框架已冻结供合同设计。此阶段未接受任何V4因子、Profile、Seed、scanner、marked benchmark消费或能力切换。 |

## 开项证据

- 已按REV2 §10A0/§72–73/§49A.2/§78/§87A复核，REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`。
- `src/factors/registry.py` SHA-256 `c6486d571be26412ba841e1cf79cd14010079e79dfafc2e534afd1a90dd4d7b1`采用当前 Universe，不是V4 PIT合同。
- `config/history_windows.yaml` SHA-256 `8e4c728c6247857c46a0c99748ed68e370d6193dd49f8479b80db7ada4b0fec3`为旧窗口依赖，不是逐字段V4窗口合同。
- V3 schema和V3.3 registry不能替代V4 producer验收。本阶段未运行测试/scanner。

## 独立关闭条件

1. 每个V4模块/字段有版本化AST/schema/参数、producer/time/quality/window/舍入/输出身份、缺失语义和独立正反向向量；消费者不得自行推断规则。
2. 用单日/连续停牌、复牌、涨停低/无成交、非停牌缺口、新股、日历边界核验三类窗口，保存逐字段计数和确定性digest。
3. V4-00H用固定T0权重、停牌/退市/缺口/身份/复权样本冻结minimum_endpoint_weight_coverage、maximum_suspension_quote_age和quality→consumer权限；此前marked-relative不可正式消费。
4. Rotation retention及各能力Forward事件参数须注册并经独立验收，未赋值不给权限。
5. Legacy V3/V3.3精确提取源码hash、有序谓词、参数与golden vectors；禁止推断等价。
6. 受影响模块实现验收前解决或明确限域REV2跨合同问题，包括MDD、结算顺序、事件前驱/revision、AS_RECORDED和缺失AST。
7. V4-00H输出最终Phase 0 status、scope、证据与下一阶段；该回执前禁止scanner。

保持 `OPEN`，直至对应模块/能力证据由独立验收接受。框架schema冻结不代表生产准备就绪。