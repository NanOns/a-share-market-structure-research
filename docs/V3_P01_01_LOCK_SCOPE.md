# V3 P01-01 数据库锁作用域阶段报告

## 阶段合同

| 字段 | 值 |
|---|---|
| task_id | P01-01 |
| 输入代码版本 | `3f6f664`（P00-03 合同冻结） |
| 适用主实施文档 | `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，当前工作区版本 |
| 主实施文档 SHA-256 | `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24` |
| 目标 | 缩短数据库锁作用域，避免在线热榜等待阻塞本地只读请求 |
| 范围 | `app.py::request_scope`、`do_GET`、`Api.hot_rankings`、响应发送异常处理 |
| 不在范围 | 热榜分页/总数语义、单源失败策略、V3 scanner、数据库 schema、TDX 输入 |

本阶段没有发现 V3 文档与现有代码之间的阻断性歧义。P01-01 的“短本地读→网络→短批量补字段”可直接落到现有 `/api/hot-rankings` 路由；P01-02 的分页和单源失败问题保持独立，不提前改动。

## 当前 GET 区段

| 区段 | P01-01 前 | P01-01 后 |
|---|---|---|
| 本地读 | `do_GET` 进入 `request_scope`，`Api.hot_rankings` 查询最新 publication | 热榜路由先在 `Api.hot_rankings` 内做一次短 `publications()` 读，使用 `_con` 的既有连接生命周期保护 |
| 网络等待 | 热榜源抓取、远程行情补全在同一个请求级 `RLock` 内 | `/api/hot-rankings` 不进入请求级 `request_scope`；源抓取和行情补全在无数据库锁区段运行，仍使用既有有界策略 |
| 补字段 | 远程等待前后均可能通过 `name_lookup` 触发数据库读 | 网络完成后收集全部返回行的 security_id，一次 `_security_names` 批量短读，再回填本地名称 |

### 并发规则

- 其他只读 GET 路由继续使用 `request_scope`，复用一个请求连接并保留 `_db_lock` 的连接生命周期串行化规则。
- 热榜 GET 只让两个本地读区段进入 `_con`；网络等待不持有 API 数据库锁。
- POST 写任务原有入口不进入 `request_scope`，继续由发布、历史任务、运维服务各自的既有锁/任务状态协调；本阶段没有扩大或重写写任务并发规则。
- `request_scope` 和 `_con` 的 `finally` 关闭连接逻辑未删除；客户端断开时 `_send` 设置 `close_connection=True` 并静默结束响应写入，避免二次发送异常。

## 有界等待与异常边界

- `OnlineFetchPolicy` 仍限制在线请求超时不超过 30 秒；当前热榜直连默认 15 秒、零重试、响应体上限 1,000,000 字节。
- Eastmoney 解码子进程继续使用 5 秒超时。
- 热榜源抓取异常沿现有 GET 错误处理返回失败；行情补全异常沿现有 direct-ephemeral 路径降级为 `quote: null` 和 `UNAVAILABLE:*`，不写入本地快照。
- `BrokenPipeError`、`ConnectionAbortedError`、`ConnectionResetError`、`TimeoutError` 在响应写入处被视为客户端断开，标记连接关闭，不再尝试发送第二个错误响应。

## 证据与验收

### 代码与回归证据

- `tests/upgrade_v3/test_p01_01_lock_scope.py`：3 passed；覆盖热榜路由跳过请求级锁、外部模拟 8 秒等待期间短本地读不被阻塞、客户端断开关闭连接。
- `tests/upgrade_v3/test_p00_03_contracts.py` 与 `tests/upgrade_m14/test_hot_rank_api.py`：合计 8 passed，确认 P00-03 合同和热榜 ephemeral 输出未回归。
- `python -m py_compile src/workbench_service/app.py`：通过。
- `git diff --check`：通过。

### 慢源期间本地请求测量

回归测试注入一个最长 8 秒等待的 direct response，并在等待期间通过同一 `Api` 执行本地 publication 读；断言本地读耗时 `<0.5s`，且远程线程仍在等待。该证据验证的是锁释放边界，不把测试通过本身当作完整发布就绪证明。

### 阶段验收结论

**PASS。** P01-01 的锁作用域已缩短，普通本地只读路由保持原连接生命周期规则，热榜网络阶段不再持有数据库锁，响应写入对客户端断开 fail-closed。未访问或修改 TDX 输入，未写数据库，未持久化热榜 payload、行、批次或历史快照。

下一阶段：**P01-02 修复热榜分页与单源失败语义**。其验收必须单独确认 `total`、`ALL`/单源失败、`cache:false` 和零持久化边界。

## 独立未决项

- `tests/upgrade_m15/test_performance.py::test_assets_are_versioned_for_m15_03` 在当前工作区仍要求 `m15-03`，而资源已是 `m15-04`；本阶段未修改该既有 M15 资源或测试，单独跟踪。
- P00-03 已记录的 HOT_RANKINGS V3 capability P09-01 复核仍未提前完成；本阶段仅维护旧 direct-ephemeral 路由边界。
