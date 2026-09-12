# V3 P04-03-02：保留源包恢复 resolver

> **状态更新（2026-09-12）**：本文原始证据先以合成 ZIP 和临时目录验证为 `PASS (SCOPED)`。随后已对实际保留的 2026-09-10 V3 bundle 完成全量恢复复验；当前正式状态以 [V3_P04_03_02_REAL_RECOVERY.md](V3_P04_03_02_REAL_RECOVERY.md) 为准，原始测试记录保留不改。

## 结论

依据最新 V3 主实施文档 §17.8、§18.7 P04-03，完成第二个子任务：**PASS（SCOPED）**。

本轮只补充并验证“从保留源包恢复缺失解包目录”的 resolver。验证在临时目录和合成 ZIP 上完成；未删除、移动或覆盖现有 `input_staging`，未写入生产数据库，未访问或修改 `D:/new_tdx`。P04-03 整体仍未完成。

## 阶段合同

- 合同版本：`v3-p04-03-resolver-recovery-v1.0`。
- 输入是只读 `source_bundle-v1.0` 回执和其声明的保留 ZIP；回执身份、包 SHA-256、包字节数和原解包 entry/expanded 计数必须一致。
- `package.staged_path` 存在时必须在项目根内安全解析；旧回执缺失该字段时，兼容回退到 `data/input_staging/packages/<target_trade_date>/hsjday.zip`，并在结果中标记 `fallback_used=true`。
- 目标目录必须是新的、原子解包的、非 TDX 路径；已有目标、符号链接越界、项目根外的包路径和 `D:/new_tdx` 均 fail-closed。
- 可选 `required_members` 在解包前按 ZIP 成员路径核对，避免以“成功解包”冒充所需文件已恢复。

## 实现与证据

### 源码

- `src/workbench_input/pipeline.py`
  - 新增 `_verified_bundle_body()`：统一校验 source bundle 身份和只读合同。
  - 新增安全包路径/TDX 路径边界检查。
  - 新增 `restore_source_bundle_extraction()`：显式 staged path、旧回执日期回退、包 hash/大小、成员存在性、原子解包和 sealed 计数核对。
  - `verify_source_bundle()` 复用统一回执校验，保持已有“验证现有解包目录”的职责，不把恢复动作隐式塞进发布校验。
- `src/workbench_input/__init__.py`：公开 resolver 入口。

### 测试

- `tests/upgrade_v3/test_p04_03_02_resolver.py`
  - 新目标目录恢复两个 day 文件并核对计数/hash。
  - 缺失 `staged_path` 的旧回执按交易日约定路径恢复，并显式记录回退。
  - 源包被篡改时在创建目标目录前 fail-closed。
- 定向结果：`pytest -q tests/upgrade_v3/test_p04_03_02_resolver.py tests/upgrade_m3/test_automatic_input.py` → **15 passed**。
- `git diff --check`：通过。

## 验收

| 条目 | 结果 |
|---|---|
| 保留 ZIP 可恢复所需成员 | PASS；合成源包两个成员均恢复并读取一致 |
| 旧回执无 `staged_path` 可兼容恢复 | PASS；日期约定回退且可审计标记 |
| 回执/包/hash/计数一致性 | PASS；篡改源包在写目标前拒绝 |
| 原子目标目录与已有目标保护 | PASS；复用 `safe_extract_zip` 的 staged + replace |
| TDX/越界路径保护 | PASS；包路径项目根限定，目标拒绝 `D:/new_tdx` |
| 生产激活/真实大包恢复 | 未在本子任务执行；需后续运维窗口或独立证据 |

## 边界与独立遗留

- 没有改写历史 bundle 以补 `staged_path`；旧字段缺失仍由版本化兼容读取处理，对应 `P04-03-01-A` 的“历史身份不重写”要求。
- 没有启用最近 2 个 bundle 的保留/回收策略，没有写 cleanup preview，没有审查 backup 调用链；这些属于后续 P04-03 子任务。
- `source_files=0` 和 backup catalog/物理对象对照仍分别由 `P04-03-01-B/C` 跟踪。

## 下一项

继续 `P04-03-03`：按 §17.8 启用最近 2 个已使用 bundle 的解包保留与 `.phase1_cache` 预算边界；先做预览和保护判断，不执行删除。
