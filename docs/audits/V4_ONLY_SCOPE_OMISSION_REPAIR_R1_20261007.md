# V4-only 外审范围遗漏修复 R1

外审基线 d68adc4a。修复 root test selector 的大小写敏感判断，将源码中的 V4_ 合同同样识别为 V4。旧 212 个测试文件绑定全部不变，新增遗漏的 test_r17a_historical_governance.py 和一项实际仓库范围防复发测试，当前 214 个文件。

新增文件实际执行 14 个节点，全部通过。全范围重新 collection 的逐节点集合与此前外审认可的 4759 节点及本次新增执行的并集完全一致。归并验收：4773 total，4771 passed，0 failed，0 errors，2 platform symlink skipped（原 V4 portable equivalents 已通过）。没有 ignore/deselect/xfail。未再重跑 41 分钟的原已验收 profile；不是一次新全量零错误声明。原始 XML、collection ledger 与依赖绑定完整保留。

本次补跑前后全部 TDX 指纹相同，保护的运行目录 bytes/mtime、已接受头、SQL migration 均不变。旧事故 5 次写入、4 文件、zero-write=false 永久保留。IA-07 能力债务保持，不授权运行、shadow、production、focus、default UI，不增加真实样本，不运行 pre-V4 测试。

候选结论：CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。新外部验收尚未取得，commit/push 不代表进入后续门禁阶段。
