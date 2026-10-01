# V4-10 R1.2 closure

V4_10_R1_2_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT

Tested implementation: `6a339e71d38ced6e97c077fddef8dc7a8dfbd104`.
Clean detached regression: 1116 passed / 2 skipped / 0 failures / 0 errors; only the existing authorized historical node deselected.
180 static vectors PASS. Original 149 expected values retained with explicit fixture adaptation. G01–G22 and no-symbol PASS.

Real OLD→CURRENT authority, no-op rejection, implemented-status authority, trusted TRUE suppression defenses, controlled publisher/ordinary reader permission separation, legacy row readback, append-only/revisions and exact 024 schema/role/grant rollback all pass.

Original 022/023, R1/R1.1 configurations/reports, V4-09 runtime and accepted heads remain unchanged. Business thresholds remain 2/10/3/3. No production/shadow/Focus permission; V4-10 Accepted Head is absent.

Independent V0 source is a frozen engineering golden, not a market acceptance claim. Accepted migration correctly stays UNKNOWN until required detector owners arrive; no fake enrollment. Only the trusted owner imports source authority; publisher credentials are not provisioned to ordinary applications.

Cross-stage master first-entry package e368f87 separately records nine OPEN work packages and A01/A08/A09 implementation entries. It does not claim capability repairs or external acceptance.

| Gate | Result |
| --- | --- |
| G01_V4_09_unchanged | PASS |
| G02_prior_content_identity | PASS |
| G03_calendar_lineage | PASS |
| G04_input_manifest_shape | PASS |
| G05_real_old_current_boundary | PASS |
| G06_noop_rejected | PASS |
| G07_implemented_status_authority | PASS |
| G08_implemented_unknown_publication | PASS |
| G09_true_not_suppressed | PASS |
| G10_not_implemented_missing_owner_only | PASS |
| G11_not_applicable_scope | PASS |
| G12_ordinary_direct_insert_denied | PASS |
| G13_controlled_publisher_positive | PASS |
| G14_DB_identity_lineage | PASS |
| G15_022_023_unchanged | PASS |
| G16_024_exact_rollback | PASS |
| G17_original_149_expectations | PASS |
| G18_new_negative_vectors | PASS |
| G19_clean_detached_regression | PASS |
| G20_no_new_deselect | PASS |
| G21_permissions_false | PASS |
| G22_accepted_head_absent | PASS |
| NO_SYMBOL | PASS |

STOP for independent external R1.2 reaudit. V4-11 remains blocked; a push is not external acceptance.
