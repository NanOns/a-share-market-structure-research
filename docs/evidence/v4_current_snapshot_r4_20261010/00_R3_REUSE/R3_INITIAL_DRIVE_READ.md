# V4 Immediate R3 执行结果（范围化工程证据）

合同 V4-IMMEDIATE-R3-20261010；T0=2026-10-09。BASE_SHA=d35a82707e332de1231f5a6369460d06abe056df。本报告不代签外部验收，不启用新生产域。

| 工作包 | 当前结果 | 精确限制 |
|---|---|---|
| P0-ALG | 22452 独立比较、0 差异，PASS_SCOPED | ATR/结构输入、首次 pulse 和完整 LOO 排名递归尚需独立闭环，工程总体仍 OPEN |
| P0-OWNER | 349 原始成员→322 已映射+27 逐条待证；已有字段来源/API/DOM贯通 | 27 条 INSUFFICIENT_EVIDENCE；板块成熟度/健康度无正式日期 Owner，精确 SOURCE_INCOMPLETE/UNKNOWN |
| P0-AMOUNT | 三实际日期15,632条可比较，14,292条 binary32精度匹配、995条完全相同 | 345条待解释；Amount A独立审计 OPEN，不切换Native权限 |
| P1-COHORT | 新冻结读取契约、去重/改写拒绝/交易会话成熟规则；73项回归通过 | NO_ASOF_OWNER；FEP模型与权限 NOT_READY，无历史正式入组或真实预测 |
| P1-QA | 42路由、6种行情、六入口双尺寸DOM及隔离故障恢复 | 当前快照范围化PASS；独立FP13/FP14仍未授权 |
| PIT inventory | 五日期88条Owner清单 | corrected/latest reconstructed不等于历史AS_RECORDED，严格PIT缺口保留 |

生产Head、严格Head和10/09回执逐字节SHA保持不变。通达信只读；不生成10/12实际日更。各代码提交在Git中可追踪；归档复核小包含stdlib离线oracle和冻结输入，上传/回读收据单独记录精确RESULT_SHA。

R2旧oracle使用原SHA绑定，未冒充本轮重跑；R3脚本不导入被测业务计算模块。独立对比的零差异只支持列明字段。当前未完成项目和下一动作见08_REMAINING_LEDGER.json，外部方据此分别判定PASS_SCOPED/FAIL/NOT_VERIFIABLE。

