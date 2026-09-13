# V3 P10-02：集合筛选和跨页关联

## 阶段合同

执行前读取了最新适用升级文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，适用范围为 §12、§18.13 P10-02、§20.3–§20.8；本阶段合同为 `V3_P10_SECTOR_SET_LINKAGE_V1_0`，旧集合兼容合同仍为 `M11_SECTOR_INTERSECTION_V1_0`。

目标是把板块、股票和交集接成一条可回返路径：用户可以通过名称搜索选择 2–4 个板块；API14 先执行旧成员集合，再按已完成的 `research_context` 角色过滤，最后计算总数、排序和分页；V3 个股详情的主/备板块链接携带原发布日、交易日和 context；交集结果打开个股证据后关闭仍保留联动选择状态。未传新增参数的旧 API14 请求走原字段和原输出形状。

## 实现

- `src/workbench_service/intersection.py` 增加可选 `include_sector_names/exclude_sector_names/research_context_id/member_role` 校验；旧字段仍按 M11 规则处理。
- `src/workbench_service/app.py` 在 API14 内按同一 `sector_base_daily` 快照解析名称；名称不存在或不唯一时 fail-closed；角色使用 `research_sector_member_roles`，`ALL_MEMBERS` 保持旧成员集合语义；context 的发布日和交易日不匹配时拒绝。
- `src/workbench_service/static/v2/index.html`、`app.js`、`router.js`、`api.js` 增加板块名称候选、2–4 个选择 chips、研究角色、context 路由保持和旧输入兼容；分页查询仍由服务端返回 `total` 后计算页数。
- `src/workbench_service/static/research-v3.html` 为个股主板块、备选板块和角色板块生成联动链接，携带 `publication_id/trade_date/context_id/member_role`。

## 输入、来源、计算与落点

| 能力 | 输入/来源 | 计算 | 存储 | API/页面 |
|---|---|---|---|---|
| 名称选择 | `/api/sector-library` 当前发布绑定的 `sector_base_daily` | 服务端候选；选中后保存 ID+名称到前端状态 | 不新增库表 | `/v2?page=linkage` |
| 集合交并排除 | API14 旧成员快照 | 先集合、再角色、再显示过滤/排序/分页 | 不新增集合快照 | `POST /api/sector-intersection/query` |
| 研究角色 | `research_context_id` 对应 COMPLETE run；角色表只读 | `TODAY_LEADER/CURRENT_RESEARCH/EARLY_WATCH` 按 selected sectors 过滤；`ALL_MEMBERS` 不改变旧集合 | 不写 run 或成员表 | API14 返回 context/role 证据 |
| 主/备板块回返 | V3 stock `shortlists` 与 `sector_roles` | 生成到旧联动页的 context-bound URL | 不新增链接表 | V3 个股 modal |
| 证据回返 | V2 个股透视路由和 linkage state | modal close 只清 `security_id/tab/days`，不清板块选择/context | 不新增历史状态 | V2 linkage + stock insight |

明确排除：P10-03 的前瞻结果、基线和效果判断不在本阶段；不创建自动交易、概率字段或新的 TDX 输出。

## 证据与验收

阶段脚本：`scripts/verify_p10_02_sector_set_linkage.py`；机器回执：`reports/upgrade_v3/P10-02-SECTOR-SET-LINKAGE.json`。

验收覆盖：

1. 真实只读发布上用名称选 2 个板块，服务端返回解析后的 ID，API14 新合同和 `total == candidate_total_before_filters` 成立。
2. 真实 COMPLETE context 上用 `TODAY_LEADER` 过滤，返回成员属于角色集合，且过滤发生在分页前。
3. 不传新参数的旧 API14 请求不出现 context/role/name 新字段，M11 原测试继续通过。
4. V2 名称选择、候选、角色和路由保持以及 V3 主/备板块链接静态证据存在；Node 语法、compileall 和 diff check 通过。

## 阶段结论与下一步

P10-02 只有在机器回执为 `FULL_PASS` 时关闭。本阶段不宣称信号提前效果；下一阶段为 `P10-03`，进入前瞻结果和简单基线记录。
