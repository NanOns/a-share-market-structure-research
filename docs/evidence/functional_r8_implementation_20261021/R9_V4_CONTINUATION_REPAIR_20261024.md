# V4 R9 续修报告（2026-10-24）

本报告续接 [R9 独立外审实修报告](R9_INDEPENDENT_AUDIT_REPAIR_REPORT.md)，记录后续发现的 V4 业务代码修复、复测和仍未闭合的验收项。**本轮继续修复已确认问题，但 V4 全范围功能修复与发布门禁尚未全部通过。**代码推送不构成独立外审、正式 Head 更新或发布验收。

## 范围与基线

范围按用户澄清，限定为现役 V4 功能模块及其真实调用依赖；不把 V1–V3 的独立旧功能纳入重构。静态扫描仍读取仓库文件来解析 V4 入口图，但全仓维护脚本计数不等于 V4 缺陷数。工作分支为 `codex/v4-unified-development`，续修代码提交为 `e95b3be0d2f35cf731d868dfb3849bb5513c13e1`，前态与推送前远端均为 `ca7f71b62278cc32c81eca6702fb6fb3ce0fdb04`。

本轮未更改接受合同或正式 Head，未写 PG、未调用 DuckDB、未重启服务或 Windows，也未切换 28765/28766。只读端口核对结果为 PG `5432` 由 PID 8640 监听，开发端口 `28766` 由 PID 52916 监听，`28765` 无监听。此前 R9 报告中已记录的候选 PG 真实全量读回证据继续有效；本轮新增改动以真实候选数据计算及隔离回归测试验证，没有新增数据库写入。

## 本轮实际修复

- **市场预览跨日缓存和冷路径：** 当某日已经有精确限价回放收据时，`r6_candidate_market_stress.py` 不再扫描所有历史 R5 物化目录；已有精确前态 Core Owner 时，以其身份集合计算三会话比较分母，不再解压、解析 239 MB 历史 universe。没有前态 Core 的旧候选仍走原绑定 fallback。对同一真实候选 token `14ee0cf8…ad378` 和同一 2026-10-19 至 2026-10-21 窗口，以精确、仅开发候选用途的 R9 scope 执行 A/B：续修版 43.027 秒，续修前 `ca7f71b` 版本 84.966 秒，单次耗时减少 49.4%；两次均为 `READY`、`production_admission=false`。先运行续修版、后运行基线版，因此存在操作系统文件缓存顺序影响；该单次对比不代表冷启动 P95 或完整 Home 页面达标。趋势仍为 `UNKNOWN_REFERENCE_PATH_NOT_COMPLETE_AT_T0`，综合状态仍为 `NOT_PUBLISHED_V4_03`。无 R9 scope 的历史 Head 会被 `R7_MARKET_CORE_CONSUMED_FIELD_REVISION_REQUIRED` 拒绝；该 fail-closed 结果不被当作性能样本。
- **Daily Owner 的来源绑定：** R43 Core Owner 把当前精确 acquisition 收据写入 `SOURCE_BINDINGS.sources.acquisition`；结构 Profile 的状态重放只消费该绑定下带日期的查询回执，缺少交易日即拒绝，不再从固定 10/09 收据构造当前状态。操作适配器把本次 membership snapshot 注入结构重放，避免当前流程落回冻结历史快照。日期查询负例和本地换日/来源上下文回归通过。
- **TDX 写入隔离：** R43、Focus 与 corrected owner 输出防护改读配置中的通达信只读根；Core 写入的 GBBQ 快照改从配置根读取。R43 写入防护会检查全部配置根，配置缺失时 fail closed。未在 TDX 源目录创建或修改文件。
- **历史/修正路径的 fail-closed：** Sector 对每个日期要求唯一匹配的行业查询并验证查询载荷存在；Corrected owner、Focus、Sector 写入保护不再硬编码 `D:/new_tdx`。

具体变更位于 `src/workbench_analysis/{r6_candidate_market_stress,r43_owner_replay,r43_structure_replay,operational_owner_adapter_v1,r43_focus_replay,corrected_owner_replay,corrected_focus_replay,corrected_sector_replay}.py`；新增市场缓存范围回归及来源上下文回归，更新 R43 gzip 写入测试。

## 测试和扫描证据

V4 定向回归：`105 passed, 3 skipped`。扩展到冻结历史 DM01 R3 合同测试后：`130 passed, 3 skipped, 4 failed`。4 个失败都追溯到同一冻结源码绑定差异：合同期望 `scripts/v4_02_build_raw_selected_v2.py` 为 SHA-256 `128325a48c818378d78116f9785f50bedba348f401ce164802a81e0e7ab88cf6`、25,823 字节；该字节版本仍可从历史 Git 提交 `38d129a1d749d81cb40d2f88ba95d3ac622b04e6` 精确取回，而当前工作树版本为 SHA-256 `fa4e08b425a4d0f536086fe53bca1a5e2bf10198c7e474d8861b9685ec7a0c72`、26,218 字节。本轮没有修改该文件，也没有放宽冻结哈希门。失败发生在当前 checkout 源码与历史精确合同的交界；这是待独立处理的历史合同/回放缺口，不应误报成续修代码导致的回归。

依照用户澄清重新解释字面量扫描器：现有 V4 活动入口合同共 7 个，入口 SHA 均经核验；从这些入口按静态导入、资源引用构成的闭包共有 652 个可达文件。当前闭包扫描发现 2,211 个未裁定业务字面量候选、0 个自动确认违规、25 个未解析动态导入边和 25 个浏览器 fetch/import 位点。候选数代表需核实的命中，不等于已确认缺陷；V4 运行闭包仍因未解析项阻断。前次报告的 82 个动态项包含维护脚本，5,003 个维护候选来自全仓非活动维护入口，不能作为 V4 缺陷数。本轮没有把它们算作 V4 运行缺陷；V4 维护脚本仍需按确切入口和依赖单独归类，不能静默豁免。

增改业务行的固定值检查未发现新增股票代码、板块代码或交易日分支。修改文件中保留的日期字面量仅是 `r43_structure_replay.py` 的显式历史直放回退路径 `docs/evidence/r4_3_four_session_closeout_20261009/MEMBER_SNAPSHOT_S.json`；当前日更适配器传入当前 snapshot，直接历史回放仍保留原冻结输入。新增测试只使用合成证券身份和合成日期。`git diff --check` 通过。

## 仍未解决、需外部来源或业务裁定的事项

1. **D2：** 入场时如何生成冻结失效价仍没有已批准合同。用户明确要求交下一轮 ChatGPT 独立审计；本轮不生成价格、不回填 875 个旧 episode，D2 保持 `BLOCK_CONTRACT`。
2. **D0：** cutoff/source seal 合同未闭合；三态向量复放不等于新 Owner 封口或 PG publication。
3. **市场趋势及综合：** 趋势参考路径尚未绑定当前 publication；SIGN 与正收益指示器 breadth 公式仍待业务裁定；综合继续 `NOT_PUBLISHED_V4_03`。
4. **完整日更：** 10/22 同日 Identity/Member authority 未发行，10/23 缺 BaoStock 对应日线和因子。新日期完整 Source→Core→派生链、G1/G3、PG publication、CAS 一胜及失败恢复尚未全部重演。
5. **UI 与性能：** 28766 仍载入旧运行代码，本轮按要求未重启；未完成新版浏览器端验收。市场单项冷计算有所下降，但此前交付版 Home 单次冷请求为 111.933 秒；冷启动 P95、图表和三并发预算仍未验证。
6. **Focus/Forward：** Focus Priority 子页排序规则未获业务定义；Forward 仍无经授权的 LIVE 首捕获 cohort，历史研究样本不能替代 LIVE 证据。
7. **来源差异及历史复算：** 跨源 Amount 差异仍须独立审计；10/09 原 Owner 全数值流水线尚无本轮端到端重算证书。
8. **V4 运行闭包扫描：** 2,211 个候选、25 条动态边及 25 个浏览器路由尚需逐项定位、裁定或解析；外审/发布仍阻断。前次全仓 5,003 项维护计数不应拿来代替 V4 范围盘点。
9. **冻结 DM01 R3 历史源码合同：** 上述 4 个测试失败需要在历史回放/版本化源码归档层解决，不能通过改写已冻结合同哈希或忽略校验消除。

机器可读证据见 `R9_V4_CONTINUATION_EVIDENCE_20261024.json`。上一份完整任务报告及其机器证据继续保留：`R9_INDEPENDENT_AUDIT_REPAIR_REPORT.md` 与 `R9_INDEPENDENT_AUDIT_REPAIR_EVIDENCE.json`。本报告只覆盖这次续修新增的代码、复测和范围更正。
