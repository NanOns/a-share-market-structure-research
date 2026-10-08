# R2 修复执行合同

授权：用户明确要求执行两份 R2 审计文档修复要求。入口 HEAD 682ed2d779e33d5cef24188ff5fa727d41626f70，工作区干净。已读取两份 R2、R1 全卡、项目和 scripts AGENTS、FP13/14 既有结论。R2 successor 取消 Edge 专项；R1 收据不改。Phase 0 沿用已归档正式结果，不启动新 scanner。

合同：config/v4_r2_repair_contract_v1.json、config/v4_full_product_qa_contract_v2.json。每张卡独立记录 source、反例、验收和下一卡；综合源一致性/字段覆盖/日链/严格 PIT 独立审计，不凭测试关闭。

A1：修复首页展示去重、Focus typed read、股票 owner timeline；QA V2 独立 IAB 实测；逐域 owner/date/source 矩阵。A2：联合单指针 CAS 发布、验证/健康失败精确回滚；B：真实日 journal、PIT 冻结和字段/CSV；C：IAB 和发布签收。

状态：IN_PROGRESS。TDX 输入严格只读；无合成新交易日，无交易执行。下一关 A1 独立验收。
