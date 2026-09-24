# 持续观察独立审计问题修复回执

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 4、7、10–13、15 节；`docs/audits/FOCUS_TRACKER_INDEPENDENT_AUDIT_20260923.md` |
| stage_contract | `FOCUS_READ_API_V1` 历史详情读取；`FOCUS_PREDECESSOR_HEAD_READER_V1`；本次审计项 FT-A01、FT-A02、FT-A03 |
| scope | 只修复 Focus 只读详情与前态查询、回滚探针；不修改生产 Focus run/head、TDX 输入、来源算法或 outcome 结果 |
| evidence | `_episode` 与 `_entity` 逐日 observation 从所选 run 当日及之前各日 `VALID` accepted head 读取 `AS_RECORDED`；transition、anchor 与关联 outcome 采用相同事件可见性。显式历史 run 在所选日只读自身，不混入该日其他 revision。重入候选 episode 必须在有效 accepted head 的 `AS_RECORDED` observation 中出现。回滚探针新增两个交易日、一个旧同日 revision 和无 accepted observation 的 episode，验证逐日记录、事件/锚点隔离及前态排除。探针 `persisted_changes=0`；Focus 定向测试 `59 passed, 355 deselected`；编译与 `git diff --check` 通过。 |
| acceptance_result | `FULL_PASS / FT-A01–A03_CODE_AND_ROLLBACK_REPLAY`；真实库目前仅有一个正式 Focus 交易日，尚无第二日生产数据可作运行期复核 |
| next_stage | 第二个正式 `REAL_FORWARD` Focus head 激活后，用真实同 episode 的两日详情核对时间线；首次同日来源修订后复核默认与显式历史 run 事件隔离。FOCUS-04/05/06 总门继续按原合同验收。 |

## 可复现命令

在仓库根目录设置 `$env:PYTHONPATH='src;scripts'` 后执行：

```powershell
python -m scripts.probe_focus_read_api
python -m pytest tests/upgrade_v3 -q -k focus
python -m compileall -q src/focus_tracker/read_api.py src/focus_tracker/previous_reader.py scripts/probe_focus_read_api.py
git diff --check
```
