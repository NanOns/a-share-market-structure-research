"""Seal the verified two-date daily admission and activate the exact read pair."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.activate_v4_full_product import health
from workbench_service.joint_release import AUTHORITY,activate,validate,checked_path
from workbench_service.current_v4_context import SourceInvalid,digest
from workbench_service.continuous_daily_release import ADMISSION
OUT=ROOT/'docs/evidence/r2_continuous_daily_20261008'

def prepare():
    if (OUT/'CANDIDATE.json').exists():raise SourceInvalid('DAILY_CANDIDATE_ALREADY_FROZEN')
    qa=json.loads((OUT/'QA_FINAL.json').read_bytes());sources=json.loads((OUT/'TWO_DATE_SOURCE_QA.json').read_bytes())
    joint=json.loads((OUT/'TWO_DATE_JOINT_SWITCH.json').read_bytes());regression=json.loads((OUT/'REGRESSION.json').read_bytes())
    chain=json.loads((OUT/'OWNER_CHAIN_STAGING.json').read_bytes());candidate=json.loads((OUT/'REPLAY_2026-09-30.json').read_bytes())
    owners=chain.get('owner_authorities')
    if owners is None:
        run=Path(chain['receipt']['path']).parent.name
        names={'market':'v4_market_operational_authority_v1.json','sector':'v4_sector_operational_authority_v1.json',
            'stocks':'v4_stock_operational_authority_v1.json','market_center':'v4_market_center_authority_v1.json','forward':'v4_forward_operational_authority_v1.json'}
        owners={key:json.loads((ROOT/'data/v4/r2_daily_candidates'/run/name).read_bytes()) for key,name in names.items()}
        manifest=validate(ROOT,candidate)
        for owner in owners.values():
            if owner['trade_date']!=candidate['trade_date'] or owner['input_data_head']['sha256']!=manifest['context']['data_head_digest']:
                raise SourceInvalid('SEALED_NATIVE_OWNER_CONTEXT_CONFLICT')
        owners['replay']=manifest['domain_features'].get('replay')
    if not qa['iab_browser_pass'] or sources['result']!='PASS' or joint['result']!='PASS' or regression['passed']!=104:
        raise SourceInvalid('DAILY_ADMISSION_EVIDENCE_INCOMPLETE')
    if any(s['result']!='REBUILT' for s in chain['stages']):raise SourceInvalid('DAILY_NATIVE_OWNER_REBUILD_NOT_PROVEN')
    if qa['ui_build_id']!=candidate['ui_build_id'] or qa['context_token']!='research-v4-'+candidate['snapshot']['manifest']['sha256']:
        raise SourceInvalid('DAILY_QA_VERSION_CONFLICT')
    for binding in qa['evidence']:checked_path(ROOT,binding)
    paths=['scripts/run_fp02_research_snapshot.py','scripts/prepare_r2_daily_candidate.py','scripts/fp_domain_evidence.py',
        'src/focus_tracker/v4_daily_driver.py','src/workbench_service/continuous_daily_release.py','src/workbench_service/production_v4.py']
    paths+=['scripts/build_fp%02d_%s.py'%(n,name) for n,name in [(5,'market'),(6,'sector'),(7,'stock'),(9,'market_center'),(10,'forward')]]
    admission=dict(contract_id='R2_CONTINUOUS_DAILY_ADMISSION_V1',result='DEGRADED_PASS',ui_build_id=candidate['ui_build_id'],
        implementations={p:ref(p) for p in paths},evidence=[ref(OUT/name) for name in ['QA_FINAL.json','TWO_DATE_SOURCE_QA.json','TWO_DATE_JOINT_SWITCH.json','REGRESSION.json','OWNER_CHAIN_STAGING.json','CONTINUOUS_REPLAY.json']],
        continuous_daily_candidate_write=True,production_publish='OWNER_RAW_TEMPORAL_QA_THEN_JOINT_CAS_WITH_HTTP_HEALTH',
        due_forward='NO_DUE_ON_REAL_REPLAY_DATES_FUTURE_DUE_REQUIRES_SETTLEMENT_OWNER',strict_pit=False,
        historical_membership='2026-09-29_UNAVAILABLE_NOT_BACKFILLED',full_product_release=False,trading=False)
    write(ROOT/ADMISSION,admission)
    previous=json.loads((ROOT/AUTHORITY).read_bytes())
    candidate.update(operational_release_scope=previous['operational_release_scope'],
        daily_owner_authorities=owners,continuous_daily_candidate_write=True,
        daily_pipeline_admission=dict(path=ADMISSION,sha256=digest((ROOT/ADMISSION).read_bytes())),
        app_version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        focus_automatic_write=False,full_product_release=False)
    validate(ROOT,candidate);write(OUT/'CANDIDATE.json',candidate)
    print('DAILY_SUCCESSOR_GATE_PASS')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');parser.add_argument('--expected-authority-digest');args=parser.parse_args()
    if not args.activate:return prepare()
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes());admission=json.loads(checked_path(ROOT,candidate['daily_pipeline_admission']).read_bytes())
    for binding in admission['evidence']+list(admission['implementations'].values()):checked_path(ROOT,binding)
    if not args.expected_authority_digest:raise SourceInvalid('EXPECTED_JOINT_DIGEST_REQUIRED')
    receipt=activate(ROOT,candidate,args.expected_authority_digest,health)
    if receipt['result']!='NOOP':write(OUT/'RELEASE_FINAL.json',receipt)
    print(json.dumps(receipt))

if __name__=='__main__':main()
