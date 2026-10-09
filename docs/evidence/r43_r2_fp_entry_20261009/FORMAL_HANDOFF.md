# R43 R2 控制面修复及 FP 正式工程入场交接

本轮结果：SCOPED_CONTROL_REPAIR_AND_FP_INGRESS_PASS_WITH_REGISTERED_DEBT。原端口 28765 已运行 V2 适配器；10/08 运营 Head、9/30 PIT、成员 S、原用户授权和冻结 builder registry 全部原摘要不变。没有重抓551MB ZIP、重算四日Owner、修改TDX或覆盖旧PIT。

P0-A：两命名空间与日期/摘要/权限范围隔离；保留旧五域false。18定向回归通过；68隔离HTTP覆盖存在/缺失/回滚/重启及并发，37原端口生产HTTP含错误token409和越界日期400。真实RAW收盘价与板块成员数抽样和API相等。修复首页缺失列表.length异常，板块时间线/overlap缺失不再阻断真实成员；关注字段保留Episode资格、排除未来观测、记录实际观测日期，未退出的null不再冒充来源缺失。

P0-B：原Codex user-role消息找到，2026-10-09北京时间14:40:41.167，原会话与行号可回读。保留原事件，不制造独立签名。外部来源回读仍未完成，见独立AUTH-001。未来权限门提供 USER_PERMISSION_ORIGINAL_EVENT_GATE_V2，可验证新候选范围绑定与原始user事件；它本身返回permission_granted=false，不能替代发布门或独立身份审查。冻结V1只保留既有四日授权事实，后续successor须接入新门。

P0-C：正式官方日历与源证据摘要已核验，动态下一会话为10/09。当前 BLOCKED_EXACT_REASON / OPERATIONAL_SUCCESSOR_BUILDER_AND_SOURCE_QA_NOT_ADMITTED。未请求/未假设provider已完整发布。独立日增量、Source QA、身份/生命周期/GBBQ、successor/CAS/失败回滚完成前，继续10/08 last-good。既有run_v4_current_daily.py等旧路径面向严格PIT/其他authority，不能直接拿它覆盖运营Head；本轮新增只读preflight入口。

FP第一轮：最新Drive完整合同及R43交接已回读；六入口真实生产浏览器DOM/截图、代码搜索、个股详情、板块详情/成员已检查。首页1366/1920实际布局宽度核对；这是首页尺寸QA，不是全站Edge FP13。图表、Forward statistics/plans/FEP/settlement、市场子页、健康诊断、replay/compare缺失Owner及阶段已写矩阵和14张下一轮定向卡。没有伪造历史PIT或FP完整验收。

完整产品正式结果：NOT_GRANTED。Rotation全状态机与全域数值外审：NOT_GRANTED / VALIDATION_ONGOING。控制修复工程通过不关闭独立数值和权限审计。下一轮按原FP合同和每包next_tasks继续；不把10/08切换重标为待执行，也不跳过FP13进入FP14。

复跑：`E:/python/python.exe scripts/preflight_operational_next_session_v1.py`；`E:/python/python.exe scripts/qa_r43_control_namespaces_v2.py`；`E:/python/python.exe scripts/readback_r43_fp_live_v1.py`。回归使用PYTHONPATH=src，pytest的basetemp必须在E盘。适配器代码/静态资源独立SHA在config/v4_control_adapter_v2.json；数据与UI回滚独立。

归档与Git实际结果以 DELIVERY_RECEIPT.json 为准；没有成功回读的传输不填PASS。
