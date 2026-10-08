"""Independent V4 journal: verified dated sources, CAS append and exact rollback.

Corrected history remains corrected. This never claims migration of the legacy PG
ledger or fabricates path predicates/outcomes absent from an owner.
"""
import gzip,json,sqlite3
from pathlib import Path
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from .v4_successor import project

CONTRACT='R2_V4_FOCUS_NATIVE_CORE_JOURNAL_V1'

def append(path,root,binding,expected,*,fail_after_append=False,path_inputs=None):
    root=Path(root).resolve();source=(root/binding['path']).resolve()
    if not source.is_relative_to(root):raise SourceInvalid('JOURNAL_SOURCE_OUTSIDE_PROJECT')
    raw=source.read_bytes()
    if digest(raw)!=binding['sha256']:raise SourceInvalid('JOURNAL_SOURCE_DIGEST_MISMATCH')
    payload=json.loads(gzip.decompress(raw) if source.suffix=='.gz' else raw);rows=payload['rows']
    if not rows or len({r['trade_date'] for r in rows})!=1:raise SourceInvalid('JOURNAL_SOURCE_DATE_MIX')
    day=rows[0]['trade_date'];path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    try:
        db.executescript('CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY,source_digest TEXT,payload TEXT);CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE IF NOT EXISTS day_inputs(day TEXT PRIMARY KEY,payload TEXT);')
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute("SELECT value FROM metadata WHERE key='head'").fetchone();head=prior[0] if prior else None
        if head!=expected:raise SourceInvalid('JOURNAL_CAS_CONFLICT')
        mode='PATH_OUTCOME_V2' if path_inputs else 'LIFECYCLE_ONLY_V1'
        stored=db.execute("SELECT value FROM metadata WHERE key='projection_inputs'").fetchone()
        if stored and stored[0]!=mode:raise SourceInvalid('JOURNAL_INPUT_REVISION_REQUIRES_NEW_NAMESPACE')
        existing=db.execute('SELECT source_digest FROM days WHERE day=?',(day,)).fetchone()
        if existing:
            if existing[0]!=binding['sha256']:raise SourceInvalid('JOURNAL_DAY_REVISION_REQUIRES_NEW_NAMESPACE')
            inputs=db.execute('SELECT payload FROM day_inputs WHERE day=?',(day,)).fetchone()
            if path_inputs and (not inputs or inputs[0]!=canonical(path_inputs).decode()):raise SourceInvalid('JOURNAL_DAY_INPUT_REVISION_REQUIRES_NEW_NAMESPACE')
            db.rollback();return dict(status='NOOP',head=head,trade_date=day)
        last=db.execute('SELECT max(day) FROM days').fetchone()[0]
        if last and day<=last:raise SourceInvalid('JOURNAL_NON_MONOTONIC_DAY')
        if last and path_inputs:
            previous_inputs=json.loads(db.execute('SELECT payload FROM day_inputs WHERE day=?',(last,)).fetchone()[0])
            old_code={k:v['sha256'] for k,v in previous_inputs.get('implementation',{}).items()}
            new_code={k:v['sha256'] for k,v in path_inputs.get('implementation',{}).items()}
            if old_code!=new_code:raise SourceInvalid('JOURNAL_KERNEL_UPGRADE_REQUIRES_NEW_NAMESPACE')
        db.execute('INSERT INTO days VALUES(?,?,?)',(day,binding['sha256'],canonical(rows).decode()))
        days={d:json.loads(p) for d,p in db.execute('SELECT day,payload FROM days ORDER BY day')}
        if path_inputs:
            from .v4_native_core_adapter import AcceptedPaths,enriched_project
            db.execute('INSERT INTO day_inputs VALUES(?,?)',(day,canonical(path_inputs).decode()))
            current_paths=AcceptedPaths(root,path_inputs)
            if last and (last not in current_paths.calendar or current_paths.calendar.index(day)!=current_paths.calendar.index(last)+1):
                raise SourceInvalid('JOURNAL_SKIPPED_MASTER_SESSION')
            frozen={d:json.loads(p) for d,p in db.execute('SELECT day,payload FROM day_inputs')}
            class DatedPaths:
                calendar=current_paths.calendar
                cache={day:current_paths}
                def path(self,sid,start,end):
                    if end not in self.cache:self.cache[end]=AcceptedPaths(root,frozen[end])
                    return self.cache[end].path(sid,start,end)
            def native_facts(self,sid,end,fact):
                if end not in self.cache:self.cache[end]=AcceptedPaths(root,frozen[end])
                return self.cache[end].native_facts(sid,end,fact)
            DatedPaths.native_facts=native_facts
            projection=enriched_project(days,DatedPaths())
        else:projection=project(days)
        identity=dict(contract=CONTRACT,days=[list(x) for x in db.execute('SELECT day,source_digest FROM days ORDER BY day')])
        if path_inputs:identity['projection_inputs']=[list(x) for x in db.execute('SELECT day,payload FROM day_inputs ORDER BY day')]
        next_head=digest(canonical(identity))
        db.execute("INSERT OR REPLACE INTO metadata VALUES('projection_inputs',?)",(mode,))
        db.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",(next_head,))
        db.execute("INSERT OR REPLACE INTO metadata VALUES('projection',?)",(canonical(projection).decode(),))
        if fail_after_append:raise SourceInvalid('JOURNAL_INJECTED_FAILURE')
        db.commit()
        return dict(status='APPENDED',head=next_head,trade_date=day,episodes=len(projection['episodes']),events=len(projection['events']),knowledge_lineage='RECONSTRUCTED_CORRECTED',legacy_reconciled=False,path_owner_admitted=bool(path_inputs),outcomes_owner_admitted=bool(path_inputs))
    except BaseException:db.rollback();raise
    finally:db.close()
