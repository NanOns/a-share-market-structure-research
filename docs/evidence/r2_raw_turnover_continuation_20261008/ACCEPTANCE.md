# RAW 成交额与成交量显示独立验收

AUD_R2_RAW_AMOUNT_VOLUME_PRESENTATION：DEGRADED_PASS / SCOPED_OPERATIONAL_RELEASE_PASS。代码提交 aceec978422f6e8c08d61a400da1fcfaeaac4397。

接受 9/30 RAW 5213 个证券，amount/volume 原数值无缩放、无复权。股票单元全量 10426 次与 RAW 比较、10426 次与当日图表序列比较一致；全部 5213 正成交量记录的 amount/volume 位于当日 high/low 的 5% 容差范围。人民币元/股依据已接受 A 股 TDX .day 单位合同；原 RAW 单位元数据未改。先前股票字段全量与前驱一致。

独立从实际序列重算前 5/20 会话成交额/成交量比（不含当日）：20768 次一致；owner 原 UNKNOWN 继续保留，不因为 RAW 有数值自行升级缺窗口的因子。

17 tests passed，覆盖错日、未知单位、负值和非有限值，E 登记隔离目录。IAB 10 股票 × 2 桌面 × 2 字段共 40 次显示和来源单元逐值核对，无控制台错误。新 snapshot/UI 隔离联合 CAS 健康失败精确恢复、重复 NOOP；正式六入口读回同版本通过，真实页面显示 82291392 元 / 6221484 股。版本 V6 日更准入直接 NOOP，RAW OHLC 20852 次、实际 Forward 到期 0；每日 CLI NO_NEW_COMPLETED_SESSION / Focus NOOP / 源网络请求 0。

字段后继矩阵仍 110 行：owner_source_ready 62，UI 18，数值/阈值 oracle 15，browser/product_pass 16。这里不是全功能完成。下一关：剩余已有源字段的独立 owner/公式/UI 验收。

本项不关闭 M10 Amount A 跨模块算法审计，不提供换手率分母、不证明严格历史 PIT。FULL_PRODUCT_RELEASE_BLOCKED。
