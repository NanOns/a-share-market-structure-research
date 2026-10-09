# DD R2.1 定点修复结果

BASE_SHA: 851770b1932d95836ce76bb44fd292117958bf04。RESULT_CODE_SHA: 7c72943140f05e92539da95dffead3365c307637。分支 codex/v4-fp14-r2-repair；AGENTS.md 根规则及 scripts/AGENTS.md 均遵守，临时验收位于 E:。

工程结论：ENGINEERING_SCOPED_PASS / EXTERNAL_RECHECK_REQUESTED。不签 EXTERNAL_ACCEPTANCE_PASS，不宣称 DD01–DD07 全量独立数值通过。

| 工作包 | 实现和证据 | 判定 |
|---|---|---|
| R2-01 | cb74f61f；append-only scheduler_attempts、旧 Job/事件留存、source revision 后继、8 次有界尝试、用户取消抑制/rearm、暂停、checkpoint；后续 18ba69c0 补30分钟持久探测冷却和瞬时基础设施恢复 | ENGINEERING_SCOPED_PASS |
| R2-02 | 9620bda7；executor 正式调用 source_readiness_v2，实读冻结摘要/日期/停牌 OHLCV 对账，合法零因子查询证明、不可变逐源记录；SOURCE_READY 后才 DERIVING | ENGINEERING_SCOPED_PASS |
| R2-03 | 51a863fb；两日各25个 seeded +8个边界证券，先冻结名单后读数；完整5224成员列表与RPS cohort；三个板块完整ret1贡献 | SCOPED_ARITHMETIC_PASS；完整前置链/LOO/Market NOT_VERIFIABLE |
| R2-04 | 18ba69c0 / 1c1d6ddf；真实双进程CAS、崩溃恢复、HTTP失败回滚、ENOSPC隔离注入；生产无活跃任务时重载修复代码，六接口真实新token一致、旧token全409 | ENGINEERING_SCOPED_PASS |
| R2-05 | 1c1d6ddf；244组真实冻结周期样本及6组明确FIXTURE；RAW/QFQ sums/extrema，闭包窗口无未来K | SCOPED_ARITHMETIC_PASS；完整日历/closure状态链 NOT_VERIFIABLE |
| R2-06 | 单ZIP隔离解压CRC/全部SHA、标准Python无网络oracle、轻量上传和实际回读；最终Git/Drive结果以配套index及云端回读收据为准 | EXTERNAL_RECHECK_REQUESTED |

59项回归，退出码0；完整命令和stdout在 R2_04_TEST_RECEIPT.json。小包实际离线oracle 22840项，差异0，其中周/月字段1750项。独立公式未调用任何producer；运行主体仍为本轮工程执行方，外审签发尚未授予。

| Gate | 本轮结果和边界 |
|---|---|
| G01 | PASS_SCOPED：source revision变更后同target新attempt、旧Job不改成成功 |
| G02 | PASS：用户取消/暂停/稳定硬错误/8次上限/显式rearm负测 |
| G03 | PASS：SOURCE_READY实调在DERIVING之前，逐源日期/摘要/时刻可读 |
| G04 | PASS_SCOPED：缺源/错日期/停牌冲突阻断，零因子变化需原始响应SHA |
| G05 | PASS：SHA256(seed|day|security_id)离线名单复做；event/异常价量/沿袭身份分层未全部保证，单列不足 |
| G06 | PASS_SCOPED：MA20/ATR20/量额比、完整RPS排名、选定板块median/breadth；前置收益率全链、完整Native/LOO/Market NOT_VERIFIABLE |
| G07 | PASS_SCOPED：RAW/QFQ周期OHLCV/amount；闭合状态/官方日历原始历史签发 NOT_VERIFIABLE |
| G08 | PASS_SCOPED：双进程发布锁/CAS、readback回滚、PREPARED和CAS后重启恢复、checkpoint顺序保留last-good；全故障矩阵未签全量PASS |
| G09 | PASS：真实运营Head与严格PIT SHA保持锚值；Amount Native主权威未改 |
| G10 | PASS_SCOPED：实际28765六HTTP同token、旧token六个409 |
| G11 | PASS：ZIP CRC、全部SHA、隔离无网络oracle退出0 |
| G12 | PASS_DISCLOSURE：Windows整机重启/登录前NOT_TESTED，全量Owner/源数值NOT_VERIFIABLE |
| G13 | 以配套EVIDENCE_INDEX和最终CLOUD_READBACK的真实URL、SHA、Git远端精确HEAD为准；单报告不替代实际上传回读 |
| G14 | PASS_SCOPED：两个原P1风险对应实码/负测，另修context旧token一致性 |

真实运营Head变更：NO。SHA 55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e。
严格PIT变更：NO。SHA 38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40。
10/09官方ZIP锚635c775940b2efdb8c9779c9898306c475822517f072c0eddcec8273b14e7ad6，仅复用现有冻结材料，不重新下载、打包或上传。
source readiness新记录为SOURCE_RECEIPT_REPLAY，未将事后收据回填as-recorded/PIT。包内real服务回读为REAL_LOCAL；源/故障注入为ISOLATED_INJECTION/FIXTURE。

AUTO保持ON；真实服务pid37196→41528，代码重载后仍UP_TO_DATE，下一门2026-10-12 18:35 +08:00（不是10/12已成功的断言）；新日需要全部源门和QA，后继另记，不回写10/09。

DD-A01（官方日历原始历史签发）、DD-A02（全量Rotation oracle）、DD-A05（10/09当时4946项Amount表示差异/历史Amount A）、DD-A06（新canonical准入）、DD-A07（Forward成熟）、DD-A08（Windows登录前/整机启动）均OPEN，责任为各自后续独立审计阶段。Amount小包15代表样本及分布保留Native权威，不把4946固定成未来日期计数。
另外未测试：rollback写失败、双进程scheduler与manual竞争、过期锁/消息重复完整故障矩阵。当前单进程manual/scheduler去重、真实双publisher竞争和旧schema留存有证据；不合成为完整系统场景PASS。数据库旧schema为新增表迁移，未删除旧Job，未声称down-migration已经实测。

大卷均本机保留，manifest记录path/size/既有绑定SHA，未进行本轮全部大卷重哈希。路径/摘要不能替代外部上游数值验证。只交付3个轻量文件，单件<=10MiB、合计<=20MiB，禁止规避预算；最终实际字节总和见index。未续传旧分卷、未清理旧云端分卷。

离线复验：解压ZIP至全新目录，运行 `python oracle/independent_recompute.py --input . --output <separate_output>`；仅Python3.11+标准库，无本机DB/网络/登录依赖。精确校验命令及输出在EXTERNAL_REPLAY_README.md和oracle/ORACLE_RUN.txt。

REQUEST_INDEPENDENT_REAUDIT_R2

已上传离线ZIP：https://drive.google.com/file/d/1D9eln-o5zdYV24eHCuQEQ9tFH9WsH4HE/view?usp=drivesdk
实际云端回读 922122 字节，SHA 130858ffd901d0b593cc730a26c4247421fa5fdc832a69c208f36e9d29f91867；CRC及全部载荷SHA通过。鉴权下载引用返回403后改用连接器有界原字节回读，未续传/下载大卷。

7c729431补充：调度器接管手动retry时创建attempt ordinal及old_job_id关联；最终59项回归仍通过，完整命令指向dd_r21_final_v4。第二次停止并重载服务被自动审批拒绝，仅返回blocked by policy，未给具体理由；未绕过。运行pid41528已加载两项主风险与token修复，新增manual ordinal补录待下一次服务重载，不能声称补录已在运行实例执行。

云端报告URL：https://drive.google.com/file/d/1xiXFW2FnfPAmKItmUY36mA8VpC0WfvGt/view?usp=drivesdk
替换仍复用同一ZIP/MD文件ID；原上传版本和替换版本均计入累计上传字节预算，不借改名或版本逃避20MiB硬上限。
