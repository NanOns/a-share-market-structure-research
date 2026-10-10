# R3 继续处理结果

上轮停止过早，本轮继续完成数据侧可执行闭环；保留此前收据，最新判定追加到任务清单。

- ATR、前高低、斜率及结构基础字段：6021项独立比较、0差异，包含325项窗口不足/端点缺失的未知值证明。
- 当前全量LOO：50214组合、401544项比较、零差异。当前Owner实际提供剔除自身中位数和相对状态，不提供全LOO截面排名/递归episode；后者独立域缺源，不能用含自身前态替代。
- 两个真实pulse：240项冻结篮子及原始前日/当日价格基线比较，零差异；第一日有限窗口重置是corrected研究边界，不冒称历史episode不存在。
- 原345条金额残差全部由“按元HALF_UP后转binary32”精确复现，不新增容差、不改原始金额。15,632条可比较记录均有精确表示路径。此为表示兼容性证明，不推定供应商内部实现、经济等价或正式Amount A权限。
- Cohort修复历史首次可用晚于T0冻结仍被后续读取接纳的漏洞；14项针对性测试通过，缺Owner样本数改为未知。
- 板块400条日期化readiness隔离候选落盘；正式合同明确规定WARM/CONFIRMED等SECTOR extraction/entry未接纳，当前adapter仅STOCK。不是简单把接口类型改为SECTOR即可合法完成，具体缺口见SECTOR_D2_EXACT_CONTRACT_GAPS.json。
- 按用户最新指令：26个北交所成员暂缓，不继续网络求证、不扩池；SZ.001235冻结通达信日线包/身份池无记录，baostock基本信息/指定日期日线成功返回空记录，精确标SOURCE_NOT_PRESENT，不推定未上市。

Cohort/FEP正式域缺AS_RECORDED enrollment/model/grant，当前可开发读取契约已修复；不能从corrected行情伪造历史首次可用、独立入组和授权预测。保护Head SHA不变；临时数据均在G盘。当前本地+baostock数据审计PASS_SCOPED，正式能力和外部发布门仍单列。

