"""Two accepted real sessions in an independent journal; never fake T+1."""
import gzip,json,sys,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,POINTER
from workbench_service.current_v4_context import SourceInvalid
from focus_tracker.v4_journal import append

def main():
    r=ProductionV4ResearchReader(ROOT);before=ref(POINTER);current=r.manifest['sources']['states'];payload=json.load(gzip.open(ROOT/current['path'],'rt',encoding='utf8'));prior=payload['prior_binding']
    path=Path('E:/codex_tmp/r2_daily_replay/focus.sqlite');path.parent.mkdir(parents=True,exist_ok=True)
    # Each run gets an isolated journal without deleting prior audit artifacts.
    import uuid
    path=path.with_name(uuid.uuid4().hex+'.sqlite')
    first=append(path,ROOT,prior,None)
    try:append(path,ROOT,current,first['head'],fail_after_append=True)
    except SourceInvalid:rollback=True
    else:raise AssertionError('ROLLBACK_FAILED')
    second=append(path,ROOT,current,first['head']);noop=append(path,ROOT,current,second['head']);assert noop['status']=='NOOP'
    with sqlite3.connect(path) as db:
        projection=json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0]);days=[x[0] for x in db.execute('SELECT day FROM days ORDER BY day')]
    assert projection['episodes']==r.manifest['domain_features']['focus']['episodes']
    assert before==ref(POINTER)
    write(ROOT/'docs/evidence/r2_repair_20261008/R2_DAILY_E2E.json',dict(contract_id='R2_REAL_ACCEPTED_DAY_REPLAY_V1',status='DEGRADED_PASS',source_days=days,sources=[prior,current],journal=str(path),first=first,second=second,idempotent=noop,append_failure_rollback=rollback,existing_projection_equal=True,live_last_good_preserved=True,legacy_migration='NOT_RECONCILED_PG_UNAVAILABLE',path_outcome='OWNER_NOT_ADMITTED',DM01='ACCEPTED_REAL_INPUTS_REUSED_NOT_NEW_CAPTURE',owner_snapshot_ui_chain='NOT_YET_AUTOMATED_END_TO_END',full_daily_e2e_pass=False,next_stage='DAILY_OWNER_BUILD_UI_JOURNAL_ORCHESTRATION'))
    print(json.dumps(dict(days=days,events=len(projection['events']),episodes=len(projection['episodes']),status='DEGRADED_PASS')))

if __name__=='__main__':main()
