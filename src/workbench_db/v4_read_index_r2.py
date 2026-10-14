"""V4_READ_INDEX_R2: additive producer-built, immutable, Head-bound PG list projection.

HTTP never materializes this index. Missing dates fail closed once enabled.
Scalar values retain existing contracts; evidence stays in per-object details.
"""
import hashlib
import json
from pathlib import Path
from psycopg import sql
from psycopg.types.json import Jsonb
from .v4_native import connection, create_schema, workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore

CONTRACT = 'V4_READ_INDEX_R2'
AUTHORITY = 'config/v4_read_index_authority_r2.json'
NUMERIC = {'sector_rs20_pct','sector_rs5_pct','sector_rs20','sector_rs5',
           'breadth_ret1','breadth_ret5','breadth_ret20','ma20_width',
           'participation_proxy','member_count','close','rps5','rps20'}
SORTS = NUMERIC | {'id','name','symbol','state','output_state'}
FILTERS = {'state':'scenario','type':'sector_type','maturity':'maturity',
           'health':'health','rotation':'output_state','quality':'quality',
           'eligibility':'final_eligibility','event':'effective_event','validity':'validity'}
ALLOWED = {'q','state','limit','offset','sort','context_token','trade_date',
           'release_id','model_namespace','type','maturity','health','rotation',
           'quality','eligibility','period','price_basis','as_of','view','left',
           'right','mode','snapshot_token','followup'}
SUMMARY_FIELDS = {
    'stocks': {'close','scenario','final_eligibility','primary_industry','maturity','health','quality','rps5','rps20','code_status','identity_status'},
    'sectors': {'sector_type','member_count','source_member_count','unmapped_count','quoted_count','output_state',
                'prior_rotation_state','sector_rs20','sector_rs5','breadth_ret1','breadth_ret5','breadth_ret20',
                'maturity','health','seed_width','participation_proxy'},
    'focus': {'T0','event','membership','validity','path_resolution','best_confirmed_state','end_date'},
    'radar': {'effective_event','trade_date','scenario','final_eligibility','identity_status','primary_industry','validity','path_resolution'},
}
HOME_EVENT_PRIORITY={'INVALIDATED':0,'EXITED':1,'WEAKENED':2,'UPGRADED':3,'REENTERED':4,'NEW':5}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()


def summary(row, domain=None):
    domain=domain or ('focus' if row.get('focus_scope') else 'sectors' if 'sector_type' in row['fields'] else 'stocks')
    result = {k:v for k,v in row.items() if k not in
              ('source','symbol_source','display_name_source','alias_source','field_owner_bindings')}
    result['fields'] = {k:{a:b for a,b in cell.items() if a in
                            ('value','quality','unit','reason','as_of','actual_count','required_count','adjustment_basis')}
                        for k,cell in row['fields'].items() if k in SUMMARY_FIELDS[domain]}
    result['detail_href'] = ('/api/v4/stocks/' if domain=='radar' else '/api/v4/'+domain+'/')+row['entity_id']
    result['list_contract_id']='V4_LIST_SUMMARY_R1'
    return result


def validate_query(query, token, dates, default_day, path):
    route_only={'limit_state'} if path=='/api/v4/market/limits' else {'event','validity'} if path in ('/api/v4/radar','/api/v4/focus/events') else set()
    if set(query)-ALLOWED-route_only: raise ValueError('UNKNOWN_PARAMETER')
    if 'limit_state' in query:
        if path!='/api/v4/market/limits': raise ValueError('UNKNOWN_PARAMETER')
        if query['limit_state'] not in ('LIMIT_UP','LIMIT_DOWN','SUSPENDED','UNKNOWN','NOT_LIMIT'): raise ValueError('INVALID_LIMIT_STATE')
    if 'event' in query:
        if path not in ('/api/v4/radar','/api/v4/focus/events'): raise ValueError('UNKNOWN_PARAMETER')
        if query['event'] not in ('INVALIDATED','EXITED','WEAKENED','UPGRADED','REENTERED','NEW','PERSISTENT','DATA_UNAVAILABLE'): raise ValueError('INVALID_EVENT')
    day=query.get('trade_date', default_day)
    if day not in dates: raise ValueError('TARGET_DATE_NOT_GRANTED')
    if path!='/api/v4/context' and query.get('context_token')!=token:
        raise ValueError('CONTEXT_TOKEN_MISMATCH')
    if query.get('release_id',token)!=token or query.get('model_namespace','TDX_INDUSTRY_CONCEPT')!='TDX_INDUSTRY_CONCEPT':
        raise ValueError('CONTEXT_TOKEN_MISMATCH')
    offset=int(query.get('offset',0));limit=int(query.get('limit',30))
    if not 0<=offset<=1000000 or not 1<=limit<=200: raise ValueError('INVALID_QUERY_BOUND')
    return day


def query_parts(domain, query, *, entity=None, sector=None):
    offset=int(query.get('offset',0));limit=int(query.get('limit',30))
    if not 0<=offset<=1000000 or not 1<=limit<=200: raise ValueError('INVALID_QUERY_BOUND')
    needle=query.get('q','').strip().casefold()
    if len(needle)>80: raise ValueError('INVALID_QUERY_BOUND')
    specs=query.get('sort','id').split(',')
    if len(specs)>4 or any(k.lstrip('-') not in SORTS for k in specs): raise ValueError('INVALID_SORT_FIELD')
    clauses=[];args=[]
    if needle:
        clauses.append(sql.SQL('EXISTS (SELECT 1 FROM unnest(search_parts) part WHERE strpos(part,%s)>0)'));args.append(needle)
    if entity:
        clauses.append(sql.SQL('%s=ANY(aliases)'));args.append(entity)
    if sector:
        clauses.append(sql.SQL('%s=ANY(sector_ids)'));args.append(sector)
    for key,field in FILTERS.items():
        if key=='state' and domain!='stocks': field='output_state'
        if query.get(key):
            clauses.append(sql.SQL('values_json->>{}=%s').format(sql.Literal(field)));args.append(query[key])
    order=[]
    for spec in specs:
        key=spec.lstrip('-');direction=sql.SQL('DESC' if spec.startswith('-') else 'ASC')
        top={'id':'entity_id','name':'display_name','symbol':'symbol'}.get(key)
        field=('scenario' if domain=='stocks' else 'output_state') if key=='state' else key
        expression=sql.Identifier(top) if top else sql.SQL('values_json->>{}').format(sql.Literal(field))
        expression=sql.SQL('({})::numeric').format(expression) if key in NUMERIC else sql.SQL('{} COLLATE "C"').format(expression)
        order.append(sql.SQL('{} {} NULLS LAST').format(expression,direction))
    order.append(sql.SQL('entity_id COLLATE "C" ASC'))
    where=sql.SQL(' AND ').join(clauses) if clauses else sql.SQL('TRUE')
    return where,args,sql.SQL(',').join(order),offset,limit


def materialize_radar_rows(stocks, focus_rows, sector_memberships, rotations, events, forward_ref, day):
    """Build one Head-bound, de-duplicated accepted Focus event list before paging."""
    from workbench_service.r43_operational_bff import owner_cell
    focus_by_entity={row['entity_id']:row for row in focus_rows}
    covered=set()
    for rotation in rotations[:10]:covered.update(sector_memberships.get(rotation['entity_id'],set()))
    selected={}
    for event in sorted((e for e in events if e.get('event') in HOME_EVENT_PRIORITY and e.get('entity_id') in stocks),
                        key=lambda e:(HOME_EVENT_PRIORITY[e['event']],e['entity_id'])):
        selected.setdefault(event['entity_id'],event)
    result=[]
    for entity_id,event in selected.items():
        if entity_id in covered:continue
        stock=stocks[entity_id]
        row={k:stock[k] for k in ('entity_id','security_id','symbol','display_name','display_name_scope','display_name_source','trade_date') if k in stock}
        row['fields']={k:stock['fields'][k] for k in ('scenario','final_eligibility','identity_status','primary_industry') if k in stock.get('fields',{})}
        row['fields']['effective_event']=owner_cell(event['event'],forward_ref,'events.event',day)
        row['fields']['trade_date']=owner_cell(day,forward_ref,'events.trade_date',day)
        focus=focus_by_entity.get(entity_id,{})
        for key in ('validity','path_resolution','best_confirmed_state','membership'):
            cell=focus.get('fields',{}).get(key)
            if cell is not None:row['fields'][key]=cell
        row['source']=forward_ref;row['search_aliases']=stock.get('search_aliases',[])
        result.append(row)
    return result


def prepare(root, token, day, collections, responses, memberships):
    """One producer transaction; existing version content can only be verified."""
    root=Path(root);schema=workspace_schema(root,'read_index_r2')
    material=dict(contract_id=CONTRACT,head_token=token,T0=day,collections=collections,
                  producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  responses=responses,memberships=memberships)
    digest=hashlib.sha256(canonical(material)).hexdigest()
    with connection(schema) as pg:
        create_schema(pg,schema)
        pg.execute('''CREATE TABLE IF NOT EXISTS read_versions(
            token text NOT NULL, day text NOT NULL, digest text NOT NULL,
            contract text NOT NULL, sealed boolean NOT NULL DEFAULT false, PRIMARY KEY(token,day))''')
        pg.execute('''CREATE TABLE IF NOT EXISTS read_items(
            token text NOT NULL, day text NOT NULL, domain text NOT NULL,
            entity_id text NOT NULL, symbol text, display_name text,
            aliases text[] NOT NULL, search_parts text[] NOT NULL,
            sector_ids text[] NOT NULL, values_json jsonb NOT NULL,
            summary jsonb NOT NULL, detail jsonb NOT NULL, detail_sha256 text NOT NULL,
            PRIMARY KEY(token,day,domain,entity_id),
            FOREIGN KEY(token,day) REFERENCES read_versions(token,day))''')
        pg.execute('''CREATE TABLE IF NOT EXISTS read_responses(
            token text NOT NULL, day text NOT NULL, path text NOT NULL,
            payload jsonb NOT NULL, payload_sha256 text NOT NULL,
            PRIMARY KEY(token,day,path), FOREIGN KEY(token,day) REFERENCES read_versions(token,day))''')
        pg.execute('CREATE INDEX IF NOT EXISTS read_items_order ON read_items(token,day,domain,entity_id)')
        pg.execute('''CREATE OR REPLACE FUNCTION read_index_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN
            IF TG_TABLE_NAME='read_versions' THEN
              IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed AND
                 (OLD.token,OLD.day,OLD.digest,OLD.contract)=(NEW.token,NEW.day,NEW.digest,NEW.contract) THEN RETURN NEW; END IF;
              IF TG_OP='INSERT' THEN RETURN NEW; END IF;
              RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
            END IF;
            IF TG_OP<>'INSERT' OR EXISTS(SELECT 1 FROM read_versions WHERE token=NEW.token AND day=NEW.day AND sealed) THEN
              RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
            END IF;
            RETURN NEW;
          END $$''')
        for table in ('read_versions','read_items','read_responses'):
            pg.execute(sql.SQL('DROP TRIGGER IF EXISTS read_index_immutable_guard ON {}').format(sql.Identifier(table)))
            pg.execute(sql.SQL('CREATE TRIGGER read_index_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON {} FOR EACH ROW EXECUTE FUNCTION read_index_immutable()').format(sql.Identifier(table)))
        pg.execute("CREATE OR REPLACE FUNCTION read_index_no_truncate() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'READ_INDEX_IMMUTABLE'; END $$")
        for table in ('read_versions','read_items','read_responses'):
            pg.execute(sql.SQL('DROP TRIGGER IF EXISTS read_index_truncate_guard ON {}').format(sql.Identifier(table)))
            pg.execute(sql.SQL('CREATE TRIGGER read_index_truncate_guard BEFORE TRUNCATE ON {} EXECUTE FUNCTION read_index_no_truncate()').format(sql.Identifier(table)))
        pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(schema+token+day,))
        old=pg.execute('SELECT digest FROM read_versions WHERE token=%s AND day=%s',(token,day)).fetchone()
        if old and old[0]!=digest: raise ValueError('READ_INDEX_IMMUTABLE_VERSION_CONFLICT')
        if old is None:
            pg.execute('INSERT INTO read_versions(token,day,digest,contract) VALUES(%s,%s,%s,%s)',(token,day,digest,CONTRACT))
            with pg.cursor() as cur:
                for domain,rows in collections.items():
                    values=[]
                    for row in rows:
                        sid=row['entity_id'];aliases=sorted(set([sid,row['symbol'],*row.get('search_aliases',[])]))
                        aliases=sorted(set(aliases)|{v.upper() for v in aliases}|{v.upper().split('.')[-1] for v in aliases})
                        search=[str(v).casefold() for v in [sid,row['symbol'],row['display_name'],*row.get('search_aliases',[])]]
                        values.append((token,day,domain,sid,row['symbol'],row['display_name'],aliases,search,
                            memberships.get(sid,[]),Jsonb({k:c.get('value') for k,c in row['fields'].items()}),
                            Jsonb(summary(row,domain)),Jsonb(row),hashlib.sha256(canonical(row)).hexdigest()))
                    cur.executemany('INSERT INTO read_items VALUES('+','.join(['%s']*13)+')',values)
                cur.executemany('INSERT INTO read_responses VALUES(%s,%s,%s,%s,%s)',
                    [(token,day,path,Jsonb(payload),hashlib.sha256(canonical(payload)).hexdigest()) for path,payload in responses.items()])
            pg.execute('UPDATE read_versions SET sealed=true WHERE token=%s AND day=%s',(token,day))
        counts=dict(pg.execute('SELECT domain,count(*) FROM read_items WHERE token=%s AND day=%s GROUP BY domain',(token,day)).fetchall())
        if counts!={k:len(v) for k,v in collections.items() if v}: raise ValueError('READ_INDEX_COUNT_MISMATCH')
        # Read back every row once before handing the index to HTTP.
        for domain,rows in collections.items():
            actual=pg.execute('SELECT detail FROM read_items WHERE token=%s AND day=%s AND domain=%s ORDER BY entity_id COLLATE "C"',(token,day,domain)).fetchall()
            if [r[0] for r in actual]!=sorted(rows,key=lambda r:r['entity_id']): raise ValueError('READ_INDEX_ROW_PARITY_FAILED')
        identity=ForwardFactStore._database_identity(pg)
    return dict(contract_id=CONTRACT,engine='postgresql',schema=schema,head_token=token,T0=day,
                digest=digest,counts=counts,database_identity=identity)


class ReadIndex:
    def __init__(self, root, binding, token, day):
        self.root=Path(root);self.binding=binding;self.token=token;self.day=day
        if (binding.get('contract_id'),binding.get('engine'),binding.get('schema'),binding.get('head_token'),binding.get('T0'))!=(CONTRACT,'postgresql',workspace_schema(root,'read_index_r2'),token,day):
            raise ValueError('READ_INDEX_CONTEXT_MISMATCH')

    def attest(self, pg):
        if ForwardFactStore._database_identity(pg)!=self.binding['database_identity']: raise ValueError('READ_INDEX_DATABASE_MISMATCH')
        row=pg.execute('SELECT digest,contract,sealed FROM read_versions WHERE token=%s AND day=%s',(self.token,self.day)).fetchone()
        if row!=(self.binding['digest'],CONTRACT,True): raise ValueError('READ_INDEX_VERSION_UNAVAILABLE')

    def response(self, path):
        with connection(self.binding['schema'],read_only=True) as pg:
            self.attest(pg)
            row=pg.execute('SELECT payload,payload_sha256 FROM read_responses WHERE token=%s AND day=%s AND path=%s',(self.token,self.day,path)).fetchone()
        if row is None: return None
        if hashlib.sha256(canonical(row[0])).hexdigest()!=row[1]: raise ValueError('READ_INDEX_RESPONSE_DIGEST_MISMATCH')
        return row[0]

    def page(self, domain, query, *, entity=None, sector=None):
        where,args,order,offset,limit=query_parts(domain,query,entity=entity,sector=sector)
        base=(self.token,self.day,domain)
        predicate=sql.SQL('token=%s AND day=%s AND domain=%s AND {}').format(where)
        with connection(self.binding['schema'],read_only=True) as pg:
            self.attest(pg)
            total=pg.execute(sql.SQL('SELECT count(*) FROM read_items WHERE {}').format(predicate),base+tuple(args)).fetchone()[0]
            rows=pg.execute(sql.SQL('SELECT summary FROM read_items WHERE {} ORDER BY {} LIMIT %s OFFSET %s').format(predicate,order),base+tuple(args)+(limit,offset)).fetchall()
        return dict(status='READY' if total else 'EMPTY_VALID',items=[r[0] for r in rows],total=total,
                    offset=offset,limit=limit,has_next=offset+limit<total,domain=domain,gap=None)

    def detail(self, domain, key):
        with connection(self.binding['schema'],read_only=True) as pg:
            self.attest(pg)
            rows=pg.execute('''SELECT detail,detail_sha256 FROM read_items
                WHERE token=%s AND day=%s AND domain=%s AND
                (entity_id=%s OR upper(symbol)=upper(%s) OR %s=ANY(aliases)) LIMIT 2''',
                (self.token,self.day,domain,key,key,key)).fetchall()
        if len(rows)!=1: return None
        row=rows[0]
        if hashlib.sha256(canonical(row[0])).hexdigest()!=row[1]: raise ValueError('READ_INDEX_DETAIL_DIGEST_MISMATCH')
        return row[0]


def load(root, token, day, *, allow_missing=False):
    path=Path(root)/AUTHORITY
    if not path.exists(): return None
    authority=json.loads(path.read_bytes())
    if authority.get('contract_id')!=CONTRACT: raise ValueError('READ_INDEX_AUTHORITY_CONTRACT_MISMATCH')
    binding=authority.get('versions',{}).get(token,{}).get(day)
    if binding is None:
        if allow_missing:return None
        raise ValueError('READ_INDEX_DATE_NOT_PREPARED')
    return ReadIndex(root,binding,token,day)


def prepare_bff(root, candidate, *, days=None, jobs=None):
    """Producer/migration entrypoint, never invoked from an HTTP request."""
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    root=Path(root)
    api=OperationalSuccessorReaderV1(root,candidate)
    bff=CoreProductBFFR1(api,jobs);bff.building_read_index=True
    dates=days or [candidate['accepted_trade_date']]
    prepared={}
    for day in dates:
        if day not in candidate['published_sessions']: raise ValueError('READ_INDEX_UNPUBLISHED_DATE')
        # Build the exact dated full response once, then only SQL pages serve it.
        query=dict(trade_date=day,context_token=api.token)
        collections={domain:bff.project(domain,day) for domain in ('stocks','sectors','focus')}
        responses={path:bff.get(path,query)[1] for path in ('/api/v4/context','/api/v4/home')}
        stocks={row['entity_id']:row for row in collections['stocks']}
        memberships_by_sector={row['sector_id']:set(row.get('member_ids',[])) for row in bff.source('sector',day)}
        events=bff.source('forward',day).get('events',[])
        collections['radar']=materialize_radar_rows(stocks,collections['focus'],memberships_by_sector,
            responses['/api/v4/home'].get('rotations',[]),events,candidate['owners'][day]['forward'],day)
        focus=bff.get('/api/v4/focus',dict(query,limit='1'))[1]
        responses['/api/v4/focus-meta']={k:v for k,v in focus.items() if k not in
            ('context','context_token','production_accepted','items','total','offset','limit','has_next','status','domain','gap')}
        memberships={}
        for sector in bff.source('sector',day):
            for sid in set(sector.get('member_ids',[])): memberships.setdefault(sid,[]).append(sector['sector_id'])
        prepared[day]=prepare(root,api.token,day,collections,responses,memberships)
    path=root/AUTHORITY
    authority=json.loads(path.read_bytes()) if path.exists() else dict(contract_id=CONTRACT,versions={})
    if authority.get('contract_id')!=CONTRACT: raise ValueError('READ_INDEX_AUTHORITY_CONTRACT_MISMATCH')
    authority['versions'].setdefault(api.token,{}).update(prepared)
    # An old Head is a read-only migration input; the index is an additive artifact.
    atomic_json(root,path,authority)
    return dict(contract_id=CONTRACT,head_token=api.token,dates=prepared,head_changed=False)
