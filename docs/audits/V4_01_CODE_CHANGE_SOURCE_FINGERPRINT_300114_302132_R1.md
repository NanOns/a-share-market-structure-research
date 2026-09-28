# V4-01 TDX + BaoStock 代码变更源级指纹诊断

- 诊断合同：V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_DIAGNOSTIC_V1 v1.0.0
- 接受结果：PASS；模式：PATTERN_D_UNRESOLVED_IDENTITY_RELATION
- 样本：SZ.300114 → SZ.302132；有效日：2025-02-17
- 执行时间：2026-09-28T16:09:45+00:00；输入 HEAD：e4a4ae0a1020d6c63fcac41bad8904a127f5f082
- JSON SHA-256：bf69125b1594b63b2f84c7daec570db4554bceda5d16083b3d9a7167ca0718f3
- 生产 identity 修改授权：false

## 阶段合同与门禁

- 只读读取配置 TDX root；BaoStock 请求经项目 BaoStockClient 和中心 request ledger 计数。
- 不修改 canonical identity、dated alias、Historical Universe、V4-02/V4-03 或 Accepted Head。
- PASS 只表示本次诊断证据采集完整，不表示 identity candidate、V4-01 owner gate 或下游阶段通过。
- TDX 写入计数：0；源文件前后哈希一致：True。
- 本阶段验收：PASS；下一步：RETAIN_R8_3_EVIDENCE_POLICY_AND_REASSESS_OFFICIAL_EVENT_COMPLETENESS_GATE。

## TDX 日线文件

| 代码 | 存在 | 首日 | 末日 | 记录 | 字节 | SHA-256 |
|---|---:|---|---|---:|---:|---|
| SZ.300114 | True | 2010-08-27 | 2025-02-14 | 3421 | 109472 | 08cf59e7d31aa0b0eae1f097e8cf782b1d6fb2124f8a3e784e19ccf830e29d54 |
| SZ.302132 | True | 2010-08-27 | 2026-09-24 | 3816 | 122112 | 53901f418c2b0ed1e55c11532f6298095a3ff48a8f9309ab0f8db89f41d371fb |

- 共同日期：3421；解码字段完全匹配：2976；解码不匹配：445。
- 原始 32-byte record 完全匹配：2976；最长 raw 前缀：1142；旧文件是否等于新文件完整前缀：False。
- 切换窗口：2025-02-10 ~ 2025-02-21；TDX 行存在矩阵：{'previous_session': {'SZ.300114': True, 'SZ.302132': True}, 'effective_date': {'SZ.300114': False, 'SZ.302132': True}}。

## 当前 TDX 证券主数据

- SZ.300114：TNF 存在 False，名称 None，行业 assignment []。板块分类字段未由 TNF/tdxhy.cfg 直接提供。
- SZ.302132：TNF 存在 True，名称 中航成飞，行业 assignment [{'industry_code': 'T0701', 'line_number': 2949}]。板块分类字段未由 TNF/tdxhy.cfg 直接提供。

## BaoStock

- SDK：baostock 0.9.3；请求数增量：10。
- roster 前一交易日：{'sz.300114': True, 'sz.302132': True}；有效日：{'sz.300114': True, 'sz.302132': True}。
- SZ.300114 长历史：首行 2010-08-27，末行 2025-02-17，行数 3511。
- SZ.302132 长历史：首行 2010-08-27，末行 2025-02-21，行数 3514；有效日前可见 True。
- old/new 共有日期 3510；精确业务字段匹配 3429；不匹配 81；差异类别 {'ACTUAL_BAR_VALUE_DIFF': 1, 'SUSPENDED_BLANK_VS_ZERO_ONLY': 79, 'TRADING_STATUS_DIFF': 1}。
- provider 返回 code 行为：{'sz.300114': {'provider_returned_codes': ['sz.300114'], 'matches_query_code_only': True}, 'sz.302132': {'provider_returned_codes': ['sz.302132'], 'matches_query_code_only': True}}。

原始短窗口、长历史与目标股票的基本资料行保存在 JSON 中，包含 query code 与 provider 返回 code。成交量/额按项目字段映射标为股/CNY 元；TDX 按项目 .day 解码器读取浮点 amount、uint32 volume 与价格比例。没有执行复权、成交量缩放或金额换算。

## 切换与交叉源结果

| 信号 | 结果 |
|---|---|
| F1 旧文件结束于前一交易日 | True |
| F2 新文件含变更日前历史 | True |
| F3 旧文件等于新文件 raw 前缀 | False |
| F4 BaoStock roster 原子切换 | False |
| F5 Provider metadata | ipoDate 相同：True；名称不同：True；旧 outDate：2025-02-17；新 status：1 |
| F6 无双代码同时实际交易 | False；发现日期：['2025-02-14'] |
| F7 收盘/前收盘衔接 | 旧 close：72.1800；新 preclose：72.1800；新 open：73.9800 |

在 2025-02-14，BaoStock roster 同时列出两个代码，且两次 history query 都返回 tradestatus=1 的完全相同业务行情行。这触发双代码实际交易 fail-closed 条件。

- 未决项：['OVERLAPPING_DUAL_ACTUAL_TRADING', 'BAOSTOCK_OLD_NEW_OVERLAP_BUSINESS_FIELD_MISMATCH']；长历史差异分类：{'ACTUAL_BAR_VALUE_DIFF': 1, 'SUSPENDED_BLANK_VS_ZERO_ONLY': 79, 'TRADING_STATUS_DIFF': 1}。
- 结论：Contradictory or incomplete source evidence remains unresolved; fail closed.
- candidate 信号强度：BLOCKED_FAIL_CLOSED；单个样本不足以定义新的 SAME_ENTITY confirmation contract。

## 最终问题答复

1. TDX 同时存在：SZ.300114=True，SZ.302132=True。
2. SZ.300114.day 最后日期 2025-02-14。
3. SZ.302132.day 首日期 2010-08-27。
4. 包含有效日前历史：True。
5. 两文件共同日期 3421。
6. 共同日期 raw 32-byte 完全相同 2976。
7. 旧文件是否等于新文件完整前缀：False；最长前缀 1142 条。
8. BaoStock 2025-02-14 roster：{'sz.300114': True, 'sz.302132': True}。
9. BaoStock 2025-02-17 roster：{'sz.300114': True, 'sz.302132': True}。
10. BaoStock 新代码查询有效日前历史：True；first row 2010-08-27。
11. BaoStock 旧代码行数 3511，边界 2010-08-27 ~ 2025-02-17。
12. BaoStock old/new overlap 3510 dates, exact 3429, mismatch 81。
13. Provider returned code behavior {'sz.300114': {'provider_returned_codes': ['sz.300114'], 'matches_query_code_only': True}, 'sz.302132': {'provider_returned_codes': ['sz.302132'], 'matches_query_code_only': True}}。
14. 综合模式 PATTERN_D_UNRESOLVED_IDENTITY_RELATION；强度 BLOCKED_FAIL_CLOSED。
15. 仅作为 candidate evidence；不足以建议新的 confirmation contract。SAME_ENTITY 仍须独立正式证据。
16. 发现 BaoStock 2025-02-14 roster 双代码同时存在，且两查询均有完全相同的实际交易 bar；另有 81 个长历史差异日期，其中停牌空值/零值表示差异 79 日、实际字段差异 1 日、交易状态差异 1 日。

## 可复核证据

- BaoStock request ledger SHA-256：3a8137d9f5d0b8c056d71bfd5801173d8fa1435c7443a190992d36d458df5184
- JSON artifact SHA-256：bf69125b1594b63b2f84c7daec570db4554bceda5d16083b3d9a7167ca0718f3
- 原始 BaoStock 查询行随 JSON 冻结；不含账户凭据。
