"""Prepare dated native PG read packs before atomic operational publication."""
import json,gzip,hashlib,zipfile,struct,re,math
import sqlite3,tempfile
from contextlib import closing
from pathlib import Path
from collections import Counter
from .r43_owner_replay import checked,ref
from .r43_operational_publication import rows
from .operational_daily_storage_v1 import atomic_json
from workbench_db.v4_forward_pg_r1 import canonical,digest
from workbench_service.native_product_catalog_v3 import KEY,CONTRACT,load as load_catalog

def canonical_history_rows(path,logical):
    """Order immutable source rows on G disk without holding full history in RAM."""
    temporary=Path('G:/codex_tmp');temporary.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v4-history-order-',dir=temporary) as folder:
        with closing(sqlite3.connect(str(Path(folder)/'rows.sqlite'))) as db:
            db.execute('CREATE TABLE rows(security TEXT PRIMARY KEY,payload BLOB NOT NULL)')
            with gzip.open(path,'rt',encoding='utf8') as stream:
                for line in stream:
                    row=json.loads(line)
                    value=dict(security_id=row['security_id'],bars=[{key:bar[key] for key in ('trade_date','raw_ohlc','qfq_ohlc','amount','volume')} for bar in row['bars']])
                    try:db.execute('INSERT INTO rows VALUES(?,?)',(row['security_id'],canonical(value)))
                    except sqlite3.IntegrityError as error:raise ValueError('PRODUCT_HISTORY_DUPLICATE_SECURITY') from error
            db.commit()
            for (payload,) in db.execute('SELECT payload FROM rows ORDER BY security'):
                logical.update(payload+b'\n');yield json.loads(payload)

def index_benchmark_contract(root):
    root=Path(root)
    path=Path(root)/'config/core_product_index_benchmark_v1.json'
    value=json.loads(path.read_bytes())
    if value.get('contract_id')!='CORE_PRODUCT_INDEX_BENCHMARK_V1' or not value.get('version') or not value.get('benchmarks'):
        raise ValueError('VERSIONED_INDEX_BENCHMARK_CONTRACT_REQUIRED')
    reference_binding=value.get('reference_instruments')
    if not isinstance(reference_binding,dict):raise ValueError('INDEX_REFERENCE_CATALOG_REQUIRED')
    catalog=json.loads(checked(root,reference_binding).read_bytes())
    if (catalog.get('contract_id')!='V4_MARKET_REFERENCE_INSTRUMENTS_V1'
            or catalog.get('version')!=value.get('reference_version')
            or catalog.get('runtime_authorized') is not True):
        raise ValueError('INDEX_REFERENCE_CATALOG_INVALID')
    instruments=catalog.get('instruments',[])
    ids=[item.get('instrument_id','').replace('.','').lower() for item in instruments]
    if len(ids)!=len(set(ids)):raise ValueError('INDEX_REFERENCE_CATALOG_DUPLICATE')
    reference=dict(zip(ids,instruments))
    seen=set()
    for benchmark in value['benchmarks']:
        symbol=benchmark.get('symbol','').lower()
        if not re.fullmatch(r'(?:sh|sz|bj)\d{6}',symbol) or symbol in seen or not benchmark.get('display_name'):
            raise ValueError('INDEX_BENCHMARK_CONTRACT_INVALID')
        item=reference.get(symbol,{})
        if (item.get('instrument_type')!='MARKET_INDEX'
                or benchmark.get('instrument_type')!='MARKET_INDEX'
                or benchmark.get('role')!='MARKET_BENCHMARK'
                or item.get('source_kind')!='TDX_INDEX_DAY'
                or benchmark.get('source_kind')!='TDX_INDEX_DAY'
                or benchmark.get('price_basis')!='RAW_INDEX_POINTS'):
            raise ValueError('INDEX_BENCHMARK_TYPE_OR_SOURCE_INVALID:'+symbol)
        seen.add(symbol)
    return value,dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def index_series(archive,benchmark,day,source_catalog,package_sha256):
    """只有带包身份及逐序列摘要的类型目录能够授权指数点位。"""
    symbol=benchmark['symbol'].lower()
    if (source_catalog.get('contract_id')!='V4_TDX_INDEX_SOURCE_CATALOG_V1'
            or source_catalog.get('version')!='1.0.0'
            or source_catalog.get('package_sha256')!=package_sha256):
        raise ValueError('INDEX_SOURCE_CATALOG_INVALID')
    entries=[row for row in source_catalog.get('instruments',[]) if row.get('symbol','').lower()==symbol]
    if len(entries)!=1:raise ValueError('INDEX_SOURCE_MISSING_OR_AMBIGUOUS:'+symbol)
    source=entries[0];member=symbol[:2]+'/lday/'+symbol+'.day'
    if (source.get('instrument_type')!='MARKET_INDEX' or source.get('source_kind')!='TDX_INDEX_DAY'
            or source.get('role')!='MARKET_BENCHMARK' or source.get('price_basis')!='RAW_INDEX_POINTS'
            or source.get('member')!=member or source.get('trade_date')!=day):
        raise ValueError('INDEX_SOURCE_TYPE_OR_DATE_MISMATCH:'+symbol)
    if archive.namelist().count(member)!=1:raise ValueError('INDEX_SOURCE_MEMBER_MISSING_OR_AMBIGUOUS:'+symbol)
    blob=archive.read(member)
    if hashlib.sha256(blob).hexdigest()!=source.get('sha256'):
        raise ValueError('INDEX_SOURCE_DIGEST_MISMATCH:'+symbol)
    if not blob or len(blob)%32:raise ValueError('INDEX_SOURCE_RECORD_INVALID:'+symbol)
    bars=[];previous=None
    from datetime import date
    for row in struct.iter_unpack('<IIIIIfII',blob):
        dt=str(row[0]);dt=dt[:4]+'-'+dt[4:6]+'-'+dt[6:]
        date.fromisoformat(dt)
        if previous is not None and dt<=previous:raise ValueError('INDEX_SOURCE_DATE_ORDER_INVALID:'+symbol)
        previous=dt
        if dt>day:continue
        o,h,l,c=(value/100 for value in row[1:5])
        if not (0<l<=min(o,c)<=max(o,c)<=h and math.isfinite(row[5]) and row[5]>=0):
            raise ValueError('INDEX_SOURCE_PRICE_INVALID:'+symbol)
        bars.append(dict(trade_date=dt,open=o,high=h,low=l,close=c,amount=row[5],volume=row[6],quality='KNOWN'))
    if not bars or bars[-1]['trade_date']!=day:raise ValueError('INDEX_SOURCE_TARGET_SESSION_MISSING:'+symbol)
    return dict(symbol=symbol,display_name=benchmark['display_name'],bars=bars[-120:],price_basis='RAW_INDEX_POINTS',
                instrument_type='MARKET_INDEX',source_kind='TDX_INDEX_DAY',source_member=member,
                volume_unit='SOURCE_NATIVE_UNVERIFIED',source_sha256=source['sha256'])


def capture_index_source_catalog(root,package_binding,day):
    """从已核验冻结包捕获有类型的指数目录；缺失只关闭对应指数能力。"""
    contract,reference=index_benchmark_contract(root)
    catalog=dict(contract_id='V4_TDX_INDEX_SOURCE_CATALOG_V1',version='1.0.0',
        package_sha256=package_binding['sha256'],benchmark_contract=reference,trade_date=day,
        reference_instruments=contract['reference_instruments'],instruments=[],missing_sources=[])
    with zipfile.ZipFile(checked(root,package_binding)) as archive:
        for benchmark in contract['benchmarks']:
            symbol=benchmark['symbol'].lower();member=symbol[:2]+'/lday/'+symbol+'.day'
            if archive.namelist().count(member)!=1:
                catalog['missing_sources'].append(dict(symbol=symbol,reason='INDEX_SOURCE_MEMBER_MISSING_OR_AMBIGUOUS'))
                continue
            source=dict(symbol=symbol,member=member,trade_date=day,instrument_type=benchmark['instrument_type'],
                role=benchmark['role'],source_kind=benchmark['source_kind'],price_basis=benchmark['price_basis'],
                sha256=hashlib.sha256(archive.read(member)).hexdigest())
            catalog['instruments'].append(source)
            try:index_series(archive,benchmark,day,catalog,package_binding['sha256'])
            except (ValueError,KeyError,struct.error) as error:
                catalog['instruments'].pop()
                catalog['missing_sources'].append(dict(symbol=symbol,reason=str(error)))
    catalog['status']='KNOWN' if not catalog['missing_sources'] else 'SOURCE_INCOMPLETE'
    return catalog


def validate_index_catalog_contract(catalog,benchmark_binding,reference_binding):
    if (catalog.get('benchmark_contract')!=benchmark_binding
            or catalog.get('reference_instruments')!=reference_binding):
        raise ValueError('INDEX_SOURCE_CONTRACT_REVISION_MISMATCH')

def market_facts(root,candidate,day,owner):
    bindings=dict(history=owner['history'],package=owner['sources']['package'],**{name:candidate['owners'][day][name] for name in ('raw','core','market')})
    market=rows(root,bindings['market']);limitrefs=[b for b in market['input_bindings'] if 'daily_price_limits' in b['path']]
    if not limitrefs:raise ValueError('DATED_MARKET_LIMITS_REQUIRED')
    bindings.update({'limits_'+str(i):b for i,b in enumerate(limitrefs)})
    raw={r['security_id']:r for r in rows(root,bindings['raw'])};core=rows(root,bindings['core']);breadth=Counter(up=0,down=0,flat=0,unknown=0)
    for row in core:
        value=row['fields']['ret1']['value'] if row['security_id'] in raw else None
        breadth['unknown' if value is None else 'up' if value>0 else 'down' if value<0 else 'flat']+=1
    dated=[{row['security_id']:row for row in rows(root,binding)} for binding in limitrefs]
    limits=list(dated[0].values());ladders=[]
    if any(row['trade_date']!=day for row in limits):raise ValueError('MARKET_LIMIT_DATE_MISMATCH')
    for item in limits:
        if item['limit_state']!='LIMIT_UP':continue
        run=0;exact=False
        for prior in dated:
            value=prior.get(item['security_id'])
            if not value or value['limit_state']=='UNKNOWN':break
            if value['limit_state']!='LIMIT_UP':exact=True;break
            run+=1
        ladders.append(dict(entity_id=item['security_id'],symbol=item['source_security_key'],consecutive_limit_up_lower_bound=run,exact_streak=run if exact else None,reason=None if exact else 'PREFIX_NOT_BOUND'))
    index_contract,bindings['index_reference_contract']=index_benchmark_contract(root)
    indices=[];index_errors=[]
    catalog_binding=owner['sources'].get('index_source_catalog')
    source_catalog=json.loads(checked(root,catalog_binding).read_bytes()) if catalog_binding else None
    if catalog_binding:bindings['index_source_catalog']=catalog_binding
    catalog_error=None
    if source_catalog is not None:
        try:validate_index_catalog_contract(source_catalog,bindings['index_reference_contract'],index_contract['reference_instruments'])
        except ValueError as error:catalog_error=str(error)
    with zipfile.ZipFile(checked(root,bindings['package'])) as archive:
        for benchmark in index_contract['benchmarks']:
            if catalog_error:
                index_errors.append(dict(symbol=benchmark['symbol'],reason=catalog_error))
                continue
            if source_catalog is None:
                index_errors.append(dict(symbol=benchmark['symbol'],reason='SOURCE_INDEX_CATALOG_MISSING'))
                continue
            try:indices.append(index_series(archive,benchmark,day,source_catalog,bindings['package']['sha256']))
            except (ValueError,KeyError,struct.error) as error:
                index_errors.append(dict(symbol=benchmark['symbol'],reason=str(error)))
    facts=dict(contract_id='CORE_PRODUCT_MARKET_FACT_READ_R1',trade_date=day,index_benchmark_contract=dict(contract_id=index_contract['contract_id'],version=index_contract['version'],sha256=bindings['index_reference_contract']['sha256']),breadth=dict(breadth,denominator=len(core),actual_quote_count=len(raw),amount_cny=sum(row['amount'] for row in raw.values()),definition='ret1 in native T0 QFQ coordinate; actual T0 bar required'),indices=indices,
        index_quality='KNOWN' if not index_errors else 'UNKNOWN',index_missing_sources=index_errors,
        limits=dict(counts=dict(Counter(row['limit_state'] for row in limits)),rows=limits),ladders=ladders,sources=bindings,AS_RECORDED=False,PIT_ELIGIBLE=False)
    return facts,bindings

def previous_date_bindings(root,candidate,predecessor,*,historical_indices=None,previous_dates=None):
    """Resolve dated product predecessors, allowing only explicit R1 bootstrap evidence."""
    if KEY in predecessor:
        previous=load_catalog(root,predecessor)['dates']
    else:
        old=json.loads((Path(root)/'config/core_product_read_authority_r1.json').read_bytes())
        if old.get('contract_id')=='CORE_PRODUCT_READ_AUTHORITY_R2':
            previous=old['dates']
        else:
            if historical_indices is None:
                raise ValueError('INITIAL_HISTORICAL_EXACT_CORRECTION_ADMISSION_REQUIRED')
            if old.get('contract_id')!='CORE_PRODUCT_READ_AUTHORITY_R1' or previous_dates is None:
                raise ValueError('LEGACY_DATED_PRODUCT_CATALOG_REQUIRED')
            previous=previous_dates
    expected=set(candidate['published_sessions'][:-1])
    if set(previous)!=expected:raise ValueError('PRODUCT_PACK_PREDECESSOR_DATE_DENOMINATOR')
    if historical_indices is not None and set(historical_indices)!=expected:
        raise ValueError('ALL_HISTORICAL_CORRECTION_INDICES_REQUIRED')
    return previous

def prepare(root,candidate,owner,*,historical_indices=None,previous_dates=None):
    root=Path(root).resolve();predecessor=json.loads(checked(root,candidate['predecessor']).read_bytes());day=candidate['accepted_trade_date']
    if owner['trade_date']!=day:raise ValueError('PRODUCT_PACK_DATED_OWNER_REQUIRED')
    previous=previous_date_bindings(root,candidate,predecessor,historical_indices=historical_indices,previous_dates=previous_dates)
    folder=root/'data/v4/native_product_catalog_v3'/digest(canonical(dict(owners=candidate['owners'],history=owner['history'])))
    dates={}
    for prior_day,binding in previous.items():
        manifest=json.loads(checked(root,binding).read_bytes())
        manifest['fact_token']=manifest.get('fact_token',manifest['history_index']['head_token'])
        if manifest['head']['path']=='data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json':manifest['head']=candidate['predecessor']
        if historical_indices:
            if prior_day not in historical_indices:raise ValueError('ALL_HISTORICAL_CORRECTION_INDICES_REQUIRED')
            correction=historical_indices[prior_day]
            if correction.get('T0')!=prior_day or correction.get('engine')!='postgresql' or correction.get('head_token')!=manifest['fact_token']:
                raise ValueError('HISTORICAL_CORRECTION_INDEX_SCOPE_MISMATCH')
            manifest['history_index']=historical_indices[prior_day]
        path=folder/prior_day/'MANIFEST.json';atomic_json(root,path,manifest);dates[prior_day]=ref(root,path)
    facts,bindings=market_facts(root,candidate,day,owner)
    scope=folder/day/'SOURCE_SCOPE.json'
    atomic_json(root,scope,dict(contract_id='V4_NATIVE_DATED_PRODUCT_SOURCE_SCOPE_V3',T0=day,source_bindings=bindings,source_owners=candidate['owners'][day],AS_RECORDED=False,PIT_ELIGIBLE=False))
    scope_binding=ref(root,scope);logical=hashlib.sha256()
    from workbench_db.v4_history_pg_r1 import build
    history=build(root,canonical_history_rows(checked(root,owner['history']),logical),head_token=scope_binding['sha256'],t0=day,source_digest=owner['history']['sha256'])
    if history['logical_digest']!=logical.hexdigest():raise ValueError('PRODUCT_HISTORY_FULL_PG_PAYLOAD_DIFFERENCE')
    from workbench_db.v4_market_fact_pg_r1 import prepare as prepare_market,read as read_market
    market=prepare_market(root,facts,scope_binding['sha256'])
    if read_market(root,market,day)!=facts:raise ValueError('PRODUCT_MARKET_FULL_PG_PAYLOAD_DIFFERENCE')
    manifest=dict(contract_id='CORE_PRODUCT_DATED_READ_PACK_PG_MARKET_R2',T0=day,head=scope_binding,fact_token=scope_binding['sha256'],
        fact_scope_contract='V4_NATIVE_DATED_PRODUCT_SOURCE_SCOPE_V3',history_index=history,market_facts=market,source_bindings=bindings,
        history_projection_fields=['trade_date','raw_ohlc','qfq_ohlc','amount','volume'],AS_RECORDED=False,PIT_ELIGIBLE=False,read_only=True)
    path=folder/day/'MANIFEST.json';atomic_json(root,path,manifest);dates[day]=ref(root,path)
    authority=dict(contract_id=CONTRACT,dates=dates,source_owners=candidate['owners'],owner_source_digest=digest(canonical(candidate['owners'])),AS_RECORDED=False,PIT_ELIGIBLE=False,historical_PIT_permission=False)
    path=folder/'CATALOG.json';atomic_json(root,path,authority);candidate[KEY]=ref(root,path)
    load_catalog(root,candidate)
    return dict(contract_id=CONTRACT,dates=len(dates),new_history_symbols=history['symbol_count'],new_history_bars=history['bar_count'],history_payload_digest=logical.hexdigest(),publication=False)
