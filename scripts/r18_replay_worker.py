"""One invocation, one fresh OS process, exact persisted predecessor only."""
import sys,json,os
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_authority import ReplayAuthority
from workbench_analysis.v4_14_publication import validate_envelope,publish_replay
from workbench_analysis.v4_14_full_dag import replay
from workbench_analysis.v4_14_replay_io import exact,publish,digest

def run(input_path,artifact_root,namespace,receipt_path):
    start=datetime.now(timezone.utc).isoformat();a=ReplayAuthority(ROOT);envelope=json.loads(Path(input_path).read_bytes())
    prior=validate_envelope(artifact_root,envelope,a)
    if envelope['evidence_class']!='ENGINEERING_SYNTHETIC':raise ValueError('SYNTHETIC_OWNER_FACTS_CANNOT_BECOME_REAL_EVIDENCE')
    result=replay(a,envelope,prior)
    publication=publish_replay(artifact_root,envelope,result,a,namespace)
    receipt=dict(pid=os.getpid(),started_at=start,finished_at=datetime.now(timezone.utc).isoformat(),input_digest=digest(envelope),publication=publication,previous_readback=envelope['previous_state_publication'],previous_market_session=envelope['previous_market_session'],calendar_binding=a.calendar_ref,readback_mode='EXACT_PERSISTED_BYTES',in_memory_prior=False)
    publish(artifact_root,receipt_path,receipt)
    return receipt
if __name__=='__main__':print(json.dumps(run(*sys.argv[1:]),sort_keys=True))
