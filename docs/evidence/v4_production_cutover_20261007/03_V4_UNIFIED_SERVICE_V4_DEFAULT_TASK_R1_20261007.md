# P0-3｜V4 Unified Service 默认生产服务修复任务卡 R1｜2026-10-07

- Priority: P0
- Depends on: P0-1 contract
- Can run in parallel with: P0-2

## 1. 背景

当前普通 `run_workbench_service.py` 仍依赖 legacy publication recovery。

当前 clean V4 PostgreSQL baseline 已有意清理 legacy `workbench` schema，因此普通启动链可能失败。

现有临时修复：

```text
--v4-shadow-only
```

虽然能启动，但它：

```text
legacy_workbench_available=false
no database
Shadow only
```

不适合作为正式 V4 production service。

---

## 2. 目标

建立正式：

```text
V4_DEFAULT_WORKBENCH_SERVICE_V1
```

“default workbench” 指产品默认版本切到 V4；它不自行授予 capability 生产权限。

使 V4 正式工作台：

- 不依赖 legacy `workbench.jobs`；
- 不恢复已清理 legacy 数据；
- 不要求 V3 schema；
- 可读取 current accepted V4 authority；
- Shadow diagnostics 独立存在；
- UI read-only；
- daily pipeline writer 与 UI reader 解耦。

---

## 3. 服务模式

建议：

```text
python run_workbench_service.py --v4-default
```

可保留兼容别名：

```text
--v4-production
```

但 service status 必须同时返回 capability permission map，避免把产品版本和算法生产权限混为一谈。

并在完成切换后：

```text
run_workbench_service.py
```

默认也进入 V4 production mode。

如必须保留 legacy：

```text
--legacy-v3
```

必须显式指定，不得再是默认。

---

## 4. API

新增：

```text
/api/v4/current/context
/api/v4/current/summary
/api/v4/current/radar
/api/v4/current/entity
/api/v4/current/sector
/api/v4/current/cohort
/api/v4/current/settlement
/api/v4/current/health
```

保留：

```text
/api/v4/shadow/*
```

生产 current API 与 Shadow API 不共享“是否有 real shadow sample”的全局 gating。

---

## 5. Operations status

`/api/operations/status` 必须返回：

```json
{
  "service_state": "READY",
  "service_mode": "V4_DEFAULT_WORKBENCH",
  "product_version": "V4",
  "default_ui": "V4",
  "current_accepted_reader": true,
  "shadow_diagnostics": true,
  "legacy_v3_default": false,
  "read_only_ui": true
}
```

并提供：

```text
last_accepted_trade_date
freshness_state
stage
data_head_digest
```

---

## 6. 启动依赖

生产服务启动不得要求：

```text
legacy publication recovery
workbench.jobs
V3 Focus tables
real Shadow publication
tomorrow daily data
```

如果 current accepted authority 可验证，服务必须启动。

---

## 7. 生产数据存储

允许读取：

```text
accepted repository artifacts
正式 V4 PostgreSQL / SQLite store（如果已由 accepted contract 指定）
```

禁止：

```text
任意 latest DB
环境变量偷偷改变 authority
测试 DB fallback
simulation fallback
legacy V3 fallback
```

---

## 8. One-click launcher

同步修复：

```text
OPEN_RESEARCH_WORKBENCH.cmd
OPEN_UNIFIED_WORKBENCH.cmd
START_WORKBENCH_TRAY.cmd
```

最终普通用户双击应打开：

```text
V4 production home
```

而不是 V3 / Shadow-only preview。

---

## 9. 测试

至少：

```text
service_starts_without_legacy_workbench_schema
service_starts_without_real_shadow
root_is_v4_production
v4_current_routes_200
v4_shadow_routes_preserved
legacy_route_not_default
writes_rejected_from_ui
authority_digest_mismatch_blocks_only_affected_scope
restart_same_context
```

---

## 10. 不允许

不得通过以下方式“修启动”：

```text
重新建 legacy workbench schema
复制旧 V3 rows
让 V4 默认服务继续依赖 V3 recovery
关闭 digest 校验
catch all exception 后返回假 READY
```

---

## 11. 退出条件

```text
V4_PRODUCTION_SERVICE = PASS_LOCAL
LEGACY_STARTUP_DEPENDENCY = CLOSED_FOR_DEFAULT_V4
SHADOW_DIAGNOSTIC = PRESERVED
ONE_CLICK_V4 = PASS
```

## 12. Permission map

`/api/operations/status` 必须读取 V4-19 authority，并返回真实：

```text
production_permission.STOCK_CORE
production_permission.STOCK_SECTOR_DEPENDENT
production_permission.SECTOR_STAGE
production_permission.ROTATION
production_permission.SECTOR_RISK_CHANGE
```

本卡不得 hardcode true。
