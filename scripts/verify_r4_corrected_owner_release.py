"""Readback independent of producer orchestration; scoped safe-release receipt."""
import gzip,hashlib,io,json,os,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.corrected_owner_replay import OUT
from workbench_analysis.market_source_acquisition import official_sessions,freeze_membership_observation
from workbench_analysis.tdx_official_daily_source import sha256_file
from focus_tracker.v4_native_core_journal import append
from workbench_db.v4_journal_pg_r1 import open_read
from workbench_service.current_v4_context import SourceInvalid
from workbench_db.v4_historical_source_ingress_pg_r1 import ingest_captured_bytes,read_bound


def pg_bytes(binding):
    source=read_bound(ROOT,binding['path'],binding['sha256']);raw=source['raw']
    if len(raw)!=binding.get('bytes',len(raw)):raise ValueError('QA_PG_SOURCE_SIZE_MISMATCH:'+binding['path'])
    return raw

def pg_json(binding):
    try:return json.loads(pg_bytes(binding))
    except (UnicodeDecodeError,ValueError) as error:raise ValueError('QA_PG_JSON_INVALID:'+binding['path']) from error

def pg_gzrows(binding):
    with gzip.GzipFile(fileobj=io.BytesIO(pg_bytes(binding)),mode='rb') as stream:
        for line in stream:
            if line.strip():yield json.loads(line)

def pg_gzip_json(binding):
    return json.loads(gzip.decompress(pg_bytes(binding)))

def main():
    from workbench_analysis.corrected_owner_pipeline import _candidate_json
    out=ROOT/OUT;core=_candidate_json(ROOT,f'{OUT}/CORE_REPLAY.json');structure=_candidate_json(ROOT,f'{OUT}/PROFILE_STRUCTURE_REPLAY.json');health=_candidate_json(ROOT,f'{OUT}/HEALTH_PROJECTION_REPLAY.json')
    sectors=_candidate_json(ROOT,f'{OUT}/SECTOR_REPLAY.json');focus=_candidate_json(ROOT,f'{OUT}/FOCUS_FORWARD_REPLAY.json');results=[];anchors={};errors=[]
    sessions=official_sessions(ROOT)
    for c,s,h,sector,f in zip(core['owners'],structure['owners'],health['owners'],sectors['owners'],focus['owners']):
        day=c['trade_date'];m=pg_json(s['structure_manifest']);runtime=next(r for r in m['artifacts'] if r['path'].endswith('runtime_security.jsonl.gz'))
        rows=list(pg_gzrows(runtime));projection={r['security_id']:r for r in pg_gzrows(h['projection'])}
        fresh=0;preserved=0
        for row in rows:
            if row['identity']['trade_date']!=day:errors.append('STRUCTURE_DATE_MIX')
            for state in row['anchor_states']:
                aid=state['anchor_id'];anchor=state['anchor']
                if aid in anchors:
                    if anchors[aid]!=anchor:errors.append('FROZEN_ANCHOR_MUTATION')
                    preserved+=1
                else:anchors[aid]=anchor
                if state['created_this_session']:
                    fresh+=1
                    if any(v!=0 for v in state['counter_state'].values()) or state['state_observations']['support']['state']!='IDLE':errors.append('NEW_ANCHOR_SELF_CONFIRMATION')
            active=row['active_selection']['active_anchor_id'];chosen=next((x for x in row['anchor_states'] if x['anchor_id']==active),None)
            cell=projection[row['identity']['security_id']]['fields']['structure_health']
            if cell['quality']=='KNOWN' and (chosen is None or chosen['state_observations']['support']['quality']!='KNOWN'):errors.append('HEALTH_UNKNOWN_PROMOTED')
        oracle=next(x for x in core['oracle'] if x['trade_date']==day)
        if oracle['errors']:errors.append('NUMERIC_ORACLE_ERROR')
        if not all(x['target_removed'] and x['pass_'] for x in sector['oracle']):errors.append('LOO_SELF_INCLUSION_OR_MEDIAN_ERROR')
        d2=pg_gzip_json(f['D2'])
        if len(d2['rows'])!=c['rows'] or any(x['trade_date']!=day for x in d2['rows']):errors.append('D2_UNIVERSE_OR_DATE_MIX')
        results.append(dict(trade_date=day,identities=c['rows'],structure_rows=len(rows),new_anchors=fresh,preserved_anchor_observations=preserved,
             source_oracle=oracle['checks'],source_oracle_samples=len(oracle['samples']),health_known=h['known'],
             relative_sector_known=sector['relative_sector_known'],independent_LOO_samples=len(sector['oracle']),
             D0=f['D0'],PREWATCH=f['PREWATCH'],D2_freshness=f['D2_freshness'],T_minus_1=sessions[sessions.index(day)-1],T_minus_3=sessions[sessions.index(day)-3]))
    # Actual candidate journal CAS/rollback with real D2 rows. Full path
    # enrichment was separately materialized by the unchanged native path kernel.
    temp_setting=os.environ.get('TMP')
    if not temp_setting:raise ValueError('CORRECTED_QA_TEMP_REQUIRED')
    temp_root=Path(temp_setting).resolve()
    if temp_root.drive.upper()!='G:':raise ValueError('CORRECTED_QA_TEMP_MUST_USE_G_DRIVE')
    qa_root=temp_root/'r21'/'corrected_owner_release_qa';qa_root.mkdir(parents=True,exist_ok=True)
    journal_dir=qa_root/'journals';journal_dir.mkdir(parents=True,exist_ok=True)
    journal=journal_dir/f"qa_{focus['owners'][-1]['D2']['sha256'][:20]}_{uuid.uuid4().hex}.json"
    if journal.exists():journal.unlink()
    input_dir=qa_root/'candidate_inputs';input_dir.mkdir(parents=True,exist_ok=True)
    qa_focus=[]
    for index,item in enumerate(focus['owners']):
        raw=pg_bytes(item['D2']);filename=f"{index:02d}_{item['D2']['sha256'][:20]}.json.gz";source=input_dir/filename;source.write_bytes(raw)
        qa_focus.append(dict(item=item,binding=dict(path=source.relative_to(qa_root).as_posix(),sha256=item['D2']['sha256'],bytes=len(raw))))
    head=None;checks=[]
    for i,entry in enumerate(qa_focus):
        f=entry['item'];d2_binding=entry['binding']
        if i==len(focus['owners'])-1:
            try:append(journal,qa_root,d2_binding,head,fail_after_append=True)
            except SourceInvalid as error:
                if str(error)!='JOURNAL_INJECTED_FAILURE':raise
            else:raise ValueError('ROLLBACK_FAILURE_NOT_INJECTED')
            expected_day=focus['owners'][i-1]['trade_date'] if i else None
            if journal.exists():
                with open_read(journal) as db:
                    actual_day=db.execute('SELECT max(day) FROM days').fetchone()[0]
            else:actual_day=None
            if actual_day!=expected_day:raise ValueError('ROLLBACK_CHANGED_DAYS')
            checks.append('REAL_LAST_SESSION_APPEND_FAILURE_ROLLED_BACK')
        r=append(journal,qa_root,d2_binding,head);head=r['head']
    if append(journal,qa_root,qa_focus[-1]['binding'],head)['status']!='NOOP':raise ValueError('IDENTICAL_CANDIDATE_NOT_NOOP')
    checks.append('IDENTICAL_CANDIDATE_NOOP')
    try:append(journal,qa_root,qa_focus[-1]['binding'],'WRONG_EXPECTED_HEAD')
    except SourceInvalid as error:
        if str(error)!='JOURNAL_CAS_CONFLICT':raise
    else:raise ValueError('STALE_CAS_ACCEPTED')
    checks.append('STALE_CAS_REJECTED')
    qa_path=(out/'candidate_lifecycle_qa'/f"candidate_lifecycle_{focus['owners'][-1]['D2']['sha256'][:20]}.json").relative_to(ROOT).as_posix()
    qa_bytes=journal.read_bytes();qa_sha=hashlib.sha256(qa_bytes).hexdigest()
    qa_ingress=ingest_captured_bytes(ROOT,qa_path,qa_bytes,source_revision=qa_sha,
        source_origin='V4_CORRECTED_OWNER_CANDIDATE_OUTPUT')
    qa_readback=read_bound(ROOT,qa_path,qa_sha)
    if qa_readback['raw']!=qa_bytes:raise ValueError('CANDIDATE_LIFECYCLE_QA_PG_READBACK_MISMATCH')
    journal.unlink()
    projection=pg_gzip_json(focus['focus'])
    if any(o['trade_date'] in ('2026-10-01','2026-10-02','2026-10-03','2026-10-04','2026-10-05','2026-10-06','2026-10-07') for e in projection['episodes'] for o in e['observations']):errors.append('HOLIDAY_OBSERVATION')
    protected={p:sha256_file(ROOT/p)==digest for p,digest in core['protected'].items()}
    if not all(protected.values()):errors.append('PRODUCTION_POINTER_CHANGED')
    from common.paths import resolve_tdx_root
    roots=[str(resolve_tdx_root(ROOT))]
    membership_root=qa_root/'membership_project';(membership_root/'data/v4/membership_observations').mkdir(parents=True,exist_ok=True)
    observation=freeze_membership_observation(membership_root,qa_root/'future_membership_smoke',[focus['owners'][-1]['trade_date']],roots)
    result=dict(contract_id='V4_R4_CORRECTED_OWNER_INDEPENDENT_READBACK_V1',dates=results,errors=errors,
        acceptance='PASS_CORRECTED_CANDIDATE_SCOPE' if not errors else 'FAIL',journal_checks=checks,
        focus_episodes=focus['episodes'],forward_outcomes=focus['outcomes'],protected=protected,
        future_membership_capture=True,change_count=len(observation['changes']),
        candidate_lifecycle_qa=dict(path=qa_path,sha256=qa_sha,bytes=len(qa_bytes),pg_readback=True),
        production_release='BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION',production_admission=False,
        remaining_independent_items=['TDX_CONCEPT_EFFECTIVE_HISTORY','CANONICAL_BJ_IDENTITY','UNKNOWN_PRIOR_EPISODE_ABSENCE',
             'ACCEPTED_CORRECTED_ROTATION_EPISODE','TARGET_PRICE_LIMIT_OWNER','EXTERNAL_SCOPED_OWNER_ADMISSION'],
        current_live_trade_date='2026-09-30',next_stage='INDEPENDENT_EXTERNAL_REVIEW_OF_SEALED_CORRECTED_OWNERS')
    receipt_path=(out/'INDEPENDENT_QA_AND_SAFE_RELEASE_READBACK.json').relative_to(ROOT).as_posix()
    receipt_bytes=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    receipt_sha=hashlib.sha256(receipt_bytes).hexdigest()
    ingest_captured_bytes(ROOT,receipt_path,receipt_bytes,source_revision=receipt_sha,source_origin='V4_CORRECTED_OWNER_CANDIDATE_OUTPUT')
    if read_bound(ROOT,receipt_path,receipt_sha)['raw']!=receipt_bytes:raise ValueError('QA_RECEIPT_PG_READBACK_MISMATCH')
    if errors:raise ValueError(errors)
    print(json.dumps(result))
if __name__=='__main__':main()
