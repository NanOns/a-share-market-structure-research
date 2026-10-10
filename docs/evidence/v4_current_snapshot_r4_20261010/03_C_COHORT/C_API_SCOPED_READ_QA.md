# R4-C API scope

The BFF production statistics route now calls read_authorized_statistics through its trusted exact Head token; owner JSON booleans alone are rejected. Current Head has no validation_cohort owner for any of the five dates, so observed/matured/settled denominator remains unknown. Required domain reasons are NO_AUTHORIZED_COHORT_OWNER, NO_AUTHORIZED_SETTLEMENT_OWNER and MODEL_OR_PERMISSION_NOT_READY; product API/live process receipts are owned by R4-E/root and must be consulted for runtime acceptance.

C unit receipts establish hash, grant, source issuance, freeze and candidate publication scope only. They do not establish live UI/runtime acceptance. Focus remains a separate episode source; no Focus rows enter this inventory or observed cohort counts. No endpoint activation or production write occurred in C.
