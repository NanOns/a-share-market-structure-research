# R2 修复与正式分域发布交接

代码审计提交 `69abe03c4871aa404ab293d976bb52b36f2a6b39`；实际发布 app_version `53bd64e5`（完整值见 R2_RELEASE_CANDIDATE.json），UI build `87edf6dab9930ec630307f6b87d09ada6b22fcb08a30e7349a4561dee5ce8caf`。分支 `codex/v4-fp14-r2-repair`。后续提交仅收录签收证据，不倒填上述代码身份。

**SCOPED_OPERATIONAL_RELEASE_PASS，activation_performed=true；FULL_PRODUCT_RELEASE_BLOCKED。** 外部独立验收仍 PENDING，本轮由开发执行方重跑，不冒充外审。研究服务最新真实日 2026-09-30；不称10/8实时行情。

| 卡 | 本轮结果 | 证据与边界 |
|---|---|---|
| R2-01 | SCOPED_QA_PASS | 新 QA V2，IAB 1366×768/1920×1080六入口、点击、中文/键盘搜索、筛选排序、分页、详情、日期后退前进；真实停启服务恢复；隔离403/409/503。只关闭 QA13-01 的 Edge 专项依赖，不改历史 edge_pass=false，不关闭其他QA13欠项。 |
| R2-02 | DEGRADED_PASS | 35真实源摘要；5213股票、378板块、四轴；69值比对+20原生QFQ均线独立算术。11额外身份三个真实日对账，9/30均停牌无RAW bar，不扩池；历史 first-available 未证。 |
| R2-03 | P0修复/P1源债务保留 | 第16板块遗漏反例通过；Focus五子路由独立类型/分页/schema，Outcome缺源明确返回SOURCE_INCOMPLETE；股票timeline不再501，但结构事件/锚点全5213为UNKNOWN，未制造历史。H/invalid_if明确owner债务，等待/why-now沿用真实owner条件/迁移理由。 |
| R2-04 | SCOPED_OPERATIONAL_RELEASE_PASS | 单一联合CAS绑定UI bytes/Reader/运营范围；真实两版隔离联合失败恢复、陈旧CAS、无副作用NOOP、断电恢复；批准分域live切换后HTTP与IAB实际读回。紧邻前驱Replay摘要缺失单独登记，隔离演练使用另一个完整真实前驱，未冒充紧邻前驱完整恢复。 |
| R2-05 | PARTIAL_BLOCKED | 独立V4 journal真实9/29→9/30幂等、失败事务回滚，469 Episode/766事件投影对账通过。实际Path/Outcome owner全量不可用、旧PG不可读；自动Focus生产CAS及DM01→owner→snapshot→UI→Focus/Forward整链尚未交付，未伪造迁移/自动持续跟踪完成。 |
| R2-06 | DEGRADED_PASS | 保持当期成员/overlap；实际10/8开始首次观察冻结并接入日更成功/no-op路径。严格PIT仍0/3，corrected永不贴PIT标签；历史5/10/20与生命周期继续独立欠项。 |
| R2-07 | PARTIAL_PASS | IAB原生全量CSV落盘5213行、唯一身份、UTF8 BOM和9/30日期核对；Blob事件超时不计通过。110字段中文label定义齐全；V2已发布字段证据冻结，语义依赖V3独立再审有55项source ready，不能把110行刷为产品通过。分钟触板/炸板、官方事件、LOO/FEP当前绑定缺源。117入组T0均9/30，585计划未到冻结日历期限，PENDING不是工程失败。 |
| R2-08 | SCOPED签收/FULL阻断 | FP13_QA_V2_FINAL、FP14_RELEASE_V2_FINAL、R2_POST_ACTIVATION_READBACK和live截图；97项综合回归通过，发布后9项定向检查通过（集合重叠，不相加）。 |

已发布范围：个股当期事实/因子/图表、板块当期事实/完整成员/同日重叠、市场盘后四轴/指数/涨跌停、Focus事后重建读域、Forward读域、诊断、corrected比较。自动交易和自动Focus写入均关闭。全产品未发布；不作概率/收益承诺。

剩余独立审计：R2_INDEPENDENT_REPAIR_ITEMS_20261008.md；V3另发现部分owner literal UNKNOWN被KNOWN标记，已独立登记OWNER_QUALITY_ANOMALIES，不给予真实值就绪信用。该发现不把不存在数值变为已知，也不隐式修改冻结快照。

回归命令和原始日志见 REGRESSION.json；代码文件列表与精确SHA见 CODE_CHANGE_MANIFEST.json；真实源、数值、浏览器、日更、回滚、CSV和发布收据均在同目录。872历史保护项摘要不变；R1 FP13/14收据不改。R2未写TDX，也没有重跑R2前后全根checksum，不把R1旧checksum冒充本轮证据。

复核：`python -B scripts/finalize_r2_qa.py --verify-only` 只核验冻结证据和实际服务，不重写发布证据。已发布候选/QA禁止默认重跑覆盖；新审计用 `python -B scripts/run_r2_qa.py --out <项目内新版本目录>`。日更无新输入返回NO_NEW_COMPLETED_SESSION，保留当前联合发布。

下一阶段：补真实Path/Outcome owner及独立新journal生产准入/全日链；补严格首获与缺源字段后新版本复验。现有分域服务继续正式只读运行；推送不等于外部接受或全产品通过。
