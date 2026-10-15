# 大A交易

当前唯一开发目录：`G:/codex work/大A交易`。在这个目录中切换分支进行开发，不另建源码工作区。

- `main`：生产代码主分支，使用标签（`tag`）标识代码版本。
- `codex/v4-unified-development`：统一开发分支。
- `codex/v4-fp14-r2-repair`：因独有提交暂时保留，待后续处理。
- `G:/codex work/大A交易_交付`：交付包和清理归档。
- `G:/codex_tmp`：临时文件与测试临时数据。

目录职责：`src/` 为业务实现，`scripts/` 为构建、迁移及验收脚本，`config/` 为配置，`data/` 为来源和业务产物，`runtime/` 为运行状态，`docs/` 为合同与说明，`reports/` 为运行和验收记录，`tests/` 为自动化测试。根目录 `run_*.py` 是各代启动入口，不能仅凭文件名将旧入口当作当前 V4 自动日更入口。

本次收拢合同与原运行目录的归档说明见 [仓库收拢记录](docs/maintenance/REPOSITORY_CONSOLIDATION_20261015.md)。代码基线标签不替代运行包或生产数据验收。

## 早期阶段 0 历史说明

阶段 0 的实现用于审计本地通达信安装，不修改其内容。

运行方式：

```powershell
python run_phase0.py --tdx-root "D:\new_tdx"
```

阶段 0 的主要结果文件为 `reports/phase0/TDX_DATA_AUDIT.json`。

阶段 0.1：

```powershell
python run_phase0_1.py
```

该阶段的最终收据为 `reports/phase0_1/PHASE0_1_FINAL_RECEIPT.json`。此处记录的状态为 `DEGRADED_PASS`；依赖复权的结果仍属于实验性结果。

阶段 0.2：

```powershell
python run_phase0_2.py
```

本地 GBBQ 解码器和仿射前复权（QFQ）引擎已通过本地自动化验证及参考对照式验证。综合审计交接文档为 `docs/PHASE0_2_REPORT.md`；该阶段状态仍为 `DEGRADED_PASS`，唯一原因是通达信桌面端的五行前复权对照检查仍为 `NOT_CHECKED`。

阶段 0.2A 替代了上述门禁判定，其状态为 `BLOCKED_FOR_FORMAL_ADJUSTMENT`。
四个固定的外部前复权样本存在超出容差的差异，根本原因尚未解决。该阶段最新报告为 `docs/PHASE0_2A_REPORT.md`。该阶段记录的生产模式仍为 `LOCAL_TDX_ONLY`，使用 `RAW` 原始价格，正式扫描器保持禁用。不得覆盖已有网络取证资料。可离线重新封存已保留的证据：

```powershell
python scripts/seal_phase0_2a_offline.py
```
