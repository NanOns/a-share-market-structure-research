# V4 R8 硬编码实修与功能闭环报告

记录日期：2026-10-23（Asia/Shanghai）
开发分支：`codex/v4-unified-development`
本轮基线：`df6e312f773500f300d435cd51910961c79f7475`（与抓取时 `origin/codex/v4-unified-development` 一致）
验收状态：`V4_REPAIR_PARTIAL / EXTERNAL_REVIEW_BLOCKED`

## 范围和结论

本轮按用户最新限定只处理 V4 当前代码及模块功能。早于当前 V4 功能链的旧版业务代码和历史无用工具不属于本轮修复范围。目标交易日、证券全集、前态与来源应从当前调用、已接受输入/Owner 和交易日历解析；有日期的来源文件名、规则生效日、哈希绑定及历史合同只作为证据候选，不视作当前交易日计算参数。

本轮实际修改了 V4-02 输入解析、V4-04 候选运行、前向观察封存、来源/阶段治理、Owner/发布保护、市场基准合同及全局字面量扫描器；增加了回归测试。**代码与回归有实质进展，但没有达到 R8 完整功能闭环，也没有证据证明全部历史 V4 合同字面量都已逐项裁定。**扫描门仍阻断；不得据此报告全局硬编码 PASS。

## 实际改动

- V4-02 正式周期、交易状态、价格限制及全市场输入构建器改为显式输入来源路径；价格限制边界由当前接受输入/交易日上下文推导，移除业务默认的冻结路径和交易日。
- V4-04 全市场候选运行从已接受输入解析 cutoff，并参数化查询；接受输入解析器携带当前来源 cutoff。
- V4-01/V4-05 相关 Owner、Profile、行情、SourceAuthority 解析和发布校验改为由现行 Head、来源合同及输入参数确定目标范围；V4-02 raw selected 构建要求显式 `--asof`。
- 前向观察和 R3 集成封存入口要求调用方传入 cutoff；模型和基线按已封存身份/收据绑定读取，不以固定历史目录推断当前业务日。
- FP05/FP06 从接受输入读取当日 universe 与交易状态；BaoStock 运行接受要求显式日历收据，避免隐式使用旧日期日历。
- 核心市场产品的指数身份从带版本、SHA 绑定的市场基准合同读取；新增重复基准拒绝和动态合同回归。
- V4 服务、BFF、桌面 QA 与页面中的目标日/阶段读取使用当前上下文；阶段 0 anchor、Owner 来源及日期范围校验按接受输入解析。
- Priority 规则分支修正：已知 FALSE 主原因支配必需未知的组合，保留非支配未知场景的 UNKNOWN；补充两类分支回归。
- 全局字面量扫描器增加源码入口 SHA 绑定、显式入口清单、compact 日期/证券识别中的十六进制摘要边界，以及窄化的语法/证据误报判定。入口合同只证明源码清单，不证明正在运行的进程加载了该源码。

变更矩阵与完整文件清单以本次 Git 提交为准；未纳入提交的工作区文件保留原样。

## 回归与扫描证据

执行环境临时目录：`G:\\codex_tmp\\test_temp`；没有在 TDX 源目录创建或修改文件。

| 回归 | 命令覆盖 | 结果 |
|---|---|---|
| 功能/策略 | `tests/v4_policy/test_no_production_hardcoded_identities.py`、`tests/v4_joint/test_operational_product_pack_v3.py`、R8 S01/S03、Priority cache、S3 ledger、UX R2 合同 | 102 passed |
| V4 主链 | `tests/v4_02`、`tests/v4_04`、`tests/v4_05`、`tests/v4_scoped_promotions_r3`、`tests/upgrade_m1`、QFQ、Phase0 动态 anchor、scoped promotion 日期 | 243 passed |
| 变更 Python 语法 | 62 个变更 Python 文件 AST 解析 | 0 失败 |
| Git 空白检查 | `git -c core.whitespace=cr-at-eol diff --check`（含暂存差异） | 通过 |

全局扫描命令：

```powershell
python scripts/check_v4_business_literals.py --output G:\\codex_tmp\\R8_GLOBAL_LITERAL_INVENTORY_FINAL.json --allow-incomplete-inventory
```

清单 SHA-256：`cf29f40cdfb3b16faead7d6286b07c6ea061d1d872d9393f3615dce8a2260054`，大小 39,705,056 字节。扫描覆盖 3,962 个跟踪文件（3,266 Python、32 JS/TS、546 配置、100 SQL、44 UI）；Python 入口/依赖图 606 节点、10,348 边、133 个动态执行/导入站点，AST 失败 0。扫描结果为 `GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED`：活动未知候选 2,135、未核验维护候选 5,002、自动确认活动违规 0、活动入口状态 `SOURCE_VERIFIED`。其中活动未知候选主要集中于历史/版本化 V4 配置：`v4_joint_release_authority_v1.json` 828、`v4_replay_compare_authority_v1.json` 802；其余分布于规则有效期、日历事实、历史身份及证据绑定。零自动确认违规不等于逐条独立证明无违规。

V4 当前运行输入相关改动未新增固定股票代码或交易日分支；本轮已修复的目标日、cutoff、as-of 和来源目录均从调用上下文/接受输入读取。全局扫描仍保留大量冻结合同、日历、规则生效日与历史来源路径候选；这些不等同于当前目标日默认值，但仍须独立审查其合同消费者和版本状态。非当前 V4 功能链的旧代码候选按用户限定排除，不以其数量阻断本轮 V4 功能判断。

## 阶段状态（R8 R2）

| 阶段 | 本轮状态 | 证据与未完成项 |
|---|---|---|
| S00 基线/阶段0 | `DEGRADED_PASS` | 基线为远端 HEAD `df6e312…`; 阶段0限于代码修复、回归和 PG 只读核对。无候选 Head、正式 Head 或生产服务更新。 |
| S01 来源/摘要/缓存 | `PARTIAL` | 输入绑定与摘要路径有代码/测试覆盖；当前运行进程未加载本轮代码，不能完成真实冷/热 API、来源变更、坏 SHA 和消费者负例读回。 |
| S02 市场宽度/趋势 | `PARTIAL` | 目标日/来源路径更动态，市场参考有版本化合同；本轮未完成真实全市场独立数值对账及来源权限验收。 |
| S03 Priority | `PARTIAL` | 规则分支与数值边界回归通过；开发 PG 的 10/20、10/21 Priority Owner 缺失，`/api/v4/priority` 对旧进程返回 409，不能完成全集和真实 API 对账。 |
| S04 D0 | `PARTIAL` | 来源/日期/权限链检查改动；当前 Head 与开发 PG 无本轮对应 Owner，真实封存链和四场景全集未验证。 |
| S05-D / S05-I D2 | `BLOCK_CONTRACT` / `NOT_IMPLEMENTED` | R8 合同仍缺适用 D2 阈值生成、冻结时点和价格坐标裁定；不自行选择前低、均线或百分比，875 个历史 episode 未回填。 |
| S06-P / S06-I 日更 | `NOT_VERIFIED_THIS_ROUND` / `NOT_RUN` | 本轮未执行 G1–G4 独立比较、候选 PG 接续、CAS、故障恢复或日更性能采样；真实来源/Owner 前态不齐。 |
| S07 六入口 | `UI_RUNTIME_NOT_RELOADED` | 28766 仍运行旧临时脚本；`/api/v4/context` 返回旧 T0 2026-10-21，`/api/v4/health` 和 `/api/v4/priority` 返回 409。没有浏览器 DOM 或新代码页面读回。 |
| S08 正式发布 | `NOT_RUN / NOT_AUTHORIZED` | 没有 formal Head、生产调度、运行包或 28765 操作。代码推送不构成发布验收。 |

## PG、服务和保护边界

- PostgreSQL：`127.0.0.1:5432/market_research`。查询使用已有安全配置，首语句 `SET TRANSACTION READ ONLY`；`transaction_read_only=on`。本轮无 DDL/DML、Owner 发布、回填或重算。
- 只读核对未发现 2026-10-20/21 Priority Owner 或 Sector lifecycle Owner；最近已存在 Priority Owner 为 10-15，Sector lifecycle Owner 为 10-13。当前操作 Head 仍是 2026-10-09；Accepted Data Head 为 2026-09-30。
- 网页/API：28765 未监听；28766 仍为 PID 52916，命令行为 `E:\\python\\python.exe G:\\codex_tmp\\batch10r4_28766.py`。未停止或重启该进程。5432 的 PostgreSQL 主监听 PID 为 8640。
- 28766 的旧进程 `/api/v4/context` HTTP 200、状态 READY，但显示旧 T0 2026-10-21；`/api/v4/health` 与 `/api/v4/priority` HTTP 409。它不是本轮代码验证。
- 未删除或清理工作区文件/目录；未写入 D:/new_tdx 或其它 TDX 只读源目录；未切换正式 Head 或 28765。

## 剩余问题与下一轮独立验收

1. 在本轮代码部署/加载至获准的 28766 前，R8 S01、S02、S03、S04、S07 只能以回归覆盖，不可宣称实际服务闭环；下一轮需保持 28765 不动并按已授权的开发槽位流程验证。
2. 开发 PG 的 10/20、10/21 Owner 前态/来源缺失，Priority、D0、Sector、Focus/Forward 无本轮统一 token，需先判断可用输入和候选生成门，再按 R8 原合同逐日验证。
3. S05-D 业务合同裁定缺失，阻止 D2 实现和相关整链验收；这是语义门，不以代码选择代替。
4. S06-P/S06-I 的候选 G1–G4、增量日期范围、CAS/幂等/恢复和性能数据尚未产生。
5. 全局字面量扫描器仍为阻断。对 V4 当前配置中版本化来源/监管规则/日历事实与历史证据绑定需按消费者逐项核验；本轮没有把扫描器未分类候选列为通过，也不把旧非 V4 代码恢复为本轮目标。
6. `CI_NOT_RUN`；无全量性能压测；无外部来源调用、权限提升或正式发布验证。

本报告是开发修复记录，不是独立审计结论或生产准入。机器证据见同目录 `R8_GLOBAL_LITERALS_AND_FUNCTIONAL_CLOSEOUT_EVIDENCE.json`。
