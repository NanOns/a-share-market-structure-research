# FIX-D isolated PostgreSQL regression continuation

Status: ISOLATED_DB_REGRESSION_PASS, engineering scope only; EXTERNAL_RECHECK_REQUESTED.

The 22 historical setup errors were the `db` fixture consumers in `tests/fep_e5/test_e5_contract.py`. The previous default port 55488 was rejected by `tests/remainder_isolation_plugin.py` before access. This continuation used an entirely new PostgreSQL 18.6 cluster on G:/codex_tmp/test_temp/r4_d_db_20261010_55546/data, loopback port 55546, database fep_e5_legacy_fixture. The existing isolation guard remained enabled and checked actual data_directory against the registered manifest. No production/legacy database connection, migration, scoring or service installation was performed.

All 50 tests in the pinned file passed (22 database cases and 28 other contract cases), exit 0, 2.41 seconds. The exact 22 nodes and source digest are in D_DB_REGRESSION_RECEIPT.json. The tests cover grant capability rejection, frozen prediction revisions, atomic prediction/receipt rollback, independent priority failure, CAS/revocation, exact output binding, actual HTTP context and append-only triggers. All isolated fact table counts were zero after fixture rollback. No code defect emerged, so no production code changed.

The cluster was normally stopped using pg_ctl -m fast -w stop; postmaster.pid is absent. Data and logs are retained only on G: for replay.

Replay uses E:/Postgres/bin read-only installed binaries; start the above G: cluster using pg_ctl -D <data> -l <G:log> -o "-p 55546 -h 127.0.0.1" -w start. Set TMP/TEMP/TMPDIR=G:/codex_tmp, PYTHONDONTWRITEBYTECODE=1, FEP_E5_TEST_DSN="host=127.0.0.1 port=55546 user=r4_isolated_admin dbname=fep_e5_legacy_fixture", REMAINDER_TEST_TEMP_BASE=G:/codex_tmp/test_temp and REMAINDER_PG_CLUSTER_MANIFEST=<repo>/reports/r4_d_db_continuation_20261010/CLUSTER_MANIFEST.json. Run python -m pytest tests/fep_e5/test_e5_contract.py -q -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/r4_d_db_replay. Stop with pg_ctl -D <data> -m fast -w stop. Choose a fresh G: basetemp for each replay.

Acceptance limit: this closes the 22-case database setup/regression blocker; it does not admit a formal production authorization adapter, turn historical reconstruction into as-recorded evidence, change Accepted Heads, or establish external acceptance. Next stage: independent review; production adapter remains separately gated.
