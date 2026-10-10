"""Dated read adapter over accepted owners. No permission or immutable head changes."""
from pathlib import Path
from urllib.parse import unquote
from collections import Counter
from copy import deepcopy
import json, sqlite3, gzip
from .operational_successor_bff_v1 import OperationalSuccessorBFFV1
from .r43_operational_bff import owner_cell
from .stock_views import aggregate
from .domain_views import CHANGE_EVENTS, RISK_EVENTS, ROTATIONS
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.validation_cohort_read_contract_r3 import read_statistics, read_authorized_statistics
from .research_hypotheses_r3 import competing_explanations

CONTRACT='CORE_PRODUCT_BFF_R1'

class CoreProductBFFR1(OperationalSuccessorBFFV1):
    def focus_projection(self,day):
        authority=self.api.root/'config/core_product_focus_read_authority_r2.json'
        if not authority.exists() or day!=self.api.candidate['accepted_trade_date']:return None
        key=('focus-read-r2',day)
        if key not in self.api.cache:
            manifest=json.loads(checked(self.api.root,json.loads(authority.read_bytes())['manifest']).read_bytes())
            if manifest['T0']!=day or manifest['head']['sha256']!=self.api.token:return None
            checked(self.api.root,manifest['head']);checked(self.api.root,manifest['implementation'])
            for ref in manifest['source_bindings'].values():checked(self.api.root,ref)
            projection=json.loads(gzip.decompress(checked(self.api.root,manifest['projection']).read_bytes()))
            self.api.cache[key]=(manifest,projection)
        return self.api.cache[key]

    def source(self,domain,day):
        pack=self.focus_projection(day) if domain=='forward' else None
        if not pack:return super().source(domain,day)
        projection=deepcopy(pack[1]);projection['events']=[e for e in projection['events'] if e['trade_date']==day]
        return projection

    def get(self,path,query):
        code,data=self._get_product(path,query)
        day=query.get('trade_date',self.api.candidate['accepted_trade_date']);pack=self.focus_projection(day)
        if path=='/api/v4/focus' and code==200:
            episodes=self.source('forward',day)['episodes'];active={e['entity_id'] for e in episodes if e.get('end_date') is None}
            stocks={r['entity_id']:r for r in self.project('stocks',day)};groups=Counter();unknown=0
            for sid in active:
                sector=stocks.get(sid,{}).get('fields',{}).get('primary_industry',{}).get('value')
                if sector is None:unknown+=1
                else:groups[sector]+=1
            data['sector_exposure']=dict(denominator=len(active),unknown_industry=unknown,items=[dict(sector_id=sid,count=count,share=count/len(active)) for sid,count in sorted(groups.items(),key=lambda x:(-x[1],x[0]))],source=self.api.snapshot['memberships'],scope='Unique active research objects under latest reconstructed primary industry; not holdings, not a probability')
        if pack:
            old=self.api.candidate['owners'][day]['forward'];new=pack[0]['projection']
            def rebind(value):
                if isinstance(value,dict):
                    if value.get('path')==old['path'] and value.get('sha256')==old['sha256']:return deepcopy(new)
                    return {k:(new['sha256'] if k=='source_digest' and v==old['sha256'] else rebind(v)) for k,v in value.items()}
                if isinstance(value,list):return [rebind(v) for v in value]
                return value
            data=rebind(data);data['context']['focus_read_projection_contract']='CORE_PRODUCT_FOCUS_READ_R2'
            data['context']['focus_read_projection_external_acceptance']='NOT_GRANTED'
            data['context']['focus_write']=False
        return code,data
    def identity_records(self):
        key=('product-identity',)
        if key not in self.api.cache:
            head=json.loads((self.api.root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
            ref=head['identity'];data=json.loads(checked(self.api.root,ref).read_bytes())
            self.api.cache[key]=(data['records'],ref)
        return self.api.cache[key]

    def pack(self, day):
        key=('product-pack',day)
        if key not in self.api.cache:
            authority=self.api.root/'config/core_product_read_authority_r1.json'
            if not authority.exists():return None
            manifest=json.loads(checked(self.api.root,json.loads(authority.read_bytes())['manifest']).read_bytes())
            head=self.api.root/manifest['head']['path']
            if manifest['T0']!=day or head.read_bytes()!=checked(self.api.root,manifest['head']).read_bytes():return None
            checked(self.api.root,manifest['history_index'])
            facts=json.loads(checked(self.api.root,manifest['market_facts']).read_bytes())
            self.api.cache[key]=(manifest,facts)
        return self.api.cache[key]

    def envelope(self,day,**payload):
        response=super().envelope(day,**payload)
        response['context']['bff_contract_id']=CONTRACT
        response['context']['product_engineering_acceptance']='EXTERNAL_PENDING'
        response['context']['focus_write']=False
        return response

    def project(self,domain,day):
        key=('product-project',day,domain)
        if key in self.api.cache:return self.api.cache[key]
        data=deepcopy(super().project(domain,day))
        authority=json.loads((self.api.root/'config/v4_display_names_authority_v1.json').read_bytes())
        name_source=authority['source'];names=json.loads(checked(self.api.root,name_source).read_bytes())
        cores={r['security_id']:r for r in self.source('core',day)} if domain=='stocks' else {}
        d2={r['entity_id']:r for r in self.source('focus',day)} if domain=='stocks' else {}
        profiles={r['security_id']:r for r in self.source('profile',day)} if domain=='stocks' else {}
        sector_native={r['sector_id']:r for r in self.source('sector',day)} if domain=='sectors' else {}
        identities,identity_ref=self.identity_records() if domain=='stocks' else ([],None)
        aliases={}
        for record in identities:
            aliases.setdefault(record['security_id'],set()).update(str(record.get(k,'')) for k in ('symbol','source_security_key','security_name'))
        registries={r['field_id']:r for filename in ('v4_03_field_registry_v1.json','v4_04_field_registry_v2.json','v4_08_sector_field_registry_r5.json') for r in json.loads((self.api.root/'config'/filename).read_bytes())['fields']}
        for row in data:
            if domain in ('stocks','focus','events'):
                code=row['symbol'].upper();name=names['stocks'].get(code)
                if name:row.update(display_name=name,display_name_scope='OBSERVED_DISPLAY_ONLY_NOT_PIT',display_name_source=name_source,display_name_observed_at=names['observed_at'])
            if domain=='stocks':
                row['search_aliases']=sorted(aliases.get(row['entity_id'],set()))
                row['alias_source']=identity_ref
                for k,v in cores.get(row['entity_id'],{}).get('fields',{}).items():
                    row['fields'].setdefault(k,owner_cell(v,self.api.candidate['owners'][day]['core'],'fields.'+k,day))
                state=d2.get(row['entity_id'],{})
                for k in ('effective_event','transition_reasons','unknown_predicates','detector_statuses','prewatch_status'):
                    if k in state:row['fields'][k]=owner_cell(state[k],self.api.candidate['owners'][day]['focus'],k,day)
            if domain=='focus':row['focus_scope']='RECONSTRUCTED_ENGINEERING_TRACKING_READ; USER_MANUAL_WRITE_DISABLED; NOT_VALIDATION_COHORT'
            if domain=='sectors':
                native=sector_native[row['entity_id']];ref=self.api.candidate['owners'][day]['sector']
                for key,value,field in [('member_count',len(set(native['member_ids'])),'member_ids (unique)'),('source_member_count',native['current_member_count'],'current_member_count'),('unmapped_count',native['unmapped_count'],'unmapped_count'),('quoted_count',native['quoted_count'],'quoted_count')]:
                    row['fields'][key]=owner_cell(dict(value=value,quality='KNOWN',unit='members'),ref,field,day)
                for key in ('maturity','health'):
                    row['fields'].setdefault(key,dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',reason='DATED_SECTOR_D2_'+key.upper()+'_OWNER_NOT_PRESENT',as_of=day,unit='state',source=None,field=None))
            original={}
            if domain=='stocks':
                original.update(cores.get(row['entity_id'],{}).get('fields',{}))
                original.update(profiles.get(row['entity_id'],{}).get('derived_fields',{}));original.update(profiles.get(row['entity_id'],{}).get('states',{}))
            elif domain=='sectors':original.update(sector_native.get(row['entity_id'],{}).get('fields',{}))
            for field,cell in row['fields'].items():
                alias={'sector_rs5':'sector_rs5_pct','sector_rs20':'sector_rs20_pct','seed_width':'base_seed_width_adjusted'}.get(field,field) if domain=='sectors' else field
                rawcell=original.get(alias,{})
                unit=registries.get(alias,{}).get('unit')
                if unit:cell['unit']=unit
                if domain=='stocks' and field in ('open','high','low','close','amount','volume'):cell['unit']='SHARES' if field=='volume' else 'CNY'
                for k in ('window_start_trade_date','window_end_trade_date','actual_count','calendar_span','suspended_count','contract_id','parameter_set_id','input_digest','output_digest','evidence','n','k'):
                    if k in rawcell:cell[k]=rawcell[k]
                if domain=='stocks' and field in original:cell['adjustment_basis']='TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE' if unit in ('adjusted_price','return_ratio') or field.startswith(('ret','ma','atr','prior_high','prior_low')) else cell.get('adjustment_basis')
        if domain=='events':
            groups={}
            for row in data:
                identity=(row['entity_id'],row['fields'].get('event_type',{}).get('value'),row['fields'].get('created_trade_date',{}).get('value'))
                groups.setdefault(identity,[]).append(row)
            for group in groups.values():
                group.sort(key=lambda r:str(r['fields'].get('anchor_id',{}).get('value')))
                for index,row in enumerate(group,1):
                    row['fields']['anchor_ordinal']=owner_cell(dict(value=index,quality='KNOWN',unit='count'),self.api.candidate['owners'][day]['events'],'same-stock same-date same-type anchors sorted by anchor_id',day)
                    row['anchor_group_count']=len(group)
        self.api.cache[key]=data
        return data

    def page(self,domain,day,q,entity=None,sector=None):
        """Filter the full dated collection; missing sort values always remain last."""
        data=self.project(domain,day)
        if entity:data=[r for r in data if entity in (r['entity_id'],r['symbol']) or entity in r.get('search_aliases',[])]
        if sector:
            native=next((r for r in self.source('sector',day) if r['sector_id']==sector),None)
            members=set(native.get('member_ids',[])) if native else set();data=[r for r in data if r['entity_id'] in members]
        needle=q.get('q','').strip().casefold()
        if len(needle)>80:raise ValueError('INVALID_QUERY_BOUND')
        if needle:data=[r for r in data if any(needle in str(v).casefold() for v in [r['entity_id'],r['display_name'],r['symbol'],*r.get('search_aliases',[])])]
        for key,field in [('state','scenario' if domain=='stocks' else 'output_state'),('type','sector_type'),('maturity','maturity'),('health','health'),('rotation','output_state'),('quality','quality'),('eligibility','final_eligibility')]:
            if q.get(key):data=[r for r in data if str(r['fields'].get(field,{}).get('value'))==q[key]]
        keys=q.get('sort','id').split(',');allowed={'id','name','symbol','state','output_state','sector_rs20_pct','sector_rs5_pct','sector_rs20','sector_rs5','breadth_ret1','breadth_ret5','breadth_ret20','ma20_width','participation_proxy','member_count','close','rps5','rps20'}
        if len(keys)>4 or any(k.lstrip('-') not in allowed for k in keys):raise ValueError('INVALID_SORT_FIELD')
        data=sorted(data,key=lambda r:r['entity_id'])
        for spec in reversed(keys):
            k=spec.lstrip('-');top={'id':'entity_id','name':'display_name','symbol':'symbol'}.get(k)
            field=('scenario' if domain=='stocks' else 'output_state') if k=='state' else k
            value=lambda r:r.get(top) if top else r['fields'].get(field,{}).get('value')
            known=[r for r in data if value(r) is not None];unknown=[r for r in data if value(r) is None]
            data=sorted(known,key=value,reverse=spec.startswith('-'))+unknown
        code,response=self.paged(day,data,q,domain=domain,gap=None)
        if needle and not data and domain=='stocks':
            records,ref=self.identity_records();matches=[r for r in records if any(needle==str(r.get(k,'')).casefold() or needle==str(r.get(k,'')).split('.')[-1].casefold() for k in ('symbol','source_security_key','security_name','security_id'))]
            response['query_explanation']=dict(status='OUT_OF_UNIVERSE' if matches else 'IDENTITY_NOT_FOUND',reason='身份源存在，但不在当前已接受研究证券池；当前池不覆盖北交所等排除范围。' if matches else '当前证券池与已冻结身份源未找到该代码或名称。',source=ref,identities=matches)
        return response

    def paged(self,day,items,q,**payload):
        offset=int(q.get('offset',0));limit=int(q.get('limit',30))
        if not 0<=offset<=1000000 or not 1<=limit<=200:raise ValueError('INVALID_QUERY_BOUND')
        return 200,self.envelope(day,status='READY' if items else 'EMPTY_VALID',items=items[offset:offset+limit],total=len(items),offset=offset,limit=limit,has_next=offset+limit<len(items),**payload)

    def chart(self,day,sid,q):
        period=q.get('period','D');basis=q.get('price_basis','QFQ')
        if period not in ('D','W','M') or basis not in ('RAW','QFQ'):raise ValueError('INVALID_CHART_QUERY')
        pack=self.pack(day)
        if not pack:return self.missing(day,'stocks/'+sid+'/chart','DATED_HISTORY_INDEX_NOT_BOUND')
        manifest,_=pack
        path=self.api.root/manifest['history_index']['path']
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            value=db.execute('SELECT payload FROM history WHERE security=?',(sid,)).fetchone()
        if not value:return 404,self.envelope(day,status='NOT_FOUND',code='ENTITY_NOT_FOUND')
        bars=[]
        for b in json.loads(value[0]):
            if b['trade_date']>day:raise ValueError('FUTURE_CHART_BAR')
            prices=b['raw_ohlc' if basis=='RAW' else 'qfq_ohlc']
            bars.append(dict(trade_date=b['trade_date'],**dict(zip(('open','high','low','close'),prices or [None]*4)),volume=b['volume'],amount=b['amount'],quality='KNOWN' if prices else 'UNKNOWN',reason='BLOCKED_ADJUSTMENT_EVENT' if not prices else None))
        data=aggregate(bars,period)
        if period!='D' and data:
            owner_domain='period_raw' if basis=='RAW' else 'period_adjusted'
            formal=next((r for r in self.source(owner_domain,day) if r['security_id']==sid and r['period_type']==('WEEKLY' if period=='W' else 'MONTHLY')),None)
            if formal:
                data[-1].update(period_status=formal['period_status'],calendar_count=formal['calendar_count'],suspended_count=formal['suspended_count'],formal_period_source=self.api.candidate['owners'][day][owner_domain])
        for i,b in enumerate(data):
            for n in (5,20,60):
                w=data[max(0,i-n+1):i+1];b['ma'+str(n)]=sum(x['close'] for x in w)/n if len(w)==n and all(x['close'] is not None for x in w) else None
        offset=int(q.get('offset',0));limit=int(q.get('limit',120))
        if not 0<=offset<=1000000 or not 1<=limit<=200:raise ValueError('INVALID_QUERY_BOUND')
        end=max(0,len(data)-offset);start=max(0,end-limit)
        return 200,self.envelope(day,status='READY' if data else 'EMPTY_VALID',items=data[start:end],total=len(data),offset=offset,limit=limit,has_next=start>0,period=period,price_basis=basis,as_of=day,volume_unit='SHARES',amount_unit='CNY',source=manifest['source_bindings']['history'],series_index=manifest['history_index'],adjustment='TDX_NATIVE_AFFINE_T0_COORDINATE' if basis=='QFQ' else 'NONE',historical_membership='RECONSTRUCTED_NOT_STRICT_PIT',earliest_valid_date=bars[0]['trade_date'] if bars else None)

    def _get_product(self,path,query):
        q=dict(query);q.setdefault('trade_date',self.api.candidate['accepted_trade_date']);day=q['trade_date']
        # Base route validation applies before any product-specific read.
        super().get('/api/v4/context',q)
        if path!='/api/v4/context' and q.get('context_token')!=self.api.token:raise ValueError('CONTEXT_TOKEN_MISMATCH')
        p=[unquote(x) for x in path.removeprefix('/api/v4/').split('/')]
        if p[0]=='candidates' and (p[1:]==['cohort'] or len(p)==3 and p[1]=='sectors'):
            from .candidate_research_read_v2 import read_candidates
            data=read_candidates(self.api.root,head=self.api.candidate,token=self.api.token,day=day,
                                 sector_id=p[2] if len(p)==3 else None)
            return 200,self.envelope(day,status='READY',candidate_research=data,
                contract_id='OPERATIONAL_CANDIDATE_DISPLAY_READ_V2',production=False,formal_consumer_enabled=False)
        if p[0] in ('stocks','focus') and len(p)>1 and p[1] not in ('events',):
            matches=sorted({r['entity_id'] for r in self.project('stocks',day) if p[1] in (r['entity_id'],r['symbol'],r['symbol'].split('.')[-1],*r.get('search_aliases',[]))})
            if len(matches)==1:
                p[1]=matches[0];path='/api/v4/'+'/'.join(p)
        if p[0]=='stocks' and len(p)==3 and p[2]=='chart':return self.chart(day,p[1],q)
        if p[0]=='stocks' and len(p)==3 and p[2] in ('profile','why-not','why-not-prewatch','evidence'):
            code,data=super().get(path,q)
            if code!=200:return code,data
            item=data['item'];fields=item['fields'];eligibility=fields.get('final_eligibility',{}).get('value')
            classified='NOT_ELIGIBLE' if eligibility=='FALSE' else 'ELIGIBLE' if eligibility=='TRUE' else 'NOT_IMPLEMENTED' if 'NOT_IMPLEMENTED' in str(fields.get('detector_statuses',{})) else 'UNKNOWN'
            data['selection_explanation']=dict(status=classified,final_eligibility=fields.get('final_eligibility'),detector_statuses=fields.get('detector_statuses'),unknown_predicates=fields.get('unknown_predicates'),transition_reasons=fields.get('transition_reasons'),meaning='资格状态来自真实 reducer；不在列表不代表无画像；未知不等于未满足')
            for key,field in [('why_now','transition_reasons'),('waiting_for','unknown_predicates')]:
                if field in fields:data['owner_explanations'][key]=dict(value=fields[field]['value'],source=fields[field],basis='OWNER_TRANSITION_REASONS' if key=='why_now' else 'MISSING_PREDICATE_EVIDENCE_ONLY')
            data['key_prices']={k:fields[k] for k in ('ma20','prior_high20','prior_low20','atr20') if k in fields}
            data['hypothesis_scope']='情景解释不证明洗盘、吸筹、出货或账户资金行为'
            hypothesis_fields=deepcopy(fields)
            adjusted_ref=self.api.candidate['owners'][day].get('adjusted')
            adjusted=next((r for r in (self.source('adjusted',day) or []) if r['security_id']==p[1]),None) if adjusted_ref else None
            if adjusted:
                hypothesis_fields['close']=owner_cell(dict(value=adjusted.get('close'),quality='KNOWN' if adjusted.get('adjustment_readiness')=='READY' else 'UNKNOWN'),adjusted_ref,'close',day)
                hypothesis_fields['close']['adjustment_basis']='TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE'
            data['competitive_hypotheses']=competing_explanations(hypothesis_fields)
            return code,data
        if p[0]=='stocks' and len(p)==3 and p[2]=='timeline':
            history=[]
            for d in self.api.candidate['published_sessions']:
                if d>day:continue
                for r in self.source('events',d):
                    if r.get('security_id')==p[1] and r.get('created_trade_date','9999')<=day:history.append(dict(r,source=self.api.candidate['owners'][d]['events']))
            unique={}
            for row in history:unique[(row.get('event_id'),row.get('observation_revision'))]=row
            history=sorted(unique.values(),key=lambda r:(r['created_trade_date'],r.get('event_id',''),r.get('observation_revision','')))
            return self.paged(day,history,q,contract_id='STRUCTURE_OWNER_TIMELINE_READ_R2',dedup_key=['event_id','observation_revision'],PIT_ELIGIBLE=False)
        if p[0]=='sectors' and len(p)==2:
            code,data=super().get(path,q)
            if code!=200:return code,data
            row=next((r for r in self.source('rotation',day) if r['sector_id']==p[1]),None)
            rotation=row.get('rotation',{}) if row else {}
            data['why_now']=dict(prior_state=rotation.get('prior_rotation_state'),current_state=rotation.get('output_state'),
                reason_codes=rotation.get('reason_codes',[]),predicates=rotation.get('predicates',{}),
                fields={k:rotation.get('fields',{}).get(k) for k in ('dq5','breadth_delta1','breadth_delta3','ma20_delta3','base_seed_width_adjusted')},
                source=self.api.candidate['owners'][day]['rotation'],scope='Observed reconstructed rule facts; not strict PIT or independently accepted full episode reduction')
            return code,data
        if p[0]=='sectors' and len(p)==3 and p[2] in ('timeline','rotation-timeline'):
            data=[]
            for d in self.api.candidate['published_sessions']:
                if d>day:continue
                row=next((r for r in self.source('sector',d) if r['sector_id']==p[1]),None)
                rot=next((r for r in self.source('rotation',d) if r['sector_id']==p[1]),None)
                if row:data.append(dict(trade_date=d,fields=row['fields'],rotation=rot.get('rotation') if rot else None,source=self.api.candidate['owners'][d]['sector'],rotation_source=self.api.candidate['owners'][d]['rotation'],member_set_asof=row['member_set_asof'],PIT_ELIGIBLE=False))
            return self.paged(day,data,q,contract_id='DATED_CORRECTED_SECTOR_TIMELINE_READ_R1',historical_membership='LATEST_RECONSTRUCTED_NOT_STRICT_PIT',earliest_valid_date=data[0]['trade_date'] if data else None,full_rotation_validation='NOT_GRANTED')
        if p[0]=='sectors' and len(p)==3 and p[2]=='members':
            code,data=super().get(path,q);native=next((r for r in self.source('sector',day) if r['sector_id']==p[1]),None)
            if native:data['membership_coverage']=dict(source_member_count=native['current_member_count'],mapped_member_count=len(set(native['member_ids'])),unmapped_count=native['unmapped_count'],quoted_count=native['quoted_count'],source=self.api.candidate['owners'][day]['sector'],meaning='完整已映射研究成员；未映射来源记录不冒造证券身份')
            return code,data
        if p[0]=='sectors' and len(p)==3 and p[2]=='overlap':
            sectors=self.source('sector',day);target=next((r for r in sectors if r['sector_id']==p[1]),None)
            if not target:return 404,self.envelope(day,status='NOT_FOUND',code='ENTITY_NOT_FOUND')
            ids=set(target['member_ids']);shared=set();data=[];names={r['entity_id']:r['display_name'] for r in self.project('sectors',day)}
            for other in sectors:
                if other['sector_id']==p[1] or other['sector_type']!='THEME':continue
                members=set(other['member_ids']);intersection=ids&members
                if not intersection:continue
                shared|=intersection;union=ids|members;sid=other['sector_id']
                data.append(dict(sector_id=sid,display_name=names[sid],intersection_count=len(intersection),union_count=len(union),jaccard=len(intersection)/len(union),overlap_share=len(intersection)/len(ids),href='/v4/research/sectors/'+sid))
            data.sort(key=lambda r:(-r['jaccard'],r['sector_id']))
            return self.paged(day,data,q,unique_share=len(ids-shared)/len(ids) if ids else None,member_count=len(ids),source=self.api.candidate['owners'][day]['sector'],contract_id='TDX_UNIQUE_MEMBER_JACCARD_READ_R1',PIT_ELIGIBLE=False)
        if p[0]=='focus' and len(p)>=2 and p[1].startswith('SEC-'):
            episodes=[e for e in self.source('forward',day)['episodes'] if e['entity_id']==p[1]];kind=p[2] if len(p)>2 else 'episodes'
            if kind=='episodes':data=episodes
            elif kind=='timeline':data=[dict(o,episode_id=e['episode_id'],entity_id=e['entity_id']) for e in episodes for o in e['observations']]
            elif kind in ('anchors','observations','outcomes'):data=[dict(o,episode_id=e['episode_id'],entity_id=e['entity_id']) for e in episodes for o in e.get(kind,[])]
            else:return self.missing(day,'/'.join(p),'FOCUS_RESOURCE_NOT_IMPLEMENTED')
            return self.paged(day,data,q,source=self.api.candidate['owners'][day]['forward'],contract_id='FOCUS_LAYERED_DATED_READ_R1',focus_scope='RECONSTRUCTED_READ_ONLY_NOT_VALIDATION_COHORT',write_authorized=False,PIT_ELIGIBLE=False)
        if p[0]=='market' and len(p)==2:
            pack=self.pack(day)
            if not pack:return self.missing(day,'/'.join(p),'DATED_MARKET_FACT_PACK_NOT_BOUND')
            manifest,facts=pack;kind=p[1]
            if kind=='breadth':return 200,self.envelope(day,status='READY',data=facts['breadth'],source=facts['sources'],contract_id=facts['contract_id'])
            if kind=='indices':return self.paged(day,facts['indices'],q,source=facts['sources']['package'])
            if kind=='limits':return self.paged(day,facts['limits']['rows'],q,counts=facts['limits']['counts'],source=facts['sources']['limits_0'])
            if kind=='ladders':return self.paged(day,facts['ladders'],q,source={k:v for k,v in facts['sources'].items() if k.startswith('limits_')},intraday_touch='NOT_OBSERVABLE_FROM_DAILY')
        if path=='/api/v4/home':
            code,data=super().get(path,q);fw=self.source('forward',day);events=fw['events'];stocks={r['entity_id']:r for r in self.project('stocks',day)}
            # Explicit owner events only. NEW maps to Focus NEW, not PREWATCH/confirmation.
            changes=[]
            for e in events:
                if e.get('event') in ('NEW','UPGRADED','WEAKENED','INVALIDATED','EXITED','REENTERED') and e['entity_id'] in stocks:
                    row=deepcopy(stocks[e['entity_id']]);row['fields'].update(effective_event=owner_cell(e['event'],self.api.candidate['owners'][day]['forward'],'events.event',day),trade_date=owner_cell(day,self.api.candidate['owners'][day]['forward'],'events.trade_date',day));changes.append(row)
            priority={'INVALIDATED':0,'EXITED':1,'WEAKENED':2,'UPGRADED':3,'REENTERED':4,'NEW':5}
            changes.sort(key=lambda r:(priority[r['fields']['effective_event']['value']],r['entity_id']))
            changes=list({r['entity_id']:r for r in changes}.values())
            sectors=self.project('sectors',day);native={r['sector_id']:r for r in self.source('sector',day)}
            rotations=[r for r in sectors if r['fields']['output_state']['value'] in ROTATIONS and r['fields']['output_state']['value']!=r['fields']['prior_rotation_state']['value']]
            rotations.sort(key=lambda r:(0 if r['fields']['output_state']['value'] in ('ROTATION_OUT','ROTATION_FAILED') else 1,-(r['fields'].get('sector_rs5',{}).get('value') or 0),r['entity_id']))
            covered=set();cards=[]
            for row in rotations[:10]:
                members=set(native[row['entity_id']]['member_ids']);related=[r for r in changes if r['entity_id'] in members];fresh=[r for r in related if r['entity_id'] not in covered]
                covered.update(r['entity_id'] for r in related)
                cards.append(dict(item=row,member_previews=related[:5],member_total=len(members),net_information_count=len(fresh),change_counts=dict(Counter(r['fields']['effective_event']['value'] for r in related))))
            independent=[r for r in changes if r['entity_id'] not in covered]
            data.update(changes=independent[:30],change_total=len(independent),risks=[r for r in changes if r['fields']['effective_event']['value'] in RISK_EVENTS][:30],net_information_count=len(changes),persistent_count=sum(e.get('event')=='PERSISTENT' for e in events),change_scope='EXPLICIT_FOCUS_EVENTS_AND_ROTATION_OWNER_DELTAS; FULL_STRUCTURE_CHANGE_DEBT_OPEN',sector_changes=cards,sector_change_total=len(rotations),rotations=rotations[:10],rotation_total=len(rotations),source_bindings=dict(stock_changes=self.api.candidate['owners'][day]['forward'],sector_changes=self.api.candidate['owners'][day]['rotation']),rotation_validation='VALIDATION_ONGOING; NOT_INDEPENDENTLY_ACCEPTED')
            data['gaps']=[g for g in data['gaps'] if g['domain'] not in ('home/changes','home/risks','home/net-information')]
            return code,data
        if p[0]=='diagnostics' and len(p)==2 and p[1] in ('sources','health','contracts','fep'):
            if p[1]=='fep':return self.missing(day,'/'.join(p),'DATED_FEP_MODEL_RESULT_NOT_PRESENT')
            health=[]
            if p[1]=='health':
                for domain in ('stocks','sectors','focus'):
                    rows=self.project(domain,day);keys=sorted({k for r in rows for k in r['fields']});unknown={};qualities={}
                    for key in keys:
                        cells=[r['fields'].get(key,{}) for r in rows];qualities[key]=dict(Counter(c.get('quality','FIELD_MISSING') for c in cells))
                        count=sum(c.get('value') in (None,'UNKNOWN') or c.get('quality') in ('UNKNOWN','NOT_IMPLEMENTED','SOURCE_INCOMPLETE','PENDING') for c in cells)
                        if count:unknown[key]=count
                    health.append(dict(module=domain,record_count=len(rows),as_of=day,unknown_fields=unknown,field_quality_counts=qualities,quality_rule='Null, UNKNOWN literal, explicit unavailable quality; reconstructed known values remain separately identified'))
            return 200,self.envelope(day,status='READY',items=health,sources=self.api.candidate['owners'][day],contracts=self.api.candidate.get('accepted_algorithm_bindings'),amount_authority='NATIVE_TDX_CNY; BAOSTOCK_DIFFERENCE_AUDIT_OPEN',PIT_ELIGIBLE=False)
        if p==['diagnostics','jobs']:
            if self.legacy is None or not hasattr(self.legacy,'status'):return self.missing(day,'/'.join(p),'RUNTIME_OPERATIONS_STATUS_PROVIDER_NOT_BOUND')
            return 200,self.envelope(day,status='READY',operations=self.legacy.status(),source='/api/operations/status',scope='REQUEST_TIME_RUNTIME_STATUS; NOT_DATED_FACTOR_OWNER',items=[])
        if p==['diagnostics','legacy']:
            policy=json.loads((self.api.root/'config/v4_legacy_release_scope_v1.json').read_bytes())
            return 200,self.envelope(day,status='READY',items=[dict(legacy='旧版研究摘要',current='独立历史入口，保留原日期',href='/v4/legacy-summary'),dict(legacy='旧版 V4 历史读域',current='2026-09-30 独立上下文',href='/api/v4/original-0930/context')],scope='NAVIGATION_CATALOG_ONLY; NOT_CURRENT_FACTS',policy=policy,source='config/v4_legacy_release_scope_v1.json')
        if p==['diagnostics','shadow']:
            policy=json.loads((self.api.root/'config/v4_17_shadow_ui_source_v1.json').read_bytes())
            return 200,self.envelope(day,status='READY',capability_status=policy['status'],items=[],policy=policy,source='config/v4_17_shadow_ui_source_v1.json',href='/v4/shadow',scope='CAPABILITY_DIAGNOSTIC_ONLY; NO_REAL_SHADOW_DATA')
        if p[0] in ('replay','compare'):
            if p[0]=='replay':return self.missing(day,'replay','STRICT_PIT_FIRST_AVAILABLE_EVIDENCE_NOT_PRESENT')
            mode=q.get('mode','');left=q.get('left');right=q.get('right');asof=q.get('as_of',day)
            if asof not in self.api.candidate['published_sessions']:raise ValueError('TARGET_DATE_NOT_GRANTED')
            if mode not in ('stock-stock','sector-sector','stock-market','sector-market'):raise ValueError('COMPARE_MODE_NOT_IMPLEMENTED')
            domain='stocks' if mode.startswith('stock') else 'sectors';match=lambda r,key:key in (r['entity_id'],r['symbol'],r['symbol'].split('.')[-1])
            a=next((r for r in self.project(domain,asof) if match(r,left)),None)
            b=next((r for r in self.project(domain,asof) if match(r,right)),None) if mode.endswith(('stock','sector')) else self.source('market',asof)
            if not a or not b:return self.missing(day,'compare','COMPARE_OBJECT_NOT_PRESENT')
            return 200,self.envelope(day,status='READY',left=a,right=b,mode=mode,as_of=asof,PIT_ELIGIBLE=False,comparison_scope='CORRECTED_RECONSTRUCTED; NOT_STRICT_PIT',items=[],total=0)
        if path in ('/api/v4/forward','/api/v4/forward/statistics'):
            ref=self.api.candidate['owners'][day].get('validation_cohort')
            owner=None
            if ref:
                owner=json.loads(checked(self.api.root,ref).read_bytes())
                if owner.get('contract_id')!='VALIDATION_COHORT_READ_R3_V2' or owner.get('trade_date')!=day:
                    raise ValueError('COHORT_OWNER_CONTRACT_OR_DATE_MISMATCH')
            if owner:
                statistics=read_authorized_statistics(self.api.root,
                    accepted_head={'path':'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','sha256':self.api.token},
                    owner_binding=ref,trade_date=day)
            else:
                statistics=read_statistics(None,cutoff=None,trade_date=day)
            return 200,self.envelope(day,status='READY' if owner else 'SOURCE_INCOMPLETE',data=statistics,
                source=ref,contract_id='VALIDATION_COHORT_STATISTICS_BFF_R3_V1',
                reason=None if owner else 'NO_AUTHORIZED_COHORT_OWNER',
                focus_is_validation_cohort=False,write_authorized=False,PIT_ELIGIBLE=False)
        if path=='/api/v4/forward/fep':
            from workbench_analysis.fep_e5.admission import current_gate
            gate=current_gate(self.api.root)
            return 200,self.envelope(day,status='SOURCE_INCOMPLETE',reason='MODEL_OR_PERMISSION_NOT_READY',
                contract_id=gate['contract_id'],source=None,reason_text='；'.join(gate['reason_text']),
                data=dict(model_version=None,prediction_revision=None,permission_gate='MODEL_OR_PERMISSION_NOT_READY',
                    required_grant_key=['scope_id','target_id','horizon','feature_contract_id','model_set_id','model_revision','capability'],
                    capabilities={k:'NOT_GRANTED' for k in ('SHADOW_INFERENCE','DESCRIPTIVE_DISPLAY','MODEL_DISPLAY','PRIORITY_USE')},
                    prediction=None,training_authorized=False,focus_write_authorized=False,priority_v1_unchanged=True,
                    admission_gate=gate))
        if path=='/api/v4/forward/settlement':
            return 200,self.envelope(day,status='SOURCE_INCOMPLETE',reason='NO_AUTHORIZED_COHORT_SETTLEMENT_OWNER',
                contract_id='COHORT_SETTLEMENT_NOT_READY_READ_R3_V1',source=None,
                data=dict(observed_count=None,matured_count=None,outcomes=None,write_authorized=False),items=[],
                total=None,offset=0,limit=30,has_next=False,focus_is_validation_cohort=False)
        return super().get(path,q)
