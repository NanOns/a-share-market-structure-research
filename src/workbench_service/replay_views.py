"""FP12 strict temporal boundary and explicitly separate corrected comparisons."""
import json,sqlite3
from datetime import date,datetime,timezone
from .current_v4_context import canonical,digest,SourceInvalid
from .stock_views import chart
from .domain_views import value

NAMESPACE='FP12_RECONSTRUCTED_CORRECTED_V1'
def cutoff(day):return datetime.fromisoformat(day+'T23:59:59.999999+08:00')
def timestamp(text):
    if not isinstance(text,str):raise ValueError('KNOWLEDGE_TIME_NOT_PROVEN')
    t=datetime.fromisoformat(text.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('NAIVE_KNOWLEDGE_TIME_FORBIDDEN')
    return t
def temporal_projection(snapshot,day):
    """A source needs affirmative recorded evidence and all three temporal locks."""
    if snapshot.get('AS_RECORDED') is not True or snapshot.get('first_available_proven') is not True:return []
    try:
        if timestamp(snapshot['model_known_at'])>cutoff(day):return []
    except (KeyError,TypeError,ValueError):return []
    result=[]
    for item in snapshot.get('items',[]):
        fields={}
        for key,cell in item['fields'].items():
            try:
                admitted=(date.fromisoformat(cell['effective_date'])<=date.fromisoformat(day) and timestamp(cell['known_at'])<=cutoff(day) and timestamp(cell['publication_date'])<=cutoff(day) and bool(cell['model_namespace']))
            except (KeyError,TypeError,ValueError):admitted=False
            if admitted:fields[key]=cell
        if fields:result.append(dict(entity_id=item['entity_id'],symbol=item.get('symbol'),fields=fields))
    return result

def selected(reader,query):
    authority=reader.manifest.get('domain_features',{}).get('replay')
    day=query.get('as_of',reader.context['trade_date']);date.fromisoformat(day)
    if day>reader.context['trade_date']:raise ValueError('FUTURE_AS_OF_FORBIDDEN')
    if not authority:return None,None,day
    binding=next((x for x in authority['catalog'] if x['as_of']==day),None)
    if not binding:return authority,None,day
    token='fp12-'+binding['snapshot']['sha256']
    if query.get('snapshot_token') not in (None,token):raise SourceInvalid('CONTEXT_CONFLICT:SNAPSHOT_DATE_OR_VERSION')
    return authority,binding,day

def read_snapshot(reader,binding):
    from .current_v4_context import CurrentAcceptedV4Reader
    return CurrentAcceptedV4Reader(reader.root)._read(binding['snapshot'])
def envelope(reader,binding,day,**payload):
    context=dict(reader.context,trade_date=day,accepted_trade_date=day,model_namespace=NAMESPACE,source_mode='FROZEN_DATE_VIEW',publication_id=binding['snapshot']['sha256'] if binding else None,release_id=binding['snapshot']['sha256'] if binding else None)
    return dict(operational_context=reader.context,context=context,context_token='fp12-'+binding['snapshot']['sha256'] if binding else None,**payload)
def replay(reader,query):
    authority,binding,day=selected(reader,query);view=query.get('view','frozen')
    if view not in ('frozen','corrected'):raise ValueError('INVALID_REPLAY_VIEW')
    catalog=authority['catalog'] if authority else []
    if not binding:return envelope(reader,binding,day,status='PIT_NOT_AVAILABLE',items=[],total=0,catalog=catalog,reason='NO_BOUND_DATE_SNAPSHOT',result_hash=digest(canonical([day,'NO_BOUND_DATE_SNAPSHOT'])))
    snapshot=read_snapshot(reader,binding);items=temporal_projection(snapshot,day) if view=='frozen' else snapshot['items']
    if view=='frozen' and not items:return envelope(reader,binding,day,status='PIT_NOT_AVAILABLE',items=[],total=0,catalog=catalog,reason=snapshot['reason'],result_hash=digest(canonical([day,[],snapshot['reason']])),AS_RECORDED=False)
    needle=query.get('q','').casefold();entity=query.get('left');items=[x for x in items if (not entity or entity in (x['entity_id'],x['symbol'],x['symbol'].split('.')[-1])) and (not needle or needle in (x['symbol'].casefold(),x['entity_id'].casefold()) or x['symbol'].casefold().startswith(needle))]
    offset=int(query.get('offset',0));limit=int(query.get('limit',30));total=len(items)
    followup=None;history=None
    if view=='corrected' and entity and items:
        bars=chart(reader,dict(entity_id=items[0]['entity_id']),{'price_basis':'RAW','limit':200})['items']
        history=dict(items=[b for b in bars if b['trade_date']<=day][-120:],price_basis='RAW',as_of=day,source=authority['sources']['series'],AS_RECORDED=False)
    if query.get('followup'):
        if query['followup']!='1' or not entity:raise ValueError('FOLLOWUP_REQUIRES_EXPLICIT_ENTITY')
        if view!='corrected':raise ValueError('UNADMITTED_FROZEN_FOLLOWUP_SOURCE')
        sid=items[0]['entity_id'] if items else None
        bars=chart(reader,dict(entity_id=sid),{'limit':200})['items'] if sid else [];by={x['trade_date']:x for x in bars};sessions=authority['session_dates'];i=sessions.index(day);targets=[]
        for n in (1,3,5):
            target=sessions[i+n] if i+n<len(sessions) else None;bar=by.get(target);targets.append(dict(horizon=n,target_trade_date=target,status='OBSERVED_AFTER_T0' if bar else 'PENDING_NO_ACCEPTED_LATER_SESSION',bar=bar))
        followup=dict(scope='POST_T0_OBSERVATIONS_EXCLUDED_FROM_T0_HASH',AS_RECORDED=False,items=targets,coordinate_date=reader.context['trade_date'])
    history_values={k:history[k] for k in ('items','price_basis','as_of')} if history else None
    return envelope(reader,binding,day,status='READY',items=items[offset:offset+limit],total=total,offset=offset,limit=limit,has_next=offset+limit<total,catalog=catalog,view=view,AS_RECORDED=view=='frozen',knowledge_lineage=snapshot['knowledge_lineage'],result_hash=digest(canonical(dict(items=items,history=history_values))),sources=snapshot['sources'],history=history,followup=followup,warning='事后重建对照，不能作为当时可知的 PIT 判断' if view=='corrected' else None)

def cell(value,day,source,unit='RATIO',reason=None):return dict(value=value,effective_date=day,known_at=None,known_at_status='NOT_PROVEN_AT_T0',publication_date=source.get('publication_date'),publication_time_status='NOT_BOUND' if not source.get('publication_date') else 'BOUND',model_namespace=NAMESPACE,source_digest=source.get('sha256'),quality='UNKNOWN' if value is None else 'KNOWN',unit=unit,reason=reason)
def market_reference(reader):
    for row in reader.query('stocks',{'limit':200})['items']:
        ret=value(row,'ret1');rel=value(row,'rel_market_1')
        if ret is not None and rel is not None:return ret-rel
    return None
def compare(reader,query):
    authority,binding,day=selected(reader,query)
    if query.get('view','frozen')=='frozen':return envelope(reader,binding,day,status='PIT_NOT_AVAILABLE',items=[],reason='NO_FIRST_AVAILABLE_AT_T0_PROOF',result_hash=digest(canonical([day,'PIT_NOT_AVAILABLE'])))
    if query.get('view')!='corrected':raise ValueError('INVALID_REPLAY_VIEW')
    if not binding:return envelope(reader,binding,day,status='PIT_NOT_AVAILABLE',items=[],reason='NO_BOUND_DATE_SNAPSHOT')
    mode=query.get('mode','stock-stock');allowed=('stock-stock','stock-previous','stock-market','stock-sector','sector-market','sector-three','sector-lifecycle')
    if mode not in allowed:raise ValueError('INVALID_COMPARE_MODE')
    left=query.get('left','');right=query.get('right','');snapshot=read_snapshot(reader,binding)
    if mode.startswith('sector'):
        if day!=reader.context['trade_date'] or mode in ('sector-three','sector-lifecycle'):return envelope(reader,binding,day,status='PIT_NOT_AVAILABLE',items=[],reason='DATED_PRIOR_MEMBERSHIP_OR_STAGE_OUTPUT_NOT_BOUND_CURRENT_MEMBERS_NOT_BACKFILLED')
        a=reader.query('sectors',{},entity=left)['items']
        if not a:return envelope(reader,binding,day,status='EMPTY_VALID',items=[],reason='SECTOR_NOT_FOUND')
        sector=value(a[0],'sector_rs1');market=market_reference(reader)
        return envelope(reader,binding,day,status='SOURCE_INCOMPLETE' if market is None else 'READY',items=[dict(name='板块当前成员收益中位数',cell=cell(sector,day,authority['sources']['sector'])),dict(name='市场参考收益',cell=cell(market,day,authority['sources']['market_reference_factors'],reason='MARKET_RETURN_NOT_BOUND' if market is None else None))],comparison_policy='CURRENT_MEMBERSHIP_DIAGNOSTIC_NOT_FROZEN_T0_BENCHMARK',AS_RECORDED=False,window='PREVIOUS_ACCEPTED_SESSION_TO_SELECTED_DATE',coordinate_date=reader.context['trade_date'])
    candidates=[x for x in snapshot['items'] if left in (x['entity_id'],x['symbol'],x['symbol'].split('.')[-1])]
    if not candidates:raise ValueError('LEFT_STOCK_NOT_IN_SELECTED_SNAPSHOT')
    item=candidates[0];sid=item['entity_id'];bars=chart(reader,dict(entity_id=sid),{'price_basis':'QFQ','limit':200})['items'];bars=[x for x in bars if x['trade_date']<=day];calendar_days=authority['session_dates'];start=calendar_days[calendar_days.index(day)-1] if calendar_days.index(day)>0 else None
    by={x['trade_date']:x for x in bars};end=by.get(day);prev=by.get(start);ret=(end['close']/prev['close']-1) if end and prev and end['close'] and prev['close'] else None
    rows=[dict(name=item['symbol']+' · 同一复权坐标区间收益',cell=cell(ret,day,authority['sources']['series'],reason='PREVIOUS_ACCEPTED_SESSION_OR_ADJUSTMENT_MISSING' if ret is None else None))]
    if mode=='stock-stock':
        other=next((x for x in snapshot['items'] if right in (x['entity_id'],x['symbol'],x['symbol'].split('.')[-1])),None)
        if not other:raise ValueError('RIGHT_STOCK_NOT_IN_SELECTED_SNAPSHOT')
        bs=chart(reader,dict(entity_id=other['entity_id']),{'price_basis':'QFQ','limit':200})['items'];ob={x['trade_date']:x for x in bs if x['trade_date']<=day};a=ob.get(start);b=ob.get(day);r=b['close']/a['close']-1 if a and b and a['close'] and b['close'] else None;rows.append(dict(name=other['symbol']+' · 同窗收益',cell=cell(r,day,authority['sources']['series'])))
    elif mode=='stock-previous':
        prior=next((x for x in authority['catalog'] if x['as_of']==start),None);previous=read_snapshot(reader,prior) if prior else None;old=next((x for x in previous['items'] if x['entity_id']==sid),None) if previous else None
        rows.extend([dict(name='当期状态',fields={k:v for k,v in item['fields'].items() if v['unit']=='ENUM'}),dict(name='前日状态',fields={k:v for k,v in old['fields'].items() if v['unit']=='ENUM'} if old else {})])
    elif mode=='stock-market':
        market=market_reference(reader) if day==reader.context['trade_date'] else None;rows.append(dict(name='起点 Universe 市场等权参考 · 同窗',cell=cell(market,day,authority['sources']['market_reference_factors'],reason='HISTORICAL_MARKET_OWNER_NOT_BOUND' if market is None else None)))
    elif mode=='stock-sector':
        rows.extend([dict(name='T0冻结研究板块收益基准',cell=cell(None,day,authority['sources']['membership'],reason='NO_BOUND_FROZEN_BASKET_FOR_SELECTED_T0_AND_STOCK')),dict(name='当前 LOO 支持板块当日解释（独立列）',fields=reader.query('stocks',{},entity=sid)['items'][0]['fields'].get('relative_sector_state') if day==reader.context['trade_date'] else None,reason='CURRENT_EXPLANATION_NEVER_HISTORICAL_T0_BENCHMARK')])
    payload=dict(status='READY' if all(x.get('cell',{}).get('value') is not None for x in rows if 'cell' in x) else 'SOURCE_INCOMPLETE',items=rows,mode=mode,start_date=start,end_date=day,price_basis='FP07_TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',coordinate_date=reader.context['trade_date'],AS_RECORDED=False,warning='事后重建比较；不代表 T0 当时已知。状态比较与收益口径分别标注。',source_snapshot=binding['snapshot']['sha256'])
    return envelope(reader,binding,day,**payload,result_hash=digest(canonical(payload)))
