# R2 数据算法修复本轮交付与未闭项

日期：2026-10-08（北京时间）。结论：**SCOPED_REPAIR_AND_NUMERICAL_CHECK_PASS；A0–A7 全量修复未完成；FULL_PRODUCT_ACCEPTANCE_NOT_PASSED。** 本文件不是外部签收，也不把 NOT_VERIFIABLE 等同 PASS。

准确 Git 身份：

- 用户审计基准：`c68964eecc3653e3fb588113f615c925696959f9`。
- A0 入口冻结与交付分支同步：`508efc346514a8a6dcd3b26aec4fd31b257e04f8`。
- 发布绑定、现行前驱与首获时间校验修复：`ce84bb7105cb223ac765c69e3a135a8a424d7fdb`。
- 市场与六条复权坐标补充 oracle：`c11a0441b4ccb6b4310d1355f5404055a2286750`。

入口本地与 origin/codex/v4-fp14-r2-repair 均为指定基准；origin/codex/v4-system-reform 原确为 `682ed2d779e33d5cef24188ff5fa727d41626f70`。CLI 证据证明是不同交付分支，非声称缓存。上述提交已正常推送两条分支。本文随后的封存提交由交付清单及最终远端回读标识，不将文件自引用 SHA 当作来源。

## 按任务卡逐项处置

| 卡 | 状态 | 已取得的真实证据、修复及准确未闭范围 |
|---|---|---|
| A0 | PASS（当前联合矩阵范围） | 指定 SHA 入口冻结；9/30 当前 source/owner/read/Focus/Forward/snapshot 联合矩阵与哈希、业务日、source_as_of、publication_at、价格坐标、身份池和单位。当前联合矩阵是指定基准提交下的真实文件；严格 first_available_at 不存在则明确未证明。没有宣称所有历史 source 都可恢复。 |
| A1 | FAIL；完整两日轮动 NOT_VERIFIABLE | 378 个板块的当前 1,134 数值比对通过。当前 output_state 已验证非 UNKNOWN 数 **0**，保留 UNKNOWN **378**。9/29 日期归属成员未绑定，breadth_delta3 所需历史也不完整；Base/Seed 原生信号未传入当前 native producer。emergence/confirmation/生命周期非纯 PIT 文案问题。不能用 9/30 成员回填，也未用当前强度冒充轮动。5 个板块的两日成分变化、热度滞涨、状态迁移完整独立对照仍未取得。 |
| A2 | FAIL（完整 CORE 决策能力） | 当前全部 113 个股字段的 Owner、来源、参数、证据与缺失原因列入 lineage；5,213 股票的 ma20/ret5 共 **10,379** 独立数值比对。已有 trend_state 已知 5,167、未知 46。突破 5,213 全未知：5,037 缺精确前日 ATR 与接受跨基准变换，176 还缺接受复权。支撑来源元数据、相对状态历史增量与 LOO、显式等待/失效条件仍未补齐。未对每个 CORE 字段完成各 5 个成功/失败/边界样本，不宣称全算法独立验收。任意代码四类未入选原因的统一 API 表达也未完成。F/R/H/A 保留，未造 H1/H2。 |
| A3 | 部分 PASS；完整路径/异常矩阵 FAIL | 766 observations 仍 READY66/PARTIAL572/UNAVAILABLE128；旧日 297 条未绑定 native Core 不回填。最高优先未决 STRUCTURE_DAMAGED442、SECTOR_DIVERGENCE412、WEAKENING412、TOO_EXTENDED297、TREND_ACCELERATING294（谓词计数有重叠）。9/29→9/30 的 297 个 H1 目标日逐样本核对：291 RAW 坐标独立收益吻合，6 接受 QFQ 序列重算吻合；六条原始 affine 系数仍未独立复核。真实日更 NOOP、0 源请求，旧指针保留。异常撤单、重入与全部源修订/复牌矩阵尚未逐项本轮真实验收。 |
| A4 | NOT_VERIFIABLE（真实到期） | 保留 117 enrollments、585 plans、117 frozen T0；当前 due=0，585 PENDING。Focus 297 条不计 Forward 结算。相关隔离测试覆盖日历前缀保护、缺价不可 Pending、T0 append-only、幂等修订等；未把 22 项测试宣称为任务卡所有边界完整签收。真实未来到期现场验收仍待真实日出现。 |
| A5 | 部分 PASS；严格 PIT NOT_VERIFIABLE；完整积累链 FAIL | 修复 caller 任意过去时间可进入 first_observed 的漏洞，并验证已冻结归档字节；真实复读原首获收据保持原时间与哈希。旧严格 PIT 仍 0/3，corrected 不升级。50 行字段债务分域独立入账。完整模型/参数发布时间、生产实际触发时刻及未来严格 T0 全输入正式增量验收仍待建设；本轮不计算预测胜率或误报率。 |
| A6 | SCOPED PASS；旧历史前驱项 OPEN | 联合校验新增 Owner 日期/冻结输入头身份、与真实嵌入 publication 和因子/序列绑定的精确匹配；切换前校验现行前驱完整性。隔离 successor 使用**当前线上真实发布**作前驱，健康读取 5,213 股票、成功切回、健康失败精确恢复。实际生产 authority 字节未改。旧 ccbe6c 相邻前驱精确字节未恢复，原独立审计项继续 OPEN。完整全历史回滚及外部发布签收未取得。 |
| A7 | PASS（最少功能可达性） | Codex 内置浏览器启动当前研究、查 688349 返回 1 条三一重能、跨页打开个股真实行情 120/253 根；截至日 9/30、股/元单位可见。未进行 Edge、移动端、多分辨率专项；未把冒烟替代算法验收。 |

## 本轮修复实义

1. 发布器原先只看文件哈希与快照日，可能把同日但不同 Owner 内容的候选声明为联合一致；现在核对当前真实 Owner 输入头身份及 publication/因子/序列与快照的精确关系，在 CAS 前拒绝错绑。移动 accepted-head 路径仅比较冻结身份，避免新输入使健康前驱失效。
2. 回滚原先可精确恢复指针，但不保证指向的现行源可读；新增切换前验证现行发布，并以真实当前数据库在 E: 隔离验证恢复。未修改线上快照或历史收据。
3. 首获账本拒绝倒签，持久化采用运行时 UTC；传入时间仅作最多 5 秒的新鲜度断言。再次读取旧收据校验合同、日期、时区、来源集与归档 SHA，损坏即拒绝。旧首获时间保留，严格 PIT 仍 false。

## 独立数值范围

R2_NUMERICAL_ORACLE.json 保留 `ce84bb71` 的原收据；R2_NUMERICAL_ORACLE_V2.json 为补充 successor，含市场 RAW 来源核对与六条 QFQ 坐标比对，NUMERICAL_ORACLE_V2_ACCEPTANCE.json 绑定两者哈希。

市场当前：上涨 2,344 / 下跌 2,712 / 平盘 155 / 未知 13，身份分母 5,224；RAW 行情 5,213，收盘涨跌停分类比较 5,210，成交额直接以 RAW 的元单位汇总核对。该核对以接受的参考价和涨跌停边界为输入，不冒充交易制度规则重新外审或四轴算法全量重实现。

板块当前数值采用同日真实成员上的 ret5/ret20/amount_ratio20 中位数，与生产投影逐一比较。不存在可信前日成员时留空；不把前日成员缺失都归结为历史首获证明不足。个股重算读取接受的原生 QFQ 日序列，独立算 20 日均值和 5 日端点收益，不调用原因子内核。

## 验证及发布范围

22 项相关边界测试通过；真实当前候选新联合校验通过；真实日更修复后稳定 NOOP；隔离前驱健康回读与失败恢复通过。VALIDATION_RECEIPT.json、CLI_NOOP_AFTER_REPAIR.json、R2_DAILY_RELEASE_ROLLBACK.json 和 IAB_MINIMAL_SMOKE.json 给出对应范围。

TDX 仅作既有只读输入。本轮没有修改 TDX、原始入组、锚点、T0、旧收据、线上联合权限或快照身份；不新增网络行情、外部复权、自动交易及概率结论。Phase0 沿用正式 FULL_PASS 范围，不重启 scanner。

下一阶段尚未执行完成：真实逐日成员和 Base/Seed 绑定；结构 Owner 的前日 ATR/变换与显式条件；LOO；每个 CORE 全部成功/失败/边界 oracle；全部 Focus 事件异常与六条原始复权系数；完整向后严格 T0 输入/模型/参数积累；真实 Forward 到期验收。可用研究域保持开放，缺失能力仅局部 fail closed。
