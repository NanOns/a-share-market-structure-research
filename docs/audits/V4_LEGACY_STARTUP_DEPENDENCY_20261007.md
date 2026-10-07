# Independent service dependency audit item

Audit ID: V4-SERVICE-LEGACY-DEPENDENCY-01.
Scope: startup of the unified V3/legacy workbench against the deliberately clean V4 PostgreSQL baseline. Separate from V4 Shadow engineering and manual UI acceptance.
Evidence: startup on 2026-10-07 failed before listening because workbench.jobs is absent; the accepted reset audit explicitly removed all old legacy/workbench schemas. The source config declares PostgreSQL active, while the unified startup still invokes legacy publication recovery.
Disposition: explicit V4 read-only preview now avoids this dependency without restoring legacy rows. The unified legacy startup remains unavailable against this clean database.
Acceptance: OPEN_FOR_UNIFIED_SERVICE_ARCHITECTURE; preview-specific repair verified independently by the new no-database/write-rejection regression and live HTTP receipt. Closing this broader item requires an authorized unified-service architecture decision and integration acceptance, independently of the current manual V4 preview gate.
