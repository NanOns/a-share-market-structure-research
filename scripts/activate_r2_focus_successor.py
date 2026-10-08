"""Successor gate for Focus price/outcome read scope, exact joint rollback."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from scripts.run_r2_focus_continuation import OUT
from scripts.activate_v4_full_product import health
from workbench_service.joint_release import activate,validate,checked_path
from workbench_service.current_v4_context import SourceInvalid

def gate():
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes())
    qa=json.loads((OUT/'QA_FINAL.json').read_bytes())
    shadow=json.loads(checked_path(ROOT,candidate['focus_journal_admission']).read_bytes())
    manifest=validate(ROOT,candidate)
    if qa.get('result')!='FOCUS_PRICE_OUTCOME_READ_PASS' or not qa.get('iab_browser_pass'):
        raise SourceInvalid('FOCUS_UI_QA_REQUIRED')
    if qa['ui_build_id']!=candidate['ui_build_id'] or qa['context_token']!='research-v4-'+candidate['snapshot']['manifest']['sha256']:
        raise SourceInvalid('FOCUS_QA_VERSION_MISMATCH')
    for binding in qa['evidence']:checked_path(ROOT,binding)
    if shadow['outcomes'].get('OBSERVED')!=297 or not shadow['append_failure_exact_rollback']:
        raise SourceInvalid('FOCUS_SHADOW_NOT_ACCEPTED')
    if candidate['focus_automatic_write'] or candidate['full_product_release']:
        raise SourceInvalid('UNACCEPTED_WRITE_OR_FULL_SCOPE')
    if manifest['domain_features']['focus']['trade_date']!=candidate['trade_date']:
        raise SourceInvalid('FOCUS_DATE_MIX')
    return candidate

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');parser.add_argument('--expected-authority-digest');args=parser.parse_args()
    candidate=gate()
    if not args.activate:print('FOCUS_SUCCESSOR_GATE_PASS');return
    if not args.expected_authority_digest:raise SourceInvalid('EXPLICIT_EXPECTED_AUTHORITY_REQUIRED')
    receipt=activate(ROOT,candidate,args.expected_authority_digest,health)
    if receipt['result']!='NOOP':write(OUT/'RELEASE_FINAL.json',receipt)
    print(json.dumps(receipt))

if __name__=='__main__':main()
