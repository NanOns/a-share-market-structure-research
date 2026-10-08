# 已接受 RAW 成交额与成交量显示适配

独立审计 AUD_R2_RAW_AMOUNT_VOLUME_PRESENTATION，依据外审 R2-07 以及字段 V4 矩阵。既有 RAW_DAILY 5213 行包含当日 amount/volume，图表序列已使用 CNY/SHARES，股票字段适配未暴露绝对值。仅补显示事实，不改 amount_ratio/量价因子或算法。

合同 R2_RAW_AMOUNT_VOLUME_PROJECTION_V1：证券/交易日严格匹配当前接受 RAW；单位由已接受股票 unit_contract 的 A 股 .day <IIIIIfII 合同确定为人民币元/股，RAW 原始数值不乘除、不复权。原 RAW 源仍保留 TDX_SOURCE_NATIVE 元数据；新投影明示版本合同、单位依据和源摘要。非有限/负成交额、非整数/负成交量失败为字段 UNKNOWN，不能填零。

入口 Phase 0 继承 DEGRADED_PASS，TDX 全路径只读，不运行扫描器。需 5213 × 2 全量逐值源 oracle、同日 series 逐值交叉核对、量价单位 plausibility 明确统计、负值/错日/单位合同不符反例、10 股票双桌面 IAB 值/来源核对、新 snapshot/UI 联合切换和回滚、日更后继准入 NOOP。

本项不能关闭 M10 Amount A 跨模块审计，也不能证明历史 PIT、换手率分母或未来可用性。阶段 IN_PROGRESS；下一关：版本化 RAW 显示适配和实际源 oracle。
