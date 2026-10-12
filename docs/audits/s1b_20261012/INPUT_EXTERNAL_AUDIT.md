# 大A V4 R4-R3｜统一上传 ZIP 独立外审 R1（2026-10-12）

## 0. 范围、版本与结论

- 唯一受审交付物：用户手动上传的 Google Drive `V4_R4_R3_FINAL_DELIVERY.zip`，30,112,061 字节；Drive ID `1px4bMAL94guvIUW0krnmX4nADABsIEPi`。
- ZIP 代码基线及 GitHub 候选分支 `codex/r4-pg-only-20261011` 的 HEAD：`96b466a9694072e15928ca5d06c3cd4627d4a401`。在本审计读取时，原正式目标 `codex/v4-fp14-r2-repair` 仍为 `fbd23a6ba08d0948fe7ad421d1765fe363648522`，未合并候选。
- 独立读取 ZIP 内全部文件名、清单、两个 JUnit、S0/S1 结果、修复前后完整 Focus 投影、数值差异表，并审阅 GitHub 候选代码（精确身份适配、Journal、修复脚本和测试）。
- **裁决：`S0_EVIDENCE_PASS / S1_SCOPED_PASS / S1_FULL_GATE_OPEN / S2_NOT_ENTERED / EXTERNAL_ACCEPTANCE_BLOCKED`。**
- ZIP 字节审计、结果集合差异计算为本审计独立执行；本审计未连接用户的本地 PostgreSQL、未重放全部大规模算法及 77,425 条 PG 意图，因此不将 Codex 的局部执行宣称成我方独立 E2E PASS。

## 1. 本次独立核验结果

### 1.1 ZIP 清单与证据

- ZIP 有 497 个条目；`05_SOURCE_MANIFEST_SHA256.json` 正式记录 496 个文件，唯一豁免清单自身；逐项重算 **496/496 SHA-256 和文件长度完全一致**，无缺失、额外未列文件或损坏条目。
- `01_FINAL_STATUS_完成与遗留.md` 明确承认工程未闭环；`04_OPEN_ITEMS_未闭环事项.csv` 有可追索 OPEN。
- 暂停包 432 个 `.gz` 证据、未提交补丁和大型原始源引用均在 ZIP 内有对应说明；Codex 的 S0 回执标记 432 项 PASS。本审计确认清单/封装存在、对 ZIP 自身重算 SHA；尚未对 432 个解压条目再独立逐字节比对源机器原始对象。
- 受保护正式 Head/联合权限对象哈希在收据中前后相同；这是明确的**有限对象范围保护证据**，不是所有生产文件的全量保护证明。

### 1.2 定向测试

- `LOCAL_S1_FOCUS_R4.xml`：24 PASS，0 FAIL/ERROR/SKIP。
- `LOCAL_S1_IDENTITY_R4.xml`：23 PASS，0 FAIL/ERROR/SKIP。
- 独立解析两份 XML 的 `(classname,name)`：**16 个重复，合计只有 31 个唯一测试节点**，绝不能累加声称 47 项独立测试。
- 包内未包含在同一冻结合法分母下全量 clean run；原 4,568 基准节点、此前全量诊断 4,789 节点的失败不可作自动消除。

### 1.3 真正的算法修复：证券身份与公司行动

旧 Series 使用 `SEC-...` 内部 ID，GBBQ 行使用 `SH/SZ/BJ.XXXXXX`。旧代码从 Series 的 symbol 字段直接寻找事件，部分公司行动静默漏配；原无公司行动数值 PASS 因而不证明处理公司行动正确。

- 新 `src/focus_tracker/v4_exact_identity_adapter_r4.py` 强制绑定冻结的 `security_id -> source_security_key`，拒绝映射重复、缺失、符号错配，使用 v0.3 有理数复权公式；Journal 只在显式 `path_contract` 下使用候选。
- `S1_ORACLE/RESULT.json` 首轮 **实际公司行动路径=0**；修复后 FULL 回执为 **170**。首次 PASS 必须降级为旧错误路径自洽证据，不能拿来证明真实公司行动消费。
- 对 ZIP 内独立保存的 `NUMERICAL_DELTA.json` 重新计数：**101 条受影响观测、34 个不同证券、34 个不同 Episode**，日期分布：09-29 9 条、09-30 27 条、10-08 31 条、10-09 34 条。
- 独立对比两份完整 JSON：Episode ID 集合保持 2,805；在相同节点下**49 条 outcome metrics 改变、4 条 predicate_evidence 改变，outcome_status 未改变**；四条 predicate 证据从 UNKNOWN 变为 FALSE，当前主状态没有改变。整条 `price_path` 的输入 digest/身份合同也变化，不能把 10,329 项 payload 差异错算成 10,329 个数值变化。
- 对修复候选的报告：61,908 次价格比较、103,180 次谓词输入/公式检查、10,329 生命周期和优先级、15,345 结算检查、11 条实际缺失维持 UNKNOWN。上述大规模零差异由 Codex 原始 oracle 报告主张，本审计只独立重计可见输出集和部分变化，并未完整独立重算每次有理数。
- 最终修复投影保持 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`HISTORICAL_FIRST_AVAILABLE_PROVEN=false`、`production_admission=false`、`survivorship_bias_risk=true`，没有把重构历史伪称为当日首次可见。

### 1.4 Journal 与 PostgreSQL

- `S1_JOURNAL_REPAIRED/RESULT.json` 记录五个历史交易日的 append、2,805 episodes、10,329 events，77,425 条 PG 意图，以及幂等、CAS 冲突和失败回滚通过。
- 修复前旧 Journal 的 `PASS_SCOPED` 只证明**错误投影存储一致性**，必须归档保留但不得视为公司行动数值接受；修复后 Journal 的内容身份另行记录。
- 尚无最新候选经默认 HTTP + 联合 Head 同 T0、同 token 真实消费、readback、故障/回滚的完整证据。**S1 尚未完整通过，不进入生产。**

## 2. 主要未决事项

| 优先级 | 条目 | 实际未决门 |
|---|---|---|
| P0 | `AUDIT-FOCUS-SOURCE-IDENTITY-R4` | 其它重放生产者、Forward/settlement、默认 HTTP、联合 Head 对正确证券键的实际数值接受；全部受影响调用链 |
| P0 | `S1-HTTP-JOINT` | 修复候选在隔离 PG 上同 T0/source token 发布→默认读者→回滚负例 |
| P0 | `S2-DENOMINATOR` | 唯一合法 V4 分母仍 null；原 245 模块/4,568 节点保留，额外候选文档称 148，最新本地记录称 155，必须解释差额 7 |
| P0 | `ALL-PG-CONSUMERS` | 所有业务入口 DB06/08/09/12、Desktop、Source→Joint 等的动态 PG-only 调用证明 |
| P0 | `EXACT-56` | 170 条公司行动路径不是 56 类复权消费者的全量验收 |
| P1 | `FEP-87A` | 字段结构枚举不等于 producer/owner/cutoff/quality 数值语义 |
| P1 | `UI-CAPACITY` | 六入口、390 小屏 Focus 原溢出、并发/大内容扫描未获完整验收 |
| P0 | `FINAL-CLEAN` | 冻结合法节点集后一次 clean-slate 全量运行及独立复核 |
| 客观门 | PIT/H21、真实后继交易日、OOS成熟、正式权限 | 与工程缺口分开管理，不当作工程停止借口 |

### 2.1 补充代码审计风险

新 `v4_exact_identity_adapter_r4.py` 对事件类别用 `formal_disposition` 判定是否拒绝，随后实际复权公式只使用 `category == 1` 的事件。如果未来某个**非 1 类**被标为 `SUPPORTED_PRICE_AFFECTING`，其事件可能不被拒绝但也不进入复权公式。当前并无实证表明真实映射已发生这种情况，因此判为 **边界需验证**，要求增加三类反例：未知影响类别必须 UNKNOWN；非 1 类影响价格时必须 fail-closed；非价格类必须有明确忽略合同。不能先宣称这是已发生的数据损害。

## 3. 本轮是否执行完整任务？

- S0：已有支持的 PASS；人工归档与新规则一致，Codex **不需要**调用 Drive。
- S1：真实数值问题定位和隔离修复有价值；`S1_SCOPED_PASS`，但 HTTP/联合消费及跨生产者身份一致性仍 OPEN。
- S2：Codex 遵守停止门，没有自动推进。合法分母 **NOT_ENTERED**。
- 综合：**局部交付真实可信、未伪装全系统成功；用户不应回退有价值修复，也不应整体合并/切生产。**

## 4. 下一轮执行建议（Codex 本地操作）

1. **仅发 `S1-B` 工作包**：从 `96b466a` 出发，整理 `SEC/source_security_key` 跨生产者唯一映射；实测公司行动路径输出、关联消费者；完成隔离 HTTP/Joint Head 同 T0 与 token、事务 CAS、失败回滚、发布后读回。
2. **以身份缺陷为 P0 先行**：冻结 34 证券×101 数值变化及 49 outcome metrics/4 predicate 证据变化，作为未来回归固定反例。新增公司行动分类边界负例。
3. **完成 S1 出口报告**：每个入口 `PASS/FAIL/OPEN`、原始运行命令、时间、源码 SHA、数据 SHA、结果 SHA；有未决跨生产者路径则明确 S1-B NOT_FULL_PASS，不能进入 S2。
4. **S1 通过后才开始 S2**：审查 148→155 候选模块差额、冻结唯一合法测试节点分母；不要重复执行全系统数千条回归，先锁定范围。
5. **后续工作包**：消费者、EXACT-56、FEP/§87A、UI/容量、最终 clean run 分开，互不重复生产冗长证据。

## 5. Codex 归档规则（用户明确覆盖）

**不读取、不上传、不校验 Google Drive**。开发和测试只用本地 GitHub/工作树/已冻结文件，输出本地报告和证据。所有工作包完成后只写到 `G:\codex_tmp\V4_R4_R3_FINAL_DELIVERY\`，制作单一 ZIP，报告文件路径、Git HEAD 和目标人工上传目录 `https://drive.google.com/drive/folders/1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD`，由用户亲自上传。不要频繁复制大型源文件入包，用清单+SHA/本地复现脚本；例外是必须证明准确字节的少量失败样本。

## 6. 最终状态

`ZIP_MANIFEST_SHA256 = PASS (496/496)`  
`S0 = SUPPORTED_PASS`  
`S1_EXACT_SOURCE_IDENTITY = SCOPED_PASS`  
`S1_HTTP_JOINT_AND_OTHER_CONSUMERS = OPEN`  
`S2_LEGAL_DENOMINATOR = NOT_ENTERED`  
`FULL_V4 = EXTERNAL_ACCEPTANCE_BLOCKED`  
`PRODUCTION = NOT_AUTHORIZED`
