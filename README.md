# 大A交易

当前唯一开发目录：`G:/codex work/大A交易`。在这个目录中切换分支进行开发，不另建源码工作区。

- `main`：生产代码主分支，使用 tag 标识代码版本。
- `codex/v4-unified-development`：统一开发分支。
- `codex/v4-fp14-r2-repair`：因独有提交暂时保留，待后续处理。
- `G:/codex work/大A交易_交付`：交付包和清理归档。
- `G:/codex_tmp`：临时文件与测试临时数据。

目录职责：`src/` 为业务实现，`scripts/` 为构建、迁移及验收脚本，`config/` 为配置，`data/` 为来源和业务产物，`runtime/` 为运行状态，`docs/` 为合同与说明，`reports/` 为运行和验收记录，`tests/` 为自动化测试。根目录 `run_*.py` 是各代启动入口，不能仅凭文件名将旧入口当作当前 V4 自动日更入口。

本次收拢合同与原运行目录的归档说明见 [仓库收拢记录](docs/maintenance/REPOSITORY_CONSOLIDATION_20261015.md)。代码基线标签不替代运行包或生产数据验收。

## 早期 Phase 0 历史说明

Phase 0 implementation for auditing a local TongdaXin installation without modifying it.

Run:

```powershell
python run_phase0.py --tdx-root "D:\new_tdx"
```

The primary Phase 0 result is `reports/phase0/TDX_DATA_AUDIT.json`.

Phase 0.1:

```powershell
python run_phase0_1.py
```

Its final receipt is `reports/phase0_1/PHASE0_1_FINAL_RECEIPT.json`. The current status is `DEGRADED_PASS`; adjustment-dependent results remain experimental.

Phase 0.2:

```powershell
python run_phase0_2.py
```

The local GBBQ decoder and affine QFQ engine now pass automated local and reference-style validation. The consolidated audit handoff is `docs/PHASE0_2_REPORT.md`; status remains `DEGRADED_PASS` only because the five-row TongdaXin desktop QFQ check is still `NOT_CHECKED`.

Phase 0.2A supersedes that gate decision: `BLOCKED_FOR_FORMAL_ADJUSTMENT`.
Four fixed external QFQ samples differ beyond tolerance; the root cause remains
unresolved. The latest report is `docs/PHASE0_2A_REPORT.md`. Production remains
`LOCAL_TDX_ONLY` with `RAW` prices and formal scanners disabled. Existing
network evidence must not be overwritten. Re-seal the retained evidence offline:

```powershell
python scripts/seal_phase0_2a_offline.py
```
