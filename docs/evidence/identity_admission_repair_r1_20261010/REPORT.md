# Identity / State / D2 精确修复交付

基线 d7b19feabc8e17ca4948bfdef38047f10fd6f97c，Phase0 FULL_PASS。P0 门分类及同日 Identity 候选、State fail-closed resolver、D2 三值保留与显式到期分类已落实源码和定点验证。受保护运营/严格 Head 原始 SHA 完全不变；TDX 只读；无 28765 重启、真实准入变更或 Writer Grant。

|分域|结论|
|---|---|
|OPERATIONS_READ_SCOPED|既有合法研究只读范围保留；本轮源码未加载生产|
|IDENTITY_AUTHORITY_ENGINEERING|工程验证通过；正式身份准入仍关闭|
|STATE_REVIEW_TRUST_BOUNDARY|默认 resolver 与普通 caller 隔离；真实 accepted review service 尚无|
|D2_EPISODE_ENGINEERING|三值字段不变，PENDING/UNKNOWN/COMPLETE 分类工程通过|
|FP13_BROWSER_SCOPE|BLOCKED_BROWSER_ENV；FP13_RESEARCH_READ_SCOPE_PENDING_EXTERNAL_SIGNOFF|
|REAL_FIRST_CAPTURE_PENDING|真实下一交易日采集尚未发生|
|FORMAL_COHORT_NOT_GRANTED|保持关闭|
|FEP_HOLD|复用旧 E_HOLD；六预测字段仍 SOURCE_INCOMPLETE/null，无重复预测测试|
|FP14_FULL_NOT_GRANTED|保持关闭|

唯一 T0 结论 WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER，详见 10/12 手册。独立 State 服务成功通道和实际浏览器验收明确尚未完成；本轮只验收工程及失败关闭，不制造正式通过。

验证：B 定点回归 63 passed；A/C 定点回归见 A_C_REPAIR_JUNIT.xml；实际差异 Oracle、原件与前端接口样本同目录。先前 C 合成日历样本路径冲突已修正为独立捕获，最终 JUnit 为修复后的重验结果。综合审计项 M10 Amount A 等沿用独立跟踪，不用本轮工程门抵销。

复现：PowerShell 设置 TMP/TEMP/TMPDIR 到 G:/codex_tmp 及 PYTHONDONTWRITEBYTECODE=1；python -B -m pytest tests/test_identity_gate_reason_r2.py tests/test_dated_identity_candidate_v1.py tests/test_state_trusted_review_candidate_v1.py tests/test_followup_semantics_r2.py --basetemp=G:/codex_tmp/test_temp/repair_recheck -o cache_dir=G:/codex_tmp/pytest_cache_repair。Git/Drive exact-byte 回读收据在交付收尾补充。
