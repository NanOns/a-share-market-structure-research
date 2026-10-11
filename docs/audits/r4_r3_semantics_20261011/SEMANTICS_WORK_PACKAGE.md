# R4 R3 P0-4 语义包工程回执

状态：`SCOPED_EXACT_CONSUMER_PROGRESS / FULL_SEMANTICS_OPEN`。本包不签全系统工程、独立外审、历史 PIT 或生产准入。

执行合同是 R3 任务卡的 P0-4、上位 R4 PostgreSQL-only 总合同与 V4.2.2 REV4 正文 §87A。继承 R2_DISPOSITION 中 FA-016 的数值候选通过、完整消费者未通过的事实。没有修改旧 accepted Owner、v0.2 源码、TDX 输入或生产配置；新函数没有数据库连接，也没有默认生产接管。

## 实际代码及运行

`exact_factor_transport_r1.py` 补身份、合法日历日期、未来日期、正乘数、位长、字典形状校验。过去缺损形状可能产生 AttributeError/TypeError；现在给稳定的 fail-closed ValueError，不使用近似 Decimal 恢复缺失 exact 系数。

新增 `exact_ohlc_consumer_r1.py` 从原始事件源字节计算 SHA256，逐行绑定证券/日期/basis，消费有理数 numerator/denominator；拒绝 float 原价证据、非有限/非正原价、错误 OHLC 和源摘要漂移，负复权价返回 NONPOSITIVE_QFQ。所有输出显式为 ISOLATED_CANDIDATE_ONLY / RECONSTRUCTED / PIT_ELIGIBLE=false，保持准入与数值计算分离。

实际运行 36 PASS / 0 FAIL / 0 ERROR，原始日志、JUnit 和命令见本目录。运行源以 EXECUTION_SOURCE_BINDINGS.json 的未提交字节 SHA256 为准，随后提交的 Git SHA 不能冒充运行时源。此后整合修改须重新运行影响测试并生成新绑定。

独立对照包括按事件顺序直接计算价格的 Decimal 消费 oracle、旧有独立 chronological rational oracle 的 250×3 价格案例、7股16原冻结差异。负例包括四 exact 字段缺失、五损坏 coefficient 形状、五非法日期、未来日期、source 字节漂移、row 身份错配、五非法原价、错误 OHLC 和负复权质量。新消费函数仅按源字节绑定 typed 因子；并不证明源的首获时间、公司行为完备性或正式 source grant。

## 未关闭范围与逐项条件

`EXACT_FACTOR_56_CONSUMERS.csv` 保留原 A4 的全部56模块及其旧/当前源 hash。56是旧静态模块索引，不是56个已经证实的真实调用类别。每项完整消费状态仍 UNTESTED/OPEN，未凭文件名排除 legacy；必须结合父包动态 graph，给每项实际受支持入口、源字节、数值变化、独立 oracle、PIT/质量、API/UI/Rank/Core/Focus/Forward影响才能关闭。当前新增一个隔离直接消费函数的36测试不能替代此门。不能直接切 v0.2 accepted Owner，因为其源码/内容身份有冻结接受约束。

`V4_NORMATIVE_ATOM_DENOMINATOR.json` 给238个 modal-line候选、去重规则和全文位置。正式规范原子分母保持 null：modal line 可能含多条要求，非 modal 公式、表格、代码仍须审。不是84版本/674注册记录/37,264属性的代换；也不得把238报成合法原子总数。

`V4_FIELD_SEMANTIC_COMPLIANCE.csv` 完整保存 §87A 的121个分号字段表达式、源行、合同、输入、阶段、缺失规则和每项关闭条件。表达式含 RPS5/20、pos60/250 等族别，121不是版本化字段总数。每项必须展开为具体 versioned field，并绑定公式/单位/窗口/阈值/源首获/PG schema/索引/横截面/真实生产者/消费者/API/UI/反事实。Core、Amount A、Sector、D0/D1/D2、Focus/Cohort和Forward全量语义审仍 OPEN。

H21、真实首获和Forward成熟独立为真实来源/成熟条件；它们不阻止上述尚未完成的立即可执行工程门。正式 source/Owner promotion、生产切换保持 PENDING_PERMISSION，不从本包、push 或 scoped tests 推断授权。

## 可重放

环境 TMP/TEMP/TMPDIR=G:/codex_tmp，pytest --basetemp=G:/codex_tmp/test_temp/semantics_r3_final。源码 src 加 PYTHONPATH；运行 EXECUTION_SOURCE_BINDINGS.json 所记命令，再运行 `python scripts/audit_r4_r3_semantics.py`。脚本只写本目录，原56静态索引和旧证据保持只读。

审计 owner：Codex / semantics。独立审核者需先核源码字节，再重放原始测试，最后逐项审核 OPEN 的真正消费与语义关闭条件。B1本包只是可审核增量，没有满足B2全系统门。
