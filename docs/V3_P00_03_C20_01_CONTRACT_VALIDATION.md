# V3 P00-03 C20-01 追加复验

## 阶段合同

依据当前 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851` §20.2、§20.5：

- `date` 必须符合 `YYYY-MM-DD` 且能被真实日历解析。
- `timestamp` 必须是合法 ISO8601 datetime，使用 `T` 分隔并携带时区。
- `number` 和 `scalar` 中的数值必须是有限值；布尔值不能作为 number。
- 本补项不修改冻结配置文件及其参数哈希，不改写旧数据库时间列。

## 修复

修改 `src/workbench_service/research_v3_contracts.py`：使用 `date.fromisoformat`、`datetime.fromisoformat` 与时区存在性检查；所有 number/scalar 数值经过 `math.isfinite` 校验，并对整数转浮点溢出 fail-closed。

## 验收证据

- `2024-02-29` 通过；`2026-02-29`、`2026-99-99`、非零填充日期拒绝。
- `2026-09-10T12:30:00+08:00` 通过；无时区、空格分隔、非法日期和普通文本拒绝。
- `NaN`、`Infinity`、`-Infinity` 在 number 与 scalar 路径均拒绝。
- P00-03 合同测试：`8 passed`。

## 验收结论与下一项

**C20-01：PASS。** 本补项不等同于 P00-03 全部复核项完成；配置公式对照、在线 DTO 和 P04-02 生产入口仍按最新 V3 台账独立跟踪。下一项为 `P04-02-INTEGRATION`，不执行 P04-03。
