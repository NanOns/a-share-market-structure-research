# R2 数据算法独立审计项 V1

各项独立于当前生产总门禁。原 AUD-R2-SNAPSHOT-PREDECESSOR-MUTABLE-REF 与历史收据保持原状。

| ID | 独立范围与证据 | 本轮接受与未闭条件 |
|---|---|---|
| AUD-R2-GIT-DELIVERY-REF | CLI 冻结指定 SHA c68964eecc3653e3fb588113f615c925696959f9，真实工作分支 codex/v4-fp14-r2-repair；system-reform 原为 682ed2d779e33d5cef24188ff5fa727d41626f70。 | 修复交付指针：正常 fast-forward 到 508efc346514a8a6dcd3b26aec4fd31b257e04f8，后续本轮提交同步两分支；非缓存异常。 |
| AUD-R2-JOINT-OWNER-SNAPSHOT-IDENTITY | 旧联合发布仅验文件可读和快照日期，未核对候选实际 daily_owner_authorities 与快照内容。joint_release.py 新增逐 Owner 日期、冻结输入头 SHA、三类嵌入 publication 内容及 sector/stocks 核心绑定核对。 | 定点修复及真实当前候选验证通过。不是宣称历史所有候选都重新验收。移动 accepted-head 路径不作为冻结前驱的读取依赖；不可让新输入使上一快照失效。 |
| AUD-R2-PIT-CALLER-BACKDATE | pit_observation.freeze 原允许传入任意过去时间；旧路径存在即返回，未验证归档来源字节。 | 持久化采用运行时 UTC；传入时间仅作新鲜度断言，超过 5 秒拒绝；复读核对合同、日期、来源集、时区、SHA。22 项相关测试与真实 NOOP 通过。保留历史 first_observed，不改账；strict PIT 仍未证明。 |
| AUD-R2-ACTUAL-PREDECESSOR-READABILITY | 本轮把线上现行完整发布作为隔离 successor 的真实前驱，E:/codex_tmp/r2_algorithm_rollback，实际数据库健康回读、切回及健康失败精确恢复。 | 本轮现行前驱可读可恢复；旧紧邻前驱缺失字节仍 OPEN，不声称全历史回滚。发布器切换前验证现行前驱，损坏时拒绝 CAS。 |
| AUD-R2-ALGORITHM-SEMANTIC-50 | R2_VERSIONED_FIELD_DEBT_LEDGER.json 固定原 50 行，逐项局部门禁、来源及分类；R2_OWNER_FIELD_DATA_LINEAGE.json 列当前全部 113 个股字段。 | OPEN：独立数值校验 10,379 个股项目和 1,134 板块项目不是对 50 缺口的验收；没有 Owner 的公式不自造。 |
| AUD-R2-FOCUS-AFFINE-6 | 前日 297 episodes 中 291 个 RAW 与 QFQ 收盘坐标一致，独立核对 return_close 与 H1 结果；其余 6 个未以独立变换完成。 | OPEN：见 oracle 六个 episode_id；不得把 291 个扩大为 297 全路径通过，更不得算 Forward 结算。 |

证据位置：docs/evidence/r2_data_algorithm_repair_20261008。下一关：真实归属成员积累、原生 Base/Seed、结构 Owner 与全部 Focus 复权路径独立验收；不因这些局部缺口关闭已验证当期研究域。
