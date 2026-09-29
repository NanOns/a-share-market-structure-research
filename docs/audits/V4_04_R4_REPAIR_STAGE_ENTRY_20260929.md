# V4-04 R4 repair stage entry

- Starting HEAD: `1af58725b8c486904ed5149b6427739b9f2b051f`.
- Entry disposition: `V4_04_EXTERNAL_ACCEPTANCE_BLOCKED_R2_FINAL_REPAIR_REQUIRED`.
- Authority: `AGENTS.md`, REV2 executable contract, accepted V4-00–V4-03 heads, V4-04 R2 and R3 tasks, and the R4 external audit task copied to `docs/evidence/`.
- Scope: F01 technical window status validation, F02 independent machine branch and vector coverage, F03 direct source recomputation of bias20_atr and dist_high20_atr. Publish an R3 candidate and receipts only after all gates pass.
- Preserve R1 and R2 code artifacts and evidence. V4-05 remains NOT_STARTED, and no V4-04 Accepted Head may be promoted before external acceptance.
- Cross-cutting global pytest collection issue remains independently tracked under `docs/audits/V4_GLOBAL_PYTEST_COLLECTION_AUDIT_ITEM_R1_20260929.md`.
