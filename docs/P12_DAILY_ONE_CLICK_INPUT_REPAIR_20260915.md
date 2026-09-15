# P12 日常一键生成输入修复验收

## 阶段合同

依据 `V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md` 的 P12-06 完整发布要求和“保留一键生成”决定，本阶段合同为 `P12_DAILY_ONE_CLICK_INPUT_REPAIR_V1`。实际经济交易日必须从解包后的日线内容推断；调用方明确提供预期交易日时仍须严格匹配。TDX 目录全程只读。

同一个上传日期允许官方包发生内容升级。package、extraction 和 metadata 必须分别按 package SHA 和 metadata snapshot ID 保存不可变版本。恢复及校验优先使用 source bundle 已记录的 staging 路径，禁止覆盖旧身份。

## 故障与修复

页面的“生成今日数据”调用 `/api/jobs` 并进入 `run_upgrade_m3.py`。首次排查时下载到的同日早期包最后交易日为 2026-09-14；16:56 后页面真实错误变为 `STAGED_PACKAGE_IDENTITY_CONFLICT`。官方已在相同 20260915 上传日期下更新 ZIP，旧逻辑却只允许日期目录存在一个文件，导致新的15日包被旧缓存拒绝。

修复将 package、extraction 和 metadata 改为内容身份版本化路径，同日不同包 SHA 可以并存，同包不同元数据快照也可以并存。source bundle 使用已记录 staging 路径。发布状态 API 同时补回顶层 `publication_id`，幂等恢复会清除瞬态 `COMPUTING` 状态。

## 验收结果

**FULL_PASS**。修复后以页面相同请求并明确预期日期 2026-09-15 提交任务 `daily-e2f8d22c7b9940f6b1be6cd1088b0b35`，最终返回 `SUCCESS/READY`。新包 SHA 为 `7ee4401d...f932`，内容校验为上海 4,855、深圳 4,486、北京 345，共 12,411 个日线文件、29,700,517 条记录，主要指数存在且普通 A 股非法记录为零。

任务形成15日发布 `m4-29c93e09369982707899ab863c869ea1`、M10 快照 `m10-mainline-preview-1e7e6c870ee93532` 和研究运行 `research-1f70afc1e97d4439bd841c43f4509715`。定向测试 33 passed，compileall 和 `git diff --check` 通过。P12 效果审计状态未因此改变。

## 下一步

恢复日常使用“生成今日数据”。后续同一日期官方再次替换 ZIP 时会形成新的内容版本，不再与旧缓存冲突；若页面填写的预期日期确实与包内最近交易日不同，系统仍会拒绝发布。
