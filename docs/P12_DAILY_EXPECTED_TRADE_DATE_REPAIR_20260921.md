# P12 日生成目标交易日修复验收（2026-09-21）

## 阶段合同

本次依据最新 P12 日生成与数据库独占修复合同，新增 `P12_DAILY_EXPECTED_TRADE_DATE_V1`。Phase 0 为 `FULL_PASS`。本阶段仅修复日期身份传递，不触发日数据生成。

## 证据

- 在线来源已确认 `2026-09-21`。
- 本场景最新 M3 官方日包仍只验证到 `20260918`，最新发布和研究包因此继续是 9 月 18 日。
- 页面 `selectedResearchInput()` 原来只提交 `build_research_v3=true`，未传 `expected_trade_date`；后端因此无法对在线日期与本地日包做不一致拒绝。

## 修复

- 生成按钮提交前强制请求 `/api/v3/online/latest-trade-date`，并将结果放入 `expected_trade_date`。
- 页面脚本缓存版本升级为 `p12-21-expected-trade-date-1`。
- 后端对 `build_research_v3=true` 但缺少目标日的旧页面请求直接 fail closed；目标日与 M3 官方日包不一致时不发布。

## 验收

- `tests/upgrade_v3/test_v3_unified_entry.py`: `2 passed`。
- `compileall` 通过，`git diff --check` 通过。

阶段验收结果：**FULL_PASS**。

## 下一阶段

重启服务使新页面脚本生效。用户后续手动触发时，如官方日包还没有 21 日，任务应显示目标日不一致并拒绝生成，而不再静默发布 18 日。
