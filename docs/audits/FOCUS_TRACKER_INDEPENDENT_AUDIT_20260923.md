# 板块与个股持续观察独立审计（2026-09-23）

## 审计边界与基线

- 适用升级合同：`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md`，重点为第 4、10–13、15 节；Phase 0 已记录 `FULL_PASS_TDX_NATIVE`。
- 本次为只读审计，不修改 TDX、Focus 业务数据、正式 head 或实现。检查源码、Focus 定向测试、回滚探针、阶段回执及生产库只读产物。
- 当前生产产物：2026-09-23 首个 `REAL_FORWARD` run `focus-run-f8ba1c4915d1c330506d9bc8954b0a2d`，1 run/1 head、310 daily items（273 个 V3.3 候选、17 个板块、20 个 V3 个股）。真实多日连续性及到期 outcome 尚无产物。

## 独立审计项

### FT-A01（高）：详情时间线只读取所选 run 当日 observation

- 范围：`src/focus_tracker/read_api.py` 的 `_episode` 与 `_entity` observation 查询；页面“每个交易日的状态”。
- 证据：两处查询均以 `focus_run_id=%s` 且绑定请求的 run ID 过滤。每日正式发布使用不同 run，因此第二个正式日开始，详情的 observation 列表只会包含请求当天的行，而 transition 与 anchor 查询却读取截至该日的历史。页面把这列称为逐日时间线。当前回滚 API 探针只给一个 run 造 observation，不能发现跨日缺行。
- 合同偏差：最终设计第 2、11、13 节要求长期逐日观察和详情时间线；第 4 节的“固定 run”是请求一致性基准，不等于只展示该 run 当天的历史行。
- 接受条件：以至少两个 accepted 交易日、同一 episode 的 fixture 验证详情按所选日期返回两日 `AS_RECORDED` 记录，并通过各日 accepted head 过滤；同日旧 revision、未激活 run 和所选日期以后的记录均不可混入。

### FT-A02（高）：历史事件查询未限定各日 accepted head

- 范围：`src/focus_tracker/read_api.py` 的 episode/entity transition 与 anchor 查询。
- 证据：查询仅连接 `focus_runs` 并限制 `r.trade_date<=所选日期`、source authority 合同，没有连接 `focus_trade_date_heads.accepted_focus_run_id`。同日 revision 会保留旧 run 的 immutable transition/anchor；请求最新 head 时旧 revision 的事件仍可能与新 revision 一起显示。显式历史 run 请求也可能看见其后同日 revision 的事件。
- 合同偏差：最终设计第 4、10、11、15 节规定旧修订留存但页面按固定 accepted run/revision 解释，不能混合权威。
- 接受条件：构造同日 r1→r2 且事件不同的 fixture，默认详情仅展示 r2 链；显式 r1 历史视图只展示 r1 可见版本，并正确标注历史身份；跨日事件逐日只取当日 accepted head。

### FT-A03（中）：重入前态可能引用未接受 episode

- 范围：`src/focus_tracker/previous_reader.py` 的 `all_last_episodes` 查询。
- 证据：查询从 `focus_episodes` 全表按 `first_trade_date<=previous_day` 选择每实体最新 episode，没有连接 `first_focus_run_id` 对应的 accepted head，也没有限制 `REAL_FORWARD`。若旧 revision 或历史重建/未激活 run 留下较新的 episode，当前对象未在上一 head observation 中时，它可能被当作重入 parent。现有单测只覆盖 predecessor head 为 `REPLAY_REQUIRED`，没有覆盖此污染路径。
- 合同偏差：最终设计第 4、7、15 节要求前态来自上一 accepted Focus head 和权威历史链。
- 接受条件：带 accepted 与未接受 episode 的数据库 fixture 证明重入 parent 仅来自所选 head 的可追溯历史链；历史重建、旧同日 revision 或 draft run 不得进入正式前态。

## 阶段与产物结论

- Focus 定向测试：`python -m pytest tests/upgrade_v3 -q -k focus`，`59 passed, 355 deselected`；`scripts.probe_focus_read_api` 回滚探针通过，持久写入 0。它们没有覆盖上列跨日/修订反例。
- 生产只读核验：`scripts.probe_focus_source_heads` 的 9/23 来源为已接受 COMPLETE；`scripts.verify_focus_pg_schema_v1` 返回 22 表、131 约束、42 索引、1 run、1 head；`scripts.report_focus_outcome_overdue` 在 9/23 返回 0 个到期/逾期结果。这是首日尚未到期，不是结算成功率证据。
- 已登记的技术结果 hash 差异仍使 310 条 validity 为 `UNKNOWN`、path 为 `DATA_UNAVAILABLE`，详见 `docs/audits/TECHNICAL_RESULT_HASH_RECONCILIATION_20260923.md`。FOCUS-04、FOCUS-05 总阶段仍 `IN_PROGRESS`；FOCUS-06 多日真实观察、性能、真实结果及含数据备份恢复未验收。
- 本次审计接受结果：`BLOCKED / RELEASE_READINESS`。首日发布和展示可作为受限真实产物保留，但不能凭 59 项测试、单日 head 或当前页面宣布持续观察功能整体通过。下一阶段先修复 FT-A01–A03 并添加跨日/同日 revision 反例；随后用真实多日 head、到期 outcome、性能和备份恢复证据复审 FOCUS-04–06。
