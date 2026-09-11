# V3 P01-02 热榜分页与单源失败阶段报告

## 阶段合同

| 字段 | 值 |
|---|---|
| task_id | P01-02 |
| 输入代码版本 | `bc5882b`（P01-01 锁作用域完成） |
| 适用主实施文档 | `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，当前工作区版本 |
| 主实施文档 SHA-256 | `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24` |
| 在线总预算 | 12 秒（主实施文档 §15；测试通过 monkeypatch 缩短等待） |
| 目标 | 先确定热榜本页，再补本页行情；源独立并发、独立失败；修正 total |
| 范围 | `online_hot_rank.py`、Eastmoney/THS adapter 元数据、direct API 回归 |
| 不在范围 | `/api/v3` 新路由、V3 scanner、研究选择、数据库 schema、TDX 输入、前端 cache 机制改造 |

本阶段没有发现阻断性文档冲突。主实施文档同时给出了 §11.6 的热榜语义、§10.1 的子结果状态、§15 的 12 秒在线预算和 P01-02 的四项步骤；因此在现有 `/api/hot-rankings` direct-ephemeral 合同上修复行为，不把本阶段扩展成 V3 新 API 路由迁移。

## 实施边界

### 分页与总数

- adapter 明确返回 `upstream_paged`、`upstream_total`、`upstream_has_more` 元数据。
- Eastmoney 继续按其 `page` 规则取上游页；当前没有已验证的真实总数，`upstream_total` 和 `total` 返回 `NULL`，不伪造总数。
- THS 当前 adapter 返回完整集合，使用完整集合长度作为 `upstream_total/total`，再执行本地分页。
- 上游已经分页的结果只做本页大小截取，不再次按 `(page-1)*page_size` 偏移；完整集合才执行本地页偏移。
- 行情补全和本地名称补全只接收最终本页行，避免把整页或全量结果拉入远程行情请求。

成功页额外返回 `returned_count`、`has_more`、`upstream_total`；未知值为 `NULL`。旧字段 `total` 保留但不再取当前页长度。

### 多源并发与失败

- `ALL`/co-listed 的多个来源通过独立 future 并发执行，保持输出顺序为来源注册顺序。
- 单源成功返回 `status=READY`；单源异常或总预算耗尽返回该来源 `status=UNAVAILABLE`、`error_code`、空 `items`，不抛出覆盖其他来源。
- 多源结果顶层状态为全成功 `READY`、部分成功 `PARTIAL` 或全失败 `UNAVAILABLE`。单源请求也返回本来源状态，不把失败伪装成空成功。
- 总等待上限按主实施文档 §15 使用 12 秒；超时 future 被取消（若尚在运行则不等待其完成），响应不携带远程响应正文。

### 边界保留

- `cache:false` 前端请求合同未改动。
- `storage_scope=EPHEMERAL_ONLINE`、`local_snapshot_mutated=false` 保留；未新增 raw、行、batch 或历史快照写入。
- P01-01 的数据库锁隔离边界继续成立；本阶段没有重新把网络等待放回 `request_scope`。

## 证据与验收

### 合成回归

- `tests/upgrade_v3/test_p01_02_hot_rank.py`：5 passed，覆盖：
  - 100 条第 2 页 20 条时 `total=100`，且报价请求只含 20 条本页证券；
  - 上游第 2 页不被二次偏移；未知总数为 `NULL`；
  - A 源失败时 B 源仍显示并返回 `PARTIAL`；
  - 多源确实并发提交；
  - 总超时返回各来源 `UNAVAILABLE`，不等待完整 15 秒单源预算。
- `tests/upgrade_m14/test_hot_rank_api.py` 与 `tests/upgrade_m14/test_online_batches.py`：7 passed，既有 direct-ephemeral、映射、来源解码回归通过。
- 未修改既有测试预期以掩盖问题。

### 静态和契约证据

- `src/workbench_service/static/v2/api.js` 的 `hotRankings` 仍显式使用 `cache:false`。
- `m14_runtime_capabilities_v1.json` 的热榜持久化禁用门仍为 `persist_payload=false`、`persist_rows=false`、`persist_batches=false`。
- `python -m py_compile` 覆盖三个改动模块；`git diff --check` 通过。
- 未访问或修改 `D:/new_tdx`、配置的 TDX 源目录或数据库；本阶段只读 capability 文件，未产生热榜持久化文件。

### 阶段验收结论

**PASS。** P01-02 已完成“上游分页/本地分页区分、先页后报价、真实/未知 total、独立并发和总超时、单源失败隔离、cache:false、零持久化”合同。下一阶段进入 **P01-03 修证据弹窗和返回路径**。

## 独立未决项

- 当前工作区既有 `tests/upgrade_m15/test_performance.py` 仍要求资源版本 `m15-03`，而 `index.html` 已是 `m15-04`；本阶段不修改该范围。
- HOT_RANKINGS V3 capability 的长期 P09-01 复核仍按 P00-03 记录保留；P01-02 只维护现有 personal-research direct-ephemeral 能力。
