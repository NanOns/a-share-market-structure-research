# V4-DYNAMIC-DAILY-R1.1 — DD01–DD07 正式工程交付

全部七项工程已完成，真实运营截止推进至 **2026-10-09**。工程验收不等于独立外审，`EXTERNAL_ACCEPTANCE=NOT_GRANTED`。

| 任务 | 结果与证据 |
|---|---|
| DD01 | 动态正式交易日历、任意连续缺口计划、18:35成熟门；1/2/5/10/20日和跨节跨月受控测试通过 |
| DD02 | 最新TDX包提取历史与真实新日、BaoStock逐日期日线和因子双响应、预算及锁；同网页摘要替换ZIP的实际缓存问题已修复 |
| DD03 | 原算法不改，五日Core/Profile/Native/LOO/Market/Focus/Forward与受影响历史真实重算；固定输入全重算155产物SHA一致 |
| DD04 | 持久Job/Day/Event、AUTO默认ON、无页面自动触发、重试与重启恢复、受限权限和CAS/WAL；真实10/09发布成功 |
| DD05 | 正式工作台真实更新按钮、进度、详细日志、版本与开关；用户指定IAB替代Chrome/Edge，1366/1920实际验收通过 |
| DD06 | 原本地日K聚合RAW/QFQ周月链；10/09全证券当前月146272独立检查零错误，无BaoStock周月或分钟下载 |
| DD07 | 真实CAS后六HTTP同日期/token、旧token409、严格PIT隔离；实际服务重启保留截止日、Job和AUTO；60项回归全部通过；归档结果见独立回读收据 |

正式Head SHA：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`。
前驱10/08：`e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8`。
严格9/30 Head未变：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。
实际AUTO Job：`a85707e650bb42c296fcfec196eabdf3`，19:57:28 `PUBLISHED_FULL`；下一计划2026-10-12 18:35北京时间。

新官方ZIP：551726664字节，SHA `635c775940b2efdb8c9779c9898306c475822517f072c0eddcec8273b14e7ad6`，实际10/09原生5559行；BaoStock真实日线5224与8因子。沿用已接受5224证券池，实际交易5210、停牌14；349包内额外证券不冒充已准入Owner。新版GBBQ经济差异44新增/1移除，以真实版本冻结并重算，不改TDX输入。

发布提交：[d3e32a58](https://github.com/NanOns/a-share-market-structure-research/commit/d3e32a58d793ed7f7ebac26c650be66c4f112fb6)。完整产物清单560文件、33分卷，总3485847955字节。主清单SHA `7f7f8fabd05971a8038888d1c9f829333506b6bf119c78e8b211d772364f6a2a`：[Drive主清单](https://drive.google.com/file/d/1SCiwPWWXrAQcEmpVPOkrXLH34edaURmO/view)，[归档目录](https://drive.google.com/drive/folders/1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD)。云端分卷完成与每个payload的CRC/SHA验收以`DELIVERY_DRIVE_FINAL_READBACK.json`为准，不以主清单上传替代。

详细工程门、真实/模拟证据边界和24门映射见`DYNAMIC_DAILY_EXTERNAL_AUDIT.md`。当前用户AtLogon托管后台，实际验证服务重启，未执行Windows重启。Amount表示差异4946项、历史Amount A、Rotation/Forward外审、原FP页面缺口保持独立开放；不升级历史PIT、自动交易或概率权限。D:/new_tdx为只读输入。
