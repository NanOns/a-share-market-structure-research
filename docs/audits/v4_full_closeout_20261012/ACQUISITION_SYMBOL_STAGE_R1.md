# Acquisition provider smoke selection

Stage contract: NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC; real requested gap/provider identity is authoritative. The market source acquisition smoke probe now chooses the first requested stock gap, otherwise the first actual stock identity returned by the provider. It filters indices and fails closed when neither exists. It no longer inserts a named equity into an empty request.

Evidence: `G:/codex_tmp/v4_full_closeout_20261012/denominator/acquisition_r2.xml`, seven passing tests including actual provider-interface fixtures for gap priority, index filtering and empty universes. These fixtures do not represent online-source acceptance.

Acceptance: this production runtime literal issue is fixed. Other current governance scanner findings remain open and independently tracked; this is not full scanner acceptance. Next stage: review all remaining findings without denominator exclusions or blanket audit-script exemptions, followed by full legal regression.
