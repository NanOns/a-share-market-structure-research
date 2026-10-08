"""Independent V4 journal: verified dated sources, CAS append and exact rollback.

Corrected history remains corrected. This never claims migration of the legacy PG
ledger or fabricates path predicates/outcomes absent from an owner.
"""
import gzip,json,sqlite3
from pathlib import Path
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from .v4_successor import project

CONTRACT='R2_V4_FOCUS_JOURNAL_V1'

def append(path,root,binding,expected,*,fail_after_append=False):
    root=Path(root).resolve();source=(root/binding['path']).resolve()
    if not source.is_relative_to(root):raise SourceInvalid('JOURNAL_SOURCE_OUTSIDE_PROJECT')
    raw=source.read_bytes()
    if digest(raw)!=binding['sha256']:raise SourceInvalid('JOURNAL_SOURCE_DIGEST_MISMATCH')
    payload=json.loads(gzip.decompress(raw) if source.suffix=='.gz' else raw);rows=payload['rows']
    if not rows or len({r['trade_date'] for r in rows})!=1:raise SourceInvalid('JOURNAL_SOURCE_DATE_MIX')
    day=rows[0]['trade_date'];path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    try:
        db.executescript('CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY,source_digest TEXT,payload TEXT);CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);')
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute("SELECT value FROM metadata WHERE key='head'").fetchone();head=prior[0] if prior else None
        if head!=expected:raise SourceInvalid('JOURNAL_CAS_CONFLICT')
        existing=db.execute('SELECT source_digest FROM days WHERE day=?',(day,)).fetchone()
        if existing:
            if existing[0]!=binding['sha256']:raise SourceInvalid('JOURNAL_DAY_REVISION_REQUIRES_NEW_NAMESPACE')
            db.rollback();return dict(status='NOOP',head=head,trade_date=day)
        last=db.execute('SELECT max(day) FROM days').fetchone()[0]
        if last and day<=last:raise SourceInvalid('JOURNAL_NON_MONOTONIC_DAY')
        db.execute('INSERT INTO days VALUES(?,?,?)',(day,binding['sha256'],canonical(rows).decode()))
        days={d:json.loads(p) for d,p in db.execute('SELECT day,payload FROM days ORDER BY day')}
        projection=project(days)
        next_head=digest(canonical(dict(contract=CONTRACT,days=[list(x) for x in db.execute('SELECT day,source_digest FROM days ORDER BY day')])))
        db.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",(next_head,))
        db.execute("INSERT OR REPLACE INTO metadata VALUES('projection',?)",(canonical(projection).decode(),))
        if fail_after_append:raise SourceInvalid('JOURNAL_INJECTED_FAILURE')
        db.commit()
        return dict(status='APPENDED',head=next_head,trade_date=day,episodes=len(projection['episodes']),events=len(projection['events']),knowledge_lineage='RECONSTRUCTED_CORRECTED',legacy_reconciled=False,path_owner_admitted=False,outcomes_owner_admitted=False)
    except BaseException:db.rollback();raise
    finally:db.close()
