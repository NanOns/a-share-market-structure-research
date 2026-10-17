---
stage_id: V4_R17_OWNER_API_FRONTEND_LINEAGE_20261016
code_sha: 0473cbb84
test_scope: v4-publication-candidate-owner-contract-and-bff-page-lineage-focused
conclusion: BFF_CONTRACT_PASS_E2E_PARTIAL_NO_PG_BROWSER_NOT_RUN
approval_status: CODE_AND_STATIC_UI_AUDIT_AUTHORIZED
---

# V4 R17 Owner—七 API—前端数据接线阶段报告 R1

逐字段链路矩阵与现役缺口见 `docs/upgrade/V4_R17_OWNER_API_FRONTEND_LINEAGE_MATRIX_R1_20261016.md`。七接口为 summary/radar/entity/sector/cohort/settlement/health；与六个导航入口加单独首页的产品表面分开记录。保持严格的 candidate context token、trade_date 和 namespace 一致性，前端不跨 Head 回退；现场 Owner root mapping 为空。

代码修复：`PgV4CurrentAdapter` 在 publication-bound page rows 存在时即回报 `DEGRADED`（无 rows 且无 Owner 才为 `PENDING`），不要求 lifecycle 等页面另有 Owner family 才承认存在的 partial result；各字段仍逐项标明来源缺口。新增回归断言覆盖 entity lifecycle rows → `DEGRADED`。

定向测试计划：`python -m pytest --confcutdir=tests -q -p no:cacheprovider tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py tests/test_v4_pg_publication_contract_static.py tests/test_v4_server_pg_candidate_mode.py`。执行结果：73 passed。测试覆盖 BFF 候选契约、Owner 字段投影、静态 API 合同和 server candidate mode；未启动 HTTP 服务或浏览器，不能作为浏览器实际渲染验证。

状态：`CODE=PASS_FOCUSED_SUITE_73`；`OWNER_MAP=BLOCKED_NO_AUTHORIZED_ROOT_MAPPING`；`API_SEVEN=CONTRACT_PARTIAL`；`BROWSER=NOT_RUN_NO_28766_SERVICE`；`PG_LIVE=NOT_RUN_NO_READER_DSN`；真实页面数据闭环为 `E2E_PARTIAL_NO_PG`，不宣称生产验收。

