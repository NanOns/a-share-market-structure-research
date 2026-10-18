"""V4_READ_INDEX_R2: additive producer-built, immutable, Head-bound PG list projection.

HTTP never materializes this index. Missing dates fail closed once enabled.
Scalar values retain existing contracts; evidence stays in per-object details.
"""
import hashlib
import json
import re
from pathlib import Path
from psycopg import sql
from psycopg.types.json import Jsonb
from .v4_native import connection, create_schema, workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore

CONTRACT = 'V4_READ_INDEX_R2'
PG_AUTHORITY_KEY = 'native_read_index_r2'
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
    'stocks': {'close','scenario','final_eligibility','primary_industry','maturity','health','quality','rps5','rps20','code_status','owner_code_status','listing_status','first_seen_status','ipo_confirmation_status','identity_status','identity_link_status'},
    'sectors': {'sector_type','member_count','source_member_count','unmapped_count','quoted_count','output_state',
                'prior_rotation_state','sector_rs20','sector_rs5','breadth_ret1','breadth_ret5','breadth_ret20',
                'maturity','health','seed_width','participation_proxy'},
    'focus': {'T0','event','membership','validity','path_resolution','best_confirmed_state','end_date'},
    'radar': {'effective_event','trade_date','scenario','final_eligibility','identity_status','primary_industry','validity','path_resolution'},
}
HOME_EVENT_PRIORITY={'INVALIDATED':0,'EXITED':1,'WEAKENED':2,'UPGRADED':3,'REENTERED':4,'NEW':5}
HOME_RESPONSE_MAX_BYTES=512*1024


def producer_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def schema_for_revision(root, revision_sha256):
    """Store every immutable R2 read-index revision as rows in fixed schema v4."""
    if not isinstance(revision_sha256,str) or len(revision_sha256)!=64 or any(c not in '0123456789abcdef' for c in revision_sha256):
        raise ValueError('READ_INDEX_REVISION_DIGEST_INVALID')
    return 'v4'

def schema_binding_matches(root, binding):
    schema=binding.get('schema') if isinstance(binding,dict) else None
    legacy=(isinstance(schema,str) and (re.fullmatch(r'v4_read_index_r2_[a-f0-9]{16}',schema)
            or re.fullmatch(r'v4_[a-f0-9]{56}',schema)))
    return (isinstance(binding,dict) and (schema=='v4' or legacy)
            and isinstance(binding.get('digest'),str)
            and len(binding['digest'])==64
            and all(c in '0123456789abcdef' for c in binding['digest']))

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()


def validate_home_response(payload):
    """Guard both the prebuilt R2 response and HTTP response against full-row regressions."""
    if len(canonical(payload))>HOME_RESPONSE_MAX_BYTES:
        raise ValueError('HOME_RESPONSE_SIZE_LIMIT_EXCEEDED')
    def check_row(row,allowed):
        if set(row.get('fields',{}))-allowed or any(key in row for key in ('field_owner_bindings','knowledge_lineage','search_aliases')):
            raise ValueError('HOME_FULL_DETAIL_REGRESSION')
    for row in payload.get('changes',[]):check_row(row,{'effective_event','trade_date'})
    for row in payload.get('risks',[]):check_row(row,{'effective_event','trade_date'})
    for row in payload.get('rotations',[]):check_row(row,{'output_state','prior_rotation_state','sector_rs5','member_count'})
    for card in payload.get('sector_changes',[]):
        check_row(card.get('item',{}),{'output_state','prior_rotation_state','sector_rs5','member_count'})
        for row in card.get('member_previews',[]):check_row(row,{'effective_event','trade_date'})
    return len(canonical(payload))


def summary(row, domain=None):
    domain=domain or ('focus' if row.get('focus_scope') else 'sectors' if 'sector_type' in row['fields'] else 'stocks')
    result = {k:v for k,v in row.items() if k not in
              ('source','symbol_source','display_name_source','alias_source','field_owner_bindings','__detail_extras__')}
    result['fields'] = {k:{a:b for a,b in cell.items() if a in
                            ('value','quality','unit','reason','as_of','actual_count','required_count','adjustment_basis')}
                        for k,cell in row['fields'].items() if k in SUMMARY_FIELDS[domain]}
    result['detail_href'] = ('/api/v4/stocks/' if domain=='radar' else '/api/v4/'+domain+'/')+row['entity_id']
    result['list_contract_id']='V4_LIST_SUMMARY_R1'
    return result


def detail_payload(row):
    """Expand immutable producer-side detail-only facts into the detail row."""
    result=dict(row)
    extras=result.pop('__detail_extras__',{})
    if extras:
        result.update(extras)
    return result


def validate_query(query, context_id, dates, default_day, path):
    route_only=set()
    if path=='/api/v4/market/limits':
        route_only={'limit_state'}
    elif path in ('/api/v4/radar','/api/v4/focus/events'):
        route_only={'event','validity'}
    elif path=='/api/v4/forward/observations':
        route_only={'lane','rule','status','revision'}
    elif path=='/api/v4/forward/settlement':
        route_only={'lane','horizon','status','revision','settlement_revision'}
    elif path=='/api/v4/forward/statistics':
        route_only={'rule','status'}
    elif path=='/api/v4/forward/fep':
        route_only={'lane'}
    if set(query)-ALLOWED-route_only: raise ValueError('UNKNOWN_PARAMETER')
    if 'limit_state' in query:
        if path!='/api/v4/market/limits': raise ValueError('UNKNOWN_PARAMETER')
        if query['limit_state'] not in ('LIMIT_UP','LIMIT_DOWN','SUSPENDED','UNKNOWN','NOT_LIMIT'): raise ValueError('INVALID_LIMIT_STATE')
    if 'event' in query and query['event'] != '':
        if path not in ('/api/v4/radar','/api/v4/focus/events'): raise ValueError('UNKNOWN_PARAMETER')
        if query['event'] not in ('INVALIDATED','EXITED','WEAKENED','UPGRADED','REENTERED','NEW','PERSISTENT','DATA_UNAVAILABLE'): raise ValueError('INVALID_EVENT')
    day=query.get('trade_date', default_day)
    if day not in dates: raise ValueError('TARGET_DATE_NOT_GRANTED')
    if path!='/api/v4/context' and query.get('context_token')!=context_id:
        raise ValueError('CONTEXT_TOKEN_MISMATCH')
    if query.get('release_id',context_id)!=context_id or query.get('model_namespace','TDX_INDUSTRY_CONCEPT')!='TDX_INDUSTRY_CONCEPT':
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
    filters={}
    for key,field in FILTERS.items():
        if key=='state' and domain!='stocks': field='output_state'
        if query.get(key): filters[field]=query[key]
    return dict(needle=needle,filters=filters,entity=entity,sector=sector,specs=specs),offset,limit


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


def prepare(root, context_id, day, collections, responses, memberships):
    """One producer transaction; existing version content can only be verified."""
    root=Path(root);source_sha=producer_sha256()
    material=dict(contract_id=CONTRACT,head_token=context_id,T0=day,collections=collections,
                  producer_sha256=source_sha,
                  responses=responses,memberships=memberships)
    digest=hashlib.sha256(canonical(material)).hexdigest()
    schema=schema_for_revision(root,digest)
    with connection(schema) as pg:
        create_schema(pg,schema)
        pg.execute('''CREATE TABLE IF NOT EXISTS read_versions_r2(
            context_id text NOT NULL, day text NOT NULL, digest text NOT NULL,
            contract text NOT NULL, sealed boolean NOT NULL DEFAULT false, PRIMARY KEY(context_id,day,digest))''')
        pg.execute('''CREATE TABLE IF NOT EXISTS read_items_r2(
            context_id text NOT NULL, day text NOT NULL, digest text NOT NULL, domain text NOT NULL,
            entity_id text NOT NULL, symbol text, display_name text,
            aliases text[] NOT NULL, search_parts text[] NOT NULL,
            sector_ids text[] NOT NULL, values_json jsonb NOT NULL,
            summary jsonb NOT NULL, detail jsonb NOT NULL, detail_sha256 text NOT NULL,
            PRIMARY KEY(context_id,day,digest,domain,entity_id),
            FOREIGN KEY(context_id,day,digest) REFERENCES read_versions_r2(context_id,day,digest))''')
        pg.execute('''CREATE TABLE IF NOT EXISTS read_responses_r2(
            context_id text NOT NULL, day text NOT NULL, digest text NOT NULL, path text NOT NULL,
            payload jsonb NOT NULL, payload_sha256 text NOT NULL,
            PRIMARY KEY(context_id,day,digest,path), FOREIGN KEY(context_id,day,digest) REFERENCES read_versions_r2(context_id,day,digest))''')
        pg.execute('CREATE INDEX IF NOT EXISTS read_items_r2_order ON read_items_r2(context_id,day,digest,domain,entity_id)')
        pg.execute('''CREATE OR REPLACE FUNCTION read_index_r2_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN
            IF TG_TABLE_NAME='read_versions_r2' THEN
              IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed AND
                 (OLD.context_id,OLD.day,OLD.digest,OLD.contract)=(NEW.context_id,NEW.day,NEW.digest,NEW.contract) THEN RETURN NEW; END IF;
              IF TG_OP='INSERT' THEN RETURN NEW; END IF;
              RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
            END IF;
            IF TG_OP<>'INSERT' OR EXISTS(SELECT 1 FROM read_versions_r2 WHERE context_id=NEW.context_id AND day=NEW.day AND digest=NEW.digest AND sealed) THEN
              RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
            END IF;
            RETURN NEW;
          END $$''')
        for table in ('read_versions_r2','read_items_r2','read_responses_r2'):
            pg.execute(sql.Composed([sql.SQL('DROP TRIGGER IF EXISTS read_index_r2_immutable_guard ON '),sql.Identifier(table)]))
            pg.execute(sql.Composed([sql.SQL('CREATE TRIGGER read_index_r2_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON '),
                sql.Identifier(table),sql.SQL(' FOR EACH ROW EXECUTE FUNCTION read_index_r2_immutable()')]))
        pg.execute("CREATE OR REPLACE FUNCTION read_index_r2_no_truncate() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'READ_INDEX_IMMUTABLE'; END $$")
        for table in ('read_versions_r2','read_items_r2','read_responses_r2'):
            pg.execute(sql.Composed([sql.SQL('DROP TRIGGER IF EXISTS read_index_truncate_guard ON '),sql.Identifier(table)]))
            pg.execute(sql.Composed([sql.SQL('CREATE TRIGGER read_index_truncate_guard BEFORE TRUNCATE ON '),
                sql.Identifier(table),sql.SQL(' EXECUTE FUNCTION read_index_r2_no_truncate()')]))
        lock_key=hashlib.sha256(canonical([schema,context_id,day])).hexdigest()
        pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(lock_key,))
        old=pg.execute('SELECT contract,sealed FROM read_versions_r2 WHERE context_id=%s AND day=%s AND digest=%s',(context_id,day,digest)).fetchone()
        if old is None:
            pg.execute('INSERT INTO read_versions_r2(context_id,day,digest,contract) VALUES(%s,%s,%s,%s)',(context_id,day,digest,CONTRACT))
            with pg.cursor() as cur:
                for domain,rows in collections.items():
                    values=[]
                    for row in rows:
                        sid=row['entity_id'];aliases=sorted(set([sid,row['symbol'],*row.get('search_aliases',[])]))
                        aliases=sorted(set(aliases)|{v.upper() for v in aliases}|{v.upper().split('.')[-1] for v in aliases})
                        search=[str(v).casefold() for v in [sid,row['symbol'],row['display_name'],*row.get('search_aliases',[])]]
                        detail=detail_payload(row)
                        values.append((context_id,day,digest,domain,sid,row['symbol'],row['display_name'],aliases,search,
                            memberships.get(sid,[]),Jsonb({k:c.get('value') for k,c in row['fields'].items()}),
                            Jsonb(summary(row,domain)),Jsonb(detail),hashlib.sha256(canonical(detail)).hexdigest()))
                    cur.executemany('INSERT INTO read_items_r2(context_id,day,digest,domain,entity_id,symbol,display_name,aliases,search_parts,sector_ids,values_json,summary,detail,detail_sha256) VALUES('+','.join(['%s']*14)+')',values)
                cur.executemany('INSERT INTO read_responses_r2(context_id,day,digest,path,payload,payload_sha256) VALUES(%s,%s,%s,%s,%s,%s)',
                    [(context_id,day,digest,path,Jsonb(payload),hashlib.sha256(canonical(payload)).hexdigest()) for path,payload in responses.items()])
            pg.execute('UPDATE read_versions_r2 SET sealed=true WHERE context_id=%s AND day=%s AND digest=%s',(context_id,day,digest))
        elif old!=(CONTRACT,True):
            raise ValueError('READ_INDEX_IMMUTABLE_VERSION_CONFLICT')
        counts=dict(pg.execute('SELECT domain,count(*) FROM read_items_r2 WHERE context_id=%s AND day=%s AND digest=%s GROUP BY domain',(context_id,day,digest)).fetchall())
        if counts!={k:len(v) for k,v in collections.items() if v}: raise ValueError('READ_INDEX_COUNT_MISMATCH')
        # Read back every row once before handing the index to HTTP.
        for domain,rows in collections.items():
            actual=pg.execute('SELECT detail FROM read_items_r2 WHERE context_id=%s AND day=%s AND digest=%s AND domain=%s ORDER BY entity_id COLLATE "C"',(context_id,day,digest,domain)).fetchall()
            expected=sorted((detail_payload(row) for row in rows),key=lambda r:r['entity_id'])
            if [r[0] for r in actual]!=expected: raise ValueError('READ_INDEX_ROW_PARITY_FAILED')
        identity=ForwardFactStore._database_identity(pg)
    return dict(contract_id=CONTRACT,engine='postgresql',schema=schema,producer_sha256=source_sha,
                head_token=context_id,T0=day,
                digest=digest,counts=counts,database_identity=identity)


class ReadIndex:
    def __init__(self, root, binding, context_id, day):
        self.root=Path(root);self.binding=binding;self.context_id=context_id;self.day=day
        if not isinstance(binding,dict) or not {'contract_id','engine','schema','head_token','T0','digest','counts','database_identity'}<=set(binding):
            raise ValueError('READ_INDEX_BINDING_SCHEMA_INVALID')
        if binding['contract_id']!=CONTRACT:raise ValueError('READ_INDEX_BINDING_CONTRACT_MISMATCH')
        if binding['engine']!='postgresql' or not schema_binding_matches(root,binding):
            raise ValueError('READ_INDEX_SCHEMA_MISMATCH')
        if (binding['head_token'],binding['T0'])!=(context_id,day):raise ValueError('READ_INDEX_CONTEXT_MISMATCH')
        self.schema='v4'

    def attest(self, pg):
        if ForwardFactStore._database_identity(pg)!=self.binding['database_identity']: raise ValueError('READ_INDEX_DATABASE_MISMATCH')
        if self.binding['schema']!='v4':
            mapped=pg.execute("""SELECT digest,contract,domain_counts,verification FROM read_index_migration_map_r1
                WHERE generation='R2' AND source_schema=%s AND context_id=%s AND day=%s""",
                (self.binding['schema'],self.context_id,self.day)).fetchone()
            if (not mapped or mapped[0]!=self.binding['digest'] or mapped[1]!=CONTRACT
                    or mapped[2]!=self.binding['counts'] or mapped[3].get('status')!='VERIFIED'):
                raise ValueError('READ_INDEX_LEGACY_VERSION_NOT_MIGRATED')
        row=pg.execute('SELECT digest,contract,sealed FROM read_versions_r2 WHERE context_id=%s AND day=%s AND digest=%s',(self.context_id,self.day,self.binding['digest'])).fetchone()
        if row is None or row[2] is not True:raise ValueError('READ_INDEX_VERSION_UNAVAILABLE')
        if row[1]!=CONTRACT:raise ValueError('READ_INDEX_VERSION_CONTRACT_MISMATCH')
        if row[0]!=self.binding['digest']:raise ValueError('READ_INDEX_VERSION_DIGEST_MISMATCH')

    def response(self, path):
        with connection(self.schema,read_only=True) as pg:
            self.attest(pg)
            row=pg.execute('SELECT payload,payload_sha256 FROM read_responses_r2 WHERE context_id=%s AND day=%s AND digest=%s AND path=%s',(self.context_id,self.day,self.binding['digest'],path)).fetchone()
        if row is None: return None
        if hashlib.sha256(canonical(row[0])).hexdigest()!=row[1]: raise ValueError('READ_INDEX_RESPONSE_DIGEST_MISMATCH')
        return row[0]

    @staticmethod
    def _detail_row(pg, context_id, day, digest, domain, key):
        # Prefer the primary key. Combining entity, symbol and alias
        # predicates with OR prevents PostgreSQL from using the composite
        # primary-key index efficiently on the dominant detail route.
        rows=pg.execute('''SELECT detail,detail_sha256 FROM read_items_r2
            WHERE context_id=%s AND day=%s AND digest=%s AND domain=%s AND entity_id=%s LIMIT 2''',
            (context_id,day,digest,domain,key)).fetchall()
        if not rows:
            rows=pg.execute('''SELECT detail,detail_sha256 FROM read_items_r2
                WHERE context_id=%s AND day=%s AND digest=%s AND domain=%s AND upper(symbol)=upper(%s) LIMIT 2''',
                (context_id,day,digest,domain,key)).fetchall()
        if not rows:
            rows=pg.execute('''SELECT detail,detail_sha256 FROM read_items_r2
                WHERE context_id=%s AND day=%s AND digest=%s AND domain=%s AND %s=ANY(aliases) LIMIT 2''',
                (context_id,day,digest,domain,key)).fetchall()
        if len(rows)!=1:return None
        row=rows[0]
        if hashlib.sha256(canonical(row[0])).hexdigest()!=row[1]: raise ValueError('READ_INDEX_DETAIL_DIGEST_MISMATCH')
        return row[0]

    def response_and_detail(self, path, domain, key):
        """Read the shared context and one detail with a single attested PG session."""
        with connection(self.schema,read_only=True) as pg:
            self.attest(pg)
            response=pg.execute('SELECT payload,payload_sha256 FROM read_responses_r2 WHERE context_id=%s AND day=%s AND digest=%s AND path=%s',
                                (self.context_id,self.day,self.binding['digest'],path)).fetchone()
            detail=self._detail_row(pg,self.context_id,self.day,self.binding['digest'],domain,key)
        if response is None:return None,None
        if hashlib.sha256(canonical(response[0])).hexdigest()!=response[1]: raise ValueError('READ_INDEX_RESPONSE_DIGEST_MISMATCH')
        return response[0],detail

    def page(self, domain, query, *, entity=None, sector=None):
        selection,offset,limit=query_parts(domain,query,entity=entity,sector=sector)
        with connection(self.schema,read_only=True) as pg:
            self.attest(pg)
            rows=pg.execute('''SELECT entity_id,symbol,display_name,aliases,search_parts,
                                      sector_ids,values_json,summary
                                 FROM read_items_r2
                                WHERE context_id=%s AND day=%s AND digest=%s AND domain=%s''',
                            (self.context_id,self.day,self.binding['digest'],domain)).fetchall()
        matched=[]
        for entity_id,symbol,name,aliases,search_parts,sector_ids,values_json,summary in rows:
            if selection['needle'] and not any(selection['needle'] in str(part).casefold() for part in search_parts):continue
            if selection['entity'] and selection['entity'] not in aliases:continue
            if selection['sector'] and selection['sector'] not in sector_ids:continue
            if any(str((values_json or {}).get(field) or '')!=value for field,value in selection['filters'].items()):continue
            matched.append(dict(entity_id=entity_id,symbol=symbol,display_name=name,values=values_json or {},summary=summary))
        def sort_value(row,key):
            aliases={'id':'entity_id','name':'display_name','symbol':'symbol'}
            if key in aliases:return row.get(aliases[key])
            field=('scenario' if domain=='stocks' else 'output_state') if key=='state' else key
            value=row['values'].get(field)
            if key in NUMERIC and value not in (None,''):
                try:return float(value)
                except (TypeError,ValueError):return None
            return str(value).casefold() if value is not None else None
        matched.sort(key=lambda row:row['entity_id'])
        for spec in reversed(selection['specs']):
            key=spec.lstrip('-');present=[];missing=[]
            for row in matched:
                (missing if sort_value(row,key) is None else present).append(row)
            present.sort(key=lambda row:sort_value(row,key),reverse=spec.startswith('-'))
            matched=present+missing
        total=len(matched)
        page=matched[offset:offset+limit]
        return dict(status='READY' if total else 'EMPTY_VALID',items=[r['summary'] for r in page],total=total,
                    offset=offset,limit=limit,has_next=offset+limit<total,domain=domain,gap=None)

    def detail(self, domain, key):
        with connection(self.schema,read_only=True) as pg:
            self.attest(pg)
            return self._detail_row(pg,self.context_id,self.day,self.binding['digest'],domain,key)

    def display_identities(self, domain, entity_ids):
        """Bounded identity/name join for already selected event or ladder rows."""
        keys=sorted({str(v) for v in entity_ids if v})
        if not keys:return {}
        with connection(self.schema,read_only=True) as pg:
            self.attest(pg)
            rows=pg.execute('''SELECT entity_id,symbol,display_name,detail,detail_sha256
                FROM read_items_r2 WHERE context_id=%s AND day=%s AND digest=%s AND domain=%s AND entity_id=ANY(%s)''',
                (self.context_id,self.day,self.binding['digest'],domain,keys)).fetchall()
        result={}
        for entity_id,symbol,name,detail,digest in rows:
            if hashlib.sha256(canonical(detail)).hexdigest()!=digest:raise ValueError('READ_INDEX_DETAIL_DIGEST_MISMATCH')
            identity=dict(entity_id=entity_id,symbol=symbol,display_name=name,
                display_name_scope=detail.get('display_name_scope'),display_name_source=detail.get('display_name_source'),
                display_name_observed_at=detail.get('display_name_observed_at'),
                name_quality='KNOWN' if name else 'UNKNOWN',
                name_reason=None if name else 'ACCEPTED_STOCK_DISPLAY_NAME_NOT_PRESENT')
            if domain=='stocks':
                cell=detail.get('fields',{}).get('primary_industry',{})
                identity['primary_industry_id']=cell.get('value') if isinstance(cell,dict) else None
            result[entity_id]=identity
        return result


def load(root, context_id, day, *, authority=None, allow_missing=False):
    """Resolve only the exact Head-embedded PG index binding.

    The former config JSON catalogue was another runtime selector and could
    outlive or disagree with the operational Head. Existing historical Heads
    without this optional R2 binding continue through the direct PG Owner BFF.
    """
    if authority is None:
        if allow_missing:return None
        raise ValueError('READ_INDEX_PG_HEAD_BINDING_REQUIRED_NO_FILE_FALLBACK')
    if (not isinstance(authority,dict) or authority.get('contract_id')!=CONTRACT
            or authority.get('head_token')!=context_id or not isinstance(authority.get('versions'),dict)):
        raise ValueError('READ_INDEX_PG_HEAD_AUTHORITY_INVALID')
    binding=authority.get('versions',{}).get(day)
    if binding is None:
        if allow_missing:return None
        raise ValueError('READ_INDEX_DATE_NOT_PREPARED')
    if not isinstance(binding,dict):raise ValueError('READ_INDEX_BINDING_SCHEMA_INVALID')
    return ReadIndex(root,binding,context_id,day)


def prepare_bff(root, candidate, *, days=None, jobs=None):
    """Producer/migration entrypoint, never invoked from an HTTP request."""
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    root=Path(root)
    api=OperationalSuccessorReaderV1(root,candidate)
    bff=CoreProductBFFR1(api,jobs);bff.building_read_index=True
    dates=days or [candidate['accepted_trade_date']]
    prepared={}
    for day in dates:
        if day not in candidate['published_sessions']: raise ValueError('READ_INDEX_UNPUBLISHED_DATE')
        # Build the exact dated full response once, then only SQL pages serve it.
        query=dict(trade_date=day,context_token=api.context_id)
        collections={domain:bff.project(domain,day) for domain in ('stocks','sectors','focus')}
        responses={path:bff.get(path,query)[1] for path in ('/api/v4/context','/api/v4/home')}
        validate_home_response(responses['/api/v4/home'])
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
        prepared[day]=prepare(root,api.context_id,day,collections,responses,memberships)
    authority=dict(contract_id=CONTRACT,head_token=api.context_id,versions=prepared)
    candidate[PG_AUTHORITY_KEY]=authority
    return dict(contract_id=CONTRACT,head_token=api.context_id,dates=prepared,
                binding=PG_AUTHORITY_KEY,head_changed=False)
