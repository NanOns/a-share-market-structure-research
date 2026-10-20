# 2026-10-20 断档日更候选链修复记录

## 阶段与边界

- 分支：`codex/v4-unified-development`。任务指定审计基线 `bc931afea2e2e49905a2550d9b982ea12bce0da1` 是当前 `HEAD` 的祖先；开始本次续作时的 `HEAD` 为 `acac3524c07d74fb0694607b6170eb2d55f26c1d`。
- 任务授权：用户已授权为 2026-10-12 至 2026-10-14 建立连续候选链及候选专用写入。此次所有新增数据均绑定候选 token，不切换正式 Head。
- 临时根目录：`G:\\codex_tmp\\v4_daily_candidate_chain_20261020`。测试临时目录均位于 `G:\\codex_tmp\\test_temp`。
- 正式 Head：候选根和仓库正式 Head 均保持 2026-10-09，文件 SHA-256 为 `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`。正式发布/生产接受状态未更改。
- 运行：只使用 `127.0.0.1:28766`；当前候选服务 PID 41680。未监听或重启 28765。数据库仍为唯一现有 `127.0.0.1:5432/market_research`，数据库 OID `646711`；未创建数据库、数据库实例或角色，未改权限、未运行生产调度。
- BaoStock 版本：`0.9.3`，Python 包路径在 `E:\\python\\Lib\\site-packages\\baostock`。凭据没有写入证据。

## 执行记录：错误、根因、处理

1. **BaoStock 日更入口。** 此前直接在未建立 SDK 会话时发起查询，服务回 `10001001`（未登录）；这不是日期数据缺失。核对旧调用和 SDK 后确认实际流程是 `bs.login()` 的默认匿名会话，再调用查询，账号/API key 不需要由用户提供。按已成功过的入口重试 10-13、10-14：`query_all_stock(day=...)` 分别读回 7,427、7,430 条；会话正常 `logout()`。公开示例也采用无参数 `bs.login()`：[BaoStock 股票资料 API](https://www.baostock.com/mainContent?file=stockBasic.md)。
2. **10-12 数值时序核对。** 发现候选引用的 `PERIOD_NUMERIC_ORACLE` 仍指向 10-09。基于实际 10-12 输入重跑并将审计文件写入原代次目录：219,408 项核对、0 错误；随后创建 metadata-bound successor candidate，未覆盖原始候选字节。
3. **10-13/10-14 来源门。** 普通 `verify_source_gate` 对新上市身份回 `WAIT_DATED_IDENTITY_AUTHORITY`。按照现役 `operational_new_listing_r1.gate_adapter` 重发两个日期的门文件，给当日可观测新上市证券 `SZ.301660` 提供日期身份事实，门状态改为 `SOURCE_READY`。来源门不是通过绕过校验获得。
4. **候选验证代码漂移。** 10-13/14 初次校验出现 `CORRECTED_INPUT_DIGEST_MISMATCH:src/workbench_service/v4_server.py`：临时根中混入后续源码而候选 registry 绑定的是 14 个冻结源码文件。逐个按候选合同恢复冻结源码，并恢复缺失的 `runtime/r1_1/revision_admission/REVISION_GATE.json`；之后候选验证器与 release policy 校验通过。原始候选 10-12/13/14 SHA-256 分别为 `ce17a6c32550dd0f4b20ac9fd0809a9e5374669c997f135e0621094a265b4e95`、`033c35d52dfc295273b660897f6683af84e87737a03fe09221b9faef9706de18`、`121242574c6ab087885880bb8711be6c39ca3d6956e7e3c018dbb9406bf3223e`，均保持原样。
5. **10-12 Radar 优先级 400。** 10-12 到 10-14 的 R2 列表索引已在 PG，但候选 token `914092...` 没有研究优先级 Owner；接口报 `RESEARCH_PRIORITY_BINDING_MISSING`。用已绑定的股票/行业 Owner、现有参数配置和现役 `build_priority` 逐日生成 PG 优先级 Owner；每个 Owner 写入后立即读回并比较绑定及完整 payload。10-12/13/14 股票排序可读，HTTP 均为 200/READY。
6. **Forward 统计/结算接口异常。** `ForwardR7Store` 通过正式 Head 日期发现 `forward_facts` 时发现两个既有 schema 都包含 10-09，返回 `EXISTING_FORWARD_FACTS_NAMESPACE_NOT_UNIQUELY_BOUND`。两个既有 schema 为 `v4_forward_1eab1e832f0f04d0`（160 条）和 `v4_forward_812843566da3f180`（112 条）；旧解析逻辑拒绝猜选。按项目 R8 隔离合同，选择与候选 Owner workspace 对应的前者作为只读基线，复制 160 条事实到候选根专属 `v4_r8_forward_0c2b84fb3e1a0c42`，保留 identity ordinal、索引/约束并在副本安装 append-only trigger。复制前、复制后源和候选副本均为 160 条，按 `(kind,fact_key,payload_sha256,source_sha256)` 排序摘要均为 `a74245e2596b20d6e5a195d27772441bdea36e0c0b2e1add341eae044e4def33`。写入 `R8_FORWARD_BASELINE_COPY_RECEIPT.json` 及 `config/r8_forward_candidate_namespace_r1.json`，Forward 读路径随后按该 receipt 校验并锁定隔离 schema。修复后 Forward statistics 为 `READY`，candidate late observation 为 `CANDIDATE_ONLY_LATE_OBSERVED`（`PIT_ELIGIBLE=false`）；历史 observation/settlement 无记录时返回 `EMPTY_VALID`、0 行，不再返回 PG 错误。
7. **Forward plans 的实际语义。** `/api/v4/forward/plans` 返回 `SOURCE_INCOMPLETE / NO_AUTHORIZED_COHORT_OWNER`，缺少第一批 capture signal producer、已接受 cohort Owner 和显式读授权。没有伪造 cohort 或 outcome；这是当前授权范围外的验收输入缺口。UI/统计及结算读取错误已修复。
8. **前端 rotation 模块与版本错配。** static asset allowlist 缺少 `rotation-auto-acceptance.js`；并且服务端先从 joint authority 读出候选 `app.js/api.js/components.js`，之后又只把这三个文件替换为旧 R43 compatibility 版本，形成混合 UI build，旧 `app.js` 不导入 rotation module。修改服务端为 joint release 存在时完整按绑定 bundle 读取；添加 rotation 模块 allowlist，并让候选 UI refresh 清单包含该模块。候选 UI refresh 官方流程发现 joint 绑定的 `data/v4/research_snapshots/3a3f5d9074b646189ccfd830c15e7161/manifest.json` 在源仓库和候选根都不存在，因此没有运行 activation，也没有改正式 Head；只在候选根重建内容寻址 UI bundle `a346e86267a82d9795d8528db806bc66e2f1bcc37b448aa5c7242b6ffa9f7fe0`。修复服务资源优先级后，28766 实际返回的 8 个资产逐个和候选 bundle SHA/字节数完全一致。
9. **定向测试环境第一次失败。** 未向 pytest 进程加载项目已有 `.env` 时，4 个依赖 PG DSN 的测试失败于 `V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK`，没有触及测试断言或 DB。为不创建测试 schema、不给现有库增加测试副作用，改跑不依赖 DB 写入的服务/UI、候选 descriptor、R8 namespace 测试：11 passed，4 个需 DB 的测试 deselected。测试 `basetemp` 全部在 G 盘。

## 连续日结果

| 日期 | BaoStock all-stock | 原始股票条数 | 股票 Owner | 行业/板块 | Focus | Radar | Priority 股票 | D0 / PREWATCH / D2 fresh | PERIOD oracle |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2026-10-12 | 延续已成功源采集 | 5,212 | 5,224 | 400 | 3,025 | 311 | 1,752 | 164 / 646 / 92 | PASS，219,408 项，0 错误 |
| 2026-10-13 | 7,427 | 5,212 | 5,225 | 400 | 3,151 | 163 | 1,410 | 180 / 480 / 104 | PASS，219,436 项，0 错误 |
| 2026-10-14 | 7,430 | 5,214 | 5,225 | 400 | 3,247 | 177 | 967 | 145 / 397 / 65 | PASS，219,436 项，0 错误 |

三日候选 token 分别为 `c60294526a43085aa3777fc84c198a4104c528f5300b8981fcf493b12bef44b7`、`5dadf2426bf4b758e8f33c00e2b054328e8cd1fc613632d6749ffac41c98d48f`、`91409211777997a2e95933fb2aeb075a212716d6cbd455778fef23db4eabd721`。三日候选与 release policy 均校验通过；股票数值核心错误为 0。10-13/14 行业候选各 400 条。上述结果为候选预览，不构成正式 Head 接受或历史 PIT 证明。

## 配置与 schema 清单

### 使用的配置

- 现有 `config/.env`：进程内读取 `WORKBENCH_PG_DSN`、`V4_NATIVE_PG_DSN`、`V4_NATIVE_PG_READER_DSN`，只连 `127.0.0.1:5432/market_research`；密码/DSN 不入日志或证据文件。未新建连接凭据文件。
- 现有 `config/v4_daily_research_priority_r1.json`：SHA-256 `2333a66f7fa3fd285a4ddf8aef9f7726ba3d04aeb3a3a623182dd2ec3d2f1985`。
- 候选根新增 `config/r8_forward_candidate_namespace_r1.json`：SHA-256 `cf3b8bf4fb6e21e7ebdbf9c565b63c06072dac35c76e4bb2aef7bd18e6d123f5`，scope=`CANDIDATE_ONLY`，绑定 R8 副本与回执。
- 候选根新增/更新 `data/v4/research_priority_authority_r1.json`：包含 token `914092...` 的 10-12/13/14 三个不可变 Owner binding；文件 SHA-256 `4d0042c9857e70c9482fbaaa40f7e1e4fb29cfffb920f2f0b95531207cbe6a3c`。
- 候选根 `config/v4_read_index_authority_r2.json`：包含该 token 的三日绑定，文件 SHA-256 `f0ec5db17d060efbda430a55520ef25dcf80341fe58e63d907694312d5e1e2b4`。
- 候选根 `config/v4_joint_release_authority_v1.json` 的 UI asset map 已更新为候选 build；SHA-256 `e3fee2907424c78a9d68acc9f69ea521baa618e1763f80a4cf7777ac72f31490`。缺少其 15 MB research snapshot manifest，所以未执行 joint activation；正式 authority/head 未变。

### PostgreSQL schemas

全部 schemas 均在既有 `market_research` 数据库内；除基线来源外，为当前候选的新增、隔离、不可变数据。schema 不建新数据库实例。

| 用途/日期 | schema | 数据量或读回计数 |
|---|---|---:|
| 10-12 日线候选 series | `v4_research_fd2ef70117d1e9f87a8a92f1` | 31,265 bars |
| 10-13 日线候选 series | `v4_research_40a35fa59494bfb8bb970d58` | 36,477 bars |
| 10-14 日线候选 series | `v4_research_13dd9d4fc1ca96e720d2a00e` | 41,691 bars |
| 10-12 R2 read index | `v4_909aa7f00f88fc2b894facebfec8bc0ec1507c016bc11e3401542a56` | stocks 5,224 / sectors 400 / focus 3,025 / radar 311 |
| 10-13 R2 read index | `v4_2aba60621019002fc7f5b2cd13509fdf4a841de7554ca24103f069bd` | stocks 5,225 / sectors 400 / focus 3,151 / radar 163 |
| 10-14 R2 read index | `v4_2c5a277ce8f846e3de7d0d396b678d897c89a30b2ab40d14381d76bd` | stocks 5,225 / sectors 400 / focus 3,247 / radar 177 |
| 10-12 priority owner | `v4_e9d16a7c4e621a6fe5946f3d1f849a1a0ab54b7fb0c0738c42255375` | stocks rankable 1,752; sectors rankable 0 |
| 10-13 priority owner | `v4_5869198625dbebd780c6bb9004a293c1b2dd2a70269218f07c58d635` | stocks rankable 1,410; sectors rankable 0 |
| 10-14 priority owner | `v4_f6212ca8b75a552619f071364ede69115dee7035fee25b5c213759c5` | stocks rankable 967; sectors rankable 0 |
| R8 isolated Forward candidate | `v4_r8_forward_0c2b84fb3e1a0c42` | baseline 160 facts, source/copy digest match |

既有 Forward schema `v4_forward_1eab1e832f0f04d0` 是 R8 基线来源（复制前后未变）；既有冲突 schema `v4_forward_812843566da3f180` 未修改。Forward `v4_forward_1eab1e832f0f04d0` 原有 append-only source 事实没有覆盖/删除。没有新建 `operational_risk` owner schema。

## 28766 与验收

- 28766 重启前明确核对旧 PID `41404` 对应本次临时预览脚本；停止该开发服务后，以最新源码重新启动，PID `41680`。HTTP `/api/operations/status` 为 200/READY/CANDIDATE_ONLY，当前候选日 10-14、formal Head 10-09。
- `/v4/research/forward` 返回 200；`app.js`、`api.js`、`components.js`、`labels.js`、`stock.js`、`replay.js`、`rotation-auto-acceptance.js`、`style.css` 全部 200 且与候选 build SHA 匹配。
- 10-12/13/14 的 stocks、sectors、focus、radar、radar priority、forward statistics 均返回 200/READY；历史 settlement/observations 返回 `EMPTY_VALID`/0 行；candidate late observation 返回 `CANDIDATE_ONLY_LATE_OBSERVED`。
- 端口复核：只见 PostgreSQL 5432 由 PID 8640 监听及开发服务 `127.0.0.1:28766` 由 PID 41680 监听；28765 无监听。开发预览继续运行以供当前浏览器检查。
- 目标测试：`tests/test_fp04_ui_authority.py`、候选 schema binding 回归、`tests/test_r8_forward_namespace.py` 相关用例：**11 passed, 4 deselected**。`git diff --check` 通过。

## 本次代码改动与后续

- `src/workbench_service/v4_server.py`：joint release 存在时不再将已绑定 build 中的三个入口 JS 单独换成 R43 compatibility 版本；显式开放轮动 acceptance module。
- `scripts/v4_closeout_refresh_candidate_ui.py`：把 `rotation-auto-acceptance.js` 纳入候选 UI 内容寻址 bundle。
- `src/workbench_db/v4_forward_pg_r1.py`：本地 PG descriptor 文件名加 schema namespace，避免候选和 predecessor 对同一 fact key 争写同一描述符。
- 新增的 28766 入口版本回归测试和 descriptor regression test 随本记录提交。
- 下一步：如果要把候选 UI 完成 joint release 激活，需要先补回与 authority 绑定的 `data/v4/research_snapshots/3a3f5d9074b646189ccfd830c15e7161/manifest.json` 及其绑定产物；如果要发布 Forward plans，需要按合同授权 capture signal producer 与 validation cohort Owner。此二项不影响本次候选读回与 UI API 的 READY。
- 本记录不代表候选已正式发布；也不授权 PG 全面迁移、生产 Head 更新、28765、生产调度或任何 destructive cleanup。
