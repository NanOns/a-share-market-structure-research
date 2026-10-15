"""Immutable native PG dated bar index for chart, Focus and Forward consumers."""
import hashlib
import json
from pathlib import Path
from contextlib import contextmanager,ExitStack
from contextvars import ContextVar
from .v4_snapshot_pg_r1 import read
from .v4_snapshot_pg_r2 import Builder
from .v4_native import connection

CONTRACT='V4_PG_DATED_SERIES_R2'
LEGACY_CONTRACT='V4_PG_DATED_SERIES_R1'
_projection_reads=ContextVar('v4_series_projection_verified_reads',default=None)

@contextmanager
def verified_series_scope():
    """Hold fully verified repeatable-read snapshots for one batch projection."""
    if _projection_reads.get() is not None:
        yield
        return
    with ExitStack() as stack:
        token=_projection_reads.set((stack,{}))
        try:yield
        finally:_projection_reads.reset(token)

@contextmanager
def verified_series_read(descriptor):
    scope=_projection_reads.get()
    if scope is None:
        with read(descriptor) as reader:yield reader
        return
    stack,readers=scope
    # Full descriptor bytes participate in identity, including database and T0.
    key=json.dumps(descriptor,sort_keys=True,separators=(',',':'),allow_nan=False)
    if key not in readers:readers[key]=stack.enter_context(read(descriptor))
    yield readers[key]

def build(root,path,rows,*,t0,source_digest):
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_service.current_v4_context import canonical
    if len(source_digest)!=64: raise ValueError('SERIES_SOURCE_DIGEST_REQUIRED')
    path=Path(path).resolve()
    release=hashlib.sha256((source_digest+':'+t0+':'+str(path)).encode()).hexdigest()
    if path.exists():
        descriptor=json.loads(path.read_bytes())
        if (descriptor.get('series_contract_id')!=CONTRACT or descriptor.get('T0')!=t0
                or descriptor.get('source_digest')!=source_digest or descriptor.get('release_id')!=release):
            raise ValueError('IMMUTABLE_SERIES_REUSE_IDENTITY_MISMATCH')
        expected={};symbols=set()
        for sid,day,bar in rows:
            if day>t0 or bar['trade_date']!=day:raise ValueError('SERIES_FUTURE_OR_MIXED_DATE')
            if (sid,day) in expected:raise ValueError('SERIES_DUPLICATE_INPUT_ROW')
            expected[sid,day]=canonical(bar).decode();symbols.add(sid)
        if len(expected)!=descriptor.get('bar_count') or len(symbols)!=descriptor.get('symbol_count'):
            raise ValueError('IMMUTABLE_SERIES_REUSE_CONTENT_MISMATCH')
        # The reader verifies the complete immutable PG snapshot before reuse.
        # Compare desired bytes as well: a matching source label is insufficient.
        with verified_series_read(descriptor) as reader:
            saved=reader.execute('SELECT security,day::text,payload FROM bars ORDER BY security,day').fetchall()
            if len(saved)!=len(expected) or any(expected.get((sid,day))!=raw for sid,day,raw in saved):
                raise ValueError('IMMUTABLE_SERIES_REUSE_CONTENT_MISMATCH')
        return descriptor
    db=Builder(root,release,storage_kind='series')
    try:
        db.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE metadata(key text PRIMARY KEY,value text);CREATE TABLE bars(security text,day date,payload text NOT NULL,PRIMARY KEY(security,day));')
        # Content verification has an explicit C collation and NULL ordering.
        # Match that order so full real bar sets do not require an external
        # sort before the first server-cursor fetch under the bounded timeout.
        db.execute('CREATE INDEX bars_digest_order ON bars(security COLLATE "C" ASC NULLS FIRST,day ASC NULLS FIRST)')
        count=0;symbols=set();logical=hashlib.sha256()
        for sid,day,bar in rows:
            if day>t0 or bar['trade_date']!=day: raise ValueError('SERIES_FUTURE_OR_MIXED_DATE')
            raw=canonical(bar).decode();db.execute('INSERT INTO bars VALUES(?,?,?)',(sid,day,raw));count+=1;symbols.add(sid)
        with db.pg.cursor(name='series_digest') as cur:
            cur.execute('SELECT security,day::text,payload FROM bars ORDER BY security,day')
            for row in cur: logical.update(canonical(row)+b'\n')
        meta=dict(release_id=release,context=dict(accepted_trade_date=t0),source_digest=source_digest,bars=count,symbols=len(symbols),bar_logical_digest=logical.hexdigest())
        descriptor=db.seal(meta,source_binding=dict(sha256=source_digest),consumer_binding=dict(series_contract_id=CONTRACT,source_digest=source_digest,bar_count=count,symbol_count=len(symbols)))
        db.commit()
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);atomic_bytes(path,canonical(descriptor)+b'\n')
        return descriptor
    finally: db.close()

def range_rows(path,sid,start,end):
    path=Path(path)
    if path.suffix!='.json': raise ValueError('PG_SERIES_BINDING_REQUIRED_NO_FALLBACK')
    descriptor=json.loads(path.read_bytes())
    if descriptor.get('series_contract_id') not in (CONTRACT,LEGACY_CONTRACT) or end>descriptor['T0']: raise ValueError('PG_SERIES_CONTEXT_MISMATCH')
    with verified_series_read(descriptor) as db:
        rows=db.execute('SELECT day::text,payload FROM bars WHERE security=? AND day>=? AND day<=? ORDER BY day',(sid,start,end)).fetchall()
    return [(day,json.loads(payload)) for day,payload in rows]
