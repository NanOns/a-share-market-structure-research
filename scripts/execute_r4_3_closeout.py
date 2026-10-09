"""R4.3 immutable entry and final engineering evidence coordinator."""
from __future__ import annotations
import hashlib
import json
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.corrected_owner_replay import ref, load
from workbench_analysis.market_source_acquisition import write
from workbench_analysis.tdx_official_daily_source import _atomic_write

OUT = ROOT / 'docs/evidence/r4_3_four_session_closeout_20261009'
TASK = Path('D:/Users/lps/Desktop/阶段任务/V4_R4_3_9BE4A498E6A59FE78095E6AE85E9AD8EE99ABEE4A19CE6B088E598BBE4809BE797_AD.md')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def entry():
    old = load(ROOT / 'docs/evidence/r4_2_1_20261009/ENTRY_SOURCE_AND_RELEASE_HEAD.json')
    protected = {p: ref(ROOT, ROOT / p) for p in old['production_protected']}
    for p, expected in old['production_protected'].items():
        if protected[p]['sha256'] != expected:
            raise ValueError('PROTECTED_HEAD_CHANGED:' + p)
    sources = {}
    for key in ('parent_package', 'current_package'):
        binding = old[key]
        actual = ref(ROOT, ROOT / binding['path'])
        if actual['sha256'] != binding['sha256']:
            raise ValueError('FROZEN_SOURCE_CHANGED:' + key)
        sources[key] = actual
    taskbytes = TASK.read_bytes()
    _atomic_write(OUT / 'R4_3_TASK_CONTRACT.md', taskbytes, tdx_root=Path('D:/new_tdx'))
    old_evidence = []
    for folder in ('r4_1_audit_repair_r1_20261009', 'r4_2_1_20261009'):
        for p in sorted((ROOT / 'docs/evidence' / folder).rglob('*')):
            if p.is_file():
                old_evidence.append(ref(ROOT, p))
    write(OUT / '00_ENTRY_DRIVE_HEAD_AND_PROTECTED_DIGESTS.json', dict(
        contract_id='R4_3_ENTRY_V1', observed_at=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        head=git('rev-parse', 'HEAD'), branch=git('branch', '--show-current'),
        remote_head=git('ls-remote', 'origin', 'refs/heads/codex/v4-fp14-r2-repair').split()[0],
        tracking=git('rev-parse', '--abbrev-ref', '@{upstream}'),
        phase0='DEGRADED_PASS', phase0_evidence=ref(ROOT, ROOT / 'docs/V4_PHASE0_FINAL_ACCEPTANCE_R3_1_20260925.md'),
        stage_contract=ref(ROOT, OUT / 'R4_3_TASK_CONTRACT.md'),
        consulted_agents=[ref(ROOT, ROOT / 'AGENTS.md'), ref(ROOT, ROOT / 'scripts/AGENTS.md')],
        protected=protected, frozen_sources=sources, immutable_previous_evidence=old_evidence,
        authorization='FOUR_DATES_ONE_LATEST_TDX_S_OPERATIONAL_RECONSTRUCTION; STRICT_PIT_NOT_GRANTED',
        drive=dict(status='READ_DISCOVERY_PASS_WRITE_PENDING', archive_parent_id='1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD'),
        acceptance='ENTRY_HASH_BASELINE_PASS', next_stage='W1_W2_W3',
        external_acceptance='NOT_PROVIDED_FOR_NEW_R43_BYTES', W8='NOT_AUTHORIZED_BEFORE_W7_PASS'))
    print(json.dumps(dict(status='ENTRY_HASH_BASELINE_PASS', old_evidence_files=len(old_evidence))))


def protected_readback():
    baseline = load(OUT / '00_ENTRY_DRIVE_HEAD_AND_PROTECTED_DIGESTS.json')
    mismatches = []
    bindings = list(baseline['protected'].values()) + baseline['immutable_previous_evidence'] + list(baseline['frozen_sources'].values())
    for b in bindings:
        p = ROOT / b['path']
        if not p.is_file() or ref(ROOT, p)['sha256'] != b['sha256']:
            mismatches.append(b['path'])
    native = load(OUT / '03_RECONCILIATION_ACCEPTANCE.json')
    write(OUT / 'PROTECTED_PRIOR_AND_NATIVE_READBACK.json', dict(
        contract_id='R43_IMMUTABLE_PRIOR_READBACK_V1', checked_bindings=len(bindings),
        mismatch_paths=mismatches, canonical_reconciliation=native['acceptance'],
        strict_historical_PIT_permission=False, production_head_changed=bool(mismatches),
        acceptance='PASS' if not mismatches and not native['errors'] else 'FAIL'))
    if mismatches:
        raise ValueError('IMMUTABLE_PRIOR_CHANGED:' + str(mismatches))
    print(json.dumps(dict(protected_bindings=len(bindings), mismatches=mismatches)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protected-readback', action='store_true')
    args = parser.parse_args()
    protected_readback() if args.protected_readback else entry()
