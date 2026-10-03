"""Fresh-process Radar/Cohort producer with exact explicit publications."""
import argparse,json,os,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_15_radar_cohort import RadarCohortRuntime
from workbench_analysis.v4_15_persistence import Store
from scripts.r20_io import ROOT,atomic
def run(root=ROOT,namespace='reports/v4_15_runtime_r20/radar_cohort_r2'):
    authority=CurrentStageAuthority(root);store=Store(root,namespace);runtime=RadarCohortRuntime(authority,store)
    start=time.time_ns();outputs=[]
    for binding in authority.allowed_publications:outputs.append(runtime.project(binding))
    return dict(producer_pid=os.getpid(),started_ns=start,ended_ns=time.time_ns(),authority=authority.bindings(),publications=outputs,
                persisted_enrollments=store.refs('enrollment'),evidence_class='ENGINEERING_AND_REAL_ACCEPTED_CAPABILITY_SCOPED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(ROOT));p.add_argument('--namespace',default='reports/v4_15_runtime_r20/radar_cohort_r2');args=p.parse_args()
    receipt=run(Path(args.root),args.namespace);atomic(Path(args.root)/'reports/r20c/RADAR_COHORT_PERSISTED_RUN.json',receipt);print(json.dumps({'persisted_publications':len(receipt['publications']),'enrollments':len(receipt['persisted_enrollments'])}))
