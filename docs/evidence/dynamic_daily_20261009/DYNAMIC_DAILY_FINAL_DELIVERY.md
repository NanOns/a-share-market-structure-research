# DD01–DD07 关键交付说明

七项工程任务已完成，真实运营截止为 **2026-10-09**，自动更新开启。独立外审仍为 `NOT_GRANTED`。

| 任务 | 结果 |
|---|---|
| DD01 | 动态交易日历、连续缺口计划、18:35成熟门；1/2/5/10/20日与跨节跨月受控测试通过 |
| DD02 | 最新TDX包真实提取旧日和新日；BaoStock逐日日线/因子双响应；修复同网页日期替换ZIP的缓存问题 |
| DD03 | 原算法不改，五日完整Owner和受影响历史重算完成；固定输入155产物全SHA一致 |
| DD04 | 持久Job、AUTO默认ON、无页面调度、重试、发布CAS与故障恢复；真实新日发布成功 |
| DD05 | 正式工作台真实按钮与进度；按用户要求以IAB验收1366/1920；截止日与发布状态可见 |
| DD06 | 本地日K派生RAW/QFQ周月；10/09全证券146272独立检查零错误 |
| DD07 | 实际CAS后六接口同日期/token、旧token409、严格PIT隔离、发布后服务重启；60项回归通过；关键文件本地交付 |

实际任务 `a85707e650bb42c296fcfec196eabdf3` 于19:57:28（北京时间）完成 `PUBLISHED_FULL`。下一计划为2026-10-12 18:35。
TDX实际10/09有5559原生行，BaoStock日线5224行、因子8行。沿用已接受5224证券池，实际交易5210、停牌14；额外证券不冒充新增Owner准入。

正式Head SHA：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`。
严格9/30 Head未变：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。
源ZIP SHA：`635c775940b2efdb8c9779c9898306c475822517f072c0eddcec8273b14e7ad6`。

直接查看 `DD07_KEY_DATA.json` 可获取关键数字；其他JSON为真实发布、数值QA、服务重启和测试收据。截图为实际页面。`KEY_FILES_MANIFEST.json` 列出小包每个文件的SHA。
全部文件也以散文件提供，可以直接从网页上传，不必解压ZIP。按用户最新要求停止大文件API上传，完整数值产物仍保留本地；不把此前部分云端上传写成全量云端归档通过。

实际验证了服务重启，未执行Windows重启。Amount表示差异4946项、历史Amount A、Rotation/Forward外审和原FP页面缺口保持独立开放；不升级PIT或交易权限。TDX目录只读。

发布提交：[d3e32a58](https://github.com/NanOns/a-share-market-structure-research/commit/d3e32a58d793ed7f7ebac26c650be66c4f112fb6)。最终关键交付提交由小包清单记录。
