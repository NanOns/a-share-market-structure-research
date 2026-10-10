# Cohort 真实 T0 入场接口 R1

真实10/09 Head无 State cohort_signals Producer、独立 Validation Cohort Owner和 separate write grant；observed_count=null、production_write_authorized=false。八项实际 Head/原字节负例与接口回归见 C_ADMISSION_JUNIT.xml（81项，范围重叠不相加为独立样本）。使用原 Head 字节的伪 manifest 负例明确属于隔离反例，绝不表示正式新源。

1. 获准正式 State Producer 必须发布所有 eligible/ineligible 信号与明确资格及不合格原因；Focus Top-K 不可作样本源。
2. 原 Owner/manifest SHA、真实上海新 T0、first_available<=accepted_at<=实际 capture clock<=deadline；T0之前/之后首次捕获拒绝，冻结字段必须在 cutoff 可见。
3. freeze_source_candidate 同 publication/revision 原字节只冻一次；篡改/同revision覆盖拒绝。合法新revision仍需原出版和独立批准，不能借revision补旧事件。
4. extract_candidate 要求候选 Head 的 owners[T0].state 等于真实 Producer source_owner；ledger必须完整且去重，原资格/窗口/成员版本冻结。
5. prepare_capture 分别检查独立 Owner、完整 source receipt和 PREPARE_FIRST_CAPTURE write grant 的绑定/时效；READ_STATISTICS 不能代写，write grant不能代读。
6. DD候选能力失败只影响Cohort，不阻塞既有RAW/市场/股票派生；现有接口回归验证这一点。独立Owner准入、DD R2.2 CAS之后才可能正式入组。

旧2290事件永不回填。本轮没有新正式首获原件，也不模拟10/12宣称上线；工程包到此结束，下一阶段仅在真实新T0原件及独立准入存在时进入。
