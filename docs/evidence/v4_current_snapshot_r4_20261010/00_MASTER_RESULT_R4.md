# R4 当前快照修复交付（2026-10-10）

本轮工程范围状态：ENGINEERING_SCOPE_COMPLETE_WITH_DECLARED_FORMAL_GATES。全正式准入仍为 EXTERNAL_ACCEPTANCE_BLOCKED；只申请 EXTERNAL_RECHECK_REQUESTED，不自签外审。代码提交：26f7d7b3548142976384c4d265ebbc9f047dc735。精确各包代码、源字节与测试以manifest及包内收据为准。

| 包 | 本轮工程结果 | 独立保留的门 |
|---|---|---|
| A Amount | 原历史观测/归档只读追溯、日历重算、消费者金额核对；缺观测数量/覆盖率修为null | H21仍缺20日原始成员首获；经济等价与正式消费者权限未证明 |
| B Sector | 六字段版本化契约、隔离提取/Episode候选、400板块守恒与独立oracle、负例 | 正式CONFIRMED/WARM/冻结前态/due/scenario与Owner未准入；不发布成熟度 |
| C Cohort | 可信Head/grant/Owner/source SHA接线、语义负例、不可覆盖隔离publisher、原settlement日历复用 | 2290条实际结构事件不证明合法历史enrollment；真实分母未知 |
| D FEP | 3历史工程模型、615历史预测和Shadow授权盘点；六类中文禁入原因；冻结预测时钟不可改写 | 既有工程/Shadow产物不自动获得当前生产模型或评分权限 |
| E runtime | 真实PID/旧服务10路HTTP、当前代码隔离10路、正常启动模块取证入口 | 28765仍为旧进程，无安全停止接口；PROD_RESTART_PENDING；双尺寸DOM及生产故障恢复NOT_TESTED |

集成测试85项通过；C包另有43项最终准入定点测试与109项原Forward/settlement回归通过（与集成有重叠，不合计为独立样本总数）。D新增14项通过；扩大历史E5套件22项被隔离DB门拒绝setup，未声称数据库回归通过。A/B源级及边界计数见各自独立结果。

三个既有R3小包CRC/逐文件SHA已核；LOO固定种子抽样139组合/1112比较、两个真实pulse240比較均零差异。这是开发机stdlib独立公式重放，不能替代外部审计人独立执行。没有重建未变全量旧历史。

运营Head保持55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e，严格PIT Head保持38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40；AUTO=true/revision5与10/09旧日收据保持原值。TDX只读、无新能力激活、无真实FEP预测、无10/12数据或未来结果、无Windows运维改造。

浏览器限制实录：IAB本机地址ERR_BLOCKED_BY_CLIENT；Chrome不可用。HTTP或手写摘录未冒充原始DOM。正常启动入口为scripts/start_product_attested_r4.py，仅在旧服务正常退出后运行；占用端口实测拒绝，无进程被停止。E门等待实际可执行的正常关闭和浏览器工具，不阻塞本輪其他工程交付。

历史来源搜索结论仅覆盖A_SEARCH_MANIFEST列明的真实本机/归档/收据位置及Drive受限目录读取，不声称全世界不存在原件。出现真实原件或正式授权前各门保持关闭。Drive写入与字节回读结果另见09_DRIVE_READBACK_RECEIPT.json；回读收据在报告/小包之后追加，未包含于先生成归档。
