# DM01 R4R2 完成报告

本轮结论：PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。

正式路径采用 V4_16_GO_FORWARD_INPUT_AUTHORITY_V1_1、v4 runtime dependencies 和 v2 packet preflight 合同，精确绑定各自历史前驱。V1 仅保留历史/工程兼容。桥接字段参与 daily-input 与 packet digest，生产、独立 preflight 和 runtime 读取同一精确合同。

一个确定性桥接 producer 将精确父/当前 V2 子头/candidate/source/九组件/观察 receipt 串入 daily input 和 packet。daily input 的日历及原始/复权输入必须来自桥接子头。独立只读 oracle 不写文件、不授予权限、不导入 runtime 执行路径、不搜索 latest/glob/mtime。新 runtime 复用旧输入构造函数字节码和旧业务方法，以精确历史归档提供不可变算法视图；9月30日历史 Data Head 原字节被归档，当前指针未移动。

修复阶段保护核查保持当前 Data=2026-09-30。未来 packet 的保护核查按精确桥接子头验证 target，避免把未来合法子头误挡在历史日期断言上；仍要求 Stage 不变、授权关闭、真实计数为0、无真实 DB。

受测源码：`46bbc77164723ca272e0ae7ca896bd0b66f2fd80`；标签：`codex/dm01-r4r2-r25-bridge-tested-source-20261005`。两处完整扩展范围均为2181项：LOCAL：2135通过、43失败、3跳过；CLEAN：2135通过、43失败、3跳过。R4 25项、R4R1 15项、R4R2 18项全部通过，16个规定向量全覆盖。原26项债务加扩展入口18项共44项；R25 inventory WAIT 的一项已本地修复，43项仍独立开放。HTTP/DuckDB 文件占用另属 R4R1 外部审计已接受的非阻塞波动，首轮本地再次出现，日志保留；最终两轮是否出现分别记录。introduced_failures=[] 表示未超出已登记债务及波动，不表示完整回归全绿，pytest exit_code=1 原样保留。

所有正向证据限工程或 REAL 形状合成对象。完整 packet 与输入 constructor 的工程路径检查精确结构和 digest；外部/native 接受及 immutable view 使用明确测试接缝，不能算真实市场接受。无真实授权、无真实启动。工程 ZIP 有生成时间，因此工程证据使用独立显式命名空间；桥接 producer 对固定精确输入保持确定性。

实际 Stage/Data Head 保持原字节，Data=2026-09-30，V4_16_ACCEPTED_HEAD 不存在。日历覆盖至2026-12-31，10月8日 WAIT_MARKET_CLOSE，source_requests=0。REAL_TARGET_SESSION_PACKAGE=NOT_CREATED，R25=WAIT_ACCEPTED_DAILY_INPUT，REAL_SHADOW_EXECUTION=NOT_STARTED，REAL_SHADOW_OBSERVATIONS=0，PIT_OBSERVED_REAL_SAMPLES=0，Production/Shadow/Focus=false。TDX 未写入，无关文件保留。

下一步：STOP_WAIT_DM01_R4R2_INDEPENDENT_EXTERNAL_AUDIT。提交与推送不代表外部接受或下一阶段授权。
