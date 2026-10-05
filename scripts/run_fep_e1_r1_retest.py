"""Reuse unchanged E1 fresh/upgrade runner, isolate R1 evidence destination."""
from scripts import run_fep_e1_acceptance as foundation


if __name__ == '__main__':
    foundation.REPORT = foundation.ROOT / 'reports/fep_e1_r1_repair'
    raise SystemExit(foundation.run())
