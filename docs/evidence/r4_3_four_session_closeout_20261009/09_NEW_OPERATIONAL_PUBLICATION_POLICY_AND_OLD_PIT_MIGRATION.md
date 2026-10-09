# R4.3 operational publication policy

The executable `r43_operational_publication.py` accepts date-bounded reconstructed operational owners with one TDX latest-member snapshot S. It preserves AS_RECORDED=false and historical_PIT_permission=false.

Production CAS requires an independently supplied EXTERNALLY_ACCEPTED_R43_OPERATIONAL record bound to the exact candidate digest; this build does not create that authority. Legacy 9/30 accepted head and strict PIT contracts remain unchanged. Current-read V2 supplies one context token across four dates and real RAW/Core/Profile/TDX sector rows.

Isolated disk CAS tests cover stale predecessor, bad SHA, namespace/PIT rejection, injected failure, duplicate no-op and byte-exact predecessor rollback. A successful candidate read is not live cutover.
