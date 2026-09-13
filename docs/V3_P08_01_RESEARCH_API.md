# V3 P08-01：本地研究 API 与上下文

## 结论

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`、§10、§18.11，P08-01 结果为：**FULL_PASS（只读 API 与上下文合同）**。

本阶段只接入本地研究读取路径，不启动构建、不进入首页 UI、不进入 P08-02；未访问或修改 TDX，未写生产数据库。

## 已实现边界

- 新增 `research_context.py`：context 身份由合同、run、发布、日期、模式、快照和算法版本规范化摘要生成；仅 `research_runs.status='COMPLETE'` 可解析为 READY。
- 新增 `research_queries.py`：只读实现 context、home/local、sectors、sector detail、members、shortlist、stock detail/evidence、sector signals、search suggest。
- `app.py` 新增 `/api/v3` 路由；旧 `/api/*` 路由保持不变。
- 未发现 COMPLETE run 时，context 返回 `200 + NOT_BUILT`，不安装 run schema、不生成假 `run_id`、不触发全市场构建。
- 所有本地列表统一返回 `status、total_eligible、eligible_total、returned_count、total、page、page_size、has_more、items、context`；页大小默认 20、最大 50；非法分页、轨道、角色、排序、搜索条件 fail-closed。
- `ALL_MEMBERS` 读取绑定 membership snapshot；前三类角色只读 `research_sector_member_roles`，不回接旧 candidate/association 排名；名称仅从发布绑定的旧事实表补齐。

## 验收证据

| 检查项 | 结果 |
|---|---|
| P08-01 定向测试 | `4 passed` |
| NOT_BUILT HTTP smoke | `200` 返回 `NOT_BUILT`；请求前后 `research_runs` 表仍不存在 |
| COMPLETE context/list | 合成 COMPLETE run 可解析 READY；`total` 先于分页计算，`has_more` 正确 |
| 错误边界 | 未知 context、非法分页、未知 track、跨身份读取均拒绝 |
| 旧回归 | `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：`213 passed in 57.93s` |
| 静态检查 | `python -m compileall -q src scripts`、`git diff --check`：PASS |

## 范围与下一步

生产环境当前没有被本阶段伪造激活的研究 run，因此真实 API 继续按 `NOT_BUILT/EMPTY` 语义 fail-closed；本阶段没有把合成数据当作真实市场结果。下一阶段进入 P08-02，接首页双栏和板块详情成员展示。
