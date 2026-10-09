# 大A V4｜R4.3 R1 定点修复、外部复验与安全生产切换任务卡

- 版本：R4.3-AUDIT-R1-REPAIR / 2026-10-09
- 唯一入场分支：`codex/v4-fp14-r2-repair`；冻结审计提交：`52f097f82cb1dfee58b20b1a93e3339b1dc37eac`；启动时复核远端新 HEAD/干净工作树
- 父合同：Drive R4.3《四交易日基础数据全闭环》；本轮独立外审《V4_R4_3_四日数据与生产切换_独立外部验收_R1_20261009.md》；`AGENTS.md`
- **冻结四日期**：2026-09-28、09-29、09-30、10-08，价格截止 10/08；最新通达信成员快照 S 采集于 10/09，只允许运营回算、不允许历史 PIT
- **生产约束**：禁止旧 Head/证据/原始源覆盖；未经独立来源/数值/兼容验收绝不擅自推进生产 CAS；但所有已授权、可独立完成的代码修复必须连续执行，不要重复下载 551MB ZIP 或重复训练 528 条旧 QFQ。

## P0-A：修复可证明矛盾的 snapshot S 来源复解析

精确位置：`src/workbench_analysis/tdx_member_retro_r43.py`：`capture()` 生成含 `industry_level`、`primary_industry_rank_eligible` 的成员字典，`reparse_verification()` 没有这两列却用 `rows==original` 和完整 digest 相等断言。冻结的复验收据 `SOURCE_CAPTURE_REPARSE_VERIFICATION.json` 声称 PASS，执行 verifier SHA 与当前代码相同。

必须执行：

1. 用**实际**冻结 `tdxhy.cfg`、`tdxzs.cfg`、`infoharbor_block.dat` 重新解析，输出原/复解析**字段名全集、至少 20 条叶级/父级/概念样本、首个不相等记录**；确认冲突真因。运行失败必须如实保存非零退出码和 traceback；绝不能手工修改收据状态。
2. 同一 source/parser 版本下让 reparse 和 capture 使用共享、可独立测试的**确定性纯 row normalization**；保留 `industry_level`、`primary_industry_rank_eligible` 及所有原字段，不默认删列逃避问题。
3. `SOURCE_CAPTURE_REPARSE_VERIFICATION_V2.json` 必须有命令、退出码、执行源码 SHA、源三文件 SHA、55,136 全量关系 digest、多对多 key uniqueness、行业/概念/父子级覆盖和独立安全校验。变更某一位源数据或一条成员映射必须触发失败；同源两次执行 digest 必须一致。
4. 原冻结 S 身份与先前四日 Owner 若重建后值完全相同，证明 hash 一致即可不重算大文件；若集合或口径真有改动，**新 S2＋新四日 Owner 候选**，不得原地改历史快照。

验收：复解析用真实源运行 `exit_code=0`、零行差异；外部按原文件和独立解析逻辑至少能复核关键字段和成员 digest。否则 `SOURCE_REPARSE_BLOCKED` 单门，不假报完整验收。

## P0-B：保持 V4 既有 UI，分离候选调试页面

精确位置：`src/workbench_service/v4_server.py` 的 `if operational is not None: return r43-operational-preview.html` 分支位于正式 V4 UI 选路之前，会令合法新 Head 一发布就用 2KB 预览页覆盖 `/v4` 和根路径。

必须执行：

1. `/`、`/v4`、`/v4/` 保留原 production UI 的入口与版本化 authority。**R4.3 调试器只允许**独立 `/v4/operational-preview`（或版本化诊断路径），生产页面不可被替代。
2. 新 R4.3 operational 数据接入现有 V4 BFF 所需的**最小兼容 adapter**：保留原查询路由可用性、context token/日期一致性、用户可搜索与列表/详情 envelope、读源标签、UNKNOWN 及回滚；对尚未实现的模块保留旧明确降级，不返回伪造的空记录。最小兼容是 W7 发布测试范围，不是提前执行 FP-01～FP-14 的全新前端建设。
3. 在 E: 隔离测试环境真实模拟“无 operational head／有合法新 head／回滚旧 head”三个状态。分别访问 `/v4` HTML、`/api/v4/context`、stocks、sectors、focus、diagnostics 和已存在 BFF/页面 API；比较前后的导航入口、响应状态、分页/详情。加入强制回归：合法新 Head 不得返回 `r43-operational-preview.html` 作为 `/v4` 主页。
4. 让 `/v4/operational-preview` 继续有日期+域诊断，不伪称完整六入口实现；避免在 R4.3 Data Cutover 顺手替换既有产品。

验收：候选模拟切换不丢页面，原页面可使用当日 10/08 合法新领域，未新接通领域精确状态，真实回滚可读 9/30。若失败，禁止生产 CAS。

## P0-C：限定范围独立来源／数值复审，签发新的候选

1. 读取 Git LFS **真实数据字节**而非 pointer；Drive 的 17 段 1.13GB 归档可作为可恢复备份，先核实完整 SHA，再按需要有针对性提取源/Owner。不要把“仓库有 LFS pointer”和“开发方做过本机 SHA”作为外部复算。
2. 独立核验最新 S 的 55,136=52,912+2,224 关系与行业/概念多对多，原 9/30 378/50,162 快照未覆盖；至少跨 110 叶级、23 父级、268 概念抽样。T00 只有源关系、无合法成员时不伪造价格。
3. 四日 5210/5211/5213/5209 真实 RAW、12/12/11/15 停牌、T-1/T-3、当前/T-1 MA20/ATR、复权跨事件、RPS 完整排序/端点与 Profile 已知/未知、TDX 多板块 LOO 与 40 样本按可重现 oracle 验收。北交所继承 optional degraded、2,224 未映射解释要按原分母口径保留；不要求为了“全量通过”硬塞无身份证券。
4. 区分运营回算与严格历史 PIT；必须保持 `RECONSTRUCTED_LATEST_MEMBERSHIP`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`survivorship_bias_risk=true`，不能混 CSRC 83 行业。
5. 真有数据修复才生成新 S/owner 的增量修订；纯 QA 修复可保留旧 S/owner hash 并生成完整新 QA、修订代码 hash 和候选版本。独立外部审查者签收之前不得自填 `EXTERNALLY_ACCEPTED_R43_OPERATIONAL`。

## P0-D：符合准入后执行真实 10/08 切换及接口核对

1. 针对**最终实际候选 digest**生成版本化独立外审对象、范围、排除域、SHA 与审查通过记录。生产 head 地址应为新 operational namespace，旧 9/30 strict PIT Head 保留。
2. 用原子 CAS 发布，不允许落入旧版 all-nine PIT 虚假授权；验证 stale CAS、NOOP、bad source、前驱回滚、并发与崩溃注入。
3. 真实线上 `/api/v4/context` 必须 `accepted_trade_date=2026-10-08`、来源 `RECONSTRUCTED_LATEST_MEMBERSHIP` 且准确提示非历史 PIT；四日期股票／TDX 板块／LOO／Rotation／Market／Focus/Forward 同 token 可读，页面仍为原产品入口。
4. 如果某个正式权限仍阻塞，只冻结 `SCOPED_ADMISSION_REQUEST` 和明确缺失的独立证据，不得“用户已经授权”即伪造最终审计 PASS；其他可执行域继续。
5. **仅**当四日基础运营数据 `FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS` + 实际生产与页面最小兼容读回通过，才启动已归档 FP-01～FP-14 的完整前端缺失模块修复。无须等 20 个交易日的 Forward 统计成熟。

## 必交证据和 QA

- `R43_SOURCE_REPARSE_CONTRADICTION_AND_FIX_V2.json`（包含失败复现／修复代码/hash／真实重跑）。
- `R43_PRODUCTION_UI_ROUTE_AND_BFF_COMPATIBILITY_QA.json`（三个 head 状态、实际 HTML/JSON readback）。
- `R43_SCOPED_EXTERNAL_SOURCE_NUMERIC_REVIEW_V2.md`（真实字节、抽样、范围、结论）。
- `R43_NEW_OPERATIONAL_CANDIDATE_AND_CAS_V2.json`（精确 candidate digest 和已签权限）。
- `R43_LIVE_1008_FINAL_READBACK.json`（若真发布，附原 9/30 hash 保留/回滚证据）。
- `R43_R1_FORMAL_HANDOFF.md`：逐项 PASS/FAIL/NOT_VERIFIABLE；不能只写一个泛化 BLOCKED；新 commit SHA、测试、生产实际状态和能否启动 FP。

**收尾唯一规则**：任何一次 PASS 必须有真实完成动作的哈希与读取证据；未通过的独立门不能借旧版本收据洗白，实际生产仍停 9/30 时总判定不可是 `FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS`。

## Codex 直接启动指令

读取本任务卡和 R4.3 最新外审，先校验 `codex/v4-fp14-r2-repair` 新 HEAD 和 `AGENTS.md`。严禁重复整轮重算已哈希稳定的数据。首先真实复现 `tdx_member_retro_r43.py` 的 `capture` 与 `reparse_verification` 字段不一致问题（capture 含 industry_level 和 primary_industry_rank_eligible，reparse 缺少却断言 dict 完全相等）；修纯确定性 row normalization、重新用三份冻结通达信源运行，必须有真实失败和修复后成功收据。并行修复 v4_server 当前 operational Head 一接受便用 r43-operational-preview.html 抢占 `/v4` 主页面的问题：将预览迁移为独立诊断路由，建设最小 BFF/同 token 可见性兼容，验证候选 head 启用与回滚都不丢现有 V4 页面。独立复核真实 S、四日 RAW、QFQ/Core/Profile 与 400 板块/LOO/Rotation 的生产候选证据，缺失外部准入则精确降级、不得自签。真实来源/数值/兼容门通过后再申请并执行安全运营 CAS，验证线上 10/08 同版与旧 9/30 原快照。最终外部验收通过才启动 FP-01～FP-14 其他页面缺陷工程。提交源码、收据和独立验收入口到 GitHub，输出下一轮精确阻塞，拒绝报告式空转。
