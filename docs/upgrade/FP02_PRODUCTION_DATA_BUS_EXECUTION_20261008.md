# FP-02 生产数据总线执行与验收

依据：本轮总卡、02 卡与 FP-01 successor 运营发布政策；Phase 0 原收据 `phase0_status=FULL_PASS`。范围为已实现生产结果的版本化接入，不声称全部业务页或长期统计验证完成。

## 合同与实现

`V4_RESEARCH_SNAPSHOT_V1` 将已冻结当前读取合同、V4-08 owner 绑定的 Native / Rotation 产物、V4-13 高级画像接入一份不可变 SQLite 索引。读取只认明确的 owner / source SHA256，不按目录修改时间发现产物。`ProductionV4ResearchReader` 只读查询；股票、板块、事件、雷达、Forward、结算、数据源共用发布身份、日期和 context token。

发布采用独占锁、CAS、原子指针替换、独立读回；失败恢复原指针。构建固定到不可变旧读取合同并逐页核对 token；每份新快照携带 FP-01 要求的 12 个元数据字段，拒绝 fixture 来源、未来日期与隐式日期回退。旧读取合同、旧权限、旧 accepted head、FP-01 原收据均保留。`config/v4_research_snapshot_release_policy_v1.json` 记录该接入范围的 successor 工程门及实际验收引用。

列表只返回本页字段，详情按对象读取；名称、代码、历史代码、状态、板块成员建立索引。嵌套来源图通过原产物 digest / 字段定位，不重复塞入列表；数值、质量、原因仍保留。不是一次向浏览器发送全部 5,213 条完整画像。

## 真实结果与缺口

| 域 | 当前接入 | 精确限制 |
|---|---|---|
| 股票 | 5,213 只，当日行情、D2 情景/资格、原始资格/满足条件/缺失条件/变更原因及高级画像 | Core owner 画像为 9 月 28 日，不能当作 9 月 30 日 Core；另列当日补算任务 |
| 板块 | 378 个，完整成员及 Native / Rotation 逐字段输出 | owner 产物的行情/Core/前序历史能力不足如实保留；不是算法未实现 |
| 事件 / 雷达 | 33 / 117 条真实已绑定输出 | 沿用各字段能力和解释范围 |
| Forward | 117 样本、5 条结算输出 | PENDING 不变成已结算；不冒充 Focus Episode |
| Focus | 独立域、明确工程缺口 | 缺当前生产 Episode 投影，具体接线由 FP-08 完成 |
| 市场四轴 | 独立域、明确工程缺口 | 缺当前日期 owner 绑定；FP-05 定点补算，不引用旧日期替代 |

高级画像共有 5,224 行，其中 11 个身份不在当日 RAW 池；已隔离，不静默扩充股票池。Core 当日发布、四轴接线与 Focus 投影需后续合同和实际运行，不能仅凭本批测试判为全部生产计算闭环。

发现原名称产物有编码损坏后，使用已有 GB18030 解析器只读读取配置 TDX 根下的 TNF / 板块名称文件。仅作为显示和检索装饰，单独记录 10 月 8 日观察时间及原文件 SHA；不改变历史身份、成员关系、资格或 PIT 结论。历史原产物不覆盖。独立审计见 `docs/audits/FP02_CROSS_DOMAIN_SOURCE_GAPS_20261008.md`。

## 运行与证据

```powershell
python -B scripts/capture_fp02_display_names.py
python -B scripts/run_fp02_research_snapshot.py
python -B scripts/run_fp02_research_snapshot.py --daily
python -B scripts/verify_fp02_research_delivery.py
```

日更沿用现有官方交易日历及 capture → QA → owner 接受视图流程，再构建索引、原子发布和读回。当前实际返回 `NO_NEW_COMPLETED_SESSION`，最后处理日仍为 2026-09-30，源请求为 0。新交易日的完整真实生产运行尚不能由这次 no-op 证明，FP-14 运营验收仍须检查 owner 当日算法链。

回滚：`--rollback <当前指针文件SHA256>`，只恢复符合当前元数据合同的前一版本，未通过门的工程草稿不能成为回滚目标。初次迁移也保留旧 UI/reader 独立回退路径；旧 reader 与 `/api/v4/current/*` 继续保留。

`docs/evidence/fp02_20261008/REAL_READBACK_AND_ROLLBACK.json` 证明完整分页无漏项/重复项、12 个真实画像 × 5 字段直接核对、中文/代码检索、四种上下文冲突、真实发布注入失败保持原指针、成功发布后回滚恢复原 token 和指针。`TDX_READBACK.json` 与同日 FP-01 完整源指纹一致：24,493 个文件、5,242,354,968 字节，TDX 未修改。

## 验收与下一阶段

结果：**DEGRADED_PASS（已绑定真实结果接入与索引范围）**。工程接入可消费；当前 Core/四轴/Focus 的明确工程缺口独立保留，不将未知伪装成完成。下一阶段为 FP-03/04 接口和框架联调，后续具体业务闭环按 FP-05–11。

Expected Engine / 风险补充核查见 `REAL_ALGORITHM_SOURCE_AUDIT.json`：E5 既有工程证明包含 fixture 和历史重建，不能当成 9 月 30 日实时推断；缺当前特征、模型与输出绑定的真实 QA。风险已接 health/validity/structure_health/support_state；当前 Core/板块风险缺口需定点补算，不以旧生产权限否定已有引擎。
