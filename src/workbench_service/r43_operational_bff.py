"""R43_OPERATIONAL_RESEARCH_BFF_V1: existing product envelopes over exact owners.
Missing domains fail explicitly; no cross-date research fallback is permitted.
"""
from urllib.parse import unquote
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.tdx_member_retro_r43 import normalized_frozen_rows
from .production_v4 import compact_cell

CONTRACT='R43_OPERATIONAL_RESEARCH_BFF_V1'

def owner_cell(value,ref,field,day):
    """Retain explicit owner quality, infer only for owner scalar/state values."""
    if isinstance(value,dict) and 'value' in value:
        cell=dict(value)
        if 'quality' not in cell:
            cell['quality']=cell.get('quality_state') or ('UNKNOWN' if cell['value'] is None or cell['value']=='UNKNOWN' or cell.get('unknown_reason') else 'KNOWN')
    else:
        quality=value.get('quality',value.get('quality_state')) if isinstance(value,dict) else None
        reason=value.get('reason',value.get('unknown_reason')) if isinstance(value,dict) else None
        unavailable=value is None or value=='UNKNOWN'
        cell=dict(value=value,quality=quality or ('UNKNOWN' if unavailable else 'KNOWN'),reason=reason or ('OPERATIONAL_OWNER_UNKNOWN' if unavailable else None))
    return compact_cell(cell,ref,field,day)
class OperationalResearchBFF:
    def __init__(self,api,legacy):
        self.api=api;self.legacy=legacy
    def envelope(self,day,**payload):
        c=self.api.context();c.update(trade_date=day,accepted_trade_date='2026-10-08',release_id=self.api.token,model_namespace='TDX_INDUSTRY_CONCEPT',data_updated_at=self.api.candidate['membership_observed_at'],scoped_release=True,operational_release_scope=['stocks_daily','sectors_current_facts','market_current','focus_read_corrected','diagnostics'],domain_readiness={'focus':{'earliest_valid_date':'2026-09-28'}},read_source_label='通达信最新成员回算；非历史当日成员',bff_contract_id=CONTRACT)
        return dict(context=c,context_token=self.api.token,production_accepted=c.get('production_accepted',False),**payload)
    def counts(self,day):
        admitted=getattr(self.api,'domain_disposition',None)
        return {d:(None if admitted is not None and admitted.get({'stocks':'profile','sectors':'sector','focus':'forward'}[d])!='ACCEPTED' and not getattr(self.api,'user_authorized_cutover',False) else len(self.project(d,day))) for d in ('stocks','sectors','focus')}
    def source(self,domain,day):return self.api.read(domain,day,self.api.token).get('rows')
    def missing(self,day,path,reason='NO_OPERATIONAL_COMPATIBILITY_OWNER_FOR_ROUTE'):
        return 200,self.envelope(day,status='SOURCE_INCOMPLETE',reason=reason,code=reason,domain=path,gap=dict(domain=path,state='SOURCE_INCOMPLETE',reason=reason),items=[],total=0,offset=0,limit=30,has_next=False,legacy_diagnostic='/api/v4/original-0930/'+path,legacy_trade_date='2026-09-30',mixed_date_fallback=False)
    def project(self,domain,day):
        cache_key=('bff',day,domain)
        if cache_key in self.api.cache:return self.api.cache[cache_key]
        native={'stocks':'profile','sectors':'sector','focus':'forward','events':'events','sources':'diagnostic'}.get(domain,domain)
        raw=self.source(native,day)
        if domain=='sources':raw=[dict(entity_id='R43:'+day,fields={'row_count':len(self.source('raw',day)),'quality':'RECONSTRUCTED'})]
        if domain=='focus':
            raw=raw.get('episodes',[]) if isinstance(raw,dict) else []
            latest={}
            for x in raw:latest[x['entity_id']]=x
            raw=list(latest.values())
        if not isinstance(raw,list):return []
        ref=self.api.candidate['owners'][day][native];result=[]
        member_rows=normalized_frozen_rows(rows(self.api.root,self.api.snapshot['memberships'])) if domain in ('stocks','sectors') else []
        identities={r['security_id']:r for r in rows(self.api.root,self.api.snapshot['identity_source']) if r.get('security_id')}
        leaf_by_security={}
        for m in member_rows:
            if m.get('sector_type')=='INDUSTRY' and m.get('industry_level')=='LEAF' and m.get('primary_industry_rank_eligible'):leaf_by_security.setdefault(m.get('security_id'),[]).append(m['sector_id'])
        quote={r['security_id']:r for r in self.source('raw',day)} if domain=='stocks' else {}
        d2={r['entity_id']:r for r in self.source('focus',day)} if domain=='stocks' else {}
        rotation={r['sector_id']:r for r in self.source('rotation',day)} if domain=='sectors' else {}
        member_names={r['sector_id']:r.get('sector_name',r['sector_id']) for r in member_rows} if domain=='sectors' else {}
        for r in raw:
            identity=r.get('security_id',r.get('sector_id',r.get('entity_id')))
            if not identity:continue
            fs=dict(r.get('fields',{}))
            field_refs={}
            field_paths={k:'fields.'+k for k in fs}
            if domain=='stocks':
                fs.update(r.get('derived_fields',{}));fs.update(r.get('states',{}));fs.update({k:v for k,v in quote.get(identity,{}).items() if k in ('open','high','low','close','amount','volume')})
                field_paths.update({k:'derived_fields.'+k for k in r.get('derived_fields',{})})
                field_paths.update({k:'states.'+k for k in r.get('states',{})})
                fs.update({k:d2.get(identity,{}).get(k,'UNKNOWN') for k in ('scenario','final_eligibility','maturity','health','validity','tracking')})
                fs['relative_sector_state']=r.get('relative_sector_state',r.get('states',{}).get('relative_sector_state'))
                leaves=leaf_by_security.get(identity,[])
                fs['primary_industry']=leaves[0] if len(leaves)==1 else dict(value=None,quality='UNKNOWN',reason='NO_UNIQUE_TDX_LEAF_INDUSTRY')
                field_refs.update({k:self.api.candidate['owners'][day]['raw'] for k in ('open','high','low','close','amount','volume')})
                field_refs.update({k:self.api.candidate['owners'][day]['focus'] for k in ('scenario','final_eligibility','maturity','health','validity','tracking')})
                field_refs.update(primary_industry=self.api.snapshot['memberships'],relative_sector_state=self.api.candidate['owners'][day]['relative_sector'])
                field_paths.update(primary_industry='sector_id via TDX_MEMBER_ROW_NORMALIZATION_V2: unique mapped INDUSTRY LEAF',relative_sector_state='value')
            elif domain=='sectors':
                rot=rotation.get(identity,{}).get('rotation',{})
                fs.update(sector_type=r.get('sector_type'),member_count=r.get('current_member_count'),output_state=rot.get('output_state','UNKNOWN'),prior_rotation_state=rot.get('prior_rotation_state','UNKNOWN'))
                if self.api.candidate.get('external_review_contract') and getattr(self.api,'domain_disposition',{}).get('rotation')!='ACCEPTED':
                    for k in ('output_state','prior_rotation_state'):fs[k]=dict(value=fs[k] if getattr(self.api,'user_authorized_cutover',False) else None,quality='VALIDATION_ONGOING',reason='FULL_ROTATION_NOT_INDEPENDENTLY_ACCEPTED')
                field_refs.update({k:self.api.candidate['owners'][day]['rotation'] for k in ('output_state','prior_rotation_state')})
                field_paths.update(output_state='rotation.output_state',prior_rotation_state='rotation.prior_rotation_state',member_count='current_member_count',sector_type='sector_type')
                for target,source in [('sector_rs20','sector_rs20_pct'),('sector_rs5','sector_rs5_pct'),('seed_width','base_seed_width_adjusted')]:
                    if source in fs:fs[target]=fs[source];field_paths[target]='fields.'+source
            elif domain=='focus':
                last=(r.get('observations') or [{}])[-1];fs.update({k:r.get(k,last.get(k,'UNKNOWN')) for k in ('T0','event','membership','validity','path_resolution','best_confirmed_state','end_date')})
            elif not fs:fs={k:v for k,v in r.items() if k not in ('security_id','entity_id','trade_date')}
            fields={k:owner_cell(v,field_refs.get(k,ref),field_paths.get(k,k),day) for k,v in fs.items()}
            symbol=r.get('symbol') or identities.get(identity,{}).get('source_security_key') or identity
            result.append(dict(entity_id=identity,security_id=identity if domain in ('stocks','focus') else None,symbol=symbol,display_name=member_names.get(identity,symbol),display_name_scope='SOURCE_SECTOR_NAME' if domain=='sectors' else 'BOUND_IDENTITY_CODE_NAME_NOT_AVAILABLE',symbol_source=self.api.snapshot['identity_source'] if domain in ('stocks','focus') else None,trade_date=day,fields=fields,source=ref,field_owner_bindings=field_refs,knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP',AS_RECORDED=False,PIT_ELIGIBLE=False,survivorship_bias_risk=True))
        self.api.cache[cache_key]=result;return result
    def page(self,domain,day,q,entity=None,sector=None):
        data=self.project(domain,day)
        if entity:data=[r for r in data if entity in (r['entity_id'],r['symbol'])]
        if sector:
            native=next((r for r in self.source('sector',day) if r['sector_id']==sector),None)
            data=[r for r in data if r['entity_id'] in set(native.get('member_ids',[]))] if native else []
        needle=q.get('q','').strip().casefold()
        if len(needle)>80:raise ValueError('INVALID_QUERY_BOUND')
        if needle:data=[r for r in data if any(needle in str(r[k]).casefold() for k in ('entity_id','display_name','symbol'))]
        for key,field in [('state','scenario' if domain=='stocks' else 'output_state'),('type','sector_type'),('maturity','maturity'),('health','health'),('rotation','output_state'),('quality','quality'),('eligibility','final_eligibility')]:
            if q.get(key):data=[r for r in data if str(r['fields'].get(field,{}).get('value'))==q[key]]
        sort=q.get('sort','id');keys=sort.split(',')
        allowed={'id','name','symbol','state','sector_rs20_pct','sector_rs5_pct','sector_rs20','sector_rs5','breadth_ret1','ma20_width','participation_proxy','member_count','close','rps5','rps20'}
        if len(keys)>4 or any(k.lstrip('-') not in allowed for k in keys):raise ValueError('INVALID_SORT_FIELD')
        data=sorted(data,key=lambda r:r['entity_id'])
        for s in reversed(keys):
            k=s.lstrip('-');field={'id':'entity_id','name':'display_name','symbol':'symbol'}.get(k)
            data=sorted(data,key=lambda r:(r.get(field) is None,str(r.get(field,''))) if field else (r['fields'].get(k,{}).get('value') is None,r['fields'].get(k,{}).get('value') or 0),reverse=s.startswith('-'))
        offset=int(q.get('offset',0));limit=int(q.get('limit',30))
        if not 1<=limit<=200 or not 0<=offset<=1000000:raise ValueError('INVALID_QUERY_BOUND')
        selected=data[offset:offset+limit]
        return self.envelope(day,domain=domain,status='READY' if data else 'EMPTY_VALID',items=selected,total=len(data),offset=offset,limit=limit,has_next=offset+limit<len(data),gap=None)
    def get(self,path,q):
        parts=[unquote(p) for p in path.removeprefix('/api/v4/').split('/') if p];day=q.get('trade_date','2026-10-08')
        if day not in self.api.candidate['dates']:raise ValueError('TARGET_DATE_NOT_GRANTED')
        if parts not in (['context'],['current','context']) and q.get('context_token')!=self.api.token:raise ValueError('CONTEXT_TOKEN_MISMATCH')
        allowed={'q','state','limit','offset','sort','context_token','trade_date','release_id','model_namespace','type','maturity','health','rotation','quality','eligibility','period','price_basis','as_of','view','left','right','mode','snapshot_token','followup'}
        if set(q)-allowed:raise ValueError('UNKNOWN_PARAMETER')
        for k,v in [('release_id',self.api.token),('model_namespace','TDX_INDUSTRY_CONCEPT')]:
            if k in q and q[k]!=v:raise ValueError('CONTEXT_TOKEN_MISMATCH')
        name=parts[0] if parts else ''
        admission=getattr(self.api,'domain_disposition',None)
        admitted_domain={'stocks':'profile','sectors':'sector','focus':'forward','diagnostics':'diagnostic','sources':'diagnostic','data-sources':'diagnostic'}.get(name,name)
        if admission is not None and admitted_domain in admission and admission[admitted_domain]!='ACCEPTED' and not getattr(self.api,'user_authorized_cutover',False):
            status,response=self.missing(day,'/'.join(parts),'DOMAIN_NOT_INDEPENDENTLY_ACCEPTED')
            response['validation_state']=admission[admitted_domain]
            return status,response
        if name=='stocks.csv':
            return 501,self.envelope(day,status='SOURCE_INCOMPLETE',code='OPERATIONAL_CSV_EXPORT_NOT_BOUND',reason='OPERATIONAL_CSV_EXPORT_NOT_BOUND',mixed_date_fallback=False)
        if name=='current':
            parts=parts[1:]
            if parts:parts[0]={'entity':'stocks','sector':'sectors','summary':'events','health':'sources','cohort':'forward'}.get(parts[0],parts[0])
            return self.get('/api/v4/'+'/'.join(parts),q)
        offset=int(q.get('offset',0));limit=int(q.get('limit',30))
        if not 1<=limit<=200 or not 0<=offset<=1000000:raise ValueError('INVALID_QUERY_BOUND')
        if name=='context':return 200,self.envelope(day,status='READY',counts=self.counts(day),gaps=[dict(domain=k,state='SOURCE_INCOMPLETE',validation_state=v) for k,v in getattr(self.api,'domain_disposition',{}).items() if v!='ACCEPTED']+[dict(domain='forward/statistics',state='SOURCE_INCOMPLETE',reason='NO_FORWARD_ENROLLMENT_STATISTICS_OWNER')])
        if name=='home':
            market=self.source('market',day);axes=market.get('axes',{});axes.update(trend_axis=market.get('trend',{}).get('trend_axis','UNKNOWN'))
            return 200,self.envelope(day,status='READY',counts=self.counts(day)|{'radar':None,'forward':None},market=dict(row=axes,raw=market,sources=market.get('input_bindings'),regime=market.get('regime',{}),comparison_trade_date=market.get('comparison_trade_date')),gaps=[dict(domain='forward',state='SOURCE_INCOMPLETE')],rotations=[],sector_changes=[],events=[])
        if name in ('diagnostics','sources','data-sources'):
            if len(parts)>1:return self.missing(day,'/'.join(parts),'NO_OPERATIONAL_DIAGNOSTIC_SUBPAGE_OWNER')
            return 200,self.envelope(day,status='READY',items=self.project('sources',day),total=1,offset=0,limit=30,has_next=False,sources=self.api.candidate['owners'][day],gaps=[dict(domain='forward/statistics',reason='NO_FORWARD_ENROLLMENT_STATISTICS_OWNER')],publication_scope=self.api.candidate['production_eligible_scope'],code_contract=CONTRACT)
        if name=='focus' and len(parts)>1:
            if parts[1]!='events' and (not parts[1].startswith('SEC-') or (len(parts)>2 and parts[2] not in ('episodes','timeline','anchors','observations','outcomes'))):
                return self.missing(day,'/'.join(parts),'NO_OPERATIONAL_FOCUS_SUBPAGE_OWNER')
            forward=self.source('forward',day)
            if parts[1]=='events':data=forward.get('events',[])
            else:
                episodes=[e for e in forward.get('episodes',[]) if e['entity_id']==parts[1]]
                kind=parts[2] if len(parts)>2 else 'episodes';data=episodes if kind in ('episodes','timeline') else [x for e in episodes for x in e.get(kind,[])]
            offset=int(q.get('offset',0));limit=int(q.get('limit',30))
            return 200,self.envelope(day,status='READY' if data else 'EMPTY_VALID',items=data[offset:offset+limit],total=len(data),offset=offset,limit=limit,has_next=offset+limit<len(data),source=self.api.candidate['owners'][day]['forward'],contract_id=CONTRACT,legacy_history='NOT_MIXED_WITH_OPERATIONAL')
        if name in ('stocks','sectors','focus','events'):
            if name=='stocks' and len(parts)==3 and parts[2] in ('profile','evidence','why-not','why-not-prewatch'):
                page=self.page('stocks',day,q,entity=parts[1])
                if not page['items']:return 404,self.envelope(day,status='NOT_FOUND',code='ENTITY_NOT_FOUND')
                item=page['items'][0];fields=item['fields'];relations=[]
                for member in normalized_frozen_rows(rows(self.api.root,self.api.snapshot['memberships'])):
                    if member.get('security_id')!=item['entity_id']:continue
                    if member['sector_type']=='INDUSTRY' and member['industry_level']!='LEAF':continue
                    relations.append(dict(role='primary_industry' if member['sector_type']=='INDUSTRY' else 'supporting_concepts',entity_id=member['sector_id'],display_name=member['sector_name'],sector_type=member['sector_type'],href='/v4/research/sectors/'+member['sector_id'],source=self.api.snapshot['memberships']))
                fkeys={'open','high','low','close','amount','volume'}
                debt=[dict(field=k,reason='NO_OPERATIONAL_EXPLANATION_OWNER') for k in ('why_now','waiting_for','invalid_if','hypothesis')]
                explanations={k:dict(value=None,source=dict(quality='UNKNOWN',reason='NO_OPERATIONAL_EXPLANATION_OWNER'),basis='MISSING_OWNER') for k in ('why_now','waiting_for','invalid_if','hypothesis')}
                return 200,self.envelope(day,status='READY',item=item,F={k:v for k,v in fields.items() if k in fkeys},R={k:v for k,v in fields.items() if k not in fkeys},membership_relations=dict(items=relations,owner_gap=[] if relations else ['primary_industry','supporting_concepts'],source=self.api.snapshot['memberships'],membership_mode='TDX_LATEST_MEMBER_RETRO_V1',PIT_ELIGIBLE=False),owner_explanations=explanations,owner_specific_debt=debt)
            if len(parts)>2 and name=='sectors' and parts[2]=='members':return 200,self.page('stocks',day,q,sector=parts[1])
            if len(parts)>2:return self.missing(day,'/'.join(parts))
            page=self.page(name,day,q,entity=parts[1] if len(parts)>1 else None)
            if len(parts)>1:
                if not page['items']:return 404,self.envelope(day,status='NOT_FOUND',code='ENTITY_NOT_FOUND')
                page['item']=page['items'][0]
            return 200,page
        if name in ('raw','core','profile','relative_sector','rotation','lifecycle','special_phase','sector','forward','market','diagnostic','prewatch','seed') and len(parts)==1:
            payload=self.api.dispatch('/api/v4/'+name+'?trade_date='+day+'&context_token='+self.api.token+'&limit='+q.get('limit','100')+'&offset='+q.get('offset','0'))
            return 200,self.envelope(day,**{k:v for k,v in payload.items() if k not in ('context_token','context')})
        return self.missing(day,'/'.join(parts))

