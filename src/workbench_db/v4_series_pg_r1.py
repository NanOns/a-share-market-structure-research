"""Immutable native PG dated bar index for chart, Focus and Forward consumers."""
import hashlib
import json
from pathlib import Path
from .v4_snapshot_pg_r1 import Builder,read
from .v4_native import connection

CONTRACT='V4_PG_DATED_SERIES_R1'

def build(root,path,rows,*,t0,source_digest):
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_service.current_v4_context import canonical
    if len(source_digest)!=64: raise ValueError('SERIES_SOURCE_DIGEST_REQUIRED')
    path=Path(path).resolve()
    if path.exists():raise ValueError('IMMUTABLE_SERIES_OUTPUT_ALREADY_EXISTS')
    release=hashlib.sha256((source_digest+':'+t0+':'+str(path)).encode()).hexdigest()
    db=Builder(root,release)
    try:
        db.executescript('CREATE TABLE objects(domain text,id text,payload text);CREATE TABLE aliases(alias text,id text);CREATE TABLE members(sector text,security text);CREATE TABLE metadata(key text PRIMARY KEY,value text);CREATE TABLE bars(security text,day date,payload text NOT NULL,PRIMARY KEY(security,day));')
        count=0;symbols=set();logical=hashlib.sha256()
        for sid,day,bar in rows:
            if day>t0 or bar['trade_date']!=day: raise ValueError('SERIES_FUTURE_OR_MIXED_DATE')
            raw=canonical(bar).decode();db.execute('INSERT INTO bars VALUES(?,?,?)',(sid,day,raw));count+=1;symbols.add(sid)
        with db.pg.cursor(name='series_digest') as cur:
            cur.execute('SELECT security,day::text,payload FROM bars ORDER BY security,day')
            for row in cur: logical.update(canonical(row)+b'\n')
        meta=dict(release_id=release,context=dict(accepted_trade_date=t0),source_digest=source_digest,bars=count,symbols=len(symbols),bar_logical_digest=logical.hexdigest())
        descriptor=db.seal(meta)
        db.pg.execute('CREATE TRIGGER immutable_snapshot BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON bars FOR EACH STATEMENT EXECUTE FUNCTION reject_snapshot_mutation()')
        db.commit();descriptor.update(series_contract_id=CONTRACT,source_digest=source_digest,bar_count=count,symbol_count=len(symbols))
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);atomic_bytes(path,canonical(descriptor)+b'\n')
        return descriptor
    finally: db.close()

def range_rows(path,sid,start,end):
    path=Path(path)
    if path.suffix!='.json': raise ValueError('PG_SERIES_BINDING_REQUIRED_NO_FALLBACK')
    descriptor=json.loads(path.read_bytes())
    if descriptor.get('series_contract_id')!=CONTRACT or end>descriptor['T0']: raise ValueError('PG_SERIES_CONTEXT_MISMATCH')
    with read(descriptor) as db:
        rows=db.execute('SELECT day::text,payload FROM bars WHERE security=? AND day>=? AND day<=? ORDER BY day',(sid,start,end)).fetchall()
    return [(day,json.loads(payload)) for day,payload in rows]
