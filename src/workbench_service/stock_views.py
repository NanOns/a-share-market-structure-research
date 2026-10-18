"""Actual bar charts and owner-derived explanations; no invented hypotheses."""
import json
from collections import defaultdict
from datetime import date
from .domain_views import value
from .current_v4_context import SourceInvalid

def aggregate(bars,period):
    if period=='D':return bars
    groups=defaultdict(list)
    for b in bars:
        day=date.fromisoformat(b['trade_date']);key=day.isocalendar()[:2] if period=='W' else (day.year,day.month)
        groups[key].append(b)
    result=[]
    for key,items in sorted(groups.items()):
        known=all(b['quality']=='KNOWN' for b in items)
        result.append(dict(trade_date=items[-1]['trade_date'],first_trade_date=items[0]['trade_date'],open=items[0]['open'] if known else None,high=max(b['high'] for b in items) if known else None,low=min(b['low'] for b in items) if known else None,close=items[-1]['close'] if known else None,volume=sum(b['volume'] for b in items),amount=sum(b['amount'] for b in items),quality='KNOWN' if known else 'UNKNOWN',actual_count=len(items),period_status='FORMING_AS_OF' if key==sorted(groups)[-1] else 'CLOSED_OBSERVED_BUCKET'))
    return result

def chart(reader,item,query):
    authority=reader.manifest.get('domain_features',{}).get('stocks')
    if not authority:return reader.envelope(status='SOURCE_INCOMPLETE',items=[],total=0,reason='HISTORICAL_INDEX_NOT_BOUND')
    period=query.get('period','D');basis=query.get('price_basis','QFQ');limit=int(query.get('limit',120));offset=int(query.get('offset',0))
    if period not in ('D','W','M') or basis not in ('RAW','QFQ') or not 1<=limit<=200 or offset<0:raise ValueError('CHART_QUERY_INVALID')
    if getattr(reader,'pg_candidate_schema',None):
        from workbench_db.v4_native import connection
        from workbench_db.v4_history_pg_r1 import read as read_pg_history
        from psycopg import sql
        source=authority.get('sources',{}).get('history',{})
        head=reader.manifest.get('context',{}).get('data_head_digest')
        source_digest=source.get('sha256') if isinstance(source,dict) else None
        if not isinstance(head,str) or not isinstance(source_digest,str):
            return reader.envelope(status='SOURCE_INCOMPLETE',items=[],total=0,reason='PG_HISTORY_HEAD_OR_SOURCE_BINDING_MISSING')
        # Resolve existing history by immutable PG lineage keys, never by a
        # repository-root-derived schema name or a local pointer file.
        matches=[]
        declared=authority.get('history_index')
        if isinstance(declared,dict):
            # New stock authorities carry the immutable history version
            # directly. Older accepted snapshots can still resolve the exact
            # same PG lineage tuple without consulting any local index file.
            if (declared.get('contract_id')=='V4_PG_DATED_HISTORY_INDEX_R1'
                    and declared.get('engine')=='postgresql'
                    and declared.get('T0')==reader.context['trade_date']
                    and declared.get('head_token')==head
                    and declared.get('source_digest')==source_digest):
                matches=[(declared.get('schema'),declared.get('version'),declared.get('head_token'),
                    declared.get('T0'),declared.get('source_digest'),declared.get('logical_digest'),
                    declared.get('symbol_count'),declared.get('bar_count'))]
        else:
            with connection('v4_meta',read_only=True) as pg:
                schemas=[row[0] for row in pg.execute("SELECT schemaname FROM pg_tables WHERE schemaname LIKE 'v4_history_%' AND tablename='history_versions' ORDER BY schemaname").fetchall()]
                for schema in schemas:
                    rows=pg.execute(sql.SQL(
                        'SELECT version,head_token,t0::text,source_digest,logical_digest,symbol_count,bar_count '
                        'FROM {}.history_versions WHERE t0=%s AND head_token=%s AND source_digest=%s ORDER BY version'
                    ).format(sql.Identifier(schema)),(reader.context['trade_date'],head,source_digest)).fetchall()
                    matches.extend((schema,*row) for row in rows)
        if len(matches)!=1:
            return reader.envelope(status='SOURCE_INCOMPLETE',items=[],total=0,reason='NO_UNIQUE_PG_HISTORY_VERSION_MATCHING_SNAPSHOT_HEAD_AND_SOURCE',
                history_versions_found=len(matches),as_of=reader.context['trade_date'],
                price_basis=basis,period=period,source=dict(head_token=head,source_digest=source_digest))
        history_schema,version,head_token,t0,actual_source,digest_value,symbol_count,bar_count=matches[0]
        binding=dict(contract_id='V4_PG_DATED_HISTORY_INDEX_R1',engine='postgresql',schema=history_schema,
            version=version,head_token=head_token,T0=t0,source_digest=actual_source,
            logical_digest=digest_value,symbol_count=symbol_count,bar_count=bar_count)
        rows=read_pg_history(reader.root,binding,t0,item['entity_id']) or []
        bars=[]
        for row in rows:
            prices=row['raw_ohlc'] if basis=='RAW' else row['qfq_ohlc']
            values=list(map(float,prices)) if prices else [None]*4
            bars.append(dict(trade_date=row['trade_date'],**dict(zip(('open','high','low','close'),values)),
                volume=row['volume'],amount=row['amount'],quality='KNOWN' if prices else 'UNKNOWN',reason=row.get('adjustment_reason')))
        result=aggregate(bars,period);total=len(result);end=max(0,total-offset);start=max(0,end-limit);items=result[start:end]
        for i,b in enumerate(result):
            for n in (5,20,60):
                window=result[max(0,i-n+1):i+1]
                b['ma'+str(n)]=sum(x['close'] for x in window)/n if len(window)==n and all(x['close'] is not None for x in window) else None
        return reader.envelope(status='READY' if items else 'EMPTY_VALID',items=items,total=total,limit=limit,offset=offset,
            has_next=start>0,period=period,price_basis=basis,split_adjustment='ACCEPTED_QFQ' if basis=='QFQ' else 'NONE',
            as_of=reader.context['trade_date'],earliest_valid_date=rows[0]['trade_date'] if rows else None,
            volume_unit='SHARES',amount_unit='CNY',source=dict(history_version=version,head_token=head,source_digest=actual_source),
            factor_registry_ref=reader.manifest['source_contract_digest'],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    return reader.envelope(status='SOURCE_INCOMPLETE',items=[],total=0,
        reason='PG_HISTORY_BINDING_REQUIRED',as_of=reader.context['trade_date'],
        price_basis=basis,period=period,
        source=dict(required='V4_PG_DATED_HISTORY_INDEX_R1',available=False))

def membership_relations(reader,item):
    """Resolve only actual published current relations to bound sector identities."""
    cells={k:item['fields'].get(k) for k in ('primary_industry','supporting_concepts')}
    primary=value(item,'primary_industry');concepts=value(item,'supporting_concepts')
    if concepts is not None and (not isinstance(concepts,list) or any(not isinstance(x,str) for x in concepts) or len(concepts)>378):
        raise SourceInvalid('STOCK_MEMBERSHIP_RELATION_SHAPE')
    requested=([('primary_industry',primary)] if primary else [])+[('supporting_concepts',x) for x in concepts or []]
    rows=[]
    with reader.connect() as db:
        for kind,sid in requested:
            source=db.execute("SELECT payload FROM objects WHERE domain='sectors' AND id=?",(sid,)).fetchone()
            member=db.execute('SELECT 1 FROM members WHERE sector=? AND security=?',(sid,item['entity_id'])).fetchone()
            sector=json.loads(source[0]) if source else None;ready=bool(sector and member)
            rows.append(dict(role=kind,sector_id=sid,display_name=sector['display_name'] if sector else None,
                sector_type=value(sector,'sector_type') if sector else None,trade_date=reader.context['trade_date'],
                membership_verified=bool(member),status='READY' if ready else 'SOURCE_INCOMPLETE',
                href='/v4/research/sectors/'+sid if ready else None,source=cells[kind]))
    return dict(contract_id='R2_CURRENT_MEMBERSHIP_NAMED_RELATIONS_V1',trade_date=reader.context['trade_date'],
        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,items=rows,source_cells=cells,
        membership_source=reader.manifest['sources']['membership'],scope='CURRENT_PUBLISHED_RELATIONS_ONLY_NO_SUPPORT_ALGORITHM_OR_HISTORICAL_BASKET',
        owner_gap=[k for k,c in cells.items() if not c or c.get('quality')=='UNKNOWN'])

def explanation(reader,item):
    raw=value(item,'raw_qualification') or {};prewatch=raw.get('PREWATCH','UNKNOWN')
    presentation={}
    for name,fallback in [('why_now','transition_reasons'),('waiting_for','unknown_predicates'),('invalid_if',None),('hypothesis',None)]:
        source=name if name in item['fields'] else fallback
        cell=item['fields'].get(source) if source else None
        presentation[name]=dict(source_field=source,source=cell,
            basis='EXPLICIT_OWNER_FIELD' if source==name else 'OWNER_TRANSITION_REASONS' if name=='why_now' and cell else 'MISSING_PREDICATE_EVIDENCE_ONLY' if name=='waiting_for' and cell else 'OWNER_FIELD_NOT_BOUND',
            value=value(item,source) if cell else None)
    return reader.envelope(status='READY',item=item,membership_relations=membership_relations(reader,item),eligibility='NOT_ELIGIBLE' if prewatch=='FALSE' else 'ELIGIBLE' if prewatch=='TRUE' else 'UNKNOWN',
        satisfied=value(item,'matched_predicates') or [],not_satisfied=[],not_satisfied_reason='OWNER_FALSE_PREDICATE_LIST_NOT_PUBLISHED',
        indeterminate=value(item,'unknown_predicates') or [],not_implemented=value(item,'detector_statuses'),
        F={k:v for k,v in item['fields'].items() if k in ('close','ma5','ma10','ma20','ma60','atr14','pos20','pos60','rps5','rps20','amount','volume','amount_ratio20','volume_ratio20','turnover')},
        R={k:v for k,v in item['fields'].items() if k.endswith('_state') or k in ('core_participation_result','core_extension_risk')},
        H=value(item,'hypothesis') or [],hypothesis_reason='NO_BOUND_OWNER_HYPOTHESIS_OUTPUT_NO_UI_INFERENCE' if 'hypothesis' not in item['fields'] else None,
        waiting_for=value(item,'waiting_for') if 'waiting_for' in item['fields'] else value(item,'unknown_predicates'),
        why_now=value(item,'why_now') if 'why_now' in item['fields'] else value(item,'transition_reasons'),why_now_basis='OWNER_EMITTED_TRANSITION_REASONS',
        invalid_if=value(item,'invalid_if'),invalid_if_reason='OWNER_INVALIDATION_CONDITIONS_NOT_PUBLISHED' if 'invalid_if' not in item['fields'] else None,
        explanation_contract_id='R2_OWNER_EXPLANATION_PRESENTATION_V1',owner_explanations=presentation,
        owner_specific_debt=[dict(field=k,owner='V4_11_STATE' if k in ('waiting_for','invalid_if','why_now') else 'V4_13_PROFILE',reason='NO_EXPLICIT_OWNER_FIELD_PUBLISHED',fallback_basis=presentation[k]['basis']) for k in ('hypothesis','waiting_for','invalid_if','why_now') if k not in item['fields']])

def timeline(reader,item,query):
    """Expose only bound owner structure records, with field-local debts."""
    rows=[];debts=[]
    for field,kind in [('structure_events','STRUCTURE_EVENT'),('anchor_view_asof_t','ANCHOR')]:
        cell=item['fields'].get(field)
        if not cell or cell.get('quality')=='UNKNOWN' or cell.get('value') is None:
            debts.append(dict(field=field,owner='V4_12',reason=cell.get('reason') if cell else 'OWNER_FIELD_NOT_BOUND'))
            continue
        values=cell['value'] if isinstance(cell['value'],list) else [cell['value']]
        for entry in values:rows.append(dict(kind=kind,data=entry,source_field=field,source=cell))
    offset=int(query.get('offset',0));limit=int(query.get('limit',30))
    return reader.envelope(status='SOURCE_INCOMPLETE' if debts else 'READY' if rows else 'EMPTY_VALID',
        resource_type='stock_owner_timeline',items=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit,
        has_next=offset+limit<len(rows),owner_specific_debt=debts,contract_id='R2_STOCK_OWNER_TIMELINE_V1',
        scope='BOUND_OWNER_RECORDS_ONLY_NO_RECONSTRUCTED_EVENT_DATES')
