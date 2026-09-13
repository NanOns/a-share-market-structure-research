# V3 P05–P08 审计修复与最终收口（2026-09-12）

## 结论

依据最新 `WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` §4–§10、§18.8–§18.11 和§20，P05–P08 最终验收结论为 **FULL_PASS**。

本文是针对原 P05–P08 台账的独立整改审计项，不回写或伪装旧阶段当时的证据。

## 修复范围与证据

| 问题 | 修复与验收 |
|---|---|
| P06 `dq5_3` 错读 q20 | `build_v3_p06_02_potential_distribution.py` 改为读取 `sector_rs5_pct q5`，并严格计算 `q5[t]-q5[t-3]`；重生真实 P06-02 JSON。 |
| P06 W 缺共同成员分支 | `build_sector_current()` 新增绑定 `comparison_features`，执行 `(m1<0 and b_delta3<=-.20)`；无该证据时保持 UNKNOWN。P06-01 真实产物已重生。 |
| P07-03 只有 Store、无完整 builder/job | 新增 `research_builder.py`，按股票特征→信号→CURRENT/POTENTIAL→episode→角色→关联/短名单→事务封存顺序执行；`app.py` 接入 `POST/GET /api/v3/research/jobs`。 |
| P08 无真实 COMPLETE run | 正式项目库生成 `research-5369ba9e65074cf599bbea230e24ff7b`：6,178 股票、554 板块、2,316 紧凑角色，状态 COMPLETE。 |
| P08 无真实页面验收 | 使用真实服务和正式库打开 `/v3`；页面显示 `2026-09-10 | READY | RESEARCH_V3_PREVIEW_1`，CURRENT/POTENTIAL 及两条清单均显示合同规定的可解释空态，未用 fixture 充当市场结果。 |
| 旧 M4 daily 回归失败 | 保留生产 stdout/receipt fail-closed，对显式测试替身的非字符串 stdout 保留兼容；单独用例已通过。 |

## 真实结果和边界

- 修复后 P06-01/P06-02 真实报告均 PASS；CURRENT/POTENTIAL 真实命中仍为 0，原因是当日覆盖与三值门，未为凑数改阈值。
- 真实 COMPLETE run 不使用旧 candidate/association 填充；研究角色和短名单为 0 时保持空态。
- GET 仍只读 COMPLETE run；构建由显式 `BUILD_RESEARCH_V3` job 触发，不由 GET 暗中启动。
- 未访问或修改 TDX，未使用未来数据、外部复权或概率声明。

## 验收结果

- P05–P08 及关联 M4/M5/M7 定向回归：222 passed。
- 全库回归：`998 passed`。
- `python -m compileall -q src scripts`：PASS。
- `git diff --check`：PASS。
- 真实 API/UI：READY，身份绑定为上述 COMPLETE run，双轨空态解释正确。

## 门与下一阶段

P05、P06、P07、P08 均为 **FULL_PASS**；G05、G06、G07、G08 关闭。下一任务按主规格为 `P09-01`，不把 P05–P08 的工程验收声称为算法收益或全部 V3 升级完成。
