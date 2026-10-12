# 原始运行命令

cwd: G:/codex work/s1-b-20261012。PowerShell child 环境：TMP=TEMP=TMPDIR=G:/codex_tmp，PYTHONDONTWRITEBYTECODE=1，PYTHONPATH=src;.，V4_NATIVE_PG_DSN=host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres，R4_PG_DATA_DIRECTORY=G:/codex_tmp/full_system_r4_fbd23a6b/pg_data。

```
git worktree add -b codex/s1-b-20261012 G:/codex work/s1-b-20261012 96b466a
```

首次 checkout 在 LFS smudge 下载中非常缓慢，终止本次创建命令，移除本次残留 index.lock 后，在新工作树设置 GIT_LFS_SKIP_SMUDGE=1：

```
git sparse-checkout init --cone
git sparse-checkout set src scripts tests config docs/audits/r4_r3_local_delivery_20261012
git reset --hard 96b466a
```

只重置新建的本次工作树，不触碰旧工作树。稀疏 checkout 不读取本次未使用的大型 data/reports。冻结运行数据从已知 G: 路径及 SHA 读取。

最终测试（R4_NATIVE_ISOLATION=1；R4_CONNECTION_LEDGER=G:/codex_tmp/s1b_tests_intents_r3.jsonl）：

```
python -m pytest tests/test_v4_focus_source_identity_r4.py tests/test_v4_joint_pg_content_r2.py --basetemp=G:/codex_tmp/test_temp/s1b_r3 -o cache_dir=G:/codex_tmp/pytest_cache_s1b --junitxml=docs/audits/s1b_20261012/TESTS_FINAL.xml -q
python scripts/run_s1b_identity_http.py R4
```

先前测试 R1 因漏设 R4_NATIVE_ISOLATION 而加载旧隔离 profile，在 configure 阶段被拒绝；没有测试通过。补设后 R2 为 20 PASS，最终增加共享映射测试后 R3 为 21 PASS。最终只计 21 个唯一节点。

HTTP R1/R2/R3 为迭代运行，资格见 EXIT_REPORT。最终 R4 EXECUTION 记录 argv、cwd、UTC 时间、脚本 SHA 与 PG 意图 SHA。对照检查只用冻结文件与本地隔离 PG，没有网络数据采集、TDX 写入、Drive 调用、生产权限更改。

```
python scripts/package_s1b_delivery.py
```

打包脚本要求 final RESULT 的脚本/修复源码 SHA 与当前文件一致，重算 ZIP 每个条目的 SHA，检验唯一清单自身豁免，报告最终 HEAD。接受门禁保持 NOT_FULL_PASS。
