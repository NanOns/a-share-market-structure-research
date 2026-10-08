"""Isolated actual two-date joint replay; never writes the live authority."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from workbench_service.current_v4_context import digest
from workbench_service.joint_release import AUTHORITY,activate,validate
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.v4_server import serve_v4
OUT=ROOT/'docs/evidence/r2_continuous_daily_20261008'
SANDBOX=Path('E:/codex_tmp/r2_focus_preview')

def health(candidate):
    reader=ProductionV4ResearchReader(SANDBOX)
    return dict(pass_=True,**{'pass':reader.context['trade_date']==candidate['trade_date']},
        trade_date=reader.context['trade_date'],context_token=reader.token,counts=reader.manifest['counts'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--switch',action='store_true');args=parser.parse_args()
    candidates=[json.loads((OUT/('REPLAY_'+day+'.json')).read_bytes()) for day in ('2026-09-29','2026-09-30')]
    if args.switch:
        old=(SANDBOX/AUTHORITY).read_bytes();expected=digest(old)
        try:activate(SANDBOX,candidates[1],expected,lambda c: {'pass':False})
        except ValueError:assert (SANDBOX/AUTHORITY).read_bytes()==old
        else:raise AssertionError('EXPECTED_ROLLBACK')
        receipt=activate(SANDBOX,candidates[1],expected,health)
        noop=activate(SANDBOX,candidates[1],receipt['authority_digest'],health)
        write(OUT/'TWO_DATE_JOINT_SWITCH.json',dict(result='PASS',exact_failure_restore=True,activation=receipt,noop=noop))
        print(json.dumps(receipt));return
    for candidate in candidates:
        manifest=validate(ROOT,candidate)
        for binding in [candidate['snapshot']['manifest'],manifest['database'],*manifest['sources'].values(),*candidate['ui_assets'].values()]:
            target=SANDBOX/binding['path'];target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() or digest(target.read_bytes())!=binding['sha256']:shutil.copyfile(ROOT/binding['path'],target)
    # Previous isolated Focus rehearsal already froze the runtime acceptance
    # context. It is required here, not silently synthesized from historical values.
    assert (SANDBOX/'config/v4_production_runtime_authority_v1.json').exists()
    write(SANDBOX/AUTHORITY,candidates[0]);validate(SANDBOX,candidates[0]);health(candidates[0])
    serve_v4(SANDBOX,'127.0.0.1',28767)

if __name__=='__main__':main()
