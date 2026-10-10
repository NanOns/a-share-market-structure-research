"""Evidence entry point; uses the existing module and issues no production grant."""
from workbench_analysis.validation_cohort_read_contract_r3 import publish_isolated_candidate

# Invoke only with an independently accepted Head/read grant/source manifest.
# Output must be docs/evidence; current production has no authorized owner.
__all__ = ['publish_isolated_candidate']
