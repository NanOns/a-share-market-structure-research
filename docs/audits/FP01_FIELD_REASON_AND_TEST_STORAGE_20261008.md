# FP-01 跨域独立审计项｜2026-10-08

## AUD-FP01-FIELD-REASON-GAPS

状态 OPEN_AFFECTED_FIELD。范围：已有V4-13真实高级画像的 sector_context_state 字段，5224条质量UNKNOWN而直接reason为null，保留source_identity。证据：docs/evidence/fp01_20261008/QA_V4_13_PROFILE_ADVANCED.json 的 original_reason_gaps，以及已绑定原始profile gzip。该问题不等于字段可标KNOWN；本轮未改写原画像。

修复责任 FP02/03：按真实owner/字段路径在新版本适配层给出具体来源/能力缺口原因，保留原始值和source identity；涉及算法缺陷则独立修复生产器，不伪造来源。验收：全部受影响行原因可追溯、无UNKNOWN变KNOWN、无原文件修改、其他域不受此项全局阻塞。此项与FP01合同门、Amount A等其他跨域审计独立。

## AUD-FP01-TEST-TEMP-STORAGE

状态 OPEN_CLEANUP_POLICY_REJECTED / TEST_EXECUTION_PATH_REPAIRED。首次新测试误用了pytest默认C盘临时目录；产生的是工程fixture而非生产数据。后续命令及finalize_fp01.py均显式指定E:/codex_tmp/test_temp并设置TEMP/TMP，最终123项运行证据可复查。

曾尝试只清理本轮已命名测试目录、逐目标验证绝对路径边界，自动审批拒绝该清理动作，仅返回blocked by policy，未提供更具体原因；未重试删除，目录保留。保留位置 C:/Users/lps/AppData/Local/Temp/pytest-of-lps/pytest-1 下本轮 test_fp01_operational_release.py 的工程临时项。验收分开：测试路径修复已PASS；清理关闭需要可执行的批准清理或用户自行清理，不计入生产源/算法/TDX状态。该债务不伪称已清理。
