# 独立审计项 AUD-LEGACY-IDENTIFIER-REGEX-20261010

Scope：冻结phase2.prepare、legacy_valid_member_a05_v1.exact_value、a05 exact AST及所有valid-member消费者，独立于W1/W2阶段验收。

Evidence：两份源码使用原始正则r'(SH|SZ|BJ)\\.\\d{6}'，其模式包含字面反斜杠，不能匹配普通SH.688349。原10/09 Core source_security_key均标准交易所格式；研究重放400板块资格均FALSE。没有用最新成员/ret1代替valid_member，也未修冻结源。

Acceptance：OPEN_INDEPENDENT_SOURCE_SEMANTICS_REVIEW_REQUIRED。需要独立复核源实际语义、原A05黄金样本与冻结AST/批准范围，决定是否批准新的版本化correctness合同及全消费者迁移。修正必须与原旧合同隔离，不能自签A05新日期授权或改旧已接纳Head。

Next：独立审查此项；W2正向资格业务门未完成。候选FALSE不作为板块投资判断。
