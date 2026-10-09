# R4.3 四日闭环外审交接

**唯一最终状态：EXTERNAL_ACCEPTANCE_BLOCKED**。工程重建和候选 QA 已执行；未收到针对本轮实际字节的独立外部验收，生产未切换。

- FOUR_SESSION_SOURCE_AND_NUMERIC_PASS：已通过既有正式 required 四板范围的四日证券、RAW、停牌、GBBQ/复权、Core/Profile 独立工程复算。北交所继承 optional DEGRADED_BSE，未宣称全市场 PASS。
- FOUR_SESSION_OPERATIONAL_RECONSTRUCTED_PASS：同一最新通达信 S 已实际计算行业/概念 Native、LOO、Seed、B0、Rotation、股票/市场与事后 Focus/Forward。
- FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS：未获准。线上仍为 2026-09-30；候选 10/08 HTTP/API/UI 读回与正式生产读回分开。
- STRICT_HISTORICAL_PIT_NOT_GRANTED；W8 页面剩余缺陷任务未启动。

| 工作包 | 结果 | 实际证据／下一步 |
|---|---|---|
| W0 | PASS | HEAD/任务/AGENTS/原 85 证据及源 SHA 入场；89 绑定复核未变化 |
| W1 | PASS | 133 行业（110 叶级、23 父级解释层）、268 概念，55136 关系；2224 未映射关系完整隔离，T00 无有效成员另列 |
| W2 | PASS | RAW 5210/5211/5213/5209，真实停牌 12/12/11/15，非停牌缺 BAR 0；GBBQ 193554 事件；新 lifecycle/special |
| W3 | PASS | 实际新 owner_v3 重建；128 多样性真实数值样本，41786 RPS 和26119前驱差分复核，128 Profile样本及103680日涨跌限检查 |
| W4 | PASS | 四日各400计算板块，40独立LOO样本；真实成员移动及重复确定性测试通过，原9/30成员digest保留 |
| W5 | PASS（字段级降级） | 原结构+可证事后突破观察、四轴、日K限制、真实锚定Focus/Forward；缺episode前态／日内源等保留具名未知 |
| W6 | PASS（候选工程） | 版本化发布合同，实际E盘CAS/并发/坏源/故障/NOOP/stale/回滚，候选HTTP及UI同版读回 |
| W7 | NOT_VERIFIABLE | 缺独立外部审查与正式准入签名；未执行生产CAS，无CUTOVER_PASS |
| W8 | NOT_VERIFIABLE | W7未过，顺序门未放行 |

快照 S：`TDX_MEMBER_SNAPSHOT_S_20261009_44f6d2c7cfd4eaf4b218bf237b7776aad81ab11b54b2c01175e6eebf9a65b0ca`；实际采集 `2026-10-09T09:44:01.158745+08:00`。全链保留 RECONSTRUCTED_LATEST_MEMBERSHIP / AS_RECORDED=false / PIT_ELIGIBLE=false / survivorship_bias_risk=true。

四日板块实际结果：
```json
[
  {
    "trade_date": "2026-09-28",
    "sector_count": 400,
    "relative_sector_known": 5134,
    "rotation_counts": {
      "NONE": 328,
      "ROTATION_PULSE": 36,
      "UNKNOWN": 36
    },
    "b0_counts": {
      "FALSE": 197,
      "TRUE": 26,
      "UNKNOWN": 177
    }
  },
  {
    "trade_date": "2026-09-29",
    "sector_count": 400,
    "relative_sector_known": 5136,
    "rotation_counts": {
      "NONE": 233,
      "ROTATION_PULSE": 81,
      "ROTATION_FAILED": 4,
      "UNKNOWN": 79,
      "ROTATION_IN": 3
    },
    "b0_counts": {
      "TRUE": 104,
      "FALSE": 121,
      "UNKNOWN": 175
    }
  },
  {
    "trade_date": "2026-09-30",
    "sector_count": 400,
    "relative_sector_known": 5134,
    "rotation_counts": {
      "NONE": 252,
      "ROTATION_PULSE": 49,
      "UNKNOWN": 77,
      "ROTATION_IN": 18,
      "ROTATION_ACCEPTED": 1,
      "ROTATION_FAILED": 3
    },
    "b0_counts": {
      "FALSE": 111,
      "TRUE": 101,
      "UNKNOWN": 188
    }
  },
  {
    "trade_date": "2026-10-08",
    "sector_count": 400,
    "relative_sector_known": 5128,
    "rotation_counts": {
      "NONE": 201,
      "ROTATION_IN": 14,
      "ROTATION_ACCEPTED": 2,
      "ROTATION_PULSE": 29,
      "UNKNOWN": 130,
      "ROTATION_FAILED": 24
    },
    "b0_counts": {
      "TRUE": 89,
      "UNKNOWN": 161,
      "FALSE": 150
    }
  }
]
```

Focus/Forward 结果：
```json
{
  "episodes": 2477,
  "events": 7524,
  "outcomes": {
    "OBSERVED": 3418,
    "PENDING": 9742
  }
}
```

外审必须检查实际 Git LFS 对象字节，而非指针；验收须绑定最终候选 digest 和审查者。独立审计项与现阶段门分别登记于 12。原9/30 last-good与strict PIT不被新代理口径覆写。

源码入口：`scripts/build_r43_operational_successor.py`；候选服务：`scripts/serve_r43_candidate_preview.py --port 8768`。有独立有效外审记录后才可调用新CAS；固定生产head路径及authority均由新合同约束。

完整证据字节及SHA：
```json
[
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/00_ENTRY_DRIVE_HEAD_AND_PROTECTED_DIGESTS.json",
    "sha256": "a53e912bd4c020da73f4ade4125caecd917a52d0e63ae05e1afa50bcf43bef18",
    "bytes": 20490
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json",
    "sha256": "bfb8405b1ca84787ba425df0ec83592b4b47bb90b0843d2dcd87855aa2143d9d",
    "bytes": 3086
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/02_TDX_MEMBER_SNAPSHOT_S_AND_0930_PIT_DIFF.jsonl.gz",
    "sha256": "0365e0cccb365d46ea334a8ac7d6444acdbbc8e88fc3707ea276eaa439f23559",
    "bytes": 19290
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/03_FOUR_SESSION_UNIVERSE_BAR_SUSPENSION_BJ_RECONCILIATION.csv",
    "sha256": "0dee76e22225aec4c34b1562f481d5e29593811fd0a3240bf9e5f2365e3b14d0",
    "bytes": 7209758
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json",
    "sha256": "590a572c160d77ac2b886a3f5cde746c4858ed2d20d133b8c08ecf835ef16c99",
    "bytes": 6292
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/05_FOUR_SESSION_RAW_QFQ_CORE_PROFILE_NUMERIC_ORACLE.json",
    "sha256": "c910e62d7010b366362fd072968e0ba8cb4e47d247bd5382c5e15dc3dd23e9e3",
    "bytes": 1410631
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json",
    "sha256": "f8018ed18c1f72f4b6d9a74406082f664e5b978e56b81724485b08d1a222b30b",
    "bytes": 58508
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/07_FIELD_LINEAGE_AND_UNKNOWN_REASONS_BY_DATE.csv",
    "sha256": "f4e8e046411d73d8d955861a11cc00ed541947dfa17340c488cd90b04837bedb",
    "bytes": 222869
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/08_CANONICAL_IDENTITY_AND_CORRECTED_OWNER_ADMISSION.json",
    "sha256": "8afa70406b386e1bbb499f7faf182a796edaa4df9e2d630fc718a2a868365925",
    "bytes": 784
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/09_NEW_OPERATIONAL_PUBLICATION_POLICY_AND_OLD_PIT_MIGRATION.md",
    "sha256": "e8cff9f1496941b1f5f1bd399aef493364a81de423b087298e22b4b4f7c671b7",
    "bytes": 799
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/10_SUCCESSOR_ATOMIC_CAS_BAD_SOURCE_ROLLBACK_QA.json",
    "sha256": "7deb5f4eccdedb618641903e066d0422f189e066cd9b32cfae122463734dda6d",
    "bytes": 2033
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/11_FOUR_SESSION_LIVE_API_SAME_CONTEXT_AND_UI_READBACK.json",
    "sha256": "507dd7dbb88a7197125c2a715327d6fa10a3d43b494b817bccbf2b7e78fa920c",
    "bytes": 1694
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/12_INDEPENDENT_EXTERNAL_REVIEW_AND_FIX_REGISTER.md",
    "sha256": "e3b3ba95027cdf079339ea0aa985ca5a05b06ec688a168151d5a63bec7dfebb2",
    "bytes": 3854
  },
  {
    "path": "docs/evidence/r4_3_four_session_closeout_20261009/13_ALL_TEST_COMMANDS_SHA_AND_SCOPE.json",
    "sha256": "5bcd85381184bbb2b195dfab3bb625915c6aaa0a23737c2037543e284dbcee49",
    "bytes": 3070
  }
]
```
