"""Read-only staged manifest preflight; never schedules/activates a producer."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis.operational_sealed_resume_r1 import verify,CONTRACT
from workbench_analysis.r43_owner_replay import load
from workbench_analysis.tdx_official_daily_source import sha256_file


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    head=args.root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=sha256_file(head)
    result=dict(contract_id='V4_STAGED_SEALED_WORKER_READONLY_PREFLIGHT_R1',manifest_path=str(args.manifest.resolve()),manifest_sha256=sha256_file(args.manifest),head_sha256_before=before,producer_started=False,producer_activated=False,formal_config_mutated=False)
    try:
        manifest=load(args.manifest)
        if manifest.get('contract_id')!=CONTRACT or manifest.get('allowed_modes')!=['CATCH_UP']:raise ValueError('SEALED_RESUME_JOB_MODE_CONTRACT_REQUIRED')
        candidate=verify(args.root,manifest)
        result.update(acceptance='PASS' if candidate else 'NOOP_ALREADY_CURRENT',target_session=manifest['target_session'],candidate=manifest['candidate'],runtime_policy=manifest['runtime_policy'])
    except Exception as exc:
        result.update(acceptance='FAIL',error_type=type(exc).__name__,error=str(exc))
    result.update(head_sha256_after=sha256_file(head),head_unchanged=before==sha256_file(head))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False));return int(result['acceptance']=='FAIL' or not result['head_unchanged'])


if __name__=='__main__':raise SystemExit(main())
