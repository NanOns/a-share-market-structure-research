# V3 P00–P04 源码与产物复审（2026-09-12）

## 审计结论

本次以 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` 当前 SHA-256
`3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851` 为最高执行依据。
旧 M0–M15 合同仅在 V3 明确保留兼容语义或作为 V3 基线证据时采信。

总体验收：**BLOCKED**。

- P00–P03：`PASS（证据保留并经当前工作树/生产库只读复核）`。
- P04-01：`PASS`，规划器的 R19-02～04 反例与 fail-closed 规则已有测试覆盖。
- P04-02：`BLOCKED`。当前正式 daily 调用链没有让 V3 build plan 控制旧构建器的计算和写入，不能满足 §18.7“计划真正控制写入”和 G04“重复运行不扩大业务数据”。
- P04-03：`PASS（当前源包、缓存预算、备份链范围）`。

在 P04-02 阻塞项关闭前，不应进入 P05，也不应继续使用“P00–P04 全部 FULL_PASS”作为当前状态。

## 审计范围与方法

- 读取最新 V3 主规格 §17～§20、实施台账、P00–P04 阶段报告、缺陷闭环报告。
- 静态核查 P00–P04 相关配置、schema、迁移、关系 resolver、结果对象、规划器、增量 writer、daily 入口、旧 M8/M9 构建器及 `run_today` 调用顺序。
- 只读查询 `data/database/market_research.duckdb` 的关系、结果对象、source catalog、backup catalog 与 publication binding 状态。
- 复跑 `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`、`python -m compileall -q src scripts` 与 `git diff --check`。
- 未访问或修改 `D:/new_tdx`，未运行生产 daily，未写生产数据库，未执行备份、恢复或删除。

## 阶段核对

| 阶段 | 当前结论 | 关键证据 | 边界 |
|---|---|---|---|
| P00 | PASS | 当前配置/schema/校验器和合成夹具存在；V3 主规格 hash 与后续收口记录一致；非法日期、无时区 timestamp、NaN/Infinity 等回归通过 | 早期容量数字是历史基线，不作为当前容量事实 |
| P01 | PASS（原范围） | 锁作用域、热榜分页/单源失败、证据 modal 回归均在 175 项回归中通过 | 新 V3 页面和新增在线路由仍须按 P08/P09 重新验收，不能由 P01 代替 |
| P02 | PASS | 当前生产库只读值：`relation_revisions=4`、`relation_observations=7`、`relation_snapshot_bindings=6`、`relation_publication_bindings=1`；resolver/source_scope 回归通过 | 旧 `membership_entries=435472` 作为历史兼容基线保留，不等于仍允许新全量双写 |
| P03 | PASS | 当前生产库 `analysis_result_objects=51`、`analysis_slice_result_bindings=154`；六域对象数与台账一致，兼容视图已查域的 unbound fallback 为 0 | 旧表保留属于兼容/待 P11 回收，不影响本阶段通过 |
| P04-01 | PASS | RET60 `d+60`、空成员/缺映射、价格/复权闭包、未知参数域 fail-closed 测试通过 | 规划正确不等于生产入口已受规划控制 |
| P04-02 | BLOCKED | `app.py::run_today` 先完整执行 `scripts/build_m8_m9_preview.py`，之后才执行 `run_v3_daily_entry()`；旧构建器仍遍历 `frames` 的所有 domain/date 并写 slice/result | V3 后置入口只重算 technical、复用旧构建已生成的其他域，不能证明先止住旧全量计算/写入 |
| P04-03 | PASS | 当前报告显示 source bundle 5/5、`source_files=32`、cache 44.46%、backup catalog 12/12 完整、孤立项 0；保护/删除边界明确 | 只证明源包、缓存与备份链治理，不可替代 P04-02 |

## 阻塞项 A-P04-02-01：增量入口位于旧全量构建之后

### 事实证据

1. `src/workbench_service/app.py::run_today` 在调用 V3 入口前，无条件以子进程执行 `scripts/build_m8_m9_preview.py`。
2. `scripts/build_m8_m9_preview.py` 仍为 `frames` 中每个 domain 拆分全部交易日，并逐日创建 slice、调用各域 writer、写 snapshot entry，最后绑定 publication。
3. `src/workbench_service/v3_daily_entry.py` 的模块合同也明确写明：旧 daily job 先产生已绑定分析切片，V3 再计算 technical 并复用其他目标域。
4. 因此 V3 plan 没有控制前置旧构建器；即使后置 V3 对同一 result object 去重，旧构建的全量计算、slice 身份写入和非共享域写入仍已发生。

### 与最新 V3 的冲突

- §18.7 P04-02 要求“构建器只执行 build_plan 中的对象”“计划必须真正控制写入”。
- G04 要求重复运行不扩大业务数据，并从根源停止每日旧历史重算。
- §20 C20-16 要求生产调用、失效范围、复用和绑定全链，而不是在旧全量构建完成后追加一个 V3 binding。

### 验收要求

P04-02 只有在以下证据全部成立后才可恢复为 PASS：

1. `run_today` 的正式分析路径由已验证 build plan 驱动；旧兼容产物作为显式 executor/adapter 参与，不得先无条件执行全量构建。
2. 新日、同输入重跑、历史单证券修订、关系变化四类真实副本运行分别记录：计划任务、实际计算、复用、业务事实新增、slice/日志新增和物理增长。
3. 同输入重跑不仅 `result_rows` 新增为 0，旧构建器也不得再次产生整窗计算与整窗 slice 身份。
4. 失败不得替换 publication binding；旧接口仍可读到完整兼容结果。
5. 在仓库内保留可复核的 `reports/v3/daily/*.plan.json` 和 `*.report.json`，或等价的版本化、带 hash 的真实副本证据。

## 证据一致性问题 A-P04-02-02

`docs/V3_P04_02_INTEGRATION.md` 自身将结论限定为 `PASS（SCOPED）`，并明确未执行生产 daily；但实施台账后续把 P00–P04-02 提升为 `FULL_PASS`，且 P04-03 收口后直接指向 P05。当前仓库不存在 `reports/v3/daily` 目录，文档中三次真实副本运行的 plan/report 原始产物无法在仓库内复核。

处置：阶段报告和历史台账原文保留以便追溯；以本复审的 `BLOCKED` 状态覆盖当前放行判断。该问题与 A-P04-02-01 同属 P04-02，但证据完整性单独验收。

## 本轮验证结果

- `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：`175 passed in 50.54s`。
- `python -m compileall -q src scripts`：PASS。
- `git diff --check`：PASS。
- 当前生产库只读核对：result objects 51；source bundles 5；source files 32；backup catalog 12。

这些结果证明已覆盖实现没有触发当前测试失败，但不消除调用顺序造成的 P04-02 合同违背。

## 下一阶段

下一任务固定为：**P04-02-REMEDIATION**。

在其通过前：不启动 P05，不运行新的 scanner，不把 P04-03 的通过扩张为整个 P04 通过。

## P04-02-REMEDIATION 复验追加（2026-09-12）

上述 A-P04-02-01 与 A-P04-02-02 已完成代码修复和证据链补强，原 `BLOCKED` 为历史审计结论；当前更新为：**FULL_PASS（代码与非生产验证范围）**。

1. `app.py::run_today` 不再先跑完整旧构建器、再跑第二个 V3 入口；正式分析阶段只启动一次 `build_m8_m9_preview.py --incremental-current`。
2. 增量模式只传入当前交易日，并把 membership 收窄到当前日。真实项目输入只读计算得到 technical/strength/high 各 6,178 行、structure 27,300 行、summary 5,460 行，其余有结果的域也只输出当前日。
3. 新快照只写当前日切片，同时引用前一绑定快照中未被替换的历史切片；不为新日重写旧日 slice 身份或旧日结果。
4. 同输入命中已有 snapshot 时，仍为最新成功 publication 原子更新 binding，避免幂等短路造成新 publication 无分析绑定。
5. 正式增量运行原子生成 `reports/v3/daily/{cutoff}.plan.json` 和 `.report.json`，记录逐域日期、行数及 `full_window_rebuild=false`。

新增回归覆盖单一正式入口、当前日边界、历史 entry 复用、同 snapshot 新 publication 重绑。全回归为 `178 passed in 50.87s`；compileall 与 diff check 通过。未运行生产 daily、未写生产数据库、未访问或修改 TDX。

放行边界：P00–P04 工程门已满足进入 P05；首次生产 daily 仍须按既有运维窗口执行并留存实际 daily plan/report，它属于生产激活证据，不冒充本轮已执行。
