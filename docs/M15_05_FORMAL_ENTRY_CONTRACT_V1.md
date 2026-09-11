# M15-05 正式入口合同 v1

版本：`M15_FORMAL_ENTRY_V1_0`  
依据：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 5、16.4、22.10 章；M6 角色与结论采用 `docs/M6_INTERNAL_ACCEPTANCE_OVERRIDE_V1.md`；执行前已复读 M15-04 数据/恢复审计回执、M15-03 性能回执和 M6 内部验收回执。  
目标：在全部前置门通过后，将已验收工作台按配置切换为正式入口，同时保留旧入口与可验证回退。

## 切换前置条件

1. M6 用户内部验收必须为 `INTERNAL_USER_ACCEPTED`，且 M6 回执明确 `production_entry_switch_allowed=true`。
2. M15-03 性能预算、浏览器热 30 次和 M15-04 历史共享 slice 锚点项必须完成独立验收；当前 M15-03/M15-04 均为 `DEGRADED_PASS` 且 `release_ready=false`。
3. 正式切换必须使用新的配置修订和期望 head 身份，不能修改旧发布、覆盖旧 manifest 或把 `/view` 历史入口变成不可回退状态。
4. 切换前须有 activation receipt、旧入口可用证据、服务重启/失败回退证据；激活失败不得登记成功版本或半完成 head。

## 当前门禁结论

本阶段只做门禁核验，不写配置、不调用激活接口、不修改数据库。当前 `OPEN_UNIFIED_WORKBENCH.cmd` 仍可启动 `/v2` 预览服务，旧 `OPEN_RESEARCH_WORKBENCH.cmd`、静态旧入口和 `/view` 路由继续保留；这不等于正式入口已切换。当前工作台指针仍为 `current-workbench-v1.0` 的 2026-09-10 旧版工作台，不将它改写为 v2 正式身份。

因为 M6 最终门和 M15 性能/审计门未满足，本阶段结果为 `BLOCKED`，`release_ready=false`。这是安全停机门，不是数据丢失或核心计算错误；不得以已有预览入口、历史外部复审或定向测试替代当前版本的正式切换许可。

## 解阻条件与下一步

- 取得并绑定针对当前 M7–M15 版本和当前发布身份的 M6 用户内部验收结论。
- 关闭 M15-03 性能预算、浏览器热 30 次和 M15-04 历史锚点三个独立审计项，重新生成对应回执。
- 由人工再次启动 M15-05，执行配置修订 → 预检查 → 原子激活 → 健康检查 → 失败回退演练；成功前保持旧入口。

## 2026-09-11 阶段闭环补充

M6 已按用户授权采用内部验收，M15-03 浏览器冷/热证据和 M15-04 旧共享 slice 兼容合同均已通过。正式入口采用原子写入的 `runtime/workbench_entry.json`：`OPEN_UNIFIED_WORKBENCH.cmd -> /v2` 为主入口，`OPEN_RESEARCH_WORKBENCH.cmd -> /view` 和 `CURRENT_WORKBENCH.json` 保留为旧版回退；不写生产数据库、不改旧发布。详见 `reports/upgrade_m15/m15_05_formal_entry_closure_receipt_20260911.json`。
