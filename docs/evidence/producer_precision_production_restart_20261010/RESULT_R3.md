# R2 精修：生产重启与范围化验证（2026-10-10）

用户明确授权“重启服务 然后再次验证 可以推进项”。结论：**PRODUCTION_RESEARCH_READ_PASS_SCOPED**。本阶段将此前修复加载到实际 127.0.0.1:28765 服务并验证读取，未变更数据接受指针或正式权限。

## 实际生产验收

原服务 PID 34900，核对命令后停止该进程，按既有 scripts/start_product_attested_r4.py 方式重启为 PID 42552；监听127.0.0.1:28765。启动提交 0c9305129cfe90148008d898162f0f40959d1af5，STARTUP_ATTESTATION.json 保存源码路径、摘要及函数字节码摘要。启动stderr为空。

HTTP共12项定点读回：context、operations、10/09与10/08的板块候选/Cohort候选/股票、未获准10/12的三个路由、旧令牌。10/09板块 AVAILABLE；Cohort RESEARCH_CANDIDATE_FROZEN（5224证券、20896场景、300研究条件满足）；正式observed_count/matured_count为null，formal_consumer_enabled=false。10/08候选明确NOT_CAPTURED/HISTORICAL_CANDIDATE_SOURCE_NOT_CAPTURED，股票仍可读。10/12返回400 TARGET_DATE_NOT_GRANTED，旧令牌返回409 CONTEXT_TOKEN_MISMATCH。

实际浏览器1366×900、1920×1080验证：关注页显示候选及准入边界；切换10/08显示中文历史缺源说明；关注页跳转板块详情保留10/08；返回10/09显示原冻结候选；股票10/08第二页保留日期，URL offset=30，浏览器error日志为空。DOM及截图在本目录。两个合法不同Head的正反例引用上一阶段隔离真实BFF验证；今天没有新接受D1及历史候选，不冒称完成未来现场跨日验收。

日更AUTO_ON保留，active_job=null，missing_sessions=[]，latest_closed_session=2026-10-09，既定下次触发2026-10-12T18:35:00+08:00。没有人为触发未来采集，没有修改TDX输入。

两个Head前后摘要完全相同：运营55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e；严格38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40。

## 任务推进与剩余边界

P2-05从隔离预览推进为用户授权后的实际生产研究读取验证；P1-04实际生产读取及页面历史日期保持已验证。P1-02/P1-03工程代码及上阶段147个非重复测试已完成。本阶段没有新增源码或复算候选，不虚增测试数。旧V2诊断保留，V3严格资格审计仍为独立追加证据，未替换旧候选或正式算法。

剩余：下一真实合法交易日原始捕获、同日全集对账及现场QA；权威全市场State来源和独立Source Owner/Writer grant；资格口径外部复验。正式Sector D2/Cohort/FEP/FP14准入及独立外审仍未获得。重启与Git/Drive归档不构成独立签收。

HTTP_ACCEPTANCE.json记录路由、状态及响应SHA，配套响应原件；FINAL_ACCEPTANCE.json记录断言与最终日更状态；STARTUP_ATTESTATION.json记录运行加载证据。上阶段147测试见 ../producer_precision_continuation_20261010/FINAL_JUNIT.xml。
