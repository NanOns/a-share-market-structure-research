"""Actual accepted controls population and scope; never invent rank features."""
import json
import math
import time
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P
from workbench_analysis.v4_15_settlement import freeze_controls


def build():
    path = 'reports/v4_15_runtime_r20/r20d_accepted_source_r3/snapshots/ccf05627352fcf4065e1ac98d730c7f15b882e3e55af23fbe4fda509265e8f16.json'
    snapshot = json.loads((ROOT / path).read_bytes())
    rows = snapshot['universe']
    features = ('prior20_mean_amount', 'vol20', 'RPS20')
    counts = {k: sum(isinstance(r.get(k), (int, float)) and math.isfinite(r[k]) for r in rows) for k in features}
    pool = [r for r in rows if r.get('hard_safety') is True]
    complete = [r for r in pool if all(isinstance(r.get(k), (int, float)) and math.isfinite(r[k]) for k in features) and r['prior20_mean_amount'] > 0]
    measures = []
    for scale, size in (('small', min(100, len(rows))), ('medium', min(1000, len(rows))), ('full_available', len(rows))):
        population = rows[:size]
        eligible = [r for r in population if r.get('prewatch_final_eligible') is True]
        started = time.perf_counter()
        outputs = [freeze_controls(population, r, len(eligible)) for r in eligible]
        measures.append(dict(scale=scale, population_count=size, actual_eligible_signal_count=len(eligible),
                             actual_owner_invocations=len(outputs), wall_seconds=time.perf_counter() - started,
                             rank_matching_measured=bool(complete and eligible),
                             status='NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY' if not complete else 'OWNER_EXECUTED'))
    matrix = 'config/v4_15_source_capability_matrix_v1.json'
    capability = json.loads((ROOT / matrix).read_bytes())
    absolute = next(r for r in capability['capabilities'] if r['capability'] == 'ABSOLUTE_FORWARD_SETTLEMENT')
    write(P + 'IA07_ACCEPTED_CAPABILITY_SCOPE.json', dict(snapshot=binding(path), source=binding(matrix),
        accepted_quality=snapshot['quality'], population_count=len(rows), hard_safety_pool=len(pool),
        complete_rank_population=len(complete), feature_nonmissing_counts=counts, measurements=measures,
        acceptance='NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY', IA07_FULL_PASS=False,
        absolute_settlement_capability=absolute, control_debt_blocks_control_matching_acceptance=True,
        synthetic_row_expansion=False, imputed_missing_features=False,
        production=False, shadow=False, focus=False, default_ui=False,
        next_stage='INDEPENDENT_FEATURE_PROJECTION_ACCEPTANCE_REQUIRED_BEFORE_FULL_CONTROL_PERFORMANCE'))


if __name__ == '__main__':
    build()
