# V3 P08-02：首页双栏与板块详情成员

## 结论

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`、§10、§18.11，P08-02 结果为：**FULL_PASS（双轨本地研究预览）**。

本阶段只交付本地 `/v3` 研究预览页；旧 `/`、`/v2` 和旧 API 保留，不进入 P08-03 的全局清单/个股深度入口。

## 已实现边界

- 新增 `src/workbench_service/static/research-v3.html`，并由 `GET /v3` 提供独立页面。
- CURRENT 与 POTENTIAL 双栏各请求最多 6 张板块卡；每张卡最多展示 3 名后端返回的成员预览。
- CURRENT 卡点击后默认选择 `TODAY_LEADER`；POTENTIAL 卡点击后默认选择 `EARLY_WATCH`。右侧同时展示板块指标、理由、等待/失效条件和成员分页。
- 成员角色可切换 `TODAY_LEADER/CURRENT_RESEARCH/EARLY_WATCH/ALL_MEMBERS`；分页 `total`、`has_more` 和空态由 API 决定。
- 每个上下文、轨道、详情和成员请求使用独立 `AbortController` 与递增序列号；切换日期/板块时取消旧请求，迟到响应不能覆盖当前选择。
- 双栏和详情使用受限网格、窄屏单列布局与成员卡，不使用会撑宽页面的固定大表格。
- `NOT_BUILT`、`EMPTY`、`UNAVAILABLE` 分开呈现；页面不在无 COMPLETE run 时制造数据或触发构建。

## 验收证据

| 检查项 | 结果 |
|---|---|
| P08-02 定向测试 | `2 passed` |
| 静态页面契约 | 双栏、6 卡上限、3 成员预览、角色默认值、AbortController、窄屏 CSS 均存在 |
| `/v3` HTTP smoke | `200` 返回页面；请求前后不创建 `research_runs` 表 |
| JavaScript 语法 | Node `vm.Script` 解析通过 |
| 旧回归 | `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：`215 passed in 59.24s` |
| 静态检查 | `python -m compileall -q src scripts`、`git diff --check`：PASS |

## 真实数据范围与下一步

当前生产数据库没有被本阶段伪造激活的 COMPLETE research run，因此页面真实访问会显示 `NOT_BUILT/EMPTY` 安全空态；定向 UI 证据验证页面合同和请求边界，不冒充真实市场截图。下一阶段进入 P08-03。
