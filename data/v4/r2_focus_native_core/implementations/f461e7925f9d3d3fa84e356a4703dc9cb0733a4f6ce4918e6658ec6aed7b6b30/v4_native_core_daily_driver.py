"""Continuous immutable journal candidates from accepted V4 owner snapshots."""
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from workbench_service.current_v4_context import SourceInvalid,canonical,digest
from workbench_service.production_v4 import reference
from workbench_service.v4_daily_refresh import atomic_bytes
from .v4_native_core_journal import append
from .v4_native_core_adapter import checked,CONTRACT as PATH_CONTRACT,CAPABILITY

CONTRACT='R2_V4_CONTINUOUS_FOCUS_NATIVE_CORE_DAILY_V1'


def path_inputs(root,manifest):
    root=Path(root).resolve()
    market=json.loads(checked(root,manifest['sources']['market_operational']).read_bytes())
    sources=market['sources']
    inputs=dict(series=manifest['sources']['stock_series'],calendar=sources['calendar'],
                gbbq=sources['gbbq'],classification=sources['adjustment_classification'],
                status={k.split(':')[0]:v for k,v in sources.items() if k.endswith(':TRADING_STATUS')})
    day=manifest['context']['accepted_trade_date'];authority=manifest['domain_features']['stocks']
    inputs['native_core']={day:dict(contract_id=CAPABILITY,trade_date=day,price_basis=authority['price_basis'],factors=authority['factors'],profiles=authority['profiles'],series=authority['series'])} if authority['trade_date']==day else {}
    inputs['implementation']={}
    for name in ('v4_path_adapter','v4_native_core_adapter','v4_native_core_journal','v4_native_core_daily_driver','v4_successor','path_state_v2','states','outcomes','price_path'):
        path=root/'src/focus_tracker'/(name+'.py');raw=path.read_bytes()
        target=root/'data/v4/r2_focus_journal/implementations'/digest(raw)/path.name
        if target.exists() and target.read_bytes()!=raw:raise SourceInvalid('DAILY_IMMUTABLE_KERNEL_CONFLICT')
        if not target.exists():atomic_bytes(target,raw)
        inputs['implementation'][name]=reference(root,target)
    return inputs


def advance(root,manifest,*,previous_journal=None,previous_publication=None,expected_head=None,
            work_root='E:/codex_tmp/r2_native_core_daily',fail_after_append=False):
    """Stage a closed immutable journal; production is changed only by joint CAS.

    Every old observation reads its frozen owner binding. New price/market
    artifacts may advance, but algorithm changes require a new namespace.
    """
    root=Path(root).resolve();work_root=Path(work_root).resolve()
    if work_root.drive.upper() not in ('E:','F:'):raise SourceInvalid('DAILY_TEMP_REQUIRES_E_OR_F')
    day=manifest['context']['accepted_trade_date'];states=manifest['sources']['states']
    inputs=path_inputs(root,manifest)
    if previous_journal:
        source=checked(root,previous_journal)
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as db:
            head=db.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]
            prior_day=db.execute('SELECT max(day) FROM days').fetchone()[0]
            prior_source=db.execute('SELECT source_digest FROM days WHERE day=?',(day,)).fetchone()
            prior_inputs=db.execute('SELECT payload FROM day_inputs WHERE day=?',(day,)).fetchone()
        if head!=expected_head:raise SourceInvalid('DAILY_JOURNAL_CAS_CONFLICT')
        if day<prior_day:raise SourceInvalid('DAILY_OLDER_INPUT_FORBIDDEN')
        if day==prior_day:
            if not prior_source or prior_source[0]!=states['sha256'] or not prior_inputs or prior_inputs[0]!=canonical(inputs).decode():
                raise SourceInvalid('DAILY_SAME_DAY_REVISION_REQUIRES_NEW_NAMESPACE')
            return dict(contract_id=CONTRACT,status='NOOP',trade_date=day,head=head,journal=previous_journal,
                        publication=previous_publication,production_changed=False,source_requests=0)
    work_root.mkdir(parents=True,exist_ok=True);path=work_root/(uuid.uuid4().hex+'.sqlite')
    if previous_journal:
        shutil.copyfile(source,path)
    elif expected_head is not None:raise SourceInvalid('DAILY_INITIAL_HEAD_MUST_BE_EMPTY')
    result=append(path,root,states,expected_head,path_inputs=inputs,fail_after_append=fail_after_append)
    if result['trade_date']!=day:raise SourceInvalid('DAILY_STATE_SNAPSHOT_DATE_MIX')
    if result['status']=='NOOP':
        return dict(contract_id=CONTRACT,status='NOOP',trade_date=day,head=expected_head,
                    journal=previous_journal,publication=previous_publication,production_changed=False,source_requests=0)
    with sqlite3.connect(path) as db:
        projection=json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
        start=db.execute('SELECT min(day) FROM days').fetchone()[0]
    publication=dict(projection,contract_id=PATH_CONTRACT,trade_date=day,earliest_valid_date=start,
        namespace='V4_NATIVE_CORE_CORRECTED_JOURNAL_V1',sources=dict(states=states,previous=previous_publication,**inputs),
        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
        permissions=dict(read=True,automatic_event_write=False,manual_pin=False),
        legacy_history=dict(status='UNRECONCILED_PG_UNAVAILABLE',preserved=True),
        write_block_reason='DAILY_CANDIDATE_REQUIRES_OWNER_SNAPSHOT_UI_JOINT_GATE')
    folder=root/'data/v4/r2_focus_native_core'/result['head'];folder.mkdir(parents=True,exist_ok=True)
    frozen=folder/'journal.sqlite';published=folder/('focus_'+digest(canonical(publication))+'.json')
    if frozen.exists():
        with sqlite3.connect(frozen.as_uri()+'?mode=ro',uri=True) as db:
            if db.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]!=result['head']:
                raise SourceInvalid('DAILY_FROZEN_JOURNAL_CONFLICT')
    else:atomic_bytes(frozen,path.read_bytes())
    if published.exists() and published.read_bytes()!=canonical(publication):raise SourceInvalid('DAILY_PUBLICATION_CONFLICT')
    if not published.exists():atomic_bytes(published,canonical(publication))
    return dict(contract_id=CONTRACT,status='CANDIDATE_APPENDED',trade_date=day,head=result['head'],
                journal=reference(root,frozen),publication=reference(root,published),
                owner_inputs=inputs,production_changed=False,source_requests=0)
