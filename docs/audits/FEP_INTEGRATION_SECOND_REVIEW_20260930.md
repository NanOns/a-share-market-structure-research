# FEP R1 二轮集成审计

日期：2026-09-30。输入：`artifacts/fep_20260930/FEP_R1_DRAFT.md`、`docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql`。只读设计审计；未执行DDL、数据库或功能测试。

结论：DESIGN_CHANGES_REQUIRED，修复下列两个表达缺口后可复核设计通过；不把未实现的跨表接受服务当实现缺陷。首轮架构依赖、旁路阶段、时序、产品边界、权限与旧实现复用边界已在R1得到明确修复。

## R2-I01：模型缺失时无法登记slot失败（P1）

DDL第152–160行prediction_slots.model_set_id为NOT NULL外键；第193–198行slot_receipts又要求已存在的slot。没有任何模型的日期无法合法建slot，因而无法记录FAILED/MISSED。R1第47行“失败/漏跑也写slot receipt”、第55行完整分母以及第200行模型缺失测试无法落实。

建议：预期slot与模型选择分离。slot不依赖成功模型；独立append-only slot_selection绑定所选model_set或明确NONE/MISSING状态。预测仅允许成功selection的复合FK。不要为无模型情况造一个虚假的accepted模型。验收反例：模型表空时仍可登记全量expected slots、missed receipts且产生零预测，分母保持完整。

## R2-I02：没有标签的排除样本不能进入dataset分母账本（P1）

DDL第101–117行dataset_rows同时接受EXCLUDED，但label_revision NOT NULL且外键指向label_revisions。行政未成熟、没有权威binding的数据缺口无法创建合法row。虽然observations保留所有单位，仍未冻结“这一dataset本来包含哪些observation/target及为何排除”的精确集合。

建议新增dataset_expected_targets或eligibility_ledger，键为(dataset_id,observation_id,target_id)，记录预期、状态、原因、as-of cutoff与可空selected label revision；只有正式training rows要求标签FK与positive weight。冻结expected ledger摘要进dataset manifest。不能用最新observations查询临时代替历史分母。

## 主合同并入检查

R1已经声明E1–E5旁路及未部署DDL/参数门，可作为设计修订；尚未看到最终§90+及定点修改后的主文，不能提前宣称跨章一致性通过。最终必须同步首轮报告所列§2/3/4.9/45/46/50/51/52B/60/77B/78/80/81/83/84–87A，而不只是追加一章。REV2历史证据不改hash，REV3注明设计授权不修改已有accepted heads。

剩余未部署触发器、服务验证和参数冻结可保留E1/E5明确门，不要求设计审计阶段执行或伪称已实现。
## 修复后最终设计复核

再次核对：更新后的设计DDL、`artifacts/fep_20260930/FINAL_REV3_FEP_DRAFT.md`及`REV2_to_REV3_FEP.diff`。

结论：DESIGN_INTEGRATION_PASS_WITH_IMPLEMENTATION_GATES。

- R2-I01已设计关闭：planned slot不再要求model_set；slot_model_bindings仅在成功选择时冻结模型集合；预测复合FK绑定该选择。无模型仍能登记slot/receipt。初始selection_status保持不可变，后续binding/receipt是权威的解释已在DDL末尾明确。
- R2-I02已设计关闭：dataset_eligibility_ledger允许缺失label revision；dataset_rows仅包含FIT/TUNE/CALIBRATION/OUTER_TEST。末尾明确接受服务须核对ELIGIBLE、selected revision和dataset scope，相关服务尚待E1实现。
- 跨章修订已核查：§2/3、§4.9、§45/46、§50/51/52A/52B、§60、API、§72、§77B/78、§80/81/83、§84–87A与新增§90有明确连接；E1–E5旁路、保留PRIORITY_V1、M14边界、独立rollback、完整分母、权限未授予相互一致。
- 原REV2与accepted heads保持历史证据；REV3声明后续已接受阶段修订优先，未把旧基线误当当前已实现状况。

本次通过只表示上述集成设计阻断已解决，可并入设计主文。未执行SQL、真实FK反例、数据库权限、接受服务、模型训练、实时Shadow或统计效力验证；这些明列门仍OPEN，不能据此启动生产预测或Priority排序。没有追加新的集成设计阻断。