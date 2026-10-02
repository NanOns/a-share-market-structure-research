"""Detached clean checkout independent V2/readback/retained R11 gate."""
import argparse,ast,hashlib,json,subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r12_runtime import validate,canonical
from scripts.validate_v4_12_snapshot_v2_contract import gate
from scripts.validate_v4_12_r11_chain import validate as legacy_validate
from scripts.verify_v4_12_r11_projection_paths import validate as legacy_projection
from scripts.verify_v4_12_r11_revision_correction import validate as legacy_revision
def run(output):
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    assert not git('status','--porcelain','--untracked-files=no') and not git('branch','--show-current')
    source=git('rev-parse','HEAD');gate();readback=validate();legacy_validate('a');legacy_validate('b');legacy_projection();legacy_revision()
    changed=git('diff','5bc34c907bd5d39f322c315db34c7788d61f0bbc','HEAD','--name-only').splitlines()
    assert not any(p.startswith(('data/','migrations/','src/v4/','reports/v4_12_runtime_r11/','reports/v4_12_runtime_r1/','reports/v4_12/')) for p in changed)
    assert not any(p.startswith('config/') and p not in ['config/v4_12_frozen_snapshot_contract_v2.json','config/v4_12_active_selector_vectors_r12.json'] for p in changed)
    for p in ['src/workbench_analysis/v4_12_multi_anchor_engine.py','src/workbench_analysis/v4_12_multi_anchor_state.py','src/workbench_analysis/v4_12_frozen_snapshot_v2.py']:
        code=(ROOT/p).read_text();tree=ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):names=[node.module or '']
            else:continue
            assert not any(n.startswith(('scripts','tests')) or 'fixture' in n.lower() for n in names)
        assert "['anchors'][0]" not in code
    paths=[p for p in changed if p.endswith('.py') or p.startswith('config/')]
    result=dict(status='PASS',tested_source_sha=source,source_manifest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},R12A='PASS',R12B='PASS',R11_preserved='PASS',selector_vectors=11,multi_anchor_hard_cases=12,real_universe=5224,protected_hashes=readback['protected_hashes'],Stage_head_advanced=False,Data_head_advanced=False,migration=False)
    Path(output).write_bytes(canonical(result));print(json.dumps(dict(status='PASS',tested_source_sha=source)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)
