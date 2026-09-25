# V4-01/V4-02 R3 BaoStock 公共链路复审与续办记录

- 日期：2026-09-25
- 分支：`codex/v4-system-reform`
- 执行基线 HEAD：`6429e420b1069d37214ff9d493bc92edf95428c2`
- 适用输入：`V4_01_02_R3_BAOSTOCK_PUBLIC_ROUTE_REAUDIT_AND_CONTINUE_20260925.md`
- 当前阶段结论：BaoStock 匿名公共链路已在干净环境的 0.9.3 上通过 B0/B1；B3/B4/B5/B6 形成运行证据，但字段、生命周期和指纹容差验收仍未通过。V4-01、V4-02 均维持 `BLOCKED`，不得降级宣告完成。

## 1. 执行环境与安装核实

- 当前 `E:\python\python.exe` 已安装官方 `baostock==0.9.4`，包路径为 `E:\python\Lib\site-packages\baostock`。
- 为区分 SDK 版本与运行环境，另建无 system-site-packages 的干净 Python 3.13.14 虚拟环境，安装 PyPI 官方 `baostock==0.9.3` 及其依赖；没有把账号、密码或 API key 写入代码、配置、收据或 Git。
- 官方 PyPI Quick Start 展示匿名 `bs.login()`；0.9.3 wheel SHA-256 为 `acbd19403285bc4e254cee8297cf0e2646ae2276e5af7e549deed3988ab02293`。当前 0.9.4 wheel SHA-256 为 `0bf71c6069ab5890ff3596632f9c3f8f1fbc6bfcac582c2f9d6a5c11ab2cfaf8`。[BaoStock PyPI 项目页](https://pypi.org/project/baostock/)、[0.9.3 官方发行页](https://pypi.org/project/baostock/0.9.3/)

## 2. B0/B1 公共匿名路由证据

| 阶段 | 运行方式 | 实际结果 | 收据 |
|---|---|---|---|
| B0 | 已安装 0.9.4；不设置 API key，不传用户凭据；官方匿名 `bs.login()` | DNS/TCP 已到达 `public-api.baostock.com:10030`（peer `114.94.20.42:10030`）；SDK 登录 30.371 秒后超时，错误 `10002007`。登录失败后未发送 history 查询；不是 `10001015` 查询响应 | `reports/v4_baostock/public_b0_history_receipt.json` |
| B0 | 干净 venv，0.9.3 匿名登录 | login/query/logout 均为 0；`sh.600000` 返回 2026-09-01 至 2026-09-07 的 5 行 | `reports/v4_baostock/public_b0_093_clean_venv_receipt.json` |
| B1 | 同一干净 venv，0.9.3 匿名登录 | `query_stock_basic` 1 行、`query_trade_dates` 7 行、`query_all_stock` 7,380 行/4 页；查询及登出错误码均为 0 | `reports/v4_baostock/public_b1_093_clean_venv_receipt.json` |

结论仅限实测路径：0.9.3 公共链路已通过；0.9.4 的公共匿名登录失败。0.9.4 登录问题是否由 SDK 版本变更导致尚未证实。原 0.9.4 VIP/API-key 路由的 history/basic 查询 `10001015` 仍是独立问题，不能据此判定公共服务不可用。

## 3. B3/B4/B5/B6 结果

### B3：字段覆盖抽样

- 公共匿名模式成功查询 14 只证券、日期范围 2026-09-01 至 2026-09-14；请求增量 17。
- 板块覆盖：沪主板 8、深主板 2、创业板 2、科创板 2；观察到 1 只有 ST 行、1 只近期 IPO。
- 北交所未进入样本；未观察到停牌行、复牌转换；无事件样本未建立。因此状态为 `B3_SMOKE_PASS_WITH_ACCEPTANCE_GAPS`，不是字段验收通过。
- 收据：`reports/v4_baostock/public_b3_field_smoke_receipt.json`。

### B4：运行时测量

- `sh.600000` 两年窗口：486 行、1 次查询、1.424 秒。
- 全市场单日：5,216 行、1 页/1 次查询、8.931 秒。
- 本次总计 4 次 RPC（登录、两次查询、登出）。记录的是实测，不代表完整数据集 ETL 时延或在线稳定性保证。
- 收据：`reports/v4_baostock/public_b4_runtime_measurement.json`。

### B5：历史 supplemental 物化

- `sh.600000`，2025-09-01 至 2025-09-30，成功物化 22 行；字段仅含归一化换手率、交易状态、ST 状态及价格指纹，不保存原始行情载荷。
- 对应本地 TDX snapshot 中没有任何一行同时精确匹配 close、volume、amount；22 行均保持 `UNBOUND`。补充文件标注 `SUPPLEMENT_ONLY_TDX_REMAINS_PRICE_AUTHORITY`，不进入核心事实/价格主链。
- 数据文件：`reports/v4_baostock/supplements/20260925T115724Z_67ab885d_sh_600000_2025-09-01_2025-09-30.json`；SHA-256 记于 B5 收据。
- 收据：`reports/v4_baostock/public_b5_supplement_bootstrap_receipt.json`。

### B6：50 股 × 15 日期指纹诊断

- 本地不可变快照：`1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70`；窗口 2024-09-25 至 2025-09-30。
- 50 只沪/深样本各查询成功，每只抽样 15 个共同日期，共 750 组。先前一次运行中 `sz.000016` 返回不可规范化行，遂将其作为显式异常排除；正式 50 股样本不包含该代码。
- 750 组 close 全部精确匹配；volume 716 组精确匹配，最大绝对差 8 股；amount 8 组精确匹配，最大绝对差约 229.29 CNY，最大相对差约 `5.81e-8`；三项全精确共 8 组。
- 结果状态 `B6_DIAGNOSTIC_SAMPLE_PASS_ACCEPTANCE_PENDING`。样本抽取按当前证券目录和代码排序，且只覆盖沪/深样本，尚不足以制定或批准可推广的容差合同。`BOUND_STRICT` 仍禁止启用；必须独立验收样本、来源语义、排除条件和 source-specific 容差。
- 收据：`reports/v4_baostock/public_b6_fingerprint_sample_receipt.json`。

## 4. 请求预算与安全

- 当日 ledger 总请求数：229；远低于用户给定 50,000 次外部上限、系统 40,000 次软停和 45,000 次硬停。
- BaoStock 匿名探测没有传入用户凭据或调用 API-key setter；收据不包含账号密钥。
- 原始 provider 响应不落盘。B5 只追加写入隔离的 supplemental 版本文件；TDX snapshot 仍是 OHLCV/amount 权威来源。

## 5. 阶段合同、证据与验收结果

- BaoStock 公共匿名 B0/B1：`PASS`（仅限干净环境 0.9.3）。
- 公共字段覆盖 B3：`PASS_WITH_ACCEPTANCE_GAPS`。
- 公共运行测量 B4：`MEASURED_ACCEPTANCE_PENDING`。
- Supplemental B5：`MATERIALIZED_UNBOUND`。
- Fingerprint B6：`DIAGNOSTIC_SAMPLE_PASS_ACCEPTANCE_PENDING`，不得据此启用 `BOUND_STRICT`。
- BaoStock datasets 保持 disabled；binding tolerance contract 仍 unfrozen。
- V4-01：`BLOCKED / NOT COMPLETE`。至少仍需在 V4-01 本身完成 ZIP↔extraction 验证、local-over-package source selection、canonical identity mapping、历史生命周期和可评估 universe、调整数据验收与 AS_RECORDED 等合同。
- V4-02：`BLOCKED / NOT COMPLETE`，V4-01 gate 未满足，未输出新的正式 canonical。
- V4-03：`BLOCKED`。

## 6. 下一步

1. 在线独立验收 B3 覆盖缺口、B5 字段语义及 B6 采样/容差诊断；未收到独立验收不得将容差或数据集设为已验收。
2. 在 BaoStock 外继续处理 V4-01 的 source priority、ZIP 自验证、identity/lifecycle/universe 与 adjustment 接受条件；所有审计条目分别记录、分别验收。
3. 仅当 V4-01 gate PASS 后才继续正式 V4-02 canonical 重建与相应 PIT/泄漏验收。
