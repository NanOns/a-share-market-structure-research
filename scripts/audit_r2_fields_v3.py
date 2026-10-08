"""Independent 110-row source/UI/oracle inventory; never mass-admit placeholders."""
import bisect,collections,gzip,json,math,re,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.domain_views import objects,sector_view,home
from workbench_service.diagnostic_views import diagnostic
OUT=ROOT/'docs/evidence/r2_field_continuation_20261008'

ALIASES={
 'ma_structure':['ma_structure_state'],'relative_state':['relative_market_state','relative_sector_state'],
 'turnover_state':['turnover_state'],'risk':['core_price_damage','core_extension_risk'],
 'market_regime':['regime_ui'],'price':['open','high','low','close'],
 'ma':['ma5','ma10','ma20','ma60'],'atr_normalized_position':['bias20_atr','dist_high20_atr'],
 'relative':['rel_market_1','rel_market_3','rel_market_5'],
 'compression':['range_ratio','atr_ratio','vol_ratio'],'amount':['amount','amount_ratio5','amount_ratio20'],
 'turnover':['turnover'],'sector_facts':['primary_industry','supporting_concepts'],
 'anchors':['anchor_view_asof_t'],'structure_events':['structure_events'],
 'why_now':['why_now'],'waiting_for':['waiting_for'],'invalid_if':['invalid_if'],
 'anchor':['anchor_id'],'observation':['price_path']}

def main():
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes());reader=ProductionV4ResearchReader(ROOT,snapshot_authority=candidate['snapshot'])
    inventory=json.loads((ROOT/'docs/evidence/r2_repair_20261008/R2_PRODUCT_FIELD_COVERAGE.json').read_bytes())['rows']
    data={d:objects(reader,d) for d in ('stocks','sectors','focus')};focus=reader.manifest['domain_features']['focus']
    timeline=json.loads((OUT/'browser/focus_timeline_payload.json').read_bytes())
    assert timeline['context_token']==reader.token and timeline['resource_type']=='timeline'
    entity=timeline['items'][0]['entity_id']
    expected_events=[e for e in focus['events'] if e['entity_id']==entity]
    assert timeline['items']==expected_events and timeline['total']==len(expected_events)
    write(OUT/'TIMELINE_ORACLE.json',dict(result='PASS',entity=entity,event_comparisons=len(expected_events),
        source=reader.manifest['sources']['focus_operational'],browser=ref(OUT/'browser/focus_timeline_payload.json'),
        scope='CORRECTED_FOCUS_EVENTS_ONLY',strict_pit=False))
    sector=reader.manifest['domain_features']['sector'];factors=[json.loads(l) for l in gzip.open(ROOT/sector['factors']['path'],'rt',encoding='utf8')]
    rps_checks=0
    for horizon in (5,20):
        values=sorted(r['fields']['ret'+str(horizon)]['value'] for r in factors if r['fields']['ret'+str(horizon)]['value'] is not None)
        for row in factors:
            value=row['fields']['ret'+str(horizon)]['value'];actual=row['fields']['rps'+str(horizon)]['value']
            if value is None:assert actual is None;continue
            expected=100*(bisect.bisect_left(values,value)+0.5*(bisect.bisect_right(values,value)-bisect.bisect_left(values,value)-1))/(len(values)-1)
            assert math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-9);rps_checks+=1
    write(OUT/'RPS_ORACLE.json',dict(result='PASS',comparisons=rps_checks,universe=len(factors),
        formula='100*(less + 0.5*(equal-1))/(evaluable-1)',factors=sector['factors']))
    browser_stock=json.loads((OUT/'browser/stock_browser_rows.json').read_bytes());browser_sector=json.loads((OUT/'browser/width_browser_rows.json').read_bytes())
    labels=(ROOT/'src/workbench_service/static/research/labels.js').read_text(encoding='utf8')
    factor_lookup={r['security_id']:r for r in factors};ma_checks=0;atr_checks=0
    with sqlite3.connect((ROOT/reader.manifest['sources']['stock_series']['path']).as_uri()+'?mode=ro',uri=True) as db:
        for index,sample in enumerate(browser_stock):
            sid=sample['url'].split('/')[-1];factor=factor_lookup[sid];item=next(r for r in data['stocks'] if r['entity_id']==sid)
            bars=[json.loads(r[0]) for r in db.execute('SELECT payload FROM bars WHERE security=? AND day<=? ORDER BY day DESC LIMIT 60',(sid,reader.context['trade_date']))]
            assert len(bars)==60 and all(b['qfq_ohlc'] for b in bars)
            prices=[list(map(float,b['qfq_ohlc'])) for b in reversed(bars)]
            for n in (5,10,20,60):
                expected=sum(p[3] for p in prices[-n:])/n
                assert math.isclose(item['fields']['ma'+str(n)]['value'],expected,rel_tol=1e-12,abs_tol=1e-9);ma_checks+=1
            atr=sum(max(p[1]-p[2],abs(p[1]-previous[3]),abs(p[2]-previous[3])) for previous,p in zip(prices[-21:-1],prices[-20:]))/20
            assert math.isclose(factor['fields']['atr20']['value'],atr,rel_tol=1e-12,abs_tol=1e-9);atr_checks+=1
            item=next(r for r in data['stocks'] if r['entity_id']==sid)
            expected_bias=(prices[-1][3]-sum(p[3] for p in prices[-20:])/20)/atr
            expected_distance=(max(p[1] for p in prices[-21:-1])-prices[-1][3])/atr
            for field,expected in [('bias20_atr',expected_bias),('dist_high20_atr',expected_distance)]:
                assert math.isclose(item['fields'][field]['value'],expected,rel_tol=1e-12,abs_tol=1e-9)
            dom=(OUT/('browser/stock_'+str(index)+'_dom.txt')).read_text(encoding='utf8')
            for field in ('open','high','low','close','ma5','ma10','ma20','ma60','bias20_atr','dist_high20_atr'):
                label=re.search(r"\b"+field+r":'([^']+)'",labels).group(1)
                value=format(item['fields'][field]['value'],'.3f')
                assert 'row "'+label+' '+value+' 来源"' in dom,(sid,field,value)
    raw=json.loads((ROOT/reader.manifest['sources']['RAW_DAILY']['path']).read_bytes())['rows'];raw_lookup={r['security_id']:r for r in raw}
    raw_checks=0
    for item in data['stocks']:
        for field in ('open','high','low','close'):
            assert item['fields'][field]['value']==raw_lookup[item['entity_id']][field];raw_checks+=1
    write(OUT/'STOCK_FIELD_ORACLE.json',dict(result='PASS',actual_raw_comparisons=raw_checks,ma_windows=ma_checks,atr_windows=atr_checks,stock_samples=10,raw=reader.manifest['sources']['RAW_DAILY']))
    for sample in browser_stock:
        sid=sample['url'].split('/')[-1];item=next(r for r in data['stocks'] if r['entity_id']==sid)
        for field,label in [('close','收盘价'),('ma5','五会话均线'),('ma20','二十会话均线'),('rps5','五会话相对强度分位'),('rps20','二十会话相对强度分位')]:
            expected=label+format(item['fields'][field]['value'],'.3f')+'来源'
            assert expected in sample['rows'],(sid,field,expected)
    width=json.loads((OUT/'WIDTH_ORACLE.json').read_bytes());known_width={r['sector_id']:r for r in width['comparisons']}
    from urllib.parse import unquote
    for sample in browser_sector:
        sid=unquote(sample['url'].split('/')[-1]);expected='二十会话均线宽度'+format(known_width[sid]['value'],'.3f')+'来源'
        assert sample['row']==[expected]
    rows=[]
    for old in inventory:
        row={k:old[k] for k in ('section','feature','production_required','owner')};feature=row['feature'];section=row['section'];domain='sectors' if section=='62C/64' else 'stocks' if section=='62D/65' else 'focus' if section=='62F' else None
        row.update(owner_source_ready=False,ui_rendered=False,numeric_oracle=False,browser_pass=False,product_pass=False,
            source_fields=ALIASES.get(feature,[feature]),known_rows=0,unknown_rows=0,api=old['api'],ui=old['ui'],debt_reason='NO_EXPLICIT_BOUND_OWNER_OUTPUT')
        if domain:
            keys=row['source_fields'];present=0;reasons=collections.Counter()
            for item in data[domain]:
                cells=[item['fields'].get(k) for k in keys]
                if any(c is not None for c in cells):present+=1
                ready=all(c and c.get('value') is not None and c.get('value') not in ('UNKNOWN','NOT_IMPLEMENTED') and c.get('quality') not in ('UNKNOWN','NOT_IMPLEMENTED') for c in cells)
                if ready:row['known_rows']+=1
                else:
                    row['unknown_rows']+=1
                    for c in cells:
                        reason=(c.get('reason') or 'OWNER_NULL_OR_NON_READY_VALUE') if c else 'OWNER_FIELD_NOT_PUBLISHED'
                        reasons[json.dumps(reason,ensure_ascii=False) if isinstance(reason,(list,dict)) else reason]+=1
            row.update(owner_source_ready=row['known_rows']>0,source_present_rows=present,reason_counts=dict(reasons))
            if feature=='ma20_width' and domain=='sectors':row.update(ui_rendered=True,numeric_oracle=True,browser_pass=True)
            if domain=='stocks' and feature in ('price','ma','atr_normalized_position','rps5','rps20'):
                row.update(ui_rendered=True,browser_pass=True,numeric_oracle=True)
            if row['owner_source_ready']:row['debt_reason']='FIELD_SCOPE_UI_ORACLE_OR_BROWSER_NOT_FULLY_PROVEN'
            elif present:row['debt_reason']='BOUND_OWNER_FIELD_UNAVAILABLE_SEE_EXACT_REASON_COUNTS'
        if domain=='focus' and feature in ('anchor','observation','outcome_status'):
            key={'anchor':'anchors','observation':'observations','outcome_status':'outcomes'}[feature]
            records=[v for e in focus['episodes'] for v in e[key]]
            row.update(owner_source_ready=bool(records),source_present_rows=len(records),known_rows=len(records),api='/api/v4/focus/{id}/'+key,
                debt_reason='TYPED_SOURCE_EXISTS_FIELD_SPECIFIC_BROWSER_PROOF_STILL_REQUIRED')
        if domain=='stocks' and feature=='focus_timeline':
            row.update(owner_source_ready=bool(focus['events']),source_present_rows=len(focus['events']),api='/api/v4/focus/{id}/timeline',
                ui_rendered=True,browser_pass=True,numeric_oracle=True,
                admission_scope='CORRECTED_FOCUS_EVENTS_ONLY_NOT_STRUCTURE_EVENTS',
                debt_reason='CORRECTED_FOCUS_TIMELINE_TYPED_ORACLE_AND_BROWSER_SCOPE_SEPARATE_FROM_STRUCTURE_EVENTS')
        if domain=='sectors' and feature in ('overlap','unique_member_share'):
            overlap=sector_view(reader,data['sectors'][0],'overlap',{'limit':200})
            row.update(owner_source_ready=True,source_present_rows=overlap['total'],api='/api/v4/sectors/{id}/overlap',debt_reason='CURRENT_MEMBERSHIP_SOURCE_READY_FULL_FIELD_BROWSER_ORACLE_PENDING')
        if section=='62G':
            center=reader.manifest['domain_features']['market_center'];key=feature.replace('facts_events','facts_events')
            payload=center.get(key)
            ready=payload is not None and (not isinstance(payload,dict) or payload.get('status','READY')=='READY')
            row.update(owner_source_ready=ready,api='/api/v4/market/'+key.replace('_','-'),debt_reason='REAL_CENTER_FIELD_SCOPE_UI_ORACLE_BROWSER_PENDING' if ready else 'OWNER_SOURCE_NOT_AVAILABLE_NO_INTRADAY_OR_APPROVED_FACT_EVENT_SOURCE')
        if section=='62H/68' and feature in ('health','sources','contracts','jobs','legacy','shadow'):
            payload=diagnostic(reader,feature);row.update(owner_source_ready=payload is not None,api='/api/v4/diagnostics/'+feature,debt_reason='BOUNDED_DIAGNOSTIC_SOURCE_EXISTS_BROWSER_SCOPE_PENDING')
        if section=='66/67':
            authority=reader.manifest['domain_features'].get('replay',{})
            ready=bool(authority) and feature in ('corrected_history','stock_previous','stock_market','date_token','followup')
            row.update(owner_source_ready=ready,debt_reason='CORRECTED_SCOPE_EXISTS_FIELD_SPECIFIC_BROWSER_PENDING' if ready else 'STRICT_PIT_OR_FROZEN_MEMBER_OR_LOO_OWNER_NOT_ADMITTED')
        if section=='62A/62B/63':
            payload=home(reader);key={'navigation':'counts','four_axes':'market','rotation_changes':'rotations','sector_changes':'sector_changes','stock_changes':'changes','risk_changes':'risks','member_preview':'top_sectors'}.get(feature)
            ready=bool(payload.get(key))
            row.update(owner_source_ready=ready,debt_reason='ACTUAL_HOME_SCOPE_EXISTS_FIELD_SPECIFIC_BROWSER_PENDING' if ready else 'NO_ACCEPTED_EVENT_OR_NATIVE_HISTORY_FOR_THIS_HOME_SECTION')
        row['product_pass']=all(row[k] for k in ('owner_source_ready','ui_rendered','numeric_oracle','browser_pass'))
        if row['product_pass']:row['debt_reason']=None
        rows.append(row)
    assert len(rows)==110
    write(OUT/'FIELD_INVENTORY_V3.json',dict(contract_id='R2_FIELD_ADMISSION_V3',inventory_count=110,rows=rows,
        counts={k:sum(bool(r[k]) for r in rows) for k in ('owner_source_ready','ui_rendered','numeric_oracle','browser_pass','product_pass')},
        context_token=reader.token,full_product_pass=False,strict_pit=False,
        audit_id='AUD_R2_110_FIELD_INDEPENDENT_ADMISSION',next_stage='UNPROVEN_FIELD_OWNER_AND_BROWSER_ADMISSION_REMAIN_OPEN'))
    print(json.dumps(dict(rows=110,source_ready=sum(r['owner_source_ready'] for r in rows),field_pass=sum(r['product_pass'] for r in rows),rps_comparisons=rps_checks)))

if __name__=='__main__':main()
