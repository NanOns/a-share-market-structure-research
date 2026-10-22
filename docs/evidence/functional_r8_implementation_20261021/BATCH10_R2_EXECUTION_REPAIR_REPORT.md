# BATCH10-R2 执行与源码修复报告

- 执行日期：2026-10-22（Asia/Shanghai）
- 仓库 / 分支：`NanOns/a-share-market-structure-research` / `codex/v4-unified-development`
- 用户指定审计基线：`00e4a34c64d2767f8b9f9ebc6efb7c7f7b50aeb3`
- 开始执行前确认远端最新 HEAD：`fb147663612c9c07c1ee4c61f4f89d7097c72c66`（已含 D0 不可变源码归档实现）
- 当前候选：10/21 Token `e8094ffefe07e18e90dcbd2a0077347745269b94a9ca56d85aa8c3a512031af4`
- 结论：`BATCH10_R2_PARTIAL / M0_PASS / M1_PASS / M2_PARTIAL / M3_PARTIAL / M4_PARTIAL`
- 阶段 0：`DEGRADED_PASS`。所有历史数据继续保留 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`；未切换正式 28765。

## 执行结果

完成 10/16 日期成员重新绑定后的 R8/D0 发布，并以此为 predecessor 依次发布 10/19、10/20、10/21。四个日期均在开发 PG 中有独立 R8 publication 和 D0 publication，D0 行数分别为 5,226、5,224、5,224、5,224；四个新 Token 的 D0 `as_recorded` 和 `pit_eligible` 均为 false。

修复 D0 消费源码的 content-addressed 不可变归档；候选日期市场读取另增加开发候选专用的精确日期产品包回退，校验当前 Head、日期、Owner 原始/核心/市场绑定、Core 同目录历史文件、PostgreSQL 历史索引 Token。该路径只允许 `DEVELOPMENT_CANDIDATE_PREVIEW`，没有跨日期或全局可变数据回退。新增市场包回归测试，与 D0 归档测试合计 5 项通过。

28766 已运行当前 checkout 的修复代码并绑定 10/21 新 Token。六个主入口均能加载候选数据。市场页面修复后能显示真实宽度、成交额、指数、涨跌停统计及涨停梯队。入口级验收仍有明确缺口：Forward 没有已发布历史研究分母；板块生命周期与个股资格仍显示来源不完整；日期切换到 10/20 后列表停留在“正在读取研究数据”，直接 API 返回的 context 仍标记 10/21。因此本轮不能把六入口、日期周期或全模块全因子验收标为通过。

## M0—M4

| 里程碑 | 结果 | 证据与限制 |
|---|---|---|
| M0 不可变 D0 源码 | **PASS** | D0 发布前按 SHA256 原子归档被消费源码字节；既有归档路径字节损坏时 fail closed。正例与损坏负例均通过。D0 reader 原有 SHA256/bytes 检查未放宽。`tests/test_d0_immutable_source_archive_r2.py` 2 项通过。 |
| M1 10/16 日期成员新候选 R8/D0 | **PASS** | 新 Token `ef87b9b4212908e56a0ba3fb315d173e18522f70e8d73f81b6d02bc18c55227f` 的 R8 于 PG `2026-10-22 14:20:06+08` 发布，随后 D0 `...:r1` 发布 5,226 行。R8 Owner Authority SHA `e274702bdb4e2c6f6eb41ef0a2725bcb6288b438894b8463a1478e3362a6bd8e`；Source Freeze SHA `840e9dcb50c6d092ef5dd819b5cb9b306d193a32dc3840a07aa3fe1b8d87ec92`。 |
| M2 顺序重建 10/19—10/21 | **PARTIAL** | predecessor 顺序和 PG R8/D0 写入均完成，Token 依次为 `e6065c7e728aa50e011e656ff9f46225339ec69220212ad6b8a4219dbd85a49f`、`906c16ca05fe185871652e001044cea06971dcd7860d73f2442980d1474e7147`、`e8094ffefe07e18e90dcbd2a0077347745269b94a9ca56d85aa8c3a512031af4`。但已发布 10/20 Core 的 `rps5_delta3` 只有 2,825 OBSERVED / 2,399 UNKNOWN；独立重算证据要求 5,202 / 24。10/21 Core 为 5,205 / 19。10/20 全链下游已绑定该不合格因子结果，故全部可计算因子和相应派生 Owner 的数值验收未通过。 |
| M3 28766 六入口实际验收 | **PARTIAL** | 28766 当前返回新 10/21 Token，状态为只读开发候选；市场页四模块显示真实数据，股票搜索、板块搜索和行业筛选成功。六入口 DOM 都已实读；Home 5,224 股/400 板块/368 Radar/Forward 缺值，Market 宽度及分母有效，Sectors 400 行但生命周期 UNKNOWN，Stocks 5,224 行但资格 UNKNOWN，Focus 3,929 行但非正式验证样本，Forward 历史分母未发布、到期 0。日期选择器能选 10/20，但列表无法退出读取状态；直接 10/20 API 返回的 context 仍为 10/21。没有把 HTTP 200 当业务验收通过。 |
| M4 故障恢复与性能 | **PARTIAL** | 内容归档篡改拒绝、D0 幂等重试及 R8/CAS 回滚前态证据可用；四日链每次 PG 发布具有精确 token、Owner Authority 和 Source Freeze。未完成 PG 写入后故障恢复、部分链恢复演练、日期混读故障演练及要求的两轮服务端性能测试。单轮 Priority 计时：生命周期 29.941ms、源 SHA 校验 61.878ms、排名/分页摘要 14.792ms，仅作观察值。 |

## Token 与 PG 读回

| 交易日 | 旧 Token | 新 Token | D0 publication | D0 rows / 真假未知 |
|---|---|---|---|---|
| 2026-10-16 | `33cf6cdb91f51592cddebb41667c22720eb68e47592d179e8dfd0b0b5b5fc440` | `ef87b9b4212908e56a0ba3fb315d173e18522f70e8d73f81b6d02bc18c55227f` | `D0B07:2026-10-16:ef87b9b4212908e56a0ba3fb315d173e18522f70e8d73f81b6d02bc18c55227f:r1` | 5,226 / 90·5,084·52 |
| 2026-10-19 | `f9c4fa37dcef3cb4d28cf2a4e6e41f448898947be9fb16240f67cfd8ee136862` | `e6065c7e728aa50e011e656ff9f46225339ec69220212ad6b8a4219dbd85a49f` | `D0B07:2026-10-19:e6065c7e728aa50e011e656ff9f46225339ec69220212ad6b8a4219dbd85a49f:r1` | 5,224 / 152·5,018·54 |
| 2026-10-20 | `dba3131d7405ab5eac4fddff2a4b3ccb1ecb76ce3c70e907fd63a68406bd9aad` | `906c16ca05fe185871652e001044cea06971dcd7860d73f2442980d1474e7147` | `D0B07:2026-10-20:906c16ca05fe185871652e001044cea06971dcd7860d73f2442980d1474e7147:r1` | 5,224 / 115·2,736·2,373 |
| 2026-10-21 | `c8b6b32f7fd578c7a6bb347320382f091c1545b01c1d70b4a9ca68b049d3c528` | `e8094ffefe07e18e90dcbd2a0077347745269b94a9ca56d85aa8c3a512031af4` | `D0B07:2026-10-21:e8094ffefe07e18e90dcbd2a0077347745269b94a9ca56d85aa8c3a512031af4:r1` | 5,224 / 99·5,076·49 |

PostgreSQL 只读读回：`market_research`，`127.0.0.1:5432`，database OID `646711`。R8 schema `v4_r8pub_fde08c597fc76d13`；D0 schema `v4_r8d0seal_batch07_r1`。每一行的完整 Authority/Freeze SHA、D0 Owner SHA 与 Predicate Digest 在配套 Evidence JSON。所有新 D0 publication 为 `DEV_ASOF_SOURCE_VERIFIED`；两项 PIT 标志为 false。PG 只读核验事务已回滚。

## 页面业务值与验收缺口

- 28766 `127.0.0.1:28766`，进程 PID 44092；唯一数据库服务 `127.0.0.1:5432`，进程 PID 8640。28765 未监听、未切换。
- 市场宽度：涨 1,935、跌 3,061、平 220、未知 8，分母 5,224；实际行情 5,216；成交额 CNY 1,429,171,847,255.75。限价状态：LIMIT_UP 50、LIMIT_DOWN 5、NOT_LIMIT 5,143、SUSPENDED 8、UNKNOWN 18；可分类分母 5,206，可交易且规则可评价分母 5,198；日线涨停梯队 50（首板 34、连板前缀未知 16）。指数五项均来自真实指数 Owner。
- Candidate Priority：股票可排名 936 / 5,224，板块可排名 8 / 400。ReadIndex：股票 5,224、板块 400、Focus 3,929、Radar 368。
- 搜索验收：股票代码 `600703` 命中三安光电 1 行；板块名 `煤炭` 命中 2 行；板块类型筛选“行业”返回 132 行。
- 日期周期验收：10/21 初始选择显示 10/21；选择 10/20 后 URL 与下拉值变成 10/20，但结果区停在“正在读取研究数据”。直接请求 10/20 的 sectors API 虽返回 200，响应 context 的 `accepted_trade_date` 仍为 10/21。此项判失败。
- 市场候选四轴仍明确显示“正式环境尚未发布”；Forward 历史候选/验证队列和结果分母无授权的正式数据。未伪造风险值、资格或 Forward 结果。

## 源码与交付

- `src/workbench_analysis/d0_source_seal_r2.py`：此前提交中的不可变源归档与发布闭包修复（HEAD `fb147663612c9c07c1ee4c61f4f89d7097c72c66`）。
- `src/workbench_service/core_product_bff_r1.py`：开发候选精确日期市场产品包读取；强制 Candidate Head、Owner、日期、PG 历史 Token 校验。
- `scripts/run_batch10_r2_d0_release.py`：保留候选 token 精确选择参数。
- `tests/test_core_product_candidate_pack_r2.py`：精确日期同目录历史绑定正例、跨日期绑定负例、正式域禁止回退负例。
- `tests/test_d0_immutable_source_archive_r2.py`：归档原字节和损坏对象 fail-closed 测试。
- 两份交付文件：本报告及 `BATCH10_R2_EXECUTION_REPAIR_EVIDENCE.json`。源码、回归测试和报告随后提交并推送至 `codex/v4-unified-development`，供 ChatGPT 独立外审。

## 复现

```powershell
$env:TMP='G:\codex_tmp'; $env:TEMP='G:\codex_tmp'; $env:TMPDIR='G:\codex_tmp'; $env:PYTHONPATH='src'
python -m pytest -q tests\test_d0_immutable_source_archive_r2.py tests\test_core_product_candidate_pack_r2.py
```

本次结果：`5 passed`。测试通过只证明源码回归行为；不改变上表 M2—M4 的业务验收结论。
