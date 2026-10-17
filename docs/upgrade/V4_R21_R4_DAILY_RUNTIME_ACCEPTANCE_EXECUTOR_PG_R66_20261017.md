---
stage_id: V4_R21_R4_DAILY_RUNTIME_ACCEPTANCE_EXECUTOR_PG_R66_20261017
branch: codex/v4-workspace-cleanup
status: DAILY_EXECUTOR_RUNTIME_ACCEPTANCE_AND_NATIVE_RESPONSE_READ_FROM_PG_BY_DEFAULT
code_commit: 2a522ed9cd1cdb212361d7245330da63a3b15ea4
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
unmapped_reference_edges: 22
---

# V4 R21-R4 日更 runtime acceptance PG 执行链 R66

日期：2026-10-17（Asia/Shanghai）。本批延续 R64 的 BaoStock runtime acceptance PG 事实，复核 R65 的合同注册表 XML 校验与 R56 的日更合同 Reader；执行入口依正式任务卡继续推进到现役 `operational_daily_executor_v1.execute_sources`。

## 代码迁移

- 默认模式 `V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE=PG` 下，执行器从日期键控的 PG fact 读取清单、烟测回执、精确原始 BaoStock 响应和数据库身份；PG 缺少记录或验证失败时不回退读取本地清单。
- 将原始响应字节以 base64 随 PG fact 保存，校验响应 SHA、回执路径/SHA、目标交易日、`observed_at`、JSON 解析结果和字节长度。日报 source-freeze 需要文件 binding，执行器原子导出 PG 派生缓存并将 PG contract/version、trade date、schema、database identity、fact payload SHA 和 native-response binding 写入 source-freeze。
- `V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE=FILE` 仅作为显式历史 fixture/开发入口。BaoStock SDK metadata、schema normalization、TDX bars、source-freeze gate 和原有发布日期/Head CAS 约束继续沿当前执行器路径校验。
- 清理旧测试对 `D:/new_tdx` 的路径字符串替换，改用配置化 TDX 临时只读夹具，保持源目录不写入。

## 验证与限制

- R66 聚焦回归 **14 passed**；完整选定 V4 PG/消费者工作流 **315 passed**，包括现有历史精确绑定和 Universe 用例。
- BaoStock PG Reader、native-response tamper rejection 与执行器缓存接线测试使用受控 PG 边界；未连接 live PG，未运行 BaoStock 网络采集、实际 PG 登记/写入、accepted Head CAS 或完整业务验收。模拟边界测试只证明代码路径与拒绝行为，不等于业务通过。
- 当前未提供合规只读 DSN，且无真实 PG 写入授权；运行时合同/事实的正式 namespace 登记与真实读回仍为现场门。
- R66 code/doc commit `45d414fbb16f8577d9ee28672a28bc2cc482ec53` 的 Push/PR CI 均成功：`39026564472` / `39026567221`。R65 Push/PR CI 也已通过：`39025631882` / `39025635111`。后加的贯穿 `execute_sources` 回归尚在本地，其结果计入上述 14/315。

## 原 266 项逐项核对

| 分类 | 基线 | 代码级 PG 路径，待 live reconciliation | OPEN | Ingress open |
|---|---:|---:|---:|---:|
| 其他业务读取 | 28 | 4 | 23 | 1 |
| Owner 业务读取 | 200 | 44 | 149 | 7 |
| 行情来源入口 | 38 | 0 | 38 | 0 |
| 合计 | 266 | 48 | 210 | 8 |

R66 继续加深已有日更 runtime-contract / acceptance 调用链，没有新增独立 baseline ID。原 266 项正式完成 **0/266**、正式剩余 **266/266**；未映射边 **22**。本轮不因代码或受控测试减少计数。

## 下一批

继续迁移其他业务的 Head、freeze/seal/gate 合同消费者及 Owner authority/descriptor 读取，补齐逐行 source/T0/namespace/digest/正反向证据；并持续调查 DM-01 业务状态的真实 PG 关系以及 TDX/BaoStock 生效入口。所有可独立完成的源码、测试、CI 继续推进；live PG 状态仍按授权门记录。
