# V4-00D TDX VIPDATA Source Contract 阶段回执（2026-09-25）

| 字段 | 记录 |
|---|---|
| stage | `V4-00D / TDX_VIPDATA_SOURCE_CONTRACT` |
| stage_contract | V4.2.2 REV2 §3B.4、§3E、§3F、§78：官方页面发现与目标日期门、有界下载、隔离 staging、source manifest、下载/解析/市场日期/全市场重叠验收、TDX 只读边界。 |
| consulted_upgrade | 最新桌面 REV2《A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md》，SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`；执行前复核一致。合同复审 `docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md` SHA-256 `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`，原有 OPEN 项不因本阶段关闭。 |
| input_identity | HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`；正式 adapter contract id `TDX_VIPDATA_ADAPTER_V1`。既有包 source_bundle `6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2`，package SHA-256 `b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f`，目标日期 2026-09-24，大小 550,821,395 bytes，parser `m3-tdx-input-v1.0`。 |
| execution_boundary | 仅复用本地已封存 2026-09-24 包并读取官方页面、适配器代码、本地包与 `D:/new_tdx/vipdoc`；未发起新行情下载、未运行 scanner、未写数据库，未改动 TDX root。新报告和回执均原子写入项目 `reports/` 与 `docs/`。 |

## 合同与能力边界

- 官方入口：`https://www.tdx.com.cn/article/vipdata.html`。本次页面声明适用于个人版 PC 盘后下载，包包含沪深京日线；提示需要当日数据时应等待更新日期变成当日。页面当前“更新日期”字段为空，所以 2026-09-25 对应能力门为 `SOURCE_NOT_READY`，没有把 9 月 24 日包冒充 9 月 25 日包，也未触发新下载。
- 已有 `src/workbench_input/pipeline.py`（SHA-256 `66e8d2b97dc579b73cc1c8039f55f697a16a83eab6af21d5c383541294e1dbfc`）具备 HTTPS host/path 固定、重定向限制、下载字节上限 4 GiB、curl connect timeout 15s / max time 600s / retry 2、ZIP CRC、临时文件与原子替换、解压最多 20,000 entries / 16 GiB / compression ratio 200、ZIP 路径与符号链接防护、项目 staging 和 source bundle hash 封存。urllib 路径的连接与读取 timeout 未分离实现；source bundle 也没有 V4 所需的完整页面观察/声明日期、下载起止时间与 failure reason 字段。因此旧 M3 能力可复用作已有包校验，不代表 V4 adapter 实现验收。
- 版本化 V4 source manifest 最低字段冻结为：`package_id`、`source_page_url`、`page_observed_at`、`page_declared_update_date`、`download_url`、`target_trade_date`、`frozen_source_cutoff`、`download_started_at`、`download_finished_at`、filename、byte_count、package SHA-256、ZIP entry count、extracted content digest、parser version、status、failure_reason。任何失败都保留有界、可审计回执；禁止在 TDX 根目录解压/覆盖。
- 复用下载预算边界：单次作业最多 1 次官方页面发现；页面目标日期未就绪时 0 次包下载；就绪后最多 1 个 package transfer，瞬态网络/5xx/timeout/partial/CRC 错误最多 2 次重试。transfer 上限 4 GiB、connect timeout 15s、总时限 600s；隔离 ZIP 解包上限 20,000 entries / 16 GiB / 压缩比 200。`429` 遵从 Retry-After/有界退避；identity、目标日期、unexpected file family、overlap 失败不重试。现有 transport 的实际路径差异和页面门缺失列为 `IMPLEMENTATION_NOT_VERIFIED`，在实现前不启用网络流程。

## 全市场重叠证据

按 REV2 §3B.4，用官方包内 SH/SZ broad-market index chains 取最近 60 个实际交易日（2026-07-03 至 2026-09-24）。同 market+filename+trade_date 配对，对 TDX 32-byte `.day` 记录的 `open/high/low/close/volume/amount` 做全字段精确解析值对比；本地 TDX 只读。明细和样本见 [v4_00d_overlap_20260925.json](../reports/v4_00d/v4_00d_overlap_20260925.json)，SHA-256 `5415057758c1feba89849b11825ae1e5e0dd6440a953d49ca7a657f67c44d70a`。

- 配对文件 12,156；包独有文件 282；本地独有文件 89；解析格式异常 0。
- 同证券同日可比行 468,339：精确一致 465,186；字段差异 3,153（0.67323%）。其中成交量差异 3,134 行；OHLC 差异：open 4、high 9、low 8、close 3；amount 精确值差异 0。
- package-only rows 109,485；local-only rows 3,998；按 market 与交易日期的拆分写入 JSON。`identity_mismatch_count=0` 仅表示所用 market+文件名+日期键无键冲突，不构成独立 issuer identity 核验。
- 合同要求 `exact_match_rows`、`normalized_tolerance_match_rows`、`mismatch_rows`、package/local-only rows 与 identity mismatch 输出；但 §3B.4 没有给出数值 mismatch 阈值，也没有定义 normalized tolerance 的字段归一化与算法。按 §3E fail-closed，本次没有自行设阈值或容差，normalized tolerance 记为未计算，重叠验收为 `NOT_ACCEPTED`。故此包不能进入 V4 `ACCEPTED_SOURCE_PACKAGE`，也不能供 Canonical Daily / V4-01 bootstrap 作正式输入。

## 独立跟踪与验收

- 新开独立审计 `V4-00D-OVERLAP-GATE-01`，状态 `OPEN`：范围为重叠阈值、标准化算法、差异指标与 row-only 语义。接受条件见 [独立审计回执](audits/V4_00D_OVERLAP_GATE_AUDIT_20260925.md)。它不由 V4-00D 的阶段回执或后续算法阶段自动关闭。
- **阶段接受结果：`DEGRADED_PASS / SOURCE_CONTRACT_INVENTORY_COMPLETE_OVERLAP_ACCEPTANCE_OPEN`。** 下载/解析/目标日期证据已盘点，合同与请求预算已冻结；真实 60 日比较存在差异且规范缺少判定阈值，source package 尚未被 V4 接受。`DEGRADED_PASS` 只覆盖合同/证据回执，不是数据源放行。
- **下一阶段：`V4-00E / HISTORICAL_ADJUSTMENT_COORDINATES`。** 可继续定义调整/坐标合同；V4-01 历史 bootstrap、Canonical Daily 和 scanner 仍受 source acceptance 与 V4-00H Phase 0 最终回执约束。
