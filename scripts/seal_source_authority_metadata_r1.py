"""Seal new governance stages, preserving prior audit registries byte for byte."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes, atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', choices=['R3', 'R4', 'A10_R2', 'A12_R2', 'A10_A12_R3', 'A13', 'A13_FORMALIZATION'], required=True)
    parser.add_argument('--clean-root', required=True)
    args = parser.parse_args()
    wp = args.package
    paths = [f'reports/audits/{wp}_{suffix}' for suffix in ('CLEAN_CHECKOUT_R1.json', 'CLEAN_REGRESSION_R1.xml', 'CLEAN_REGRESSION_R1.log', 'NO_SYMBOL_SCAN_R1.json')]
    clean = Path(args.clean_root)
    receipt = json.loads((clean / paths[0]).read_text(encoding='utf8'))
    assert receipt['status'] == 'PASS'
    assert receipt['tested_commit'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    entry = json.loads((ROOT / f'reports/audits/{wp}_STAGE_ENTRY_R1.json').read_text(encoding='utf8'))
    assert all(bind(b['path'])['sha256'] == b['sha256'] for b in entry['protected_bindings'])
    assert bind_from(clean / paths[1]) == receipt['junit_sha256']
    for path in paths:
        atomic_bytes(ROOT / path, (clean / path).read_bytes())
    gatepath = f'reports/audits/{wp}_ENGINEERING_GATES_R1.json'
    gates = json.loads((ROOT / gatepath).read_text(encoding='utf8'))
    for key, value in gates['gates'].items():
        if value == 'PENDING_CLEAN_DETACHED':
            gates['gates'][key] = 'PASS_ENGINEERING'
    assert all(v in ('PASS_ENGINEERING', 'PENDING_INDEPENDENT_EXTERNAL_AUDIT') for v in gates['gates'].values())
    gates.update(status=gates['allowed_candidate_status'], clean_regression=bind(paths[0]))
    atomic_json(ROOT / gatepath, gates)
    atomic_json(ROOT / f'reports/audits/{wp}_STAGE_CLOSURE_R1.json', dict(
        status=gates['status'], tested_commit=receipt['tested_commit'], stage_completed=True,
        external_acceptance='PENDING', gates=bind(gatepath), evidence_bindings=[bind(p) for p in paths],
        protected_bindings=entry['protected_bindings'], accepted_business_heads_unchanged=True,
        next_stage=gates['next_stage'], permissions=dict(production=False, shadow=False, focus_cutover=False)))
    print(gates['status'])

def bind_from(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__ == '__main__':
    main()
