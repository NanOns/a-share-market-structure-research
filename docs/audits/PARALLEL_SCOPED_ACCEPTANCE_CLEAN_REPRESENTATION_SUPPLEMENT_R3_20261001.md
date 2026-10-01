# Scoped formalization clean checkout representation repair R3

The first whole clean checkout stopped in the new scoped-record validator because two historical protected Head bindings refer to original CRLF bytes, while the repository preserves their explicitly registered LF representations. This is a representation mismatch, not permission to rewrite a historical binding or normalize arbitrary hashes.

Before repair, the complete current new runtime module, targeted test source and R2 formalization script were archived byte-for-byte under `data/v4/source_evidence/next_round_r2_clean_repair/`. The original logical bindings and archive bindings are retained by `CLEAN_REPAIR_ORIGINAL_SOURCE_ARCHIVES_R1.json` and `CLEAN_REPRESENTATION_SOURCE_SUPERSESSION_R1.json`. All earlier closures and acceptance records remain unchanged.

The actual `validate_record` API now applies a separate resolver only to `protected_heads`. It permits exactly the two previously registered original bindings: `V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json` and `V4_03_ACCEPTED_HEAD.json`. The prior representation metadata is fixed at 1,666 bytes, SHA-256 `8a3b878ef00b2540eda1f1280e7a0faf7438e699c9704beec0823c1351a9e405`. Its declaration cannot be replaced by caller-created metadata. The exact original binding, original archive SHA/size, current canonical SHA/size, and original-CRLF-to-current-LF byte equality are independently verified. Every evidence, runtime and other source binding still uses the strict original hash/path reader.

Nineteen dedicated tests pass, including actual A03 `validate_record` execution against copied LF checkout inputs. Altered current bytes, original archive bytes, metadata, caller hash/size/path, missing archives and unregistered heads are rejected. Moving either registered protected binding into evidence or runtime inputs does not enable the representation resolver.

The new R3 formalization script creates semantic readback R4 without changing any old report. Readback passes the five scoped records, exact immutable A03 capture replay, A07 capture-time boundary, fail-closed A06, inactive Owner metadata and concurrent history/current validator boundaries. Targeted regression passes **184 tests**, with zero failures/errors/skips.

The current closure is `reports/next_round_r2/scoped_acceptance/SCOPED_FORMALIZATION_CLOSURE_R3.json`, binding readback R4, targeted tests R4, the new runtime and source supersession. No new full No-Symbol result is claimed here: the parent must run the new whole clean checkout, scan and joint regression against the new committed source. The previous exact scan remains historical evidence.

No old Accepted Head, accepted validator, scanner, policy, source artifact, acceptance record or evidence was modified. Data/Stage Head and Production/Shadow/Focus/global adoption remain unchanged.
