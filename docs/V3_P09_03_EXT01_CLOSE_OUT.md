# V3 P09-03-EXT01：简图与证据链阶段收口

## 阶段合同

本小任务依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §18.12、§19.5、§20.8、§22.3 执行。收口合同为 `v3-p09-ext01-slice-close-out-v1.0`，范围严格限定为 `EXT01 / LIMIT_POOL_UP` 的收盘涨停简图及其来源证据。

## 收口结论

EXT01 产品链已完成工程预览闭环：当前探测、事件 DTO、批次读取、收盘批次存储/事务写入、涨停简图 API/页面、字段证据、单股下钻和证据弹窗回归均有独立回执。工程链为 `FULL_PASS`；源能力为 `DEGRADED`，本切片结论为 `DEGRADED_PASS`，`release_ready=false`。

已确认的入口：

- `GET /api/v3/events/ladder`
- `GET /api/v3/events/ladder/{security_id}`
- `/v3/events`

## 能力边界与未关闭项

- EXT01 当前证据只有单页 40 行；完整分页覆盖尚未确认。
- `ret1`、金额、封单额、流通市值、换手率的倍率/口径仍有未确认项；页面保持 NULL/“未确认”。
- `source_as_of` 缺失时只展示 `observed_at`，不解释为逐股成交时间。
- EXT02–09 的独立当前探测与产品页面、市场概况、题材/七池、热榜和 P09-04 盘中成员报价不属于本收口范围，继续独立跟踪。
- 不启用生产数据库写入、全市场覆盖声明、自动交易或概率结论；EXT11 历史 BLOCKED 记录保持不变。

## 验收证据

机器回执：[P09-03-EXT01-CLOSE-OUT.json](../reports/upgrade_v3/P09-03-EXT01-CLOSE-OUT.json)。验证命令：

```text
python scripts/verify_p09_03_ext01_close_out.py
python -m pytest -q tests/upgrade_v3/test_p09_03_ext01_evidence_ui_regression.py tests/upgrade_v3/test_p09_03_ext01_ladder_evidence.py tests/upgrade_v3/test_p09_03_ext01_ladder_slice.py tests/upgrade_v3/test_p09_02_d_ext01_close_batch_writer.py tests/upgrade_v3/test_p09_02_c_ext01_close_batch_store.py tests/upgrade_v3/test_p09_02_b_ext01_batch_read.py tests/upgrade_v3/test_p09_02_a_ext01_event_dto.py tests/upgrade_v3/test_p09_01_b_lz_ext01.py tests/upgrade_v3/test_p09_01_b_ext11_probe.py tests/upgrade_v3/test_p09_01_source_registry.py tests/upgrade_m14/test_online_batches.py tests/upgrade_m7/test_migration_executor.py
git diff --check
```

本阶段关闭的是 EXT01 切片的边界与证据记录，不关闭整体 P09。下一小任务按 V3 §22.2 的独立来源顺序为 `P09-01-B-LZ-EXT02-CURRENT-PROBE`。
