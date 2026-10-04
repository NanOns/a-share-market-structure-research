"""Baseline-enumerated protection, independent of runtime input discovery."""
import subprocess
from scripts.r24r1_io import ROOT, BASE, ref

def protected_bytes(root=ROOT):
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=root,text=True,encoding='utf8').splitlines()
    prefixes=('reports/r22/','reports/r22r1/','reports/r23/','reports/r23r1/','reports/r24/',
              'docs/evidence/r22/','docs/evidence/r22r1/','docs/evidence/r23/','docs/evidence/r23r1/','docs/evidence/r24/',
              'config/v4_10_','config/v4_11_','config/v4_12_','config/v4_13_','config/v4_14_','config/v4_15_',
              'config/v4_current_stage_authority_','config/v4_16_','migrations/v4_16_')
    protected=[p for p in names if p.startswith(prefixes) or (p.startswith('data/v4/V4_') and 'HEAD' in p) or p in [
        'scripts/v4_16_real_shadow_runtime.py','scripts/v4_16_real_owner_projection_v1.py','scripts/validate_r24_activation.py',
        'src/workbench_analysis/v4_current_stage_authority.py','src/workbench_analysis/v4_15_radar_cohort.py','src/workbench_analysis/v4_15_settlement.py']]
    changed=subprocess.check_output(['git','diff','--name-only',BASE],cwd=root,text=True,encoding='utf8').splitlines()
    assert not set(protected)&set(changed),'HISTORICAL_PROTECTED_BYTES_CHANGED'
    return dict(execution_baseline=BASE,protected_path_count=len(protected),git_diff_protected=[],
        explicit_heads=[ref(p,root) for p in protected if p.startswith('data/v4/V4_') and 'HEAD' in p],
        old_authority=ref('config/v4_current_stage_authority_v2.json',root),
        old_runtime=ref('scripts/v4_16_real_shadow_runtime.py',root),
        engineering_head=ref('data/v4/V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1.json',root))
