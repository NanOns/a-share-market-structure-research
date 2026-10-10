# Producer 续推 R2：候选工程完成，正式准入待独立验收

本轮依据用户 2026-10-10“继续推进可以推进的模块”执行，以及同日 Producer Bootstrap / Credential Deadlock 两份任务文档。文档用于约束实现和验收边界；用户授权范围是工程续推，不能据此生成独立审计签字。阶段合同 `PRODUCER_CONTINUATION_R2_CANDIDATE_ONLY`，前置 Phase 0 既有 FULL_PASS。

## 完成与现场证据

- 新来源捕获保留 BaoStock 日线/因子两次真实请求与接收时钟、通达信官方有效包请求/接收时钟。挑战页面回退的旧包不会继承新请求时钟，旧文件缺失时间不补写。捕获收据完成时间晚于所有本地读取接收时间。
- 全市场 State 冻结实际生成时间，原样冻结 target_values、场景判定、排除原因及输入绑定；未来窗口、重复对象、错误日期拒绝。即使真实当前日抓到输入，未独立接纳的严格窗口/成员仍保留缺口与 `PIT_ELIGIBLE=false`。
- 独立研究板块 V2 从真实 Lifecycle/Core/Native/State 提取候选；q20/dq5_3 接入原有 strength 的正常宇宙 RET 减同日中位数、sector cycle 同类型平均并列排名及三会话稳定窗口。没有用 Native 百分位替代原算法排名。
- 10/09 真实历史回放：5,224 只证券、20,896 个场景、300 个研究条件满足信号；400 个板块的 CONFIRMED 研究诊断 TRUE 79 / FALSE 321，WARM FALSE 364 / UNKNOWN 36。仅是独立证券代码诊断修订后的研究结果，正式 A05、D2 和 Cohort 均未准入。原冻结算法代码、AST 和参数未改变。
- 板块详情及 Focus 下的 Cohort 来源准备区已接入版本化候选接口。对 Head、Owner、成员、模型和排名收据核对 SHA；坏候选只降级本区，正式统计 null 保留。
- 138 项定点回归通过；真实 API 校验候选可读、空/旧 token 409、预览变更请求 405。板块编码重复转义问题已通过实际页面发现并修复。
- 稳定 28765 未重启，股票/板块/Focus/市场读回 200。28766 是本轮最新代码的临时只读预览，无 AUTO worker、无 CAS、无安装系统服务。磁盘接线完成不等于旧 28765 进程已经加载这些 Python 新入口。
- 两个受保护 Head 原字节 SHA 保持不变，见 `PROTECTED_HEAD_READBACK.json`。

## 独立审计项：证券代码诊断修订

延续 R1 的 `AUDIT_LEGACY_IDENTIFIER_REGEX` 独立审计项。旧冻结正则对正常 `SH.688349` 等代码不匹配；V2 使用独立合同 `LEGACY_VALID_MEMBER_DIAGNOSTIC_CORRECTION_V2`，检查真实 Lifecycle 日期、映射及 traded/suspended 状态，供研究计算。外审须独立比较旧表达式和新诊断、复核 missing-state 与资格分母、确认 A05 可授权日期/对象，不能以当前候选 79 个 TRUE 反向批准旧算法或历史状态。本项状态 `INDEPENDENT_A05_REVIEW_REQUIRED`，与页面工程验收分开。

## 尚未完成的正式门及下一阶段

`PER_CAPABILITY_ADMISSION_REQUESTS.json` 是申请材料而非许可。来源捕获不等待 Writer grant；正式 Writer/Owner/Head 发布仍只走原独立入口。

1. 新真实交易日发生后，用当日实际时钟采集原字节、当日成员、完整 State 及截断窗口，独立审源。10/09 本轮资料是历史重建，不能转为当日首获；10/12 尚未发生，没有报告其真实首获 PASS。
2. 板块正式资格须独立接纳精确 valid-member 输入及算法版本。已有研究诊断可审阅；Episode 只能从新的真实 Genesis 产生，T+1/3/5 只按实际日历与 settlement 逐步成熟。
3. Cohort 须先独立接纳完整 State 来源及模型/窗口/成员，再审独立 Writer grant、事件/基准身份、正式 Owner admission 和 Head CAS。不能把当前 300 个研究信号当成正式入组或胜率样本。
4. 候选页面运行升级可作为单独范围化部署验收；本轮未重启稳定生产进程。FP13 既有读域保留，FP14_FULL_RELEASE 和 FEP 正式生产均未授予。

本轮工程裁决 `PASS_SCOPED_ENGINEERING_CANDIDATE`；来源严格准入 `PENDING_NEW_REAL_T0_AND_INDEPENDENT_REVIEW`，FP14 全量外审 `NOT_GRANTED`。Git/Drive 交付只证明代码与证据可取回，不代表独立来源或发布验收。
