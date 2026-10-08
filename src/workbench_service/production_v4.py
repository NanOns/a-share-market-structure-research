"""FP02 immutable indexed research snapshots. No source discovery or TDX writes."""
import gzip
import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .current_v4_context import CurrentAcceptedV4Reader, SourceInvalid, canonical, digest
from .v4_daily_refresh import atomic_bytes, refresh_status

POINTER = 'config/v4_research_snapshot_authority_v1.json'
DOMAINS = ('stocks', 'sectors', 'events', 'radar', 'forward', 'settlement', 'sources', 'market', 'focus')
REQUIRED_METADATA=('owner','release_id','source_snapshot','contract_version','source_as_of','trading_date','input_digest','published_at','evidence_origin','evidence_state','data_quality_state','knowledge_lineage')

def validate_release_metadata(manifest):
    metadata=manifest.get('metadata',{})
    if any(k not in metadata for k in REQUIRED_METADATA) or metadata.get('evidence_origin')!='REAL_ACCEPTED_SOURCE':raise SourceInvalid('RELEASE_METADATA_INCOMPLETE_OR_NON_REAL')
    if metadata['trading_date']!=manifest['context']['accepted_trade_date']:raise SourceInvalid('RELEASE_METADATA_DATE_CONFLICT')
    return metadata

def value_projection(value):
    # Repeated lineage is addressable through source_digest/source_field. Preserve
    # every research value, quality and reason, without copying its source graph.
    omit={'source_refs','source_identity','producer_identity','source_publications','input_digests','contract_refs','runtime_source_bindings'}
    if isinstance(value,dict):return {k:value_projection(v) for k,v in value.items() if k not in omit}
    if isinstance(value,list):return [value_projection(v) for v in value]
    return value


def reference(root, path):
    p = Path(path)
    if not p.is_absolute(): p = root / p
    h = hashlib.sha256()
    with p.open('rb') as f:
        while chunk := f.read(8 * 1024 * 1024): h.update(chunk)
    return dict(path=p.relative_to(root).as_posix(), sha256=h.hexdigest(), bytes=p.stat().st_size)


def frozen_current_reader(root):
    root=Path(root).resolve()
    runtime=json.loads((root/'config/v4_production_runtime_authority_v1.json').read_bytes())
    if runtime.get('contract_id')!='V4_PRODUCTION_RUNTIME_AUTHORITY_V1' or not runtime.get('ui_read_only') or runtime.get('tdx_write_authorized') or runtime.get('trading_action_authorized'):
        raise SourceInvalid('RUNTIME_AUTHORITY_INVALID')
    verifier=CurrentAcceptedV4Reader(root,require_runtime=True);verifier._read(runtime['read_authority'])
    reader=CurrentAcceptedV4Reader(root,contract_path=runtime['read_authority']['path'],follow_runtime=False)
    _,sha=reader._contract()
    if sha!=runtime['read_authority']['sha256']:raise SourceInvalid('FROZEN_READ_AUTHORITY_MISMATCH')
    return reader,runtime['read_authority']


def compact_cell(cell, ref, field, date):
    """Retain value/quality/reason; provenance points to exact original field."""
    if not isinstance(cell, dict): cell = dict(value=cell, quality='KNOWN')
    quality = cell.get('quality', 'UNKNOWN')
    reason = cell.get('reason') or cell.get('reason_code') or cell.get('unknown_reason')
    if quality in ('UNKNOWN', 'NOT_IMPLEMENTED') and not reason:
        reason = 'OWNER_FIELD_REASON_MISSING_SEE_AUD_FP01_FIELD_REASON_GAPS'
    price = field in ('open', 'high', 'low', 'close')
    return dict(value=value_projection(cell.get('value')), quality=quality, reason=reason,
        source_digest=ref['sha256'], source_field=field,
        source_contract_id=cell.get('producer_contract_id') or cell.get('model_contract_id') or cell.get('contract_id') or ref.get('contract_id'),
        parameter_set_id=cell.get('parameter_set_id'), source_as_of=cell.get('max_source_date', date),
        unit=cell.get('unit') or ('CNY' if price else ('count' if field.endswith('count') else ('OWNER_UNIT_NOT_DECLARED' if isinstance(cell.get('value'),(int,float)) else 'NOT_APPLICABLE_TYPED_VALUE'))),
        denominator=cell.get('n'), window=cell.get('window_identity'),
        adjustment_basis='RAW_UNADJUSTED' if price else cell.get('coordinate_basis'),
        computation_domain=cell.get('producer') or cell.get('producer_contract_id') or 'OWNER_PROJECTION')


def build_snapshot(root, *, expected_pointer=None, fail_readback=False):
    root = Path(root).resolve(); started = time.perf_counter()
    pointer = root / POINTER
    before = pointer.read_bytes() if pointer.exists() else None
    if expected_pointer is not None and (digest(before) if before else None) != expected_pointer:
        raise SourceInvalid('SNAPSHOT_CAS_CONFLICT')
    legacy,read_authority = frozen_current_reader(root)
    context = legacy.load_context(); date = context['context']['accepted_trade_date']
    if date>datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat():raise SourceInvalid('FUTURE_TRADE_DATE_FORBIDDEN')
    if before:
        previous=legacy._read(json.loads(before)['manifest'])
        if date<previous['context']['accepted_trade_date']:raise SourceInvalid('OLDER_SNAPSHOT_REQUIRES_EXPLICIT_ROLLBACK')
    contract, contract_digest = legacy._contract()
    sources = dict(contract['sources']); owners = dict(contract['owner_heads'])
    name_authority=json.loads((root/'config/v4_display_names_authority_v1.json').read_bytes())
    decoration=legacy._read(name_authority['source']);sources['display_names']=name_authority['source']
    sources.update({'read_contract':read_authority})
    advanced_head = legacy._read(owners['v4_13'])
    units={}
    for ref in advanced_head['contract_refs']:
        if 'field_registry' in ref['path']:
            units.update({v['field']:v.get('unit') for v in legacy._read(ref)['fields']})
    advanced = next(r for r in advanced_head['artifact_refs'] if r['path'].endswith('profile_advanced.jsonl.gz'))
    legacy._verify(advanced); sources['advanced'] = advanced
    sector_head = legacy._read(owners['v4_08'])
    units.update({v['field_id']:v.get('unit') for v in legacy._read(sector_head['field_registry'])['fields']})
    manifest = legacy._read(sector_head['r5_2_candidate_manifest'])
    for k in ('SECTOR_NATIVE', 'ROTATION'):
        sources[k] = manifest['artifacts'][k]; legacy._verify(sources[k])
    identity = legacy._source(contract, 'identity_names')['records']
    names = {}; aliases = {}
    for row in identity:
        sid = row['security_id']; symbol = row.get('symbol', '')
        aliases.setdefault(sid, set()).update((symbol, symbol.split('.')[-1]))
        if row.get('symbol_effective_from', '') <= date and (not row.get('symbol_effective_to') or row['symbol_effective_to'] >= date):
            names[sid] = row
    directory = root / 'data/v4/research_snapshots' / uuid.uuid4().hex
    directory.mkdir(parents=True); dbpath = directory / 'research.sqlite'
    db = sqlite3.connect(dbpath)
    db.executescript('''CREATE TABLE objects(domain TEXT,id TEXT,name TEXT,symbol TEXT,state TEXT,payload TEXT,PRIMARY KEY(domain,id));
        CREATE INDEX object_name ON objects(domain,name,id);
        CREATE INDEX object_symbol ON objects(domain,symbol,id);
        CREATE INDEX object_state ON objects(domain,state,id);
        CREATE TABLE aliases(alias TEXT,id TEXT,PRIMARY KEY(alias,id));
        CREATE INDEX alias_lookup ON aliases(alias,id);
        CREATE TABLE members(sector TEXT,security TEXT,PRIMARY KEY(sector,security));
        CREATE INDEX member_security ON members(security,sector);
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);''')
    counts = {}; field_registry = {}
    def put(domain, row):
        sid = row['entity_id']; ident = names.get(sid, {})
        object_id = sid if domain in ('stocks','sectors','sources') else str(sid)+':'+digest(canonical(row))[:20]
        name = ident.get('security_name') or row.get('display_name') or sid
        if '\ufffd' in name: name = ident.get('symbol') or sid
        symbol = ident.get('symbol') or row.get('fields', {}).get('source_security_key', {}).get('value') or ''
        observed_name=decoration['stocks'].get(symbol) if domain!='sectors' else decoration['sectors'].get(sid)
        if observed_name:name=observed_name
        row.update(display_name=name, security_id=sid if domain=='stocks' else None, symbol=symbol, trade_date=date)
        row['display_name_source']=dict(source_digest=sources['display_names']['sha256'],observed_at=decoration['observed_at'],pit_safe=False,scope='DISPLAY_ONLY') if observed_name else dict(scope='ACCEPTED_IDENTITY_OR_CODE_FALLBACK')
        fields = row.get('fields', {})
        if domain=='sectors':fields.pop('algorithm_state',None)  # Retired seven-summary placeholder; use real output_state.
        for key, cell in list(fields.items()):
            if 'source' in cell:
                fields[key] = compact_cell(cell,cell['source'],key,date)
        if domain=='sectors':
            candidate=fields.get('sector_name',{}).get('value')
            if not observed_name and candidate and '\ufffd' not in candidate:name=candidate
        state = next((str(fields[k]['value']) for k in ('state','scenario','output_state','eligibility_state','outcome_status') if k in fields), '')
        db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)', (domain,object_id,name,symbol,state,canonical(row).decode()))
        for key, cell in fields.items():
            field_registry.setdefault(domain, {})[key] = dict(status='ADAPTED_EXISTING_REAL_OUTPUT', unit=cell.get('unit'),
                source_digest=cell.get('source_digest'), nullable=True, quality_required=True, reason_required_when_unknown=True)
    try:
        for domain, module in [('stocks','entity'),('sectors','sector'),('events','summary'),('radar','radar'),('forward','cohort'),('settlement','settlement'),('sources','health')]:
            offset=0
            while True:
                code, page = legacy.read(module, dict(limit='200', offset=str(offset)))
                if code != 200: raise SourceInvalid('DOMAIN_SOURCE_INVALID:'+domain)
                if page['context_token']!=context['context_token']:raise SourceInvalid('BUILD_CONTEXT_CHANGED')
                for row in page['items']: put(domain,row)
                offset += len(page['items'])
                if offset >= page['total']: break
        for sid, values in aliases.items():
            db.executemany('INSERT OR IGNORE INTO aliases VALUES(?,?)', [(v.casefold(),sid) for v in values if v])
        for row in legacy._source(contract,'membership'):
            db.execute('INSERT OR IGNORE INTO members VALUES(?,?)',(row['sector_id'],row['security_id']))
        # Consume the real owner reducer output, rather than losing qualification
        # reasons in the former seven-summary state projection.
        state_fields=('raw_qualification','detector_statuses','matched_predicates','unknown_predicates','transition_reasons',
            'tracking','validity','market_age','expiry_count','downgrade_count','improvement_baseline','boundary_event')
        for row in legacy._source(contract,'states')['rows']:
            if row['trade_date']!=date:raise SourceInvalid('STATE_DATE_MIX')
            old=db.execute("SELECT payload FROM objects WHERE domain='stocks' AND id=?",(row['entity_id'],)).fetchone()
            if not old:continue
            result=json.loads(old[0])
            for key in state_fields:
                if key not in row:continue
                unknown=row[key]=='UNKNOWN'
                cell=dict(value=row[key],quality='UNKNOWN' if unknown else 'KNOWN',reason=row['unknown_predicates'] if unknown else None,
                    producer_contract_id=row['model_contract_id'],parameter_set_id=row['parameter_set_id'],max_source_date=row['cutoff'],
                    unit='sessions' if key in ('market_age','expiry_count','downgrade_count') else 'NOT_APPLICABLE_TYPED_VALUE')
                result['fields'][key]=compact_cell(cell,sources['states'],key,date)
            db.execute("DELETE FROM objects WHERE domain='stocks' AND id=?",(row['entity_id'],));put('stocks',result)
        unmatched=0;advanced_cutoff=date
        with gzip.open(root/advanced['path'],'rt',encoding='utf8') as f:
            for line in f:
                row=json.loads(line)
                advanced_cutoff=row.get('cutoff',date)
                if row['trade_date'] != date: raise SourceInvalid('PROFILE_DATE_MIX')
                old=db.execute("SELECT payload FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],)).fetchone()
                if not old: unmatched+=1;continue
                result=json.loads(old[0])
                result['fields'].update({k:compact_cell(dict(v,unit=units.get(k)),advanced,k,date) for k,v in row['fields'].items()})
                db.execute("DELETE FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],));put('stocks',result)
        for kind in ('SECTOR_NATIVE','ROTATION'):
            with gzip.open(root/sources[kind]['path'],'rt',encoding='utf8') as f:
                for line in f:
                    row=json.loads(line)
                    if row['target_trade_date'] != date: raise SourceInvalid('SECTOR_DATE_MIX')
                    old=db.execute("SELECT payload FROM objects WHERE domain='sectors' AND id=?",(row['sector_id'],)).fetchone()
                    if not old: continue
                    result=json.loads(old[0]);cells=dict(row.get('fields',{}))
                    if kind=='ROTATION': cells['output_state']=dict(value=row['output_state'],quality=row['quality'],reason=row.get('reason_codes'))
                    result['fields'].update({k:compact_cell(dict(v,unit=units.get(k)),sources[kind],k,date) for k,v in cells.items()})
                    db.execute("DELETE FROM objects WHERE domain='sectors' AND id=?",(row['sector_id'],));put('sectors',result)
        domain_features={}
        market_authority=root/'config/v4_market_operational_authority_v1.json'
        if market_authority.exists():
            authority=json.loads(market_authority.read_bytes())
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('MARKET_SOURCE_CONTEXT_MISMATCH')
            market=legacy._read(authority['market']);sources['market_operational']=authority['market']
            domain_features['market']=market
            fields={k:compact_cell(dict(value=v,quality='UNKNOWN' if v in (None,'UNKNOWN') else 'KNOWN',reason=market['trend'].get('unknown_reason') if k=='trend_axis' else market['axes']['field_quality'].get(k,{}).get('unknown_reason'),contract_id='FP05_CURRENT_MARKET_FOUR_AXES_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1'),authority['market'],k,date) for k,v in market['row'].items()}
            put('market',dict(entity_id='A_SHARE_RESEARCH_MARKET',display_name='全市场研究环境',fields=fields))
        counts={d:db.execute('SELECT count(*) FROM objects WHERE domain=?',(d,)).fetchone()[0] for d in DOMAINS}
        expected_stocks=len(legacy._source(contract,'RAW_DAILY')['rows'])
        expected_sectors=len({r['sector_id'] for r in legacy._source(contract,'membership')})
        if counts['stocks'] != expected_stocks or counts['sectors'] != expected_sectors: raise SourceInvalid('UNIVERSE_COUNT_GATE')
        gaps=[dict(domain='market',state='ENGINEERING_NOT_READY',reason='ACCEPTED_MARKET_OWNER_OUTPUT_NOT_BOUND_TO_20260930',next='FP05_TARGETED_CURRENT_FOUR_AXIS_RECOMPUTE'),
              dict(domain='focus',state='ENGINEERING_NOT_READY',reason='EPISODE_PROJECTION_NOT_PUBLISHED_IN_CURRENT_OWNER_CONTEXT',next='FP08_PUBLISH_REAL_EPISODES'),
              dict(domain='stocks',state='SOURCE_INCOMPLETE',reason='CURRENT_CORE_OWNER_PROFILE_IS_20260928_NOT_20260930',next='FP07_CURRENT_CORE_RECOMPUTE'),
              dict(domain='profile_identity',state='SOURCE_INCOMPLETE',reason='ADVANCED_ROWS_OUTSIDE_CURRENT_RAW_UNIVERSE',count=unmatched)]
        if 'market' in domain_features:gaps=[g for g in gaps if g['domain']!='market']
        meta=dict(contract_id='V4_RESEARCH_SNAPSHOT_V1', domain_features=domain_features,context=context['context'],legacy_context_token=context['context_token'],
            source_contract_digest=contract_digest, sources=sources, owners=owners, counts=counts, gaps=gaps,
            field_registry=field_registry, operational_state='OPERATIONAL_PRODUCTION_ACTIVE',
            evidence_state='VALIDATION_ONGOING', quality='QUALITY_DEGRADED', publication_scope='FP02_INDEXED_EXISTING_REAL_OUTPUTS',
            release_id=directory.name, built_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        def instant(value):
            parsed=datetime.fromisoformat(value)
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        source_as_of=max(map(instant,[context['context']['data_updated_at'],decoration['observed_at'],advanced_cutoff]))
        published_at=datetime.now(timezone.utc)
        if source_as_of>published_at:raise SourceInvalid('FUTURE_SOURCE_AS_OF_FORBIDDEN')
        meta['metadata']=dict(owner='FP02_RESEARCH_PROJECTION',release_id=directory.name,
            source_snapshot=context['context']['data_head_digest'],contract_version='1.0.0',source_as_of=source_as_of.isoformat(),
            trading_date=date,input_digest=digest(canonical(dict(sources=sources,owners=owners))),published_at=published_at.isoformat(),
            evidence_origin='REAL_ACCEPTED_SOURCE',evidence_state='VALIDATION_ONGOING',data_quality_state='QUALITY_DEGRADED',
            knowledge_lineage=context['context']['knowledge_lineage'])
        db.execute('INSERT INTO metadata VALUES(?,?)',('snapshot',canonical(meta).decode()));db.commit();db.close()
        ref=reference(root,dbpath); manifest_path=directory/'manifest.json'
        atomic_bytes(manifest_path,canonical(dict(**meta,database=ref))+b'\n')
        new=dict(contract_id='V4_RESEARCH_SNAPSHOT_AUTHORITY_V1',manifest=reference(root,manifest_path),previous=json.loads(before) if before else None)
        lock=pointer.with_suffix('.lock');fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        try:
            os.close(fd)
            if (pointer.read_bytes() if pointer.exists() else None) != before: raise SourceInvalid('SNAPSHOT_CAS_CONFLICT')
            atomic_bytes(pointer,canonical(new)+b'\n')
            try:
                check=ProductionV4ResearchReader(root)
                if fail_readback: raise SourceInvalid('INJECTED_READBACK_FAILURE')
                if check.manifest['counts'] != counts: raise SourceInvalid('READBACK_COUNT_MISMATCH')
            except Exception:
                if before is not None: atomic_bytes(pointer,before)
                else: pointer.unlink()
                raise
        finally:lock.unlink()
        return dict(status='PUBLISHED',pointer=new,counts=counts,gaps=gaps,build_seconds=round(time.perf_counter()-started,3))
    except Exception:
        db.close();raise


def rollback_snapshot(root,expected_pointer):
    root=Path(root).resolve();path=root/POINTER;before=path.read_bytes()
    if digest(before)!=expected_pointer:raise SourceInvalid('SNAPSHOT_CAS_CONFLICT')
    previous=json.loads(before).get('previous')
    if not previous:raise SourceInvalid('NO_PREVIOUS_SNAPSHOT')
    verifier=CurrentAcceptedV4Reader(root);manifest=verifier._read(previous['manifest']);verifier._verify(manifest['database'])
    validate_release_metadata(manifest)
    lock=path.with_suffix('.lock');fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.close(fd)
        if digest(path.read_bytes())!=expected_pointer:raise SourceInvalid('SNAPSHOT_CAS_CONFLICT')
        atomic_bytes(path,canonical(previous)+b'\n')
        try:ProductionV4ResearchReader(root)
        except Exception:atomic_bytes(path,before);raise
    finally:lock.unlink()
    return dict(status='ROLLED_BACK',context_token=ProductionV4ResearchReader(root).token)


class ProductionV4ResearchReader:
    def __init__(self, root):
        self.root=Path(root).resolve();verifier=CurrentAcceptedV4Reader(root)
        self.authority=json.loads((self.root/POINTER).read_bytes())
        self.manifest=verifier._read(self.authority['manifest']);verifier._verify(self.manifest['database'])
        metadata=validate_release_metadata(self.manifest)
        self.path=verifier._path(self.manifest['database']['path'])
        stat=self.path.stat();self.file_signature=(stat.st_size,stat.st_mtime_ns)
        self.token='research-v4-'+self.authority['manifest']['sha256']
        self.context=dict(release_id=self.manifest['release_id'],model_namespace='V4_RESEARCH_SNAPSHOT_V1',
            source_mode='OPERATIONAL_PRODUCTION_ACTIVE',publication_id=self.manifest['release_id'],data_as_of=self.manifest['context']['data_updated_at'],
            core_revision=self.manifest['source_contract_digest'],optional_enrichment_revision=self.manifest['sources']['advanced']['sha256'],
            turnover_as_of=None,quality=self.manifest['quality'],source_contract_id='V4_RESEARCH_SNAPSHOT_V1',
            factor_contract_id=None,state_contract_id='ACCEPTED_OWNER_SCOPED',parameter_set_id=None)
        self.context={**self.manifest['context'],**self.context}
        self.context['trade_date']=self.context['accepted_trade_date']
        self.context['release_metadata']=metadata

    def envelope(self, **payload):
        return dict(context=self.context,context_token=self.token,**payload)

    def known_identity(self,entity):
        with sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True) as db:
            return db.execute('SELECT 1 FROM aliases WHERE id=? OR alias=? LIMIT 1',(entity,entity.casefold())).fetchone() is not None

    def query(self, domain, query=None, *, entity=None, sector=None, summary=False):
        stat=self.path.stat()
        if (stat.st_size,stat.st_mtime_ns)!=self.file_signature:raise SourceInvalid('IMMUTABLE_DATABASE_CHANGED')
        q=query or {}
        allowed={'q','state','limit','offset','sort','context_token','trade_date','release_id','model_namespace'}
        if set(q)-allowed:raise ValueError('UNKNOWN_PARAMETER')
        for key, expected in [('context_token',self.token),('trade_date',self.context['accepted_trade_date']),('release_id',self.context['release_id']),('model_namespace',self.context['model_namespace'])]:
            if key in q and q[key]!=expected:raise SourceInvalid('CONTEXT_CONFLICT:'+key)
        if domain not in DOMAINS:raise ValueError('UNKNOWN_DOMAIN')
        limit=int(q.get('limit',30));offset=int(q.get('offset',0));needle=q.get('q','').strip().casefold()
        if not 1<=limit<=200 or not 0<=offset<=1000000 or len(needle)>80:raise ValueError('INVALID_QUERY_BOUND')
        sort=[]
        for entry in q.get('sort','id').split(','):
            column=entry.lstrip('-')
            if column not in ('id','name','symbol','state'):raise ValueError('INVALID_SORT_FIELD')
            sort.append(column+(' DESC' if entry.startswith('-') else ' ASC'))
        if len(sort)>4:raise ValueError('SORT_BOUND')
        sort.append('id ASC');where=['domain=?'];args=[domain]
        if needle:
            # Prefix range uses the name/symbol indexes; exact historic alias uses alias_lookup.
            where.append("id IN (SELECT id FROM objects WHERE domain=? AND id=? UNION SELECT id FROM objects WHERE domain=? AND symbol>=? AND symbol<? UNION SELECT id FROM objects WHERE domain=? AND name>=? AND name<? UNION SELECT id FROM aliases WHERE alias>=? AND alias<? UNION SELECT o.id FROM aliases a JOIN objects o ON o.domain=? AND o.id>=a.id||':' AND o.id<a.id||';' WHERE a.alias>=? AND a.alias<?)")
            args.extend((domain,needle.upper(),domain,needle.upper(),needle.upper()+'\uffff',domain,needle,needle+'\uffff',needle,needle+'\uffff',domain,needle,needle+'\uffff'))
        if q.get('state'):where.append('state=?');args.append(q['state'])
        if entity:
            where.append('id IN (SELECT ? UNION SELECT id FROM aliases WHERE alias=?)');args.extend((entity,entity.casefold()))
        if sector:where.append('id IN (SELECT security FROM members WHERE sector=?)');args.append(sector)
        clause=' AND '.join(where)
        with sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True) as db:
            total=db.execute('SELECT count(*) FROM objects WHERE '+clause,args).fetchone()[0]
            rows=db.execute('SELECT payload FROM objects WHERE '+clause+' ORDER BY '+','.join(sort)+' LIMIT ? OFFSET ?',args+[limit,offset]).fetchall()
        gap=next((g for g in self.manifest['gaps'] if g['domain']==domain),None)
        items=[json.loads(r[0]) for r in rows]
        if summary and domain in ('stocks','sectors'):
            keys=('close','scenario','final_eligibility','primary_industry','source_security_key','trade_date') if domain=='stocks' else ('sector_name','member_count','output_state','trade_date')
            for row in items:row['fields']={k:v for k,v in row['fields'].items() if k in keys}
        return self.envelope(domain=domain,items=items,total=total,offset=offset,limit=limit,
            has_next=offset+limit<total,status=gap['state'] if not total and gap else ('READY' if total else 'EMPTY_VALID'),gap=gap)
