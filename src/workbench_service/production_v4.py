"""FP02 immutable indexed research snapshots. No source discovery or TDX writes."""
import gzip
import json
import os
import time
import uuid
from contextlib import ExitStack,contextmanager,nullcontext
from contextvars import ContextVar
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .current_v4_context import CurrentAcceptedV4Reader, SourceInvalid, canonical, digest

POINTER = 'config/v4_research_snapshot_authority_v1.json'
DOMAINS = ('stocks', 'sectors', 'events', 'radar', 'forward', 'settlement', 'sources', 'market', 'focus')
REQUIRED_METADATA=('owner','release_id','source_snapshot','contract_version','source_as_of','trading_date','input_digest','published_at','evidence_origin','evidence_state','data_quality_state','knowledge_lineage')
_request_reads=ContextVar('v4_request_verified_pg_reads',default=None)

@contextmanager
def snapshot_request_scope():
    """One fully verified repeatable-read transaction per snapshot per request."""
    if _request_reads.get() is not None:
        yield
        return
    with ExitStack() as stack:
        context_token_handle=_request_reads.set((stack,{}))
        try:yield
        finally:_request_reads.reset(context_token_handle)

def numeric_sort_expressions(field,descending):
    # Preserve the accepted SQLite JSON value ordering: NULL, numeric, text.
    # Unknown literal values remain text and never enter a numeric cast.
    if field not in {'sector_rs20_pct','sector_rs5_pct','sector_rs20','sector_rs5','breadth_ret1','ma20_width','participation_proxy','member_count','close','rps5','rps20'}:raise ValueError('INVALID_SORT_FIELD')
    value="(payload::jsonb #> '{fields,"+field+",value}')"
    text="(payload::jsonb #>> '{fields,"+field+",value}')"
    order=' DESC NULLS LAST' if descending else ' ASC NULLS FIRST'
    rank="CASE WHEN "+value+" IS NULL OR "+value+"='null'::jsonb THEN 0 WHEN jsonb_typeof("+value+") IN ('number','boolean') THEN 1 ELSE 2 END"
    number="CASE WHEN jsonb_typeof("+value+")='number' THEN "+text+"::numeric WHEN "+value+"='true'::jsonb THEN 1 WHEN "+value+"='false'::jsonb THEN 0 END"
    lexical="CASE WHEN jsonb_typeof("+value+") NOT IN ('number','boolean','null') THEN "+text+" END"
    return [rank+order,number+order,lexical+order]

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


def frozen_current_reader(root):
    root=Path(root).resolve()
    reader=CurrentAcceptedV4Reader(root,require_runtime=True)
    contract,sha=reader._contract()
    # The contract bytes are selected and digest-verified in the PG Registry;
    # they are a version identity, not a workspace artifact reference.
    return reader,dict(contract_id=contract['contract_id'],version=contract.get('version'),
        namespace=contract.get('namespace'),sha256=sha,bytes=len(canonical(contract)))


def compact_cell(cell, ref, field, date):
    """Retain value/quality/reason; provenance points to exact original field."""
    if not isinstance(cell, dict): cell = dict(value=cell, quality='KNOWN')
    quality = cell.get('quality', 'UNKNOWN')
    reason = cell.get('reason') or cell.get('reason_code') or cell.get('unknown_reason')
    if cell.get('value') == 'UNKNOWN' and quality == 'KNOWN':
        quality = 'UNKNOWN'
        reason = reason or 'OWNER_LITERAL_UNKNOWN_NOT_A_KNOWN_VALUE'
    if quality in ('UNKNOWN', 'NOT_IMPLEMENTED') and not reason:
        reason = 'OWNER_FIELD_REASON_MISSING_SEE_AUD_FP01_FIELD_REASON_GAPS'
    price = field in ('open', 'high', 'low', 'close')
    return dict(value=value_projection(cell.get('value')), quality=quality, reason=reason,
        source_digest=ref['sha256'], source_field=field,
        source_contract_id=cell.get('producer_contract_id') or cell.get('model_contract_id') or cell.get('contract_id') or ref.get('contract_id'),
        parameter_set_id=cell.get('parameter_set_id'), source_as_of=cell.get('max_source_date', date),
        unit=cell.get('unit') or ('CNY' if price else ('count' if field.endswith('count') else ('OWNER_UNIT_NOT_DECLARED' if isinstance(cell.get('value'),(int,float)) else 'NOT_APPLICABLE_TYPED_VALUE'))),
        denominator=cell.get('n') if cell.get('n') is not None else cell.get('denominator') if cell.get('denominator') is not None else cell.get('known_count'), window=cell.get('window_identity'),
        adjustment_basis='RAW_UNADJUSTED' if price else cell.get('coordinate_basis'),
        computation_domain=cell.get('producer') or cell.get('producer_contract_id') or 'OWNER_PROJECTION')


def build_snapshot(root, *, expected_pointer=None, fail_readback=False, publish=False, focus_override=None, authority_overrides=None):
    root = Path(root).resolve(); started = time.perf_counter()
    if publish:raise SourceInvalid('PG_CANDIDATE_ONLY_ACCEPTED_HEAD_CAS_NOT_IMPLEMENTED')
    if expected_pointer is not None:raise SourceInvalid('WORKSPACE_POINTER_CAS_REMOVED_USE_PG_PUBLICATION_HEAD')
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path, admit_bound
    def operational(key,path):
        if authority_overrides is not None and key in authority_overrides:return authority_overrides[key]
        try:return json.loads(read_path(root,path.relative_to(root).as_posix())['raw'])
        except (OSError,ValueError):return None
    legacy,_ = frozen_current_reader(root)
    context = legacy.load_context(); date = context['context']['accepted_trade_date']
    if date>datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat():raise SourceInvalid('FUTURE_TRADE_DATE_FORBIDDEN')
    contract, contract_digest = legacy._contract()
    # Candidate creation is the explicit one-time SourceIngress boundary for
    # exact bytes already named by accepted owner bindings. Consumers still
    # deserialize only the PostgreSQL readback and never keep a file fallback.
    exact_read=legacy._read;exact_verify=legacy._verify
    def admitted_read(ref):
        try:return exact_read(ref)
        except SourceInvalid as error:
            if not str(error).startswith('BOUND_ARTIFACT_MISSING:'):raise
            admit_bound(root,ref)
            return exact_read(ref)
    def admitted_verify(ref):
        try:return exact_verify(ref)
        except SourceInvalid as error:
            if not str(error).startswith('BOUND_ARTIFACT_MISSING:'):raise
            admit_bound(root,ref)
            return exact_verify(ref)
    legacy._read=admitted_read;legacy._verify=admitted_verify
    sources = dict(contract['sources']); owners = dict(contract['owner_heads'])
    decoration={'stocks':{},'sectors':{},'observed_at':context['context']['data_updated_at']}
    advanced_head = legacy._read(owners['v4_13'])
    units={}
    for ref in advanced_head['contract_refs']:
        if 'field_registry' in ref['path']:
            units.update({v['field']:v.get('unit') for v in legacy._read(ref)['fields']})
    advanced = next(r for r in advanced_head['artifact_refs'] if r['path'].endswith('profile_advanced.jsonl.gz'))
    admit_bound(root,advanced); sources['advanced'] = advanced
    sector_head = legacy._read(owners['v4_08'])
    units.update({v['field_id']:v.get('unit') for v in legacy._read(sector_head['field_registry'])['fields']})
    manifest = legacy._read(sector_head['r5_2_candidate_manifest'])
    for k in ('SECTOR_NATIVE', 'ROTATION'):
        sources[k] = manifest['artifacts'][k]; admit_bound(root,sources[k])
    identity = legacy._source(contract, 'identity_names')['records']
    names = {}; aliases = {}
    for row in identity:
        sid = row['security_id']; symbol = row.get('symbol', '')
        aliases.setdefault(sid, set()).update((symbol, symbol.split('.')[-1]))
        if row.get('symbol_effective_from', '') <= date and (not row.get('symbol_effective_to') or row['symbol_effective_to'] >= date):
            names[sid] = row
    release_id=uuid.uuid4().hex
    from workbench_db.v4_snapshot_pg_r2 import Builder
    db = Builder(root,release_id)
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
    def jsonl_rows(ref):
        source=admit_bound(root,ref);raw=source['raw']
        if len(raw)!=ref.get('bytes',ref.get('byte_count')) or digest(raw)!=ref['sha256']:
            raise SourceInvalid('BOUND_ARTIFACT_DIGEST_MISMATCH:'+ref['path'])
        payload=gzip.decompress(raw) if ref['path'].endswith('.gz') else raw
        return (json.loads(line) for line in payload.splitlines() if line)
    def put(domain, row):
        sid = row['entity_id']; ident = names.get(sid, {})
        object_id = sid if domain in ('stocks','sectors','sources') else str(sid)+':'+digest(canonical(row))[:20]
        name = ident.get('security_name') or row.get('display_name') or sid
        if '\ufffd' in name: name = ident.get('symbol') or sid
        symbol = ident.get('symbol') or row.get('fields', {}).get('source_security_key', {}).get('value') or ''
        observed_name=decoration['stocks'].get(symbol) if domain!='sectors' else decoration['sectors'].get(sid)
        if observed_name:name=observed_name
        row.update(display_name=name, security_id=sid if domain=='stocks' else None, symbol=symbol, trade_date=date)
        row['display_name_source']=dict(source_digest=sources['display_names']['sha256'],observed_at=decoration['observed_at'],pit_safe=False,scope='DISPLAY_ONLY') if observed_name and sources.get('display_names') else dict(scope='ACCEPTED_IDENTITY_OR_CODE_FALLBACK')
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
        for row in jsonl_rows(advanced):
                advanced_cutoff=row.get('cutoff',date)
                if row['trade_date'] != date: raise SourceInvalid('PROFILE_DATE_MIX')
                old=db.execute("SELECT payload FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],)).fetchone()
                if not old: unmatched+=1;continue
                result=json.loads(old[0])
                result['fields'].update({k:compact_cell(dict(v,unit=units.get(k)),advanced,k,date) for k,v in row['fields'].items()})
                db.execute("DELETE FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],));put('stocks',result)
        for kind in ('SECTOR_NATIVE','ROTATION'):
            for row in jsonl_rows(sources[kind]):
                    if row['target_trade_date'] != date: raise SourceInvalid('SECTOR_DATE_MIX')
                    old=db.execute("SELECT payload FROM objects WHERE domain='sectors' AND id=?",(row['sector_id'],)).fetchone()
                    if not old: continue
                    result=json.loads(old[0]);cells=dict(row.get('fields',{}))
                    if kind=='ROTATION': cells['output_state']=dict(value=row['output_state'],quality=row['quality'],reason=row.get('reason_codes'))
                    result['fields'].update({k:compact_cell(dict(v,unit=units.get(k)),sources[kind],k,date) for k,v in cells.items()})
                    db.execute("DELETE FROM objects WHERE domain='sectors' AND id=?",(row['sector_id'],));put('sectors',result)
        domain_features={}
        # Optional domain contracts are not runtime authorities. They remain
        # unavailable here until their exact approved Registry binding exists.
        market_authority=root/'config/v4_market_operational_authority_v1.json'
        authority=operational('market',market_authority)
        if authority is not None:
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('MARKET_SOURCE_CONTEXT_MISMATCH')
            market=legacy._read(authority['market']);sources['market_operational']=authority['market']
            domain_features['market']=market
            fields={k:compact_cell(dict(value=v,quality='UNKNOWN' if v in (None,'UNKNOWN') else 'KNOWN',reason=market['trend'].get('unknown_reason') if k=='trend_axis' else market['axes']['field_quality'].get(k,{}).get('unknown_reason'),contract_id='FP05_CURRENT_MARKET_FOUR_AXES_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1'),authority['market'],k,date) for k,v in market['row'].items()}
            put('market',dict(entity_id='A_SHARE_RESEARCH_MARKET',display_name='全市场研究环境',fields=fields))
        sector_authority=root/'config/v4_sector_operational_authority_v1.json'
        authority=operational('sector',sector_authority)
        if authority is not None:
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('SECTOR_SOURCE_CONTEXT_MISMATCH')
            admit_bound(root,authority['native']);sources['sector_operational']=authority['native'];domain_features['sector']=authority
            for row in jsonl_rows(authority['native']):
                    old=db.execute("SELECT payload FROM objects WHERE domain='sectors' AND id=?",(row['sector_id'],)).fetchone()
                    if not old:raise SourceInvalid('SECTOR_IDENTITY_NOT_BOUND')
                    result=json.loads(old[0]);result['fields'].update({k:compact_cell(dict(v,unit=units.get(k)),authority['native'],k,date) for k,v in row['fields'].items()})
                    result['fields']['sector_type']=compact_cell(dict(value=row['sector_type'],quality='KNOWN'),authority['native'],'sector_type',date)
                    db.execute("DELETE FROM objects WHERE domain='sectors' AND id=?",(row['sector_id'],));put('sectors',result)
        stock_authority=root/'config/v4_stock_operational_authority_v1.json'
        authority=operational('stocks',stock_authority)
        if authority is not None:
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('STOCK_SOURCE_CONTEXT_MISMATCH')
            for kind in ('factors','profiles','series'):admit_bound(root,authority[kind]);sources['stock_'+kind]=authority[kind]
            from .stock_unit_projection import project as project_stock_unit
            unit_path='config/v4_stock_unit_projection_v1.json';unit_raw=read_path(root,unit_path)['raw']
            unit_binding=dict(path=unit_path,sha256=digest(unit_raw),bytes=len(unit_raw));unit_contract=json.loads(unit_raw)
            if unit_contract['contract_id']!='R2_BOUND_OWNER_UNIT_PROJECTION_V1':raise SourceInvalid('STOCK_UNIT_PROJECTION_CONTRACT_MISMATCH')
            sources['stock_unit_projection_contract']=unit_binding
            registries=[]
            for index,binding in enumerate(unit_contract['registries']):
                registry=json.loads(admit_bound(root,binding)['raw'])
                if registry['contract_id'] not in ('V4_03_FIELD_REGISTRY_V1','V4_04_FIELD_REGISTRY_V2'):raise SourceInvalid('UNADMITTED_STOCK_UNIT_REGISTRY')
                sources['stock_unit_registry_'+str(index)]=binding;registries.append(registry)
            domain_features['stocks']=authority
            for kind in ('factors','profiles'):
                for row in jsonl_rows(authority[kind]):
                        if row['trade_date']!=date:raise SourceInvalid('STOCK_DATE_MIX')
                        old=db.execute("SELECT payload FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],)).fetchone()
                        if not old:continue
                        result=json.loads(old[0]);cells=row['fields'] if kind=='factors' else {**row['derived_fields'],**row['states']}
                        for k,v in cells.items():
                            declared=project_stock_unit(k,v,registries,authority['price_basis'])
                            cell=dict(declared,quality='UNKNOWN' if v.get('unknown_reason') or v.get('value') is None else 'KNOWN',reason=v.get('unknown_reason'),unit=declared.get('unit') or units.get(k))
                            result['fields'][k]=compact_cell(cell,authority[kind],k,date)
                        db.execute("DELETE FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],));put('stocks',result)
        if authority is not None:
            from .raw_turnover import cells as raw_turnover_cells
            raw_path='config/v4_raw_amount_volume_projection_v1.json';raw_raw=read_path(root,raw_path)['raw']
            raw_turnover_contract=dict(path=raw_path,sha256=digest(raw_raw),bytes=len(raw_raw));raw_units=json.loads(raw_raw)
            if raw_units['unit_contract']!=authority['sources']['unit_contract'] or raw_units['contract_id']!='R2_RAW_AMOUNT_VOLUME_PROJECTION_V1':
                raise SourceInvalid('RAW_TURNOVER_UNIT_SOURCE_CONTRACT_MISMATCH')
            sources['raw_turnover_projection_contract']=raw_turnover_contract
            sources['raw_turnover_unit_contract']=authority['sources']['unit_contract']
            admit_bound(root,sources['raw_turnover_unit_contract'])
            for row in legacy._source(contract,'RAW_DAILY')['rows']:
                old=db.execute("SELECT payload FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],)).fetchone()
                if not old:raise SourceInvalid('RAW_TURNOVER_STOCK_IDENTITY_NOT_BOUND')
                result=json.loads(old[0])
                for field,cell in raw_turnover_cells(row,date,authority['volume_unit'],authority['amount_unit']).items():
                    result['fields'][field]=compact_cell(cell,sources['RAW_DAILY'],field,date)
                db.execute("DELETE FROM objects WHERE domain='stocks' AND id=?",(row['security_id'],));put('stocks',result)
        structure_authority=(authority_overrides or {}).get('stock_structure_timeline')
        if structure_authority is not None:
            if (structure_authority.get('contract_id')!='V4_STOCK_STRUCTURE_TIMELINE_CANDIDATE_R1'
                    or structure_authority.get('trade_date')!=date
                    or structure_authority.get('input_data_head',{}).get('sha256')!=context['context']['data_head_digest']
                    or structure_authority.get('AS_RECORDED') is not False
                    or structure_authority.get('PIT_ELIGIBLE') is not False
                    or structure_authority.get('knowledge_lineage')!='RECONSTRUCTED_CORRECTED'):
                raise SourceInvalid('STOCK_STRUCTURE_CANDIDATE_IDENTITY_INVALID')
            manifest_binding=structure_authority.get('runtime_manifest')
            if not isinstance(manifest_binding,dict):raise SourceInvalid('STOCK_STRUCTURE_RUNTIME_MANIFEST_REQUIRED')
            manifest_source=admit_bound(root,manifest_binding)
            if len(manifest_source['raw'])!=manifest_binding.get('bytes') or digest(manifest_source['raw'])!=manifest_binding['sha256']:
                raise SourceInvalid('STOCK_STRUCTURE_RUNTIME_MANIFEST_BINDING_MISMATCH')
            structure_manifest=json.loads(manifest_source['raw'])
            owner_inputs=structure_manifest.get('owner_inputs',{})
            if (structure_manifest.get('contract_id')!='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST'
                    or structure_manifest.get('formal_accepted') is not False
                    or structure_manifest.get('status')!='ENGINEERING_CANDIDATE_NOT_ACCEPTED'
                    or structure_manifest.get('knowledge_lineage')!='RECONSTRUCTED_CORRECTED'
                    or owner_inputs.get('trade_date')!=date
                    or owner_inputs.get('AS_RECORDED') is not False):
                raise SourceInvalid('STOCK_STRUCTURE_OWNER_CANDIDATE_NOT_EXACT')
            artifacts={Path(ref['path']).name:ref for ref in structure_manifest.get('artifacts',[])}
            runtime_ref=artifacts.get('runtime_security.jsonl.gz')
            if not runtime_ref:raise SourceInvalid('STOCK_STRUCTURE_RUNTIME_SECURITY_MISSING')
            admit_bound(root,runtime_ref);sources['stock_structure_runtime_manifest']=manifest_binding
            sources['stock_structure_runtime_security']=runtime_ref
            domain_features['stock_structure_timeline']=dict(structure_authority,
                runtime_security=runtime_ref,owner_contract=structure_manifest.get('contract_id'),
                owner_status=structure_manifest.get('status'))
            rows_seen=indexed=unmatched=0
            for row in jsonl_rows(runtime_ref):
                rows_seen+=1
                identity=row.get('identity',{});sid=identity.get('security_id')
                if identity.get('trade_date')!=date or not isinstance(sid,str):
                    raise SourceInvalid('STOCK_STRUCTURE_RUNTIME_ROW_IDENTITY_INVALID')
                if row.get('AS_RECORDED') is not False or row.get('PIT_ELIGIBLE') is not False:
                    raise SourceInvalid('STOCK_STRUCTURE_RUNTIME_ROW_LINEAGE_INVALID')
                events=row.get('events')
                projection=row.get('active_projection')
                if not isinstance(events,list) or not isinstance(projection,dict):
                    raise SourceInvalid('STOCK_STRUCTURE_RUNTIME_ROW_SHAPE_INVALID')
                for event in events:
                    if event.get('created_trade_date','')>date or event.get('candidate_only') is not True:
                        raise SourceInvalid('STOCK_STRUCTURE_EVENT_CUTOFF_OR_CANDIDATE_INVALID')
                active_quality=projection.get('active_anchor_selection_quality')
                anchor_value=projection.get('anchor_view_asof_t')
                anchor_quality='KNOWN' if active_quality=='KNOWN' else 'UNKNOWN'
                anchor_reason=projection.get('active_anchor_selection_reason') or projection.get('reason')
                old=db.execute("SELECT payload FROM objects WHERE domain='stocks' AND id=?",(sid,)).fetchone()
                if not old:
                    unmatched+=1
                    continue
                result=json.loads(old[0])
                result['fields']['structure_events']=compact_cell(dict(value=events,quality='KNOWN',
                    contract_id=structure_manifest['contract_id']),runtime_ref,'structure_events',date)
                result['fields']['anchor_view_asof_t']=compact_cell(dict(value=anchor_value,quality=anchor_quality,
                    reason=None if anchor_quality=='KNOWN' else anchor_reason,
                    contract_id=structure_manifest['contract_id']),runtime_ref,'anchor_view_asof_t',date)
                db.execute("DELETE FROM objects WHERE domain='stocks' AND id=?",(sid,));put('stocks',result)
                indexed+=1
            if rows_seen!=int(owner_inputs.get('rows',rows_seen)) or indexed==0:
                raise SourceInvalid('STOCK_STRUCTURE_OWNER_ROW_COUNT_MISMATCH')
            domain_features['stock_structure_timeline'].update(rows_read=rows_seen,
                securities_matched=indexed,securities_outside_current_universe=unmatched)
            owners['stock_structure_timeline']=dict(contract_id=structure_authority['contract_id'],
                trade_date=date,input_data_head=structure_authority['input_data_head'],
                runtime_manifest=manifest_binding,runtime_security=runtime_ref,
                rows_read=rows_seen,securities_matched=indexed,securities_outside_current_universe=unmatched,
                knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,PIT_ELIGIBLE=False)
        focus_authority=root/'config/v4_focus_operational_authority_v1.json'
        focus_ingress=operational('focus',focus_authority)
        if focus_override is not None or focus_ingress is not None:
            authority=focus_override if focus_override is not None else focus_ingress
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('FOCUS_SOURCE_CONTEXT_MISMATCH')
            publication=legacy._read(authority['publication']);domain_features['focus']=publication;sources['focus_operational']=authority['publication']
            if authority.get('journal'):
                admit_bound(root,authority['journal']);sources['focus_journal']=authority['journal']
            for name,binding in publication.get('sources',{}).get('implementation',{}).items():
                admit_bound(root,binding);sources['focus_kernel_'+name]=binding
            for episode in {e['entity_id']:e for e in sorted(publication['episodes'],key=lambda e:e['T0'])}.values():
                last=episode['observations'][-1];stock=db.execute("SELECT payload FROM objects WHERE domain='stocks' AND id=?",(episode['entity_id'],)).fetchone();stock=json.loads(stock[0]) if stock else {}
                fields={k:compact_cell(dict(value=v,quality='UNKNOWN' if v is None else 'KNOWN',contract_id=publication['contract_id']),authority['publication'],k,date) for k,v in {**last,**{k:episode[k] for k in ('episode_id','T0','end_date','parent_episode_id')}}.items()}
                put('focus',dict(entity_id=episode['entity_id'],display_name=stock.get('display_name',episode['entity_id']),symbol=stock.get('symbol',''),fields=fields))
        center_authority=root/'config/v4_market_center_authority_v1.json'
        authority=operational('market_center',center_authority)
        if authority is not None:
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('MARKET_CENTER_CONTEXT_MISMATCH')
            domain_features['market_center']=legacy._read(authority['publication']);sources['market_center']=authority['publication']
        forward_authority=root/'config/v4_forward_operational_authority_v1.json'
        authority=operational('forward',forward_authority)
        if authority is not None:
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('FORWARD_SOURCE_CONTEXT_MISMATCH')
            publication=legacy._read(authority['publication']);domain_features['forward']=publication;sources['forward_operational']=authority['publication']
            for row in publication['enrollments']:
                old=db.execute("SELECT id,payload FROM objects WHERE domain='forward' AND json_extract(payload,'$.fields.enrollment_id.value')=?",(row['enrollment_id'],)).fetchone()
                if not old:raise SourceInvalid('FORWARD_ENROLLMENT_NOT_PRESERVED')
                result=json.loads(old[1]);keys=('signal_type','model_contract_id','parameter_digest','primary_industry','source_publication','control_assignment_ids','benchmark_ids','comparison_reference')
                result['fields'].update({k:compact_cell(dict(value=row.get(k),quality='KNOWN' if row.get(k) is not None else 'UNKNOWN'),row['source'],k,date) for k in keys})
                db.execute("UPDATE objects SET payload=? WHERE domain='forward' AND id=?",(canonical(result).decode(),old[0]))
            if publication.get('adapter_contract_id'):
                # Materialize the accepted continuation; legacy five-row
                # settlement projection must not survive a new owner upgrade.
                db.execute("DELETE FROM objects WHERE domain='settlement'")
                entities={row['enrollment_id']:row['entity_id'] for row in publication['enrollments']}
                for outcome in publication['outcomes']:
                    sid=entities[outcome['enrollment_id']];fields={}
                    for key,value in outcome.items():
                        if key=='source':continue
                        reason='NOT_YET_DUE' if outcome['outcome_status']=='PENDING' else outcome['outcome_status']
                        unit='ratio' if key in ('R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N') else 'sessions' if key=='horizon' else 'date' if key in ('due_date','report_cutoff') else 'NOT_APPLICABLE_TYPED_VALUE'
                        fields[key]=compact_cell(dict(value=value,quality='KNOWN' if value is not None else 'UNKNOWN',
                            reason=None if value is not None else reason,unit=unit),outcome['source'],key,date)
                    put('settlement',dict(entity_id=sid,fields=fields))
        replay_authority=root/'config/v4_replay_compare_authority_v1.json'
        authority=operational('replay',replay_authority)
        if authority is not None:
            if authority['trade_date']!=date or authority['input_data_head']['sha256']!=context['context']['data_head_digest']:raise SourceInvalid('REPLAY_SOURCE_CONTEXT_MISMATCH')
            for entry in authority['catalog']:admit_bound(root,entry['snapshot'])
            admit_bound(root,authority['contract']);domain_features['replay']=authority
            sources['replay_operational']=authority
        counts={d:db.execute('SELECT count(*) FROM objects WHERE domain=?',(d,)).fetchone()[0] for d in DOMAINS}
        expected_stocks=len(legacy._source(contract,'RAW_DAILY')['rows'])
        expected_sectors=len({r['sector_id'] for r in legacy._source(contract,'membership')})
        if counts['stocks'] != expected_stocks or counts['sectors'] != expected_sectors: raise SourceInvalid('UNIVERSE_COUNT_GATE')
        gaps=[dict(domain='market',state='ENGINEERING_NOT_READY',reason='ACCEPTED_MARKET_OWNER_OUTPUT_NOT_BOUND_TO_20260930',next='FP05_TARGETED_CURRENT_FOUR_AXIS_RECOMPUTE'),
              dict(domain='focus',state='ENGINEERING_NOT_READY',reason='EPISODE_PROJECTION_NOT_PUBLISHED_IN_CURRENT_OWNER_CONTEXT',next='FP08_PUBLISH_REAL_EPISODES'),
              dict(domain='stocks',state='SOURCE_INCOMPLETE',reason='CURRENT_CORE_OWNER_PROFILE_IS_20260928_NOT_20260930',next='FP07_CURRENT_CORE_RECOMPUTE'),
              dict(domain='profile_identity',state='SOURCE_INCOMPLETE',reason='ADVANCED_ROWS_OUTSIDE_CURRENT_RAW_UNIVERSE',count=unmatched)]
        if 'market' in domain_features:gaps=[g for g in gaps if g['domain']!='market']
        if 'stocks' in domain_features:gaps=[g for g in gaps if g['domain']!='stocks']
        if 'focus' in domain_features:
            gaps=[g for g in gaps if g['domain']!='focus']+[dict(domain='focus',state='SOURCE_INCOMPLETE',reason='AUTOMATIC_WRITE_PATH_ADAPTER_AND_LEGACY_HISTORY_MIGRATION_NOT_ADMITTED',next='FP08_INDEPENDENT_FOCUS_WRITE_ADMISSION')]
            if domain_features['focus'].get('contract_id')=='R2_V4_FOCUS_PATH_OUTCOME_V2':
                gaps[-1].update(reason='UNRESOLVED_PATH_PREDICATE_OWNERS_AND_UNRECONCILED_LEGACY_PG',next='CONTINUOUS_DAILY_DRIVER_ADMISSION')
        meta=dict(contract_id='V4_RESEARCH_SNAPSHOT_V1', domain_features=domain_features,context=context['context'],legacy_context_token=context['context_token'],
            source_contract_digest=contract_digest, sources=sources, owners=owners, counts=counts, gaps=gaps,
            field_registry=field_registry, operational_state='OPERATIONAL_PRODUCTION_ACTIVE' if publish else 'STAGED_ENGINEERING_CANDIDATE',
            evidence_state='VALIDATION_ONGOING', quality='QUALITY_DEGRADED', publication_scope='FP02_INDEXED_EXISTING_REAL_OUTPUTS',
            release_id=release_id, built_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        def instant(value):
            parsed=datetime.fromisoformat(value)
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        source_as_of=max(map(instant,[context['context']['data_updated_at'],decoration['observed_at'],advanced_cutoff]))
        published_at=datetime.now(timezone.utc)
        if source_as_of>published_at:raise SourceInvalid('FUTURE_SOURCE_AS_OF_FORBIDDEN')
        meta['metadata']=dict(owner='FP02_RESEARCH_PROJECTION',release_id=release_id,
            source_snapshot=context['context']['data_head_digest'],contract_version='1.0.0',source_as_of=source_as_of.isoformat(),
            trading_date=date,input_digest=digest(canonical(dict(sources=sources,owners=owners))),published_at=published_at.isoformat(),
            evidence_origin='REAL_ACCEPTED_SOURCE',evidence_state='VALIDATION_ONGOING',data_quality_state='QUALITY_DEGRADED',
            knowledge_lineage=context['context']['knowledge_lineage'])
        db.execute('INSERT INTO metadata VALUES(?,?)',('snapshot',canonical(meta).decode()))
        descriptor=db.seal(meta);db.commit();db.close()
        check=ProductionV4ResearchReader(root,pg_candidate_schema=descriptor['schema'])
        if fail_readback:raise SourceInvalid('INJECTED_READBACK_FAILURE')
        if check.manifest['counts']!=counts:raise SourceInvalid('READBACK_COUNT_MISMATCH')
        return dict(status='STAGED_NOT_PUBLISHED',pointer=descriptor,descriptor=descriptor,
                    pg_candidate_schema=descriptor['schema'],counts=counts,gaps=gaps,
                    build_seconds=round(time.perf_counter()-started,3),production_changed=False)
    except Exception:
        db.close();raise


def rollback_snapshot(root,expected_pointer):
    raise SourceInvalid('PG_SNAPSHOT_ROLLBACK_REQUIRES_CANONICAL_PUBLICATION_HEAD_CAS')


class ProductionV4ResearchReader:
    def __init__(self, root, *, snapshot_authority=None, pg_candidate_schema=None):
        schema=pg_candidate_schema or (snapshot_authority.get('schema') if isinstance(snapshot_authority,dict) else None)
        schema=schema or os.environ.get('V4_PG_RESEARCH_CANDIDATE_SCHEMA')
        if not schema:raise SourceInvalid('PG_CANDIDATE_SCHEMA_REQUIRED_NO_WORKSPACE_AUTHORITY')
        self._init_pg_candidate(root,schema)

    def _init_pg_candidate(self, root, schema):
        """Bind the development UI to one verified immutable PG snapshot.

        The schema is injected by the 28766 development launcher. This path
        reads the snapshot descriptor and manifest from their PG relations and
        never consults the local snapshot pointer or files.
        """
        from workbench_db.v4_native import connection
        from workbench_db.v4_snapshot_pg_r2 import verify
        self.root=Path(root).resolve()
        if not isinstance(schema,str) or not schema.startswith('v4_research_'):
            raise SourceInvalid('PG_CANDIDATE_SCHEMA_INVALID')
        try:
            with connection(schema,read_only=True) as pg:
                rows=pg.execute('SELECT digest,contract_id,descriptor FROM snapshot_identity').fetchall()
                if len(rows)!=1:
                    raise SourceInvalid('PG_CANDIDATE_SNAPSHOT_IDENTITY_NOT_UNIQUE')
                digest_value,contract_id,raw_descriptor=rows[0]
                descriptor=json.loads(raw_descriptor)
                if digest_value!=descriptor.get('logical_digest') or contract_id!='V4_PG_RESEARCH_SNAPSHOT_R2':
                    raise SourceInvalid('PG_CANDIDATE_SNAPSHOT_DESCRIPTOR_INVALID')
                verify(pg,descriptor)
                metadata_rows=pg.execute("SELECT value FROM metadata WHERE key='snapshot'").fetchall()
                if len(metadata_rows)!=1:
                    raise SourceInvalid('PG_CANDIDATE_SNAPSHOT_MANIFEST_NOT_UNIQUE')
                self.manifest=json.loads(metadata_rows[0][0])
                identity=pg.execute('SELECT current_database(),(SELECT oid::int FROM pg_database WHERE datname=current_database()),coalesce(inet_server_addr()::text,\'local\'),inet_server_port()').fetchone()
                from workbench_db.v4_snapshot_pg_r2 import database_identity
                cluster=database_identity(pg)
            metadata=validate_release_metadata(self.manifest)
            if (descriptor.get('schema')!=schema or descriptor.get('T0')!=self.manifest.get('context',{}).get('accepted_trade_date')
                    or descriptor.get('release_id')!=self.manifest.get('release_id')
                    or metadata.get('trading_date')!=descriptor.get('T0')):
                raise SourceInvalid('PG_CANDIDATE_SNAPSHOT_CONTEXT_MISMATCH')
        except SourceInvalid:
            raise
        except Exception as error:
            raise SourceInvalid('PG_CANDIDATE_SNAPSHOT_READ_FAILED:'+type(error).__name__) from error
        self.pg_candidate_schema=schema
        self.pg_descriptor=descriptor
        self.path=None
        self.authority={'manifest':{'sha256':descriptor['logical_digest']}}
        self.context_key='research-v4-pg-candidate-'+descriptor['logical_digest']
        self.context=dict(self.manifest['context'],release_id=descriptor['release_id'],
            model_namespace='V4_RESEARCH_SNAPSHOT_V1',source_mode='PG_CANDIDATE_SNAPSHOT',
            publication_id=descriptor['release_id'],data_as_of=self.manifest['context']['data_updated_at'],
            core_revision=self.manifest['source_contract_digest'],optional_enrichment_revision=self.manifest.get('sources',{}).get('advanced',{}).get('sha256'),
            turnover_as_of=None,quality=self.manifest['quality'],source_contract_id='V4_RESEARCH_SNAPSHOT_V1',
            factor_contract_id=None,state_contract_id='PG_SNAPSHOT_IDENTITY',parameter_set_id=None,
            trade_date=descriptor['T0'],release_metadata=metadata,database_identity=cluster,
            scoped_release=False,operational_release_scope=[],full_product_release=False,
            joint_release_digest=None,candidate_status=metadata.get('evidence_state','VALIDATION_ONGOING'))
        self.context['available_trade_dates']=[descriptor['T0']]
        self.context['domain_readiness']={key:dict(released=False,scope='PG_CANDIDATE_SNAPSHOT',debt=[])
            for key in ('stocks','sectors','market','focus','forward','strict_pit','fep')}

    def envelope(self, **payload):
        return dict(context=self.context,context_token=self.context_key,**payload)

    def known_identity(self,entity):
        with self.connect() as db:
            return db.execute('SELECT 1 FROM aliases WHERE id=? OR alias=? LIMIT 1',(entity,entity.casefold())).fetchone() is not None

    def connect(self):
        from workbench_db.v4_native import connection
        from workbench_db.v4_snapshot_pg_r1 import ReadTransaction
        scope=_request_reads.get()
        if scope is not None:
            stack,transactions=scope
            key=(self.pg_descriptor['schema'],self.pg_descriptor['logical_digest'])
            if key not in transactions:
                @contextmanager
                def candidate_read():
                    with connection(self.pg_candidate_schema,read_only=True) as pg:
                        rows=pg.execute('SELECT digest,contract_id,descriptor FROM snapshot_identity').fetchall()
                        expected=[(self.pg_descriptor['logical_digest'],'V4_PG_RESEARCH_SNAPSHOT_R2',json.dumps(self.pg_descriptor,sort_keys=True,ensure_ascii=False,separators=(',',':')))]
                        if rows!=expected:raise SourceInvalid('PG_CANDIDATE_SNAPSHOT_IDENTITY_CHANGED')
                        yield ReadTransaction(pg)
                transactions[key]=stack.enter_context(candidate_read())
            return nullcontext(transactions[key])
        @contextmanager
        def candidate_read():
            with connection(self.pg_candidate_schema,read_only=True) as pg:
                rows=pg.execute('SELECT digest,contract_id,descriptor FROM snapshot_identity').fetchall()
                expected=[(self.pg_descriptor['logical_digest'],'V4_PG_RESEARCH_SNAPSHOT_R2',json.dumps(self.pg_descriptor,sort_keys=True,ensure_ascii=False,separators=(',',':')))]
                if rows!=expected:raise SourceInvalid('PG_CANDIDATE_SNAPSHOT_IDENTITY_CHANGED')
                yield ReadTransaction(pg)
        return candidate_read()

    def query(self, domain, query=None, *, entity=None, sector=None, summary=False):
        q=query or {}
        allowed={'q','state','limit','offset','sort','context_token','trade_date','release_id','model_namespace','type','maturity','health','rotation','quality','eligibility'}
        if set(q)-allowed:raise ValueError('UNKNOWN_PARAMETER')
        for key, expected in [('context_token',self.context_key),('trade_date',self.context['accepted_trade_date']),('release_id',self.context['release_id']),('model_namespace',self.context['model_namespace'])]:
            if key in q and q[key]!=expected:raise SourceInvalid('CONTEXT_CONFLICT:'+key)
        if domain not in DOMAINS:raise ValueError('UNKNOWN_DOMAIN')
        limit=int(q.get('limit',30));offset=int(q.get('offset',0));needle=q.get('q','').strip().casefold()
        if not 1<=limit<=200 or not 0<=offset<=1000000 or len(needle)>80:raise ValueError('INVALID_QUERY_BOUND')
        sort=[]
        for entry in q.get('sort','id').split(','):
            column=entry.lstrip('-')
            numeric={'sector_rs20_pct','sector_rs5_pct','sector_rs20','sector_rs5','breadth_ret1','ma20_width','participation_proxy','member_count','close','rps5','rps20'}
            if column not in {'id','name','symbol','state'}|numeric:raise ValueError('INVALID_SORT_FIELD')
            if column in numeric:sort.extend(numeric_sort_expressions(column,entry.startswith('-')))
            else:sort.append(column+(' DESC NULLS LAST' if entry.startswith('-') else ' ASC NULLS FIRST'))
        if len(q.get('sort','id').split(','))>4:raise ValueError('SORT_BOUND')
        sort.append('id ASC');where=['domain=?'];args=[domain]
        if needle:
            # Prefix ranges keep indexed ID/symbol/alias lookup bounded. Some
            # imported PG snapshots have a lossy legacy `name` projection while
            # canonical Unicode display_name remains intact in the JSON payload.
            indexed_match="id IN (SELECT id FROM objects WHERE domain=? AND id=? UNION SELECT id FROM objects WHERE domain=? AND symbol>=? AND symbol<? UNION SELECT id FROM objects WHERE domain=? AND name>=? AND name<? UNION SELECT id FROM aliases WHERE alias>=? AND alias<? UNION SELECT o.id FROM aliases a JOIN objects o ON o.domain=? AND o.id>=a.id||':' AND o.id<a.id||';' WHERE a.alias>=? AND a.alias<?)"
            indexed_args=(domain,needle.upper(),domain,needle.upper(),needle.upper()+'\uffff',domain,needle,needle+'\uffff',needle,needle+'\uffff',domain,needle,needle+'\uffff')
            where.append('('+indexed_match+" OR COALESCE((payload::jsonb)->>'display_name','') ILIKE ?)")
            args.extend(indexed_args+('%'+needle+'%',))
        if q.get('state'):where.append('state=?');args.append(q['state'])
        if domain in ('stocks','sectors','focus'):
            for key,field in [('type','sector_type'),('maturity','maturity'),('health','health'),('rotation','output_state'),('quality','quality'),('eligibility','final_eligibility')]:
                if q.get(key):
                    if len(q[key])>60:raise ValueError('FILTER_BOUND')
                    where.append("json_extract(payload,'$.fields."+field+".value')=?");args.append(q[key])
        if entity:
            where.append('id IN (SELECT ? UNION SELECT id FROM aliases WHERE alias=?)');args.extend((entity,entity.casefold()))
        if sector:where.append('id IN (SELECT security FROM members WHERE sector=?)');args.append(sector)
        clause=' AND '.join(where)
        with self.connect() as db:
            total=db.execute(''.join(('SELECT count(*) FROM objects WHERE ',clause)),args).fetchone()[0]
            rows=db.execute(''.join(('SELECT payload FROM objects WHERE ',clause,' ORDER BY ',','.join(sort),' LIMIT ? OFFSET ?')),args+[limit,offset]).fetchall()
        gap=next((g for g in self.manifest['gaps'] if g['domain']==domain),None)
        items=[json.loads(r[0]) for r in rows]
        if summary and domain in ('stocks','sectors'):
            keys=('close','scenario','final_eligibility','primary_industry','source_security_key','trade_date') if domain=='stocks' else ('sector_name','sector_type','member_count','output_state','prior_rotation_state','sector_rs20','sector_rs5','sector_rs20_pct','breadth_delta3','breadth_ret1','seed_width','participation_proxy','top3_concentration','trade_date')
            for row in items:row['fields']={k:v for k,v in row['fields'].items() if k in keys}
        return self.envelope(domain=domain,items=items,total=total,offset=offset,limit=limit,
            has_next=offset+limit<total,status=gap['state'] if not total and gap else ('READY' if total else 'EMPTY_VALID'),gap=gap)
