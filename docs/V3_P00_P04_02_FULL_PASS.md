# V3 P00–P04-02 验收收口记录

日期：2026-09-12
分支：`codex/v3-upgrade-analysis`
主实施文档 SHA-256：`3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`

## 结论

P00-01 至 P04-02 的阶段级代码、迁移、测试、真实 normalized parquet 副本和 V3 snapshot/publication binding 验收已完成：**FULL_PASS（阶段范围内）**。

这里的 `FULL_PASS` 只覆盖 P00–P04-02 明确要求的阶段门，不将 P05–P11、P08 UI 全面复核、P09 在线故障注入、生产运维激活或算法效果验收提前算入。

## 阶段验收

| 阶段 | 结果 | 关键证据 |
|---|---|---|
| P00-01 | FULL_PASS | §2 旧能力、读写命中、生产/预览/测试/废弃分类均有映射；未解释生产写入点为 0 |
| P00-02 | FULL_PASS | 当前只读重测：DuckDB 91 张 BASE TABLE、2,060,988,416 bytes、7,261 used blocks/601 free blocks；业务键、slice 键、内容重复和引用链分开统计 |
| P00-03 | FULL_PASS | 参数哈希、schema unknown/null/枚举、真实日期/timestamp/有限数值、Ready/NotBuilt/Online context、分页别名和 synthetic fixture 反例通过 |
| P01-01 | FULL_PASS | 锁作用域、外部最长 8 秒等待、本地 publication 读取和连接生命周期测试通过 |
| P01-02 | FULL_PASS | 100 条 total、第二页、源独立失败、总预算和 direct-ephemeral 不落盘测试通过 |
| P01-03 | FULL_PASS | modal 静态分组、返回焦点、Esc/遮罩关闭、异步防串和来源文本安全测试通过 |
| P02-01～04 | FULL_PASS | 新关系增量、六快照导入、树父成员去重、publication binding 及旧全量新写关闭证据通过 |
| P03-01 | FULL_PASS | result-object identity、slice binding、质量/语义/业务值隔离和重复输入校验通过 |
| P03-02 | FULL_PASS | technical/strength/high 六个迁移域按 old↔new 差集、window、NULL、重复重跑核验；fallback=0 |
| P03-03 | FULL_PASS | member_state/structure/summary old↔new 业务差集 0；summary JSON 按语义归一化后差集 0 |
| P04-01 | FULL_PASS | RET60 `d+60`、空成员/缺映射、价格/复权闭包、未知参数域 fail-closed 反例通过 |
| P04-02 | FULL_PASS | 真实 parquet 副本全链；三次同输入重跑新增 0；相邻日期测试通过；失败不绑定半成品 |

## P04-02 真实输入证据

输入 `data/normalized/adjusted_daily.parquet`：19,634,335 行、6,178 个证券、8,784 个交易日；入口通过 PyArrow row-group 窗口读取，避免整文件 pandas 复制。

| run | status | planned | executed | new facts | reused rows | calculated rows | DB growth |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | BUILT | 105,918 | 105,918 | 6,178 | 138,678 | 6,178 | 0 |
| 2 | BUILT | 105,918 | 105,918 | 0 | 144,856 | 0 | 0 |
| 3 | BUILT | 105,918 | 105,918 | 0 | 144,856 | 0 | 0 |

生产数据库副本清理后的保护核验：V3 `result-obj-*` 51 个全部保留；source bundle catalog/物理收据 5/5；完整备份链 12/12；不完整备份链 0；孤立备份对象 0。

## 回归与边界

- `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：`173 passed`；随后 compileall 和 diff check 通过。
- M7 取消竞态同时修复：后台进度与取消请求并发写 `job_events` 时，事件序号和状态更新均采用重试/提交边界；取消边界压力复验 30/30 通过。
- P04 默认 V3 target 仅包含已有 result-object 绑定的六个域；`sector_base`、`sector_cycle`、`mainline` 等旧域只作为兼容条目保留，显式请求且缺绑定时 fail-closed。
- 未修改 `D:/new_tdx` 或配置的 TDX 输入目录；真实验证写入的是临时数据库副本。
- `source_files=0` 仍是历史 catalog 元数据缺口，不伪造回填；它不影响本次阶段级验收，但作为独立审计项保留。

下一阶段：P04-03；仅在本记录和最新 V3 主文档状态一致后进入，不跳到 P05。
