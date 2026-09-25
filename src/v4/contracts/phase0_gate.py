from __future__ import annotations

from typing import Mapping


STAGES=("V4-00A","V4-00B","V4-00C","V4-00D","V4-00E","V4-00F","V4-00G","V4-00H")


def evaluate_phase0(stages: Mapping[str,str], core_blockers: list[str]) -> dict:
    missing=[stage for stage in STAGES if stage not in stages]
    failed=[stage for stage in STAGES if stages.get(stage) not in {"FULL_PASS","DEGRADED_PASS"}]
    blockers=list(core_blockers)+[f"STAGE_NOT_ACCEPTED:{s}" for s in missing+failed]
    passed=not blockers
    return {
        "phase0_status":"FULL_PASS" if passed else "BLOCKED",
        "v4_01_entry_permission":"AUTHORIZED" if passed else "BLOCKED",
        "raw_bootstrap_permission":"AUTHORIZED" if passed else "BLOCKED",
        "adjusted_bootstrap_permission":"SCOPE_DEPENDENT" if passed else "BLOCKED",
        "supplemental_permission":"OPTIONAL",
        "scanner_permission":"NOT_APPLICABLE_UNTIL_V4_05",
        "production_cutover_permission":"NOT_APPLICABLE_UNTIL_LATER_GATES",
        "core_blockers":sorted(set(blockers)),
    }
