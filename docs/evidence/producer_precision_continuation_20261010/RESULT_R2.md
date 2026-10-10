# Producer 定点修复：可继续推进项 R2

入口 BASE_SHA：60ef5a39e565740fae5062c7eb2d76325937d84c。用户明确继续推进任务卡中仍可实施的修复。适用合同和已查文档见 STAGE_CONTRACT.json。本文件追加上一轮结果，原诊断、Head 和历史验收保持。

本轮结论：工程范围定点修复与验证完成，申请外部复验；全局 EXTERNAL_ACCEPTANCE_BLOCKED。未来真实 T0、独立 Source Owner/Writer grant 和生产部署仍为独立门禁，不自签正式 PASS。

## 已推进的缺口

1. P1-02：原 capture 位于 readiness 后，旧身份池不等于新日池时可能先阻断。现在 source freeze 成形即执行非阻断捕获，derive 也在 gate 前确保已有收据。gate 仍决定是否进入 Owner；新未知身份不能绕过身份准入。测试证明 gate 失败仍有真实代码生成的原字节收据。实际 executor → ready adapter build/seal → strict review 调用层跑通；数值 replay/prepare 输入采用 synthetic kernel fixture，不冒充全量实际 Owner 数值计算。双 Head 验加入、移除/更名、停牌、成员变更、重试与中断。

2. P1-02 时钟：BaoStock 的 top-level、transport 和 transport.daily 请求字段均可提取，不用当前时钟替代原请求。原请求/接收、首次 captured_at 和源 SHA 对账后保持原收据。

3. P1-03：权威全市场 State 首获接口接入日更侧车。只接受 candidate 明确绑定的 state/membership/model 原件，不从研究 prewatch 推造。未提供则 SOURCE_INCOMPLETE；malformed 输入通过 optional_step 降级，不挡 DD。真实接口生成完整集合、冻结、提取，prepare_capture 的 grant 分离继续验证；未接纳源不发布正式 cohort。原 20896 场景和正式分母保持原状态。

4. P1-04 HTTP：使用真实 CoreProductBFFR1、真实研究 app.js/api.js/components.js 与隔离两日 Source fixture。D1 token 查询 D0 候选保留原来源和结果；股票 D0/D1 数值刻意不同以验无新日覆盖。HTTP 验旧 token 409、未接受 Head、篡改归档、错 session 和未来日期拒绝。

5. P1-04 浏览器：28767 隔离服务中，模拟 D0→D1 Head 切换，D0 板块和 Cohort 可见；股票第二页及跨模块导航保留 T0；切 D1 显示缺源，再切回 D0 恢复候选。1366/1920 配置、截图、DOM 和实际请求日志归档。数据明确标为 synthetic；不声称 10/12 实采或 28765 已加载新代码。夹具中本范围之外的因子历史/成员详情缺字段会局部降级，不计为全产品通过。

6. P1-04 追加独立审计项 AUD-PROD-COMPUTATION-BYTE-ARCHIVE-20261010：源码升级会使旧候选引用的源码路径 hash 不符。原 Git/冻结字节按 SHA 追加归档；读方仅对 src/config 计算依赖允许精确摘要归档回放。Owners、数据源和接受 Head 链不使用替代。新 State/V3/strict 候选自动保存计算依赖；缺归档、篡改和数据源替代均拒绝。真实 10/09 原 V2 和全市场研究候选回读 AVAILABLE/RESEARCH_CANDIDATE_FROZEN。此项仅计算字节存续范围工程验证，正式 A05 源口径独立审计仍 OPEN。

7. P0 补强：缺 source_security_key 明确 UNKNOWN，不当 FALSE。旧 A05、phase2、AST、79 TRUE 第一次诊断和受保护 Head 保持原件。

## 验证与部署边界

FINAL_JUNIT.xml 实际 147 个非重复节点通过，含新增调用层/API/归档测试及相关 DD/Cohort/资格回归；不与旧 114/138 累加，不当作统计样本。

PROTECTED_HEAD_AND_STABLE_HTTP.json 核验两个 Head、旧正式源/AST 不变；28765 HTTP 200、token 不变，未重启。28767 测试进程及临时浏览器清理，TDX 始终只读，新临时文件均在 G:。

P2-05 范围化发布方案：对象仅此次研究候选读路由、缺源提示及日更非阻断侧车；Head、权限与主流程不变。需另获生产重启授权；保留当前稳定版本作代码回滚。切换后验 context token、六入口、旧 T0 候选和 DD 状态；失败回退稳定代码并核对 Head。此次只交方案和隔离验收，不实施切换。

## 目前剩余门禁

- 下一实际交易日原件采集与 QA：日期尚未发生，不签当日首获 PASS。
- 权威完整 State 真实源、独立 Source Owner/Writer grant：正式 Cohort BLOCKED。
- legacy missing_state/资格源独立复核与正式 D2 准入：BLOCKED，不以 79 TRUE 倒推授权。
- FEP、FP14 和完整产品发布：独立门禁仍 BLOCKED。
- 独立外部复验及生产可见性操作：提交复验，不自签结论、不擅自重启。

## 小包重跑

在仓库运行 python -B -m pytest -q -p no:cacheprovider --basetemp G:/codex_tmp/test_temp/precision_reexecute tests/test_producer_precision_continuation.py tests/test_precision_historical_http.py。完整节点见 TEST_NODES.json。

浏览器重放：TMP/TEMP/TMPDIR=G:/codex_tmp，PYTHONPATH 指向仓库 src。用新的临时 root 启动 python -B tests/precision_http_harness.py --root G:/codex_tmp/precision_browser_reexecute --port 28767。仅 loopback，拒绝 28765/28766 和非 G 临时 root。打开 D0 板块详情、点击隔离 D1 按钮，验 D0、分页与导航。结束仅停止该测试进程。
