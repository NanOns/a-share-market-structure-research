"""Separate A08/A09 stage entries, authorized by the user's scope reply."""
import argparse,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    p=argparse.ArgumentParser();p.add_argument('--package',choices=['A08','A09'],required=True);args=p.parse_args();wp=args.package
    authority=bind('docs/evidence/V4_CROSS_STAGE_INDEPENDENT_AUDIT_REMEDIATION_MASTER_TASK_R1_20261001.md')
    protected=json.loads((ROOT/'config/source_authority_governance_r1.json').read_text(encoding='utf8'))['protected_bindings']
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in protected)
    paths=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('[0-9][0-9][0-9]_*.sql'))
    atomic_json(ROOT/f'reports/audits/{wp}_STAGE_ENTRY_R1.json',dict(contract_id=wp+'_V4_09_HARDENING_R1',status='AUTHORIZED_STAGE_ENTRY',authority=authority,upgrade=bind('docs/evidence/source_authority/V4_CROSS_STAGE_REMEDIATION_MASTER_AMENDMENT_R2_20261001.md'),human_scope_authorization='本轮也执行 A08/A09',baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),protected_bindings=protected,migrations_before=[bind(p.relative_to(ROOT).as_posix()) for p in paths],next_unused_v4_migration=max(int(p.name[:3]) for p in paths)+1,entered_at=datetime.now(timezone.utc).isoformat(),acceptance_result='PENDING_ENGINEERING_AND_INDEPENDENT_EXTERNAL_AUDIT',next_stage='Engineering candidate, clean detached regression, commit/push, then independent external audit',permissions=dict(production=False,shadow=False,focus_cutover=False)))

if __name__=='__main__':main()
