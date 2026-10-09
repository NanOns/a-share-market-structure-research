"""Readback independent of producer orchestration; scoped safe-release receipt."""
import gzip,json,sqlite3,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.corrected_owner_replay import load,checked,gzrows,ref,OUT
from workbench_analysis.market_source_acquisition import write,official_sessions,freeze_membership_observation
from workbench_analysis.tdx_official_daily_source import sha256_file,_atomic_write
from focus_tracker.v4_native_core_journal import append
from workbench_service.current_v4_context import SourceInvalid


def main():
    out=ROOT/OUT;core=load(out/'CORE_REPLAY.json');structure=load(out/'PROFILE_STRUCTURE_REPLAY.json');health=load(out/'HEALTH_PROJECTION_REPLAY.json')
    sectors=load(out/'SECTOR_REPLAY.json');focus=load(out/'FOCUS_FORWARD_REPLAY.json');results=[];anchors={};errors=[]
    sessions=official_sessions(ROOT)
    for c,s,h,sector,f in zip(core['owners'],structure['owners'],health['owners'],sectors['owners'],focus['owners']):
        day=c['trade_date'];m=load(checked(ROOT,s['structure_manifest']));runtime=next(r for r in m['artifacts'] if r['path'].endswith('runtime_security.jsonl.gz'))
        rows=gzrows(checked(ROOT,runtime));projection={r['security_id']:r for r in gzrows(checked(ROOT,h['projection']))}
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
        d2=json.loads(gzip.decompress(checked(ROOT,f['D2']).read_bytes()))
        if len(d2['rows'])!=c['rows'] or any(x['trade_date']!=day for x in d2['rows']):errors.append('D2_UNIVERSE_OR_DATE_MIX')
        results.append(dict(trade_date=day,identities=c['rows'],structure_rows=len(rows),new_anchors=fresh,preserved_anchor_observations=preserved,
             source_oracle=oracle['checks'],source_oracle_samples=len(oracle['samples']),health_known=h['known'],
             relative_sector_known=sector['relative_sector_known'],independent_LOO_samples=len(sector['oracle']),
             D0=f['D0'],PREWATCH=f['PREWATCH'],D2_freshness=f['D2_freshness'],T_minus_1=sessions[sessions.index(day)-1],T_minus_3=sessions[sessions.index(day)-3]))
    # Actual candidate journal CAS/rollback with real four-day D2 rows. Full path
    # enrichment was separately materialized by the unchanged native path kernel.
    journal=Path('E:/codex_tmp/r4_corrected_release_qa.sqlite')
    if journal.exists():journal.unlink()
    head=None;checks=[]
    for i,f in enumerate(focus['owners']):
        if i==len(focus['owners'])-1:
            try:append(journal,ROOT,f['D2'],head,fail_after_append=True)
            except SourceInvalid as error:
                if str(error)!='JOURNAL_INJECTED_FAILURE':raise
            else:raise ValueError('ROLLBACK_FAILURE_NOT_INJECTED')
            with sqlite3.connect(journal) as db:
                if db.execute('SELECT max(day) FROM days').fetchone()[0]!=focus['owners'][i-1]['trade_date']:raise ValueError('ROLLBACK_CHANGED_DAYS')
            checks.append('REAL_LAST_SESSION_APPEND_FAILURE_ROLLED_BACK')
        r=append(journal,ROOT,f['D2'],head);head=r['head']
    if append(journal,ROOT,focus['owners'][-1]['D2'],head)['status']!='NOOP':raise ValueError('IDENTICAL_CANDIDATE_NOT_NOOP')
    checks.append('IDENTICAL_CANDIDATE_NOOP')
    try:append(journal,ROOT,focus['owners'][-1]['D2'],'WRONG_EXPECTED_HEAD')
    except SourceInvalid as error:
        if str(error)!='JOURNAL_CAS_CONFLICT':raise
    else:raise ValueError('STALE_CAS_ACCEPTED')
    checks.append('STALE_CAS_REJECTED')
    _atomic_write(out/'candidate_lifecycle_qa.sqlite',journal.read_bytes(),tdx_root=Path('D:/new_tdx'))
    projection=json.loads(gzip.decompress(checked(ROOT,focus['focus']).read_bytes()))
    if any(o['trade_date'] in ('2026-10-01','2026-10-02','2026-10-03','2026-10-04','2026-10-05','2026-10-06','2026-10-07') for e in projection['episodes'] for o in e['observations']):errors.append('HOLIDAY_OBSERVATION')
    protected={p:sha256_file(ROOT/p)==digest for p,digest in core['protected'].items()}
    if not all(protected.values()):errors.append('PRODUCTION_POINTER_CHANGED')
    roots=load(ROOT/'config/dm01_go_forward_runtime_contract_r4.json')['read_only_tdx_roots']
    observation=freeze_membership_observation(ROOT,out/'future_membership_smoke',[focus['owners'][-1]['trade_date']],roots)
    result=dict(contract_id='V4_R4_CORRECTED_OWNER_INDEPENDENT_READBACK_V1',dates=results,errors=errors,
        acceptance='PASS_CORRECTED_CANDIDATE_SCOPE' if not errors else 'FAIL',journal_checks=checks,
        focus_episodes=focus['episodes'],forward_outcomes=focus['outcomes'],protected=protected,
        future_membership_capture=True,change_count=len(observation['changes']),
        production_release='BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION',production_admission=False,
        remaining_independent_items=['TDX_CONCEPT_EFFECTIVE_HISTORY','CANONICAL_BJ_IDENTITY','UNKNOWN_PRIOR_EPISODE_ABSENCE',
             'ACCEPTED_CORRECTED_ROTATION_EPISODE','TARGET_PRICE_LIMIT_OWNER','EXTERNAL_SCOPED_OWNER_ADMISSION'],
        current_live_trade_date='2026-09-30',next_stage='INDEPENDENT_EXTERNAL_REVIEW_OF_SEALED_CORRECTED_OWNERS')
    write(out/'INDEPENDENT_QA_AND_SAFE_RELEASE_READBACK.json',result)
    if errors:raise ValueError(errors)
    print(json.dumps(result))
if __name__=='__main__':main()
