"""Real next-session source/Owner calculation; no CAS or first-capture claim."""
import hashlib,json,os,traceback,argparse
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.operational_daily_ready_owner_v2 import build,seal
from workbench_analysis.r43_owner_replay import ref

ROOT=Path(__file__).resolve().parents[1]
STAGING=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/exact_daily_candidate_20261013_R1.json')

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='R1');parser.add_argument('--resume-checkpoint');args=parser.parse_args()
    if not args.label.isalnum():raise ValueError('VERSIONED_CANDIDATE_RUN_LABEL_REQUIRED')
    OUT=OUT.with_name('exact_daily_candidate_20261013_'+args.label+'.json')
    if OUT.exists():raise ValueError('PRESERVE_PRIOR_CANDIDATE_RUN')
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(STAGING/'config/native_pg_roles.dpapi')[ROLES[1]]
    diagnosis=json.loads(Path('G:/codex_tmp/v4_full_closeout_20261012/formal_capture_diagnosis_20261013.json').read_bytes())
    source=diagnosis['execution']
    names=('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')
    heads={n:(STAGING/'data/v4'/n).read_bytes() for n in names}
    result=dict(contract_id='V4_REAL_NEXT_SESSION_EXACT_DAILY_CANDIDATE_R1',target=diagnosis['target'],publication=False,first_capture_acceptance=False)
    print('REAL_EXACT_OWNER_BUILD_STARTED',flush=True)
    from scripts.r4_r3_consumer_trace import ConsumerTrace
    trace=ConsumerTrace(OUT.with_name(OUT.stem+'_EXACT56_TRACE.json'),'Actual formal next-session exact V2 daily Owner candidate '+args.label)
    trace.start()
    try:
        checkpoint=ref(STAGING,STAGING/args.resume_checkpoint) if args.resume_checkpoint else None
        produced,context=build(STAGING,source['source_freeze'],source_readiness=source['source_readiness'],candidate_only_exact=True,resume_checkpoint=checkpoint)
        if context.get('upstream_reuse'):result['upstream_reuse']=context['upstream_reuse']
        print('REAL_EXACT_OWNER_BUILD_FINISHED_SEAL_STARTED',flush=True)
        candidate,binding=seal(STAGING,context)
        result.update(status='CANDIDATE_SEALED_NOT_PUBLISHED',candidate=binding,
            generation_scope=ref(STAGING,context['folder']/'GENERATION_SCOPE.json'),
            numeric_core_oracle=ref(STAGING,context['folder']/'owner_v3/CORE_REPLAY.json'),
            day_receipt=candidate['day_receipt'])
    except Exception as error:
        result.update(status='FAILED_RETAINED',exception_class=type(error).__name__,traceback=traceback.format_exc())
    finally:
        trace.close()
        assert all((STAGING/'data/v4'/n).read_bytes()==raw for n,raw in heads.items())
        result['heads_unchanged']={n:hashlib.sha256(raw).hexdigest() for n,raw in heads.items()}
        temp=OUT.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2),encoding='utf8');os.replace(temp,OUT)
    print(json.dumps({k:result.get(k) for k in ('status','exception_class','candidate')}),flush=True)
    return int(result['status']=='FAILED_RETAINED')

if __name__=='__main__':raise SystemExit(main())
