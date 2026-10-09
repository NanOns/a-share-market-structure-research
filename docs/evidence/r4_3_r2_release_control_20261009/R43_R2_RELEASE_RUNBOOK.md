# R43 R2 受控发布程序

## 本轮最终执行方式：用户直接授权

用户随后明确指令“不需要等待什么批准生产准入 ,我现在要求你  进行生产数据切换”，覆盖附件原先等待独立准入的要求。最终V3候选采用独立的USER_AUTHORIZED_SCOPED_OPERATIONAL_V1模式，实际用户请求被冻结在DIRECT_USER_CUTOVER_AUTHORIZATION.md，授权指针为data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json。CLI读取并校验该用户记录，不能把它当成独立审计签署；independent_external_acceptance=false，Rotation仍持续验证。该模式已真实执行CAS及HTTP/回滚/重启验证。以下外审流程作为另一个权限路径保留，本轮不依赖它等待上线。

当前Head已存在，后续dry-run或NOOP应使用当前Head实际SHA作为expected-head-sha，不能仍用ABSENT。执行记录所用初始ABSENT是第一次发布时的真实前驱状态。

该程序只读取独立签收，绝不创建签收文件或审查人。旧9/30严格PIT Head不写入。新运营Head仍为 `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json`。

本轮控制面与按域准入代码改变，必须以本轮V3候选的实际SHA重新审签。旧V2 `9c42365c...` 及旧外审阻塞意见不构成新候选通过。

独立审查者须通过人类核实的外部流程交付固定位置 `data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json`：status为EXTERNALLY_ACCEPTED_R43_OPERATIONAL、candidate_digest精确匹配、historical_PIT_permission=false、review_contract=R43_SCOPED_EXTERNAL_ADMISSION_V2；reviewer须含id/name/organization/independence_statement/independent_of_repair_executor=true；reviewed_at为含时区且不在未来的时间，review_tools、signature、review_evidence绑定独立审查实际文件，reviewed_files绑定实际批准Owner、S、registry的完整path/bytes/sha256。

签收的domain_disposition逐项列raw/core/profile/sector/relative_sector/market/rotation/focus/forward/events/diagnostic/lifecycle/special_phase，值为ACCEPTED、VALIDATION_ONGOING、NOT_VERIFIABLE或SOURCE_INCOMPLETE。最低运营域raw/core/profile/sector/relative_sector/market须逐域独立批准；其他域未批准时读源明确降级，不能阻断无依赖基础读取。Rotation完整批准还须绑定full_rotation_independent_oracle，未批准时其路由和板块Rotation字段保持VALIDATION_ONGOING，不把原计算字节删除或伪造。Focus/Forward等若依赖未审Rotation，审查者必须明确限制其可准入字段/范围；不能由执行代理据此默认放行。

这些JSON声明和签名字串属于可追溯流程记录，程序不声称具有密码学签名认证能力。独立审查者身份、证据及批准记录的真实性必须由交付流程确认，不能仅凭自行填入字符串获得授权；本任务代理不生成接受文件、审查身份或假签名。隔离模拟只准E盘，禁止G盘生产采用simulation_only记录。

启动已更新代码的实际服务，在正式调用前确认原/v4页面可用；部署使用 `workbench_service.v4_server.serve_v4`，不能把旧进程误当新版服务。程序使用已有cas()与同一排他锁，不重算数据。发布前取得当前运营Head精确SHA；不存在则填写ABSENT。以实际V3候选SHA替换下列变量值：

```powershell
E:/python/python.exe scripts/promote_r43_operational_v1.py --candidate docs/evidence/r4_3_r2_release_control_20261009/R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V3.json --candidate-sha ACTUAL_SHA --expected-head-sha ABSENT --receipt docs/evidence/r4_3_r2_release_control_20261009/R43_R2_RELEASE_DRY_RUN.json --dry-run
E:/python/python.exe scripts/promote_r43_operational_v1.py --candidate docs/evidence/r4_3_r2_release_control_20261009/R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V3.json --candidate-sha ACTUAL_SHA --expected-head-sha ABSENT --service-url http://127.0.0.1:28765 --receipt docs/evidence/r4_3_r2_release_control_20261009/R43_R2_LIVE_CUTOVER_HTTP_AND_ROLLBACK_RECEIPT.json --promote
```

dry-run核验候选完整源/代码registry、独立记录、expected predecessor，不改Head；缺签收返回非零。promote调用生产CAS后实际读取context/status、原9/30、原产品HTML与独立预览、四日期领域；HTTP检查失败立即按CAS精确前驱恢复，若有较新Head则拒绝覆盖。首次发布前驱不存在时恢复不存在状态。归档签收、实际回执和交接；进程重启、错误token及跨期访问另以真实HTTP验收。

领域限定生产读回通过仍不等于完整FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS。只有任务所需全部领域正式获准、真实生产/页面/回滚读回全部通过才启动FP01–FP14；本轮无签收，不得填写生产PASS。
