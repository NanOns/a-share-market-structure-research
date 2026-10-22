# BATCH10-R2 执行与源码修复报告

- 执行日期：2026-10-22（Asia/Shanghai）
- 仓库 / 分支：`NanOns/a-share-market-structure-research` / `codex/v4-unified-development`
- 用户指定审计基线：`00e4a34c64d2767f8b9f9ebc6efb7c7f7b50aeb3`
- 执行前已核对本地及远端最新 HEAD：`743cd73d7442fdb5f50d43f5625cae84ef53d7cb`（与 origin 一致）
- 结果：`BATCH10_R2_PARTIAL`；M0、M1 通过，M2、M3、M4 部分通过。
- 阶段 0：`DEGRADED_PASS`。四日历史均保留 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`；只写开发 PG 和 Candidate Head；正式 Head、28765 均未更改。

## 执行摘要

已在指定开发分支修复 RPS delta 的端点横截面排序坐标：构建目标日期时，针对 t-1 与 t-3 端点使用目标日期 QFQ 坐标计算 Core return，并按各端点当日精确成员集分别排名；将实际消费的 `r43_owner_replay.py` 源码 SHA 纳入 Owner generation key。日期成员缓存已存在时，候选重建直接读取有日期的缓存，不为读取归档缓存触发 BaoStock 登录；缓存缺失时仍只对缺失日期发起有界请求并 fail closed。

10/16 新候选 R8/D0 发布成功；随后按 predecessor 顺序完成 10/19、10/20、10/21 Owner 全链重算及 R8/D0 开发 PG 发布。Oracle 对三个重建日期分别通过 292,516 项核验，零错误。限制读角色对四个日期的 D0 独立 PG 回读均为 `PG_BINDING_PRESENT`、`permission_chain_proven=true`、事务只读且 fact digest PASS。

10/21 新 Token 的 28766 Candidate Preview 已运行。Home、Stocks、Sectors、Focus、Forward 与 Priority API 可读；股票/板块搜索与行业筛选有实际结果。尚未达到“页面完整整链验收”：市场四 API 因 `CANDIDATE_PRODUCT_HEAD_BINDING_MISMATCH` 返回 400；10/19 ReadIndex 缺少候选绑定；10/20 日期请求返回的行是 10/20，但上下文仍指向 10/21 Token；浏览器可见页面验收被 Computer Use Windows URL 安全检查中止，因此没有 DOM/截图证据。不得将以上项目记为通过。

## 新旧 Token 与开发 PG 发布

| 日期 | 旧 Token | 新 Token | 前序新 Token | R8 / D0 |
|---|---|---|---|---|
| 10/16 | `33cf6cdb91f51592cddebb41667c22720eb68e47592d179e8dfd0b0b5b5fc440` | `57b1ce6b0d1610d38c03be90b8363cc338d2775dc23ab55fd9e65c58ed5e1bcc` | 10/15 `c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47` | 两者已发布开发 PG；D0 5,226 行 |
| 10/19 | `f9c4fa37dcef3cb4d28cf2a4e6e41f448898947be9fb16240f67cfd8ee136862` | `daeb6ed118605b9e1e0ed057e95ca6b84a6f2e4c25154bb71fbc70f42268a0ac` | `57b1ce6b0d1610d38c03be90b8363cc338d2775dc23ab55fd9e65c58ed5e1bcc` | 两者已发布开发 PG；D0 5,224 行 |
| 10/20 | `dba3131d7405ab5eac4fddff2a4b3ccb1ecb76ce3c70e907fd63a68406bd9aad` | `dfc64db19c5f132197d40cfa363e850fd61518a01a75325a2d088338681a5e8c` | `daeb6ed118605b9e1e0ed057e95ca6b84a6f2e4c25154bb71fbc70f42268a0ac` | 两者已发布开发 PG；D0 5,224 行 |
| 10/21 | `c8b6b32f7fd578c7a6bb347320382f091c1545b01c1d70b4a9ca68b049d3c528` | `d778e5e80eb47a52b45942d43cafe189f2757b9492d11e38b5cf08a103f368a5` | `dfc64db19c5f132197d40cfa363e850fd61518a01a75325a2d088338681a5e8c` | 两者已发布开发 PG；D0 5,224 行 |

四日 D0 publication 均为 `DEV_ASOF_SOURCE_VERIFIED`，且 `as_recorded=false`、`pit_eligible=false`、`production_admission=false`。限制 reader 对 D0 fact 读回行数依次为 10,452、10,448、10,448、10,448，摘要均 PASS。完整 owner SHA、predicate digest、PG reader 角色与只读标记见随附 JSON。

## M0—M4

| 里程碑 | 结果 | 执行证据与未完成项 |
|---|---|---|
| M0 不可变 D0 源码版本绑定 | **PASS** | 已提交基线实现将消费源码原字节原子归档到 content-addressed SHA 路径；摘要碰撞/损坏时 fail closed，reader SHA 与 bytes 检查未放宽。`tests/test_d0_immutable_source_archive_r2.py` 覆盖正例与损坏负例。 |
| M1 10/16 日期成员修复与 R8/D0 | **PASS** | 10/16 新 Token `57b1…e1bcc` 的 R8 与 D0 在开发 PG 发布；D0 5,226 行，TRUE 90 / FALSE 5,084 / UNKNOWN 52。独立限制 reader 回读 10,452 facts，digest PASS。 |
| M2 前态顺序重建 10/19—10/21 | **PARTIAL** | 三日 Owner/Core/可计算因子/Profile/Market/Sector/D0/D2/Focus/Forward 与 R8/D0 发布均执行；三个日期的数值 oracle 分别 292,516 checks、0 errors；10/20、10/21 ReadIndex 与 Priority 已生成（10/21 Priority 股票 936/5,224、板块 8/400 可排名）。10/19 ReadIndex 因版本内缺少 `native_membership_reference`，返回 `NATIVE_IDENTITY_REFERENCE_REQUIRED_NO_FALLBACK`；不能在不改变 Token 的情况下补写候选绑定，因此 M2 不能全通过。 |
| M3 28766 同版本六入口业务验收 | **PARTIAL** | 服务 Preview Token 为 `d778…368a5`；Context/Home/Stocks(5,224)/Sectors(400)/Focus(3,929)/Forward/Priority API 响应 Token 一致。搜索 600703 返回 1 项，煤炭搜索返回 2 项，`type=INDUSTRY` 返回 132 项。Forward 历史与 live 均 0 项，Home 标记 `DATA_MISSING`。市场 breadth/indices/limits/ladders 四 API 全返回 `CANDIDATE_PRODUCT_HEAD_BINDING_MISMATCH`；10/20 行读取虽为 10/20，响应上下文仍是 10/21 Token。没有完成用户要求的六入口页面可见验收、日期周期交互验收和完整市场页面数值验收。 |
| M4 独立发布与恢复演练 | **PARTIAL** | 四日 D0 限制 reader 独立读回全部 PASS；R8/D0 发布及 G1-G3/CAS rollback 演练已记录通过；10 项针对性 pytest 通过。post-insert 故障注入、完整部分链恢复、混合日期拒绝演练、双轮服务性能验收及可见浏览器页面验收未完成。 |

## 服务、数据库与保护边界

- 28766：`127.0.0.1:28766`，Candidate Preview，Token `d778…368a5`，接受日期 2026-10-21，正式接受标记 false。
- 28765：未监听；没有停止或重启生产服务。
- PostgreSQL：`127.0.0.1:5432/market_research`，OID 646711；独立 D0 查询以受限 reader role、`transaction_read_only=on` 执行。
- R8 schema：`v4_r8pub_fde08c597fc76d13`；D0 schema：`v4_r8d0seal_batch07_r1`。
- 未修改正式 Head，未改写历史 NON_PIT 身份；无 DROP/DELETE。
- Computer Use 在获取当前 Windows 浏览器 URL 时因安全置信检查失败而停止；停止后未继续桌面 UI 操作。API 读回不等同于可见页面验收。

## 源码、测试与复现

- `src/workbench_analysis/r43_owner_replay.py`：目标日期 QFQ 坐标下重算 RPS delta 的精确端点横截面。
- `src/workbench_analysis/operational_daily_owner_v1.py`：Owner generation key 纳入实际 Core producer；缓存日期齐全时不触发不必要的 provider 登录。
- 回归命令：`$env:TMP='G:\codex_tmp'; $env:TEMP='G:\codex_tmp'; $env:TMPDIR='G:\codex_tmp'; $env:PYTHONPATH='src'; python -m pytest -q tests\test_d0_immutable_source_archive_r2.py tests\test_core_product_candidate_pack_r2.py tests\test_v4_exact_policy_immutable_binding.py tests\test_operational_runtime_acceptance_v2.py`
- 本次结果：`10 passed in 1.09s`；`git diff --check` 通过。
- API、PG 限制 reader、端口、Token、hash 与保留边界的机器可读明细见 `BATCH10_R2_EXECUTION_REPAIR_EVIDENCE.json`。
