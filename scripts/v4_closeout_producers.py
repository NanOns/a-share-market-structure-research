"""Two complete real-source producers, separate outputs, no accepted-head writes."""
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
WORK=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
LABEL=sys.argv[1] if len(sys.argv)>1 else 'R1'
if not LABEL.isalnum():raise ValueError('VERSIONED_RUN_LABEL_REQUIRED')
OUT=ROOT/'docs/audits/v4_full_closeout_20261012'/('producers_'+LABEL)
GENERATION='data/v4/dynamic_daily_owners/2026-10-09/f12dba29cbad0cf13c4ab1645d237d90217fdbba39197d39a206b3ec8b76de82'

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    from scripts.r4_readonly_source_guard import install
    install(['G:/codex work/大A交易','D:/new_tdx',str(WORK/GENERATION)])
    from tests import v4_native_isolation_plugin_r4 as guard
    os.environ['R4_CONNECTION_LEDGER']=str(OUT/'PG_INTENTS.jsonl')
    config=SimpleNamespace()
    guard.pytest_configure(config)
    guard.ACTIVE='V4_FULL_CLOSEOUT_REAL_FIVE_SESSION_PRODUCERS'
    stream=(OUT/'PG_INTENTS.jsonl').open('x',encoding='utf8')
    class Intents:
        count=0
        def append(self,event):
            stream.write(json.dumps(event,ensure_ascii=False)+'\n')
            self.count+=1
            if self.count%100==0:stream.flush()
    guard.EVENTS=Intents()
    from scripts.r4_r3_consumer_trace import ConsumerTrace
    trace=ConsumerTrace(OUT/'EXACT_56_TRACE.json','Both current real five-session Focus producer implementations')
    from workbench_analysis import r43_focus_replay,corrected_focus_replay
    from v4 import confirmation,confirmation_d2_candidate_r5,research_state,state_provenance
    # Accepted frozen contract inputs stay at their attested root; executed
    # implementation remains this candidate checkout and is separately hashed.
    for module in (confirmation,research_state,state_provenance):
        module.ROOT=WORK
    protected=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_joint_release_authority_v1.json']
    before={p:hashlib.sha256((WORK/p).read_bytes()).hexdigest() for p in protected}
    results={}
    trace.start()
    try:
        selected=[('r43',r43_focus_replay),('corrected',corrected_focus_replay)]
        if len(sys.argv)>2:
            if sys.argv[2] not in ('r43','corrected'):raise ValueError('KNOWN_PRODUCER_REQUIRED')
            selected=[item for item in selected if item[0]==sys.argv[2]]
        for name,module in selected:
            kwargs=dict(input_namespace=GENERATION+'/owner_v3',output_namespace='runtime/v4_full_closeout_'+name+'_20261012_'+LABEL)
            kwargs['sector_namespace']=GENERATION+'/sector_v3'
            print(json.dumps(dict(phase='FULL_PRODUCER',producer=name)),flush=True)
            results[name]=module.materialize_focus(WORK,**kwargs)
            (OUT/(name+'_RESULT.json')).write_text(json.dumps(results[name],ensure_ascii=False,indent=2),encoding='utf8')
        assert before=={p:hashlib.sha256((WORK/p).read_bytes()).hexdigest() for p in protected}
        (OUT/'RESULT.json').write_text(json.dumps(dict(contract_id='V4_TWO_FULL_FOCUS_PRODUCERS_V1',results=results,protected=before,production_changed=False),ensure_ascii=False,indent=2),encoding='utf8')
    finally:
        trace.close()
        guard.pytest_unconfigure(config)
        stream.close()

if __name__=='__main__':main()
