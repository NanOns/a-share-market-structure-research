# R8 10/14–10/15 断档更新与修复验收

日期：2026-10-15
范围：候选隔离目录 `G:/codex_tmp/test_temp/R8_CATCHUP_CANDIDATE_20261015T1905`。本记录不代表生产发布。

## 执行结论

从生产只读基线 10/13 连续构建候选 10/14、10/15 Head。两日 TDX 与 BaoStock 实际来源均已就绪并完成抓取，批次作业 `0b1c9e6f00b74c68b1bb2634fb7c8395` 为 `PUBLISHED_FULL`。先前“15 日源未就绪”的状态判断不准确：上游源可用；当时缺的是本地冻结收据。当前真正未完成的是 Forward 对已记录时钟字段的识别及已持久化晚到记录的受控重分类。

生产 Head 仍为 10/13，SHA-256 `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3`。候选 Head 链为：

| 日期 | 前态 | 候选 Head SHA-256 | 活跃证券 |
|---|---|---|---:|
| 10/14 | 10/13 生产基线 | `967bba5fb58370561b08d6487341e512e090293fa5e9dc2a9a4778dbf1543d2f` | 5,225 |
| 10/15 | 10/14 候选 | `3607256069121cd4ad52c9b2fd055130ad8f549c1d582b1dc51038db8b1627da` | 5,226 |

没有构建发布包，也没有写生产 Head。候选作业调度器关闭。

## 双日源与数值校验

本批次 TDX 包为 552,456,022 字节，SHA-256 `768c907a6433bc5cfc1fb0c4f6b0cf0ae25f5fe94bf86d95987418558b1acd9d`。TDX 记录的源可用时刻分别为 10/14 `2026-10-15T11:23:27Z`、10/15 `2026-10-15T11:31:36Z`。BaoStock 10/14 使用 08:26 的有效晨间缓存，共 5,225 行；10/15 实时抓取 5,226 行。每个日期 `source_ready=true`。

| 日期 | Core / 活跃集合 | 原始行情行 | 前态日期 / 行数 | 数值 oracle |
|---|---:|---:|---|---|
| 10/14 | 5,225 / 5,225，集合一致 | 5,214 | 10/13 / 5,225 | PASS，219,436 项，0 错误 |
| 10/15 | 5,226 / 5,226，集合一致 | 5,215 | 10/14 / 5,226 | PASS，219,464 项，0 错误 |

10/15 新增的 `SZ.301569` 已进入完整集合。10/14 的 `SZ.301660` 按身份映射在当日和次日 Core 集合中保留。跨日计算使用前一候选状态，没有从 10/13 跳过 10/14。

## 问题 A：成员关系来源证据

修复 `classify_membership_provenance()`：成员快照哈希或路径缺失时，不再回退到板块 Owner 的哈希与路径。板块计算产物不能证明历史成员关系在 T0 已冻结。双日分类均为 `MEMBERSHIP_RETRO`（各 400 板块），`AS_RECORDED=0`、`UNKNOWN=0`；没有将最新成员表误称为历史同日快照。独立成员源快照尚未证实，因此没有在线严格 PIT 成员声明。

## 问题 B：旧 NO_QUOTE 追加纠正幂等性

旧观察保持不变，仅追加纠正版本。两日更新共完成 683 项旧 `NO_QUOTE` 纠正；10/13→10/14 有 113 项 T+1 结算，10/14→10/15 有 130 项 T+1 结算，均有接受来源。10/08 的 T+3 到期日按交易会话表为 10/13，当前读回 134 项已结算、1 项暂停。

对相同来源状态重复执行时，结算追加数与旧案 revision 追加数均为 0；未接受来源与已接受但缺来源的剩余计数均为 0。历史 Forward 分母在两次重放前后均维持 39,366。详见 `LEGACY_NO_QUOTE_CORRECTION_20261015.json`。

## Forward 时钟与未完成项

10/14 真实补采发生在下一交易日，仅属于 `LATE_OBSERVED_NOT_PIT`。10/15 冻结中有实际的 `tdx_source_available_at` 和 `observed_at`，但初次 Forward 观察器只识别 `first_available_at` / `provider_available_at`，将记录保守保存为 `LATE_OBSERVED_NOT_PIT`。代码已修复为读取现有源时钟；对应 fixture 以记录的实际时间判定为 `LIVE_OOS`。已持久化的晚到事实没有被改写，当前没有受控追加式重分类路径；重放遇到 lane 集变化会 fail closed。因此不能把现有 10/15 记录报告成 LIVE。

R7 日级成员证据均是 `MEMBERSHIP_RETRO`。统计接口因无授权 cohort owner 返回 `SOURCE_INCOMPLETE`，分母为空。候选消费者读回：stocks 5,226、sectors 400、focus 3,355、lifecycle 5,226、rotation 400 均 READY；首页带有缺少 owner 的明确缺口。风险读回的市场项 READY、股票项覆盖率约 99.6%，板块风险 0/400；优先级可排名股票 967（10/14）和 701（10/15），板块 0/400；市场许可保持 `FACT_ONLY_NO_FORMAL_PERMISSION`。

## 阶段门

| 门 | 结果 | 证据/说明 |
|---|---|---|
| V01 批次与源就绪 | PASS | 一批次绑定两日，实际 TDX、BaoStock 源已抓取 |
| V02 连续候选 Head | PASS | 10/13→10/14→10/15，生产未变 |
| V03 Forward 捕获身份/时钟 | PARTIAL | 字段消费代码与 fixture 已修；持久化 10/15 仍晚到，重分类路径待补 |
| V04 成员 provenance | PASS（如实降级） | 独立成员证据不足时两日均为 RETRO，未赋 AS_RECORDED |
| V05 旧案修订 | PASS | 追加纠正且保留原记录；未接受来源重复追加被幂等阻止 |
| V06 数值计算 | PASS | 双日 oracle 共 438,900 项、0 错误 |
| V07 身份/集合守恒 | PASS | 每日 Core 与活跃集合相等；新旧身份均保留 |
| V08 到期结算 | PASS | 10/13 T+1、10/14 T+1 与 10/08 T+3 到期日分别核对 |
| V09 消费者/Forward/风险状态 | PARTIAL | 消费者只读回读完成；无正式 cohort owner，板块风险和优先级不完整 |
| V10 候选打包 | NOT RUN | V03、V09 尚未通过，不生成包 |

## 代码与证据

相关代码已提交并推送至 `codex/v4-unified-development`：`0f6a58999`（定义字节换行规范化）、`e5162492f`（同 Head/源幂等及部分 lane fail closed）、`455111223`（读取源冻结时钟）。焦点测试此前运行结果为 28 passed。

机器可读证据：

- `TWO_SESSION_20261014_15_CATCHUP.json`
- `LEGACY_NO_QUOTE_CORRECTION_20261015.json`
- `MEMBERSHIP_AND_CAPTURE_CLOCK_RECONCILIATION_20261015.json`
- 候选运行时消费者、Forward、风险与优先级读回位于隔离目录 `runtime/`。

验证环境未启动网页服务；28765 与 28766 均未监听。使用共享 `127.0.0.1:5432/market_research`，没有新建数据库实例。运行前已停止候选采集 worker，未保留重复任务。
