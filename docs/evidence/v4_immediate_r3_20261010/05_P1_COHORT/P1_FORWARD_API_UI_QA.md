# P1-COHORT 最终只读 API/UI

真实只读 QA 服务 127.0.0.1:28767；使用冻结生产 Head，而非生成假 Owner。实际 DOM 摘录见 11_DEEPENING/ACTUAL_BROWSER_QA_EXCERPTS.json；数值与完整集合比对见 P1_PRODUCT_FP_REGRESSION_MATRIX.json。

逐字段15项定位到准确代码函数和 hash。只读统计可以读取独立 hash/date/contract 绑定的合法 validation_cohort，缺源时 observed_count/matured_count 为 null。当前 Head 无该 Owner，实际页面正确报告 NO_AUTHORIZED_COHORT_OWNER；期限结算独立报告 NO_AUTHORIZED_COHORT_SETTLEMENT_OWNER。Focus2805不替代入组。

FEP读域显式6元 grant key、4个能力 NOT_GRANTED；prediction/model_revision 为null，training/Focus写权限false，Priority V1不改变。页面为 MODEL_OR_PERMISSION_NOT_READY。135项合同/冻结/结算/路径/隔离/缺源/金额测试通过，测试不是合法历史入组、模型注册或正式授权。
