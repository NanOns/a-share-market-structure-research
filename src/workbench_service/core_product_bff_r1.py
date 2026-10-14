"""Dated read adapter over accepted owners. No permission or immutable head changes."""
from pathlib import Path
from urllib.parse import unquote
from collections import Counter
from copy import deepcopy
import json, gzip
from .operational_successor_bff_v1 import OperationalSuccessorBFFV1
from .r43_operational_bff import owner_cell
from .stock_views import aggregate
from .domain_views import CHANGE_EVENTS, RISK_EVENTS, ROTATIONS
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.validation_cohort_read_contract_r3 import read_statistics, read_authorized_statistics
from .research_hypotheses_r3 import competing_explanations

CONTRACT='CORE_PRODUCT_BFF_R1'

HOME_EVENT_PRIORITY={'INVALIDATED':0,'EXITED':1,'WEAKENED':2,'UPGRADED':3,'REENTERED':4,'NEW':5}

HOME_STOCK_SUMMARY_FIELDS={'effective_event','trade_date'}
HOME_SECTOR_SUMMARY_FIELDS={'output_state','prior_rotation_state','sector_rs5','member_count'}
HOME_IDENTITY_FIELDS={'entity_id','security_id','symbol','display_name','display_name_scope','trade_date'}
HOME_CELL_FIELDS={'value','quality','unit','reason','as_of','source','actual_count','required_count'}
LEGACY_R1_READ_CAPABILITY='R1 legacy summary; D2 detail fields may be unavailable'

def is_legacy_r1_home_fallback(payload):
    """True only for an explicitly marked legacy read-index response."""
    return (payload.get('read_index_status') in
            ('LEGACY_R1_AUTHORITY_ONLY','R2_TOKEN_NOT_PREPARED','R2_DATE_NOT_PREPARED') and
            payload.get('read_index_capability') == LEGACY_R1_READ_CAPABILITY)

def annotate_home_readiness(payload, *, cohort_authorized=False):
    """Keep prebuilt and live Home responses honest about unpublished producers."""
    result=deepcopy(payload)
    market=result.get('market')
    if isinstance(market,dict):
        market['regime_publication_status']='NOT_PUBLISHED_V4_03'
        market['formal_risk_status']='SOURCE_INCOMPLETE'
        market['formal_risk_reason']='DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT'
    # Focus weakens remain useful evidence, but they do not establish the
    # independent stock-structure, sector-ecology and market-pressure families.
    result['focus_risk_events']=result.get('risks') or []
    result['focus_risk_scope']='FOCUS_OWNER_RISK_EVENTS_ONLY; NOT_COMPLETE_RISK_FAMILIES'
    result['risks']=[]
    result['risk_families']={key:dict(status='SOURCE_INCOMPLETE',value=None,
        reason='DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT')
        for key in ('stock_structure','sector_ecology','market_pressure')}
    if not cohort_authorized:
        result.setdefault('counts',{})['forward']=dict(value=None,quality='SOURCE_INCOMPLETE',
            status='NOT_GRANTED',scope='FORMAL_VALIDATION_COHORT',
            reason='NO_AUTHORIZED_COHORT_OWNER',href='/v4/research/focus#forward-cohort')
    return result

def home_summary(row, fields):
    """Keep only the identity and explicitly rendered evidence needed by home cards."""
    result={key:row[key] for key in HOME_IDENTITY_FIELDS if key in row}
    result['fields']={name:{key:value for key,value in cell.items() if key in HOME_CELL_FIELDS}
                      for name,cell in row.get('fields',{}).items() if name in fields}
    for key in ('source','symbol_source','display_name_source'):
        value=row.get(key)
        if isinstance(value,dict):
            result[key]={name:value[name] for name in ('path','sha256','contract_id','as_of','field') if name in value}
        elif value is not None:
            result[key]=value
    return result

def product_manifest_bindings(authority):
    """Versioned authority: R1 singleton or R2 exact date catalogue."""
    if authority.get('contract_id') == 'CORE_PRODUCT_READ_AUTHORITY_R1':
        return [authority['manifest']]
    if authority.get('contract_id') == 'CORE_PRODUCT_READ_AUTHORITY_R2':
        if set(authority) != {'contract_id', 'dates'} or not isinstance(authority['dates'], dict):
            raise ValueError('PRODUCT_AUTHORITY_CATALOG_INVALID')
        return list(authority['dates'].values())
    raise ValueError('PRODUCT_AUTHORITY_CONTRACT_REQUIRED')


def dated_product_manifest(root, authority, day):
    product_manifest_bindings(authority)
    binding = authority.get('dates', {}).get(day) if authority['contract_id'] == 'CORE_PRODUCT_READ_AUTHORITY_R2' else authority['manifest']
    if binding is None:
        return None
    manifest = json.loads(checked(root, binding).read_bytes())
    if manifest['T0'] != day:
        if authority['contract_id'] == 'CORE_PRODUCT_READ_AUTHORITY_R2':
            raise ValueError('PRODUCT_AUTHORITY_DATE_MISMATCH')
        return None
    return manifest

def prioritize_home_changes(changes):
    """HOME_EVENT_SELECTION_R2: one object, highest priority explicit event."""
    selected={}
    for row in sorted(changes,key=lambda r:(HOME_EVENT_PRIORITY[r['fields']['effective_event']['value']],r['entity_id'])):
        selected.setdefault(row['entity_id'],row)
    return list(selected.values())

def d2_selection_explanation(fields,source):
    fields=fields or {}
    def owner_field(name):
        return fields.get(name) or dict(value=None,quality='SOURCE_INCOMPLETE',unit='state',
            reason='D2_OWNER_FIELD_NOT_PRESENT_IN_DATED_DETAIL',source=source,field=name)
    scenario=owner_field('scenario').get('value')
    scenario_status=owner_field('scenario_status').get('value')
    if scenario=='NONE' and scenario_status!='KNOWN':interpretation='NONE_RESULT_NOT_FULLY_EVALUATED'
    elif scenario=='NONE':interpretation='NONE_FULLY_EVALUATED_NO_MATCH'
    elif scenario is None:interpretation='SCENARIO_RESULT_NOT_PUBLISHED'
    elif scenario_status!='KNOWN':interpretation='SCENARIO_REPORTED_BUT_UNVERIFIED'
    else:interpretation='SCENARIO_REPORTED_WITH_D2_STATUS'
    names=('scenario_status','raw_qualification','final_eligibility','detector_statuses',
           'matched_predicates','unknown_predicates','transition_reasons','input_provenance','identity_status')
    return dict(scenario=scenario,**{name:owner_field(name) for name in names},
        scenario_interpretation=interpretation,source=source)

def current_identity_presentation(identity,source,day):
    identity=identity or {}
    state=('CONFIRMED_CURRENT_IDENTITY' if identity.get('code_status')=='CONFIRMED_IPO'
           else 'CURRENT_IDENTITY_PRESENT' if identity else 'CURRENT_IDENTITY_UNKNOWN')
    return dict(value=state,quality='KNOWN' if identity else 'UNKNOWN',unit='state',as_of=day,
        reason=None if identity else 'CURRENT_IDENTITY_ROW_NOT_FOUND',source=source)

def code_status_presentation(identity,source,day):
    """Render code status without promoting every existing identity to a new code."""
    identity=identity or {}
    status=identity.get('code_status')
    if status:
        value=status;quality='KNOWN';reason=None
    elif identity.get('first_seen_date')==day or identity.get('list_date')==day:
        # A same-day first observation is evidence of a newly observed code,
        # and an authoritative same-day listing date is equivalent evidence.
        # Neither field by itself establishes a historical identity.
        value='NEW_CODE_OBSERVED';quality='KNOWN'
        reason=('FIRST_OBSERVED_ON_CURRENT_TRADE_DATE' if identity.get('first_seen_date')==day
                else 'LISTED_ON_CURRENT_TRADE_DATE')
    else:
        list_date=identity.get('list_date')
        try:
            existing=bool(list_date and list_date < day)
        except TypeError:
            existing=False
        if existing:
            value='EXISTING_VERIFIED_IDENTITY';quality='KNOWN';reason='DATED_IDENTITY_PREDATES_CURRENT_TRADE_DATE'
        else:
            value='UNKNOWN';quality='SOURCE_INCOMPLETE';reason='DATED_CODE_STATUS_NOT_REPORTED_BY_IDENTITY_OWNER'
    return dict(value=value,quality=quality,unit='state',as_of=day,reason=reason,source=source)

def normalize_indexed_code_status(payload,day):
    """Repair stale list projections at read time using their dated identity facts."""
    if not isinstance(payload,dict):return payload
    candidates=list(payload.get('items') or [])
    if isinstance(payload.get('item'),dict):candidates.append(payload['item'])
    for row in candidates:
        if not isinstance(row,dict):continue
        fields=row.setdefault('fields',{})
        if not isinstance(fields,dict):continue
        previous=fields.get('code_status') or {}
        observation=row.get('identity_observation')
        source=previous.get('source') if isinstance(previous,dict) else None
        fields['code_status']=code_status_presentation(observation,source,day)
    return payload

class CoreProductBFFR1(OperationalSuccessorBFFV1):
    isolated_history=None
    def __init__(self,api,legacy,*,isolated_history_authority=None,chart_history_index_root=None,market_fact_index_root=None):
        super().__init__(api,legacy)
        self.isolated_history=None
        self.chart_history_index_root=Path(chart_history_index_root).resolve() if chart_history_index_root is not None else None
        self.market_fact_index_root=Path(market_fact_index_root).resolve() if market_fact_index_root is not None else None
        if isolated_history_authority is not None:
            from .isolated_history_read_r4 import load
            self.isolated_history=load(api,isolated_history_authority)

    def _read_index_r2(self,day):
        """Cache only the immutable binding; each PG read still attests its digest and database."""
        if getattr(self,'building_read_index',False):return None
        from workbench_db.v4_read_index_r2 import AUTHORITY,load
        path=self.api.root/AUTHORITY
        try:stat=path.stat();signature=(stat.st_mtime_ns,stat.st_size)
        except FileNotFoundError:signature=None
        key=('product-read-index-r2',self.api.token,day,signature)
        if key not in self.api.cache:
            self.api.cache[key]=load(self.api.root,self.api.token,day,
                allow_missing=day!=self.api.candidate['accepted_trade_date'])
        return self.api.cache[key]

    def _read_index_r2_state(self,day):
        from workbench_db.v4_read_index_r2 import AUTHORITY
        path=self.api.root/AUTHORITY
        if not path.exists():return 'LEGACY_R1_AUTHORITY_ONLY'
        authority=json.loads(path.read_bytes());versions=authority.get('versions',{})
        if self.api.token not in versions:return 'R2_TOKEN_NOT_PREPARED'
        if day not in versions[self.api.token]:return 'R2_DATE_NOT_PREPARED'
        return 'R2_AUTHORITY_BOUND'

    @staticmethod
    def _base_query(query):
        # These filters are validated and consumed by their product routes. The
        # legacy Context allowlist is intentionally kept narrow. Focus page
        # controls also carry their event filter and event-page offset in the
        # URL; those parameters belong only to /focus/events and must not make
        # the independent Focus list request fail validation.
        return {k:v for k,v in query.items() if k not in
                ('event','validity','limit_state','event_state','events_offset')}

    def _display_identity_map(self,day,rows,*,key_fields=('entity_id','security_id')):
        keys=[next((row.get(k) for k in key_fields if row.get(k)),None) for row in rows]
        index=self._read_index_r2(day)
        if index is not None:return index.display_identities('stocks',keys)
        from workbench_db.v4_read_index_r1 import load as load_index_r1
        legacy=load_index_r1(self.api.root,self.api.token,day,
            allow_missing=day!=self.api.candidate['accepted_trade_date'])
        if legacy is None:return {}
        return legacy.display_identities('stocks',keys)

    def _enrich_display_names(self,day,rows,*,key_fields=('entity_id','security_id')):
        identities=self._display_identity_map(day,rows,key_fields=key_fields)
        for row in rows:
            key=next((row.get(k) for k in key_fields if row.get(k)),None)
            identity=identities.get(key) or identities.get(str(key))
            row['symbol']=row.get('symbol') or (identity or {}).get('symbol')
            row['display_name']=(identity or {}).get('display_name')
            row['display_name_source']=(identity or {}).get('display_name_source')
            row['display_name_scope']=(identity or {}).get('display_name_scope')
            row['name_quality']=(identity or {}).get('name_quality','UNKNOWN')
            row['name_reason']=(identity or {}).get('name_reason','ACCEPTED_STOCK_IDENTITY_NOT_FOUND')
        return rows
    def resolve_dated_object(self,domain,day,key):
        """Same dated identity aliases for detail and compare; ambiguity fails closed."""
        if not key:return None
        if not getattr(self,'building_read_index',False):
            index=self._read_index_r2(day)
            if index is not None and domain in ('stocks','sectors','focus'):
                return index.detail(domain,str(key).strip().upper())
            from workbench_db.v4_read_index_r1 import load as load_index
            index=load_index(self.api.root,self.api.token,day,allow_missing=day!=self.api.candidate['accepted_trade_date'])
            if index is not None and domain in ('stocks','sectors','focus'):
                return index.detail(domain,str(key).strip().upper())
        needle=str(key).strip().upper()
        def aliases(row):
            values=(row['entity_id'],row['symbol'],*row.get('search_aliases',[]))
            return {str(v).upper() for v in values if v} | {str(v).upper().split('.')[-1] for v in values if v}
        matches=[r for r in self.project(domain,day) if needle in aliases(r)]
        identities={r['entity_id'] for r in matches}
        return matches[0] if len(identities)==1 else None

    def focus_projection(self,day):
        authority=self.api.root/'config/core_product_focus_read_authority_r2.json'
        if not authority.exists() or day!=self.api.candidate['accepted_trade_date']:return None
        key=('focus-read-r2',day)
        if key not in self.api.cache:
            manifest=json.loads(checked(self.api.root,json.loads(authority.read_bytes())['manifest']).read_bytes())
            if manifest['T0']!=day or manifest['head']['sha256']!=self.api.token:return None
            checked(self.api.root,manifest['head']);checked(self.api.root,manifest['implementation'])
            for ref in manifest['source_bindings'].values():checked(self.api.root,ref)
            if manifest.get('contract_id')=='CORE_PRODUCT_FOCUS_READ_MANIFEST_R3_NATIVE_PG':
                from workbench_db.v4_focus_projection_pg_closeout import read as read_focus_pg
                projection=read_focus_pg(self.api.root,manifest['projection'],t0=day,head_token=self.api.token)
            elif manifest.get('contract_id')=='CORE_PRODUCT_FOCUS_READ_MANIFEST_R2':
                projection=json.loads(gzip.decompress(checked(self.api.root,manifest['projection']).read_bytes()))
            else:
                raise ValueError('FOCUS_READ_PROJECTION_CONTRACT_UNSUPPORTED')
            self.api.cache[key]=(manifest,projection)
        return self.api.cache[key]

    def source(self,domain,day,*,security_id=None):
        if domain in ('period_raw','period_adjusted'):
            pack=self.pack(day)
            binding=pack[0].get('period_owners',{}).get(domain) if pack else None
            if binding:
                from workbench_db.v4_period_pg_r1 import read
                fact_token=pack[0].get('fact_token',self.api.token)
                if security_id is not None:return read(self.api.root,binding,day,domain,fact_token,security_id=security_id)
                key=('pg-period-owner',self.api.token,day,domain,binding['sha256'])
                if key not in self.api.cache:self.api.cache[key]=read(self.api.root,binding,day,domain,fact_token)
                return self.api.cache[key]
        pack=self.focus_projection(day) if domain=='forward' else None
        if not pack:return super().source(domain,day)
        key=('focus-dated-forward',self.api.token,day,pack[0]['projection']['sha256'])
        if key not in self.api.cache:
            # Bound immutable source objects are never modified by readers.
            # Copy the container and dated event selection, not every episode
            # observation and settlement path on every read/count request.
            projection=dict(pack[1]);projection['events']=[e for e in projection['events'] if e['trade_date']==day]
            self.api.cache[key]=projection
        return self.api.cache[key]

    def _r2_stock_profile(self,index,day,key):
        """Build stock detail from the immutable R2 row without reopening PG owners."""
        context=index.response('/api/v4/context')
        item=self.resolve_dated_object('stocks',day,str(key).strip().upper())
        if context is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
        base={k:context[k] for k in ('context','context_token','production_accepted','source_quality') if k in context}
        if item is None:
            return 404,{**base,'status':'NOT_FOUND','code':'ENTITY_NOT_FOUND','item':None}
        # The profile route bypasses page(), so normalize the embedded item here
        # as well as the separately rendered R section below.
        item=normalize_indexed_code_status({'item':item},day)['item']
        fields=item.get('fields',{});eligibility=fields.get('final_eligibility',{}).get('value')
        classified=('NOT_ELIGIBLE' if eligibility=='FALSE' else 'ELIGIBLE' if eligibility=='TRUE'
                    else 'NOT_IMPLEMENTED' if 'NOT_IMPLEMENTED' in str(fields.get('detector_statuses',{})) else 'UNKNOWN')
        selection=dict(status=classified,d2=d2_selection_explanation(fields,self.api.candidate['owners'][day]['focus']),
                       meaning='资格状态来自真实 reducer；不在列表不代表无画像；未知不等于未满足')
        owner_explanations={}
        for key_name,field,basis in (
            ('why_now','transition_reasons','OWNER_TRANSITION_REASONS'),
            ('waiting_for','unknown_predicates','MISSING_PREDICATE_EVIDENCE_ONLY')):
            if field in fields:
                owner_explanations[key_name]=dict(value=fields[field].get('value'),source=fields[field],basis=basis)
        for key_name in ('invalid_if','hypothesis'):
            owner_explanations[key_name]=dict(value=None,source=dict(quality='UNKNOWN',
                reason='DATED_D2_OWNER_FIELD_NOT_PRESENT',source=self.api.candidate['owners'][day]['focus']),basis='MISSING_OWNER')
        missing_relations=[]
        if fields.get('primary_industry',{}).get('value') is None:missing_relations.append('primary_industry')
        missing_relations.append('supporting_concepts')
        return 200,{**base,'status':'READY','item':item,
            'F':{k:v for k,v in fields.items() if k in {'open','high','low','close','amount','volume'}},
            'R':{k:v for k,v in fields.items() if k not in {'open','high','low','close','amount','volume'}},
            'selection_explanation':selection,
            'membership_relations':dict(items=[],owner_gap=missing_relations,source=None,
                membership_mode='NOT_RELOADED_FROM_OPERATIONAL_OWNER',PIT_ELIGIBLE=False),
            'owner_explanations':owner_explanations,
            'owner_specific_debt':[dict(field=k,reason='DATED_D2_OWNER_FIELD_NOT_PRESENT') for k in ('invalid_if','hypothesis')],
            'key_prices':{k:fields[k] for k in ('ma20','prior_high20','prior_low20','atr20') if k in fields},
            'hypothesis_scope':'情景解释不证明洗盘、吸筹、出货或账户资金行为',
            'competitive_hypotheses':competing_explanations(deepcopy(fields))}

    def get(self,path,query):
        from workbench_db.v4_read_index_r2 import validate_query
        from workbench_db.v4_read_index_r1 import load as load_index_r1
        day=validate_query({k:v for k,v in query.items() if k not in ('event_state','events_offset')},
                           self.api.token,self.api.candidate['published_sessions'],
                           self.api.candidate['accepted_trade_date'],path)
        index_route=(path in ('/api/v4/context','/api/v4/home','/api/v4/stocks','/api/v4/sectors','/api/v4/focus','/api/v4/radar') or
                     path.startswith('/api/v4/stocks/') or path.startswith('/api/v4/sectors/') or path.startswith('/api/v4/focus/'))
        index_r2=self._read_index_r2(day) if index_route else None
        if (index_r2 is not None and path.startswith('/api/v4/stocks/') and
                path.endswith(('/profile','/evidence','/why-not','/why-not-prewatch'))):
            parts=[unquote(part) for part in path.split('/') if part]
            if len(parts)==5:return self._r2_stock_profile(index_r2,day,parts[3])
        if path=='/api/v4/radar' and not getattr(self,'building_read_index',False):
            if index_r2 is None:raise ValueError('READ_INDEX_R2_RADAR_NOT_PREPARED')
            context=index_r2.response('/api/v4/context')
            if context is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
            page=index_r2.page('radar',query)
            return 200,{k:context[k] for k in ('context','context_token','production_accepted','source_quality') if k in context}|page|{
                'contract_id':'V4_ACCEPTED_FOCUS_RADAR_PAGE_R1','source':self.api.candidate['owners'][day].get('forward'),
                'scope':'ACCEPTED_FOCUS_EVENTS_WITHOUT_TOP_ROTATION_COVERAGE','producer_status':'FORMAL_RADAR_PRIORITY_NOT_PUBLISHED'}
        index=index_r2 if index_r2 is not None else None if getattr(self,'building_read_index',False) or not index_route or path=='/api/v4/radar' else load_index_r1(self.api.root,self.api.token,day,allow_missing=day!=self.api.candidate['accepted_trade_date'])
        if index is not None and path in ('/api/v4/context','/api/v4/home','/api/v4/stocks','/api/v4/sectors','/api/v4/focus'):
            if path in ('/api/v4/context','/api/v4/home'):
                response=index.response(path)
                if response is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
                if index_r2 is None:response=dict(response,read_index_status=self._read_index_r2_state(day),
                    read_index_capability=LEGACY_R1_READ_CAPABILITY)
                if path=='/api/v4/home':
                    cohort_ref=self.api.candidate['owners'][day].get('validation_cohort')
                    response=annotate_home_readiness(response,cohort_authorized=bool(cohort_ref))
                return 200,response
            response=index.response('/api/v4/context')
            if response is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
            response={k:v for k,v in response.items() if k in ('context','context_token','production_accepted','source_quality')}
            response.update(index.page(path.rsplit('/',1)[-1],query))
            if path=='/api/v4/stocks':response=normalize_indexed_code_status(response,day)
            if index_r2 is None:response.update(read_index_status=self._read_index_r2_state(day),
                read_index_capability=LEGACY_R1_READ_CAPABILITY)
            if path=='/api/v4/focus':
                extra=index.response('/api/v4/focus-meta')
                if extra is None:raise ValueError('READ_INDEX_FOCUS_NOT_PREPARED')
                response.update(extra)
            return 200,response
        code,data=self._get_product(path,query)
        if index is None and day!=self.api.candidate['accepted_trade_date']:
            data['read_index_status']='HISTORICAL_UNINDEXED_READ_ONLY'
        day=query.get('trade_date',self.api.candidate['accepted_trade_date'])
        focus_route=(path in ('/api/v4/focus','/api/v4/home','/api/v4/radar') or
                     path.startswith('/api/v4/focus/') or path.startswith('/api/v4/forward'))
        pack=self.focus_projection(day) if focus_route else None
        if path=='/api/v4/focus' and code==200:
            episodes=self.source('forward',day)['episodes'];active={e['entity_id'] for e in episodes if e.get('end_date') is None}
            stocks={r['entity_id']:r for r in self.project('stocks',day)};sectors={r['entity_id']:r for r in self.project('sectors',day)};groups=Counter();unknown=0
            for sid in active:
                sector=stocks.get(sid,{}).get('fields',{}).get('primary_industry',{}).get('value')
                if sector is None:unknown+=1
                else:groups[sector]+=1
            items=[]
            for sid,count in sorted(groups.items(),key=lambda x:(-x[1],x[0])):
                sector=sectors.get(sid,{});display_name=sector.get('display_name')
                items.append(dict(sector_id=sid,display_name=display_name or '行业名称待确认（'+sid.split(':')[-1]+'）',
                    sector_type=sector.get('fields',{}).get('sector_type',{}).get('value'),count=count,denominator=len(active),
                    share=count/len(active) if active else None,href='/v4/research/sectors/'+sid,
                    name_source=sector.get('display_name_source'),name_quality='KNOWN' if display_name else 'UNKNOWN'))
            data['sector_exposure']=dict(denominator=len(active),unknown_industry=unknown,items=items,source=self.api.snapshot['memberships'],scope='Unique active research objects under latest reconstructed primary industry; not holdings, not a probability')
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
        if self.isolated_history is not None:
            data['production_accepted']=False
            data['context'].update(production_accepted=False,read_scope='ISOLATED_ENGINEERING_HISTORY',isolated_authority_sha256=self.isolated_history[2])
        default_pack=self.api.cache.get(('product-pack',day))
        if default_pack and default_pack[0].get('authority_scope')=='ISOLATED_ENGINEERING_ONLY':
            data['production_accepted']=False
            data['context'].update(production_accepted=False,read_scope='DEFAULT_AUTHORITY_ISOLATED_ENGINEERING',
                                   pg_history_acceptance='NOT_GRANTED')
        return code,data
    def identity_records(self):
        key=('product-identity',)
        if key not in self.api.cache:
            from workbench_db.v4_membership_reference_pg_v1 import KEY,read_search_identity
            if KEY in self.api.candidate or self.api.candidate.get('exact_daily_adjustment_contract'):
                self.api.cache[key]=read_search_identity(self.api.root,self.api.candidate,
                    workspace_root=getattr(self.api,'pg_owner_workspace_root',None))
                return self.api.cache[key]
            head=json.loads((self.api.root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
            ref=head['identity'];data=json.loads(checked(self.api.root,ref).read_bytes())
            self.api.cache[key]=(data['records'],ref)
        return self.api.cache[key]

    def history_pack(self, day):
        if self.isolated_history is not None:
            authority,index_root,digest=self.isolated_history
            entry=authority['dates'].get(day)
            if entry is None:return None
            return dict(T0=day,history_index=entry['history_index'],source_bindings={'history':entry['source_binding']},isolated_authority_sha256=digest),{}
        return self.pack(day)

    def chart_history_pack(self, day):
        if self.isolated_history is not None:
            authority,index_root,digest=self.isolated_history
            entry=authority['dates'].get(day)
            if entry is None:return None
            return dict(T0=day,history_index=entry['history_index'],source_bindings={'history':entry['source_binding']},isolated_authority_sha256=digest),{}
        key=('product-history-only-pack',day)
        if key not in self.api.cache:
            from .native_product_catalog_v3 import KEY,load
            if KEY in self.api.candidate or self.api.candidate.get('exact_daily_adjustment_contract'):
                authority=load(self.api.root,self.api.candidate)
                binding=authority['dates'].get(day)
                manifest=json.loads(checked(self.api.root,binding).read_bytes()) if binding else None
            else:
                authority=self.api.root/'config/core_product_read_authority_r1.json'
                if not authority.exists():return None
                manifest=dated_product_manifest(self.api.root,json.loads(authority.read_bytes()),day)
            if manifest is None:return None
            if manifest.get('contract_id') not in ('CORE_PRODUCT_DATED_HISTORY_ONLY_PACK_R1','CORE_PRODUCT_DATED_READ_PACK_PG_MARKET_R2'):
                raise ValueError('PRODUCT_HISTORY_PACK_CONTRACT_UNSUPPORTED')
            if manifest.get('contract_id')=='CORE_PRODUCT_DATED_HISTORY_ONLY_PACK_R1' and manifest.get('capabilities')!=['CHART_HISTORY']:
                raise ValueError('PRODUCT_HISTORY_ONLY_SCOPE_MISMATCH')
            head=manifest.get('head') or {}
            if manifest.get('T0')!=day or (self.api.root/head.get('path','')).read_bytes()!=checked(self.api.root,head).read_bytes():
                raise ValueError('PRODUCT_HISTORY_MANIFEST_CONTEXT_MISMATCH')
            history=manifest.get('history_index') or {}
            expected_token=manifest.get('fact_token',head.get('sha256'))
            if history.get('engine')!='postgresql':raise ValueError('PG_HISTORY_BINDING_REQUIRED_NO_FALLBACK')
            if (history.get('T0'),history.get('head_token'))!=(day,expected_token):
                raise ValueError('PG_HISTORY_MANIFEST_CONTEXT_MISMATCH')
            source=manifest.get('source_bindings',{}).get('history')
            if not source:raise ValueError('PG_HISTORY_SOURCE_BINDING_REQUIRED')
            checked(self.api.root,source)
            if history.get('source_digest')!=source.get('sha256'):
                raise ValueError('PG_HISTORY_SOURCE_DIGEST_MISMATCH')
            from workbench_db.v4_native import workspace_schema
            index_root=self.chart_history_index_root or self.api.root
            if history.get('schema')!=workspace_schema(index_root,'history'):
                raise ValueError('PG_HISTORY_CONTEXT_MISMATCH')
            self.api.cache[key]=(manifest,None)
        return self.api.cache[key]

    def pack(self, day):
        key=('product-pack',day)
        if key not in self.api.cache:
            from .native_product_catalog_v3 import KEY,load
            embedded=KEY in self.api.candidate
            if embedded or self.api.candidate.get('exact_daily_adjustment_contract'):
                authority=load(self.api.root,self.api.candidate)
                binding=authority['dates'].get(day)
                manifest=json.loads(checked(self.api.root,binding).read_bytes()) if binding else None
            else:
                authority=self.api.root/'config/core_product_read_authority_r1.json'
                if not authority.exists():return None
                manifest=dated_product_manifest(self.api.root,json.loads(authority.read_bytes()),day)
            if manifest is None:return None
            head=self.api.root/manifest['head']['path']
            if manifest['T0']!=day or head.read_bytes()!=checked(self.api.root,manifest['head']).read_bytes():return None
            if manifest['history_index'].get('engine')!='postgresql':
                raise ValueError('PG_HISTORY_BINDING_REQUIRED_NO_FALLBACK')
            if (manifest['history_index'].get('T0'),manifest['history_index'].get('head_token'))!=(day,manifest.get('fact_token',manifest['head']['sha256'])):
                raise ValueError('PG_HISTORY_MANIFEST_CONTEXT_MISMATCH')
            if manifest.get('contract_id')=='CORE_PRODUCT_DATED_HISTORY_ONLY_PACK_R1':
                if manifest.get('capabilities')!=['CHART_HISTORY'] or manifest.get('market_facts') is not None:
                    raise ValueError('PRODUCT_HISTORY_ONLY_SCOPE_MISMATCH')
                facts=None
            else:
                if manifest.get('contract_id')=='CORE_PRODUCT_DATED_READ_PACK_PG_MARKET_R2':
                    from workbench_db.v4_market_fact_pg_r1 import read
                    facts=read(self.market_fact_index_root or self.api.root,manifest['market_facts'],day)
                else:
                    facts=json.loads(checked(self.api.root,manifest['market_facts']).read_bytes())
            self.api.cache[key]=(manifest,facts)
        return self.api.cache[key]

    def envelope(self,day,**payload):
        response=super().envelope(day,**payload)
        response['context']['bff_contract_id']=CONTRACT
        response['context']['product_engineering_acceptance']='EXTERNAL_PENDING'
        response['context']['focus_write']=False
        quality=self.api.candidate.get('source_quality') if day==self.api.candidate['accepted_trade_date'] else None
        if quality:
            response['source_quality']={k:v for k,v in quality.items() if k!='valid_codes'}
            response['context']['identity_coverage']=quality['status']
            response['context']['effective_universe_count']=quality['effective_universe_count']
        if self.isolated_history is not None:
            response['production_accepted']=False
            response['context'].update(production_accepted=False,read_scope='ISOLATED_ENGINEERING_HISTORY',isolated_authority_sha256=self.isolated_history[2])
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
        # Sector detail pages need the dated rotation explanation. Attach it
        # while building the immutable R2 projection so a detail request does
        # not reload the rotation owner bundle on every click.
        sector_rotation={r['sector_id']:r.get('rotation',{}) for r in self.source('rotation',day)} if domain=='sectors' else {}
        identities,identity_ref=self.identity_records() if domain=='stocks' else ([],None)
        current_identities={r['security_id']:r for r in self.identity_rows()} if domain=='stocks' else {}
        identity_ref_current=None
        if domain=='stocks':
            from workbench_db.v4_membership_reference_pg_v1 import identity_source as current_identity_source
            identity_ref_current=current_identity_source(self.api.root,self.api.candidate)
        aliases={}
        for record in identities:
            aliases.setdefault(record['security_id'],set()).update(str(record.get(k,'')) for k in ('symbol','source_security_key','security_name'))
        registries={r['field_id']:r for filename in ('v4_03_field_registry_v1.json','v4_04_field_registry_v2.json','v4_08_sector_field_registry_r5.json') for r in json.loads((self.api.root/'config'/filename).read_bytes())['fields']}
        for row in data:
            if domain in ('stocks','focus','events'):
                code=row['symbol'].upper();name=names['stocks'].get(code)
                if name:row.update(display_name=name,display_name_scope='OBSERVED_DISPLAY_ONLY_NOT_PIT',display_name_source=name_source,display_name_observed_at=names['observed_at'])
            if domain=='stocks':
                ident=current_identities.get(row['entity_id'],{})
                if ident:
                    row['identity_observation']={k:ident.get(k) for k in
                        ('first_seen_date','list_date','confirmed_ipo_date','code_status','metadata_status','alias_status')}
                    row['fields']['code_status']=code_status_presentation(ident,identity_ref_current,day)
                    if ident.get('name'):
                        row.update(display_name=ident['name'],display_name_scope='OBSERVED_METADATA_NOT_PIT',
                                   display_name_source=identity_ref_current,display_name_quality='KNOWN')
                row['fields']['identity_status']=current_identity_presentation(ident,identity_ref_current,day)
                row['search_aliases']=sorted(aliases.get(row['entity_id'],set()))
                row['alias_source']=identity_ref
                for k,v in cores.get(row['entity_id'],{}).get('fields',{}).items():
                    row['fields'].setdefault(k,owner_cell(v,self.api.candidate['owners'][day]['core'],'fields.'+k,day))
                state=d2.get(row['entity_id'],{})
                for k in ('effective_event','scenario_status','raw_qualification','matched_predicates','unknown_predicates',
                          'transition_reasons','detector_statuses','prewatch_status','input_provenance'):
                    if k in state:row['fields'][k]=owner_cell(state[k],self.api.candidate['owners'][day]['focus'],k,day)
            if domain=='focus':row['focus_scope']='RECONSTRUCTED_ENGINEERING_TRACKING_READ; USER_MANUAL_WRITE_DISABLED; NOT_VALIDATION_COHORT'
            if domain=='sectors':
                native=sector_native[row['entity_id']];ref=self.api.candidate['owners'][day]['sector']
                for key,value,field in [('member_count',len(set(native['member_ids'])),'member_ids (unique)'),('source_member_count',native['current_member_count'],'current_member_count'),('unmapped_count',native['unmapped_count'],'unmapped_count'),('quoted_count',native['quoted_count'],'quoted_count')]:
                    row['fields'][key]=owner_cell(dict(value=value,quality='KNOWN',unit='members'),ref,field,day)
                for key in ('maturity','health'):
                    row['fields'].setdefault(key,dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',reason='DATED_SECTOR_D2_'+key.upper()+'_OWNER_NOT_PRESENT',as_of=day,unit='state',source=None,field=None))
                rotation=sector_rotation.get(row['entity_id'],{})
                row['__detail_extras__']={'why_now':dict(prior_state=rotation.get('prior_rotation_state'),current_state=rotation.get('output_state'),
                    reason_codes=rotation.get('reason_codes',[]),predicates=rotation.get('predicates',{}),
                    fields={k:rotation.get('fields',{}).get(k) for k in ('dq5','breadth_delta1','breadth_delta3','ma20_delta3','base_seed_width_adjusted')},
                    source=self.api.candidate['owners'][day]['rotation'],scope='Observed reconstructed rule facts; not strict PIT or independently accepted full episode reduction')}
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
        # R1/R2 read indexes contain only stocks, sectors and focus rows.
        # Loading them for other projectors (notably dated structural events)
        # can reject a valid non-indexed route on an unrelated stale binding.
        if not getattr(self,'building_read_index',False) and domain in ('stocks','sectors','focus'):
            index=self._read_index_r2(day)
            if index is not None:
                if entity is not None:
                    context,item=index.response_and_detail(
                        '/api/v4/context',domain,str(entity).strip().upper())
                    if context is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
                    base={k:v for k,v in context.items() if k in ('context','context_token','production_accepted','source_quality')}
                    if item is None:return {**base,'status':'NOT_FOUND','items':[],'total':0,'offset':int(q.get('offset',0)),'limit':int(q.get('limit',30)),'has_next':False,'domain':domain,'gap':None}
                    response={**base,'status':'READY','items':[item],'item':item,'total':1,'offset':int(q.get('offset',0)),'limit':int(q.get('limit',30)),'has_next':False,'domain':domain,'gap':None}
                    return normalize_indexed_code_status(response,day) if domain=='stocks' else response
                context=index.response('/api/v4/context')
                if context is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
                base={k:v for k,v in context.items() if k in ('context','context_token','production_accepted','source_quality')}
                response={**base,**index.page(domain,q,entity=entity,sector=sector)}
                return normalize_indexed_code_status(response,day) if domain=='stocks' else response
            from workbench_db.v4_read_index_r1 import load as load_index
            index=load_index(self.api.root,self.api.token,day,allow_missing=day!=self.api.candidate['accepted_trade_date'])
            if index is not None:
                context=index.response('/api/v4/context')
                return {**{k:v for k,v in context.items() if k in ('context','context_token','production_accepted','source_quality')},
                        **index.page(domain,q,entity=entity,sector=sector),
                        'read_index_status':self._read_index_r2_state(day),
                        'read_index_capability':'R1 legacy summary; D2 detail fields may be unavailable'}
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
        pack=self.chart_history_pack(day)
        if not pack:return self.missing(day,'stocks/'+sid+'/chart','DATED_HISTORY_INDEX_NOT_BOUND')
        manifest,_=pack
        from workbench_db.v4_history_pg_r1 import read
        index_root=self.isolated_history[1] if self.isolated_history is not None else (self.chart_history_index_root or self.api.root)
        value=read(index_root,manifest['history_index'],day,sid)
        if value is None:return 404,self.envelope(day,status='NOT_FOUND',code='ENTITY_NOT_FOUND')
        bars=[]
        for b in value:
            if b['trade_date']>day:raise ValueError('FUTURE_CHART_BAR')
            prices=b['raw_ohlc' if basis=='RAW' else 'qfq_ohlc']
            bars.append(dict(trade_date=b['trade_date'],**dict(zip(('open','high','low','close'),prices or [None]*4)),volume=b['volume'],amount=b['amount'],quality='KNOWN' if prices else 'UNKNOWN',reason='BLOCKED_ADJUSTMENT_EVENT' if not prices else None))
        data=aggregate(bars,period)
        if period!='D' and data:
            owner_domain='period_raw' if basis=='RAW' else 'period_adjusted'
            period_rows=self.source(owner_domain,day,security_id=sid)
            if period_rows is None:
                return self.missing(day,'stocks/'+sid+'/chart','DATED_'+owner_domain.upper()+'_OWNER_NOT_BOUND')
            formal=max((r for r in period_rows if r['security_id']==sid and r['period_type']==('WEEKLY' if period=='W' else 'MONTHLY')),key=lambda r:r.get('as_of_date',r.get('max_source_date','')),default=None)
            if formal:
                formal_ref=manifest.get('period_owners',{}).get(owner_domain) or self.api.candidate['owners'][day][owner_domain]
                data[-1].update(period_status=formal['period_status'],calendar_count=formal['calendar_count'],suspended_count=formal['suspended_count'],formal_period_source=formal_ref)
        for i,b in enumerate(data):
            for n in (5,20,60):
                w=data[max(0,i-n+1):i+1];b['ma'+str(n)]=sum(x['close'] for x in w)/n if len(w)==n and all(x['close'] is not None for x in w) else None
        offset=int(q.get('offset',0));limit=int(q.get('limit',120))
        if not 0<=offset<=1000000 or not 1<=limit<=200:raise ValueError('INVALID_QUERY_BOUND')
        end=max(0,len(data)-offset);start=max(0,end-limit)
        response=self.envelope(day,status='READY' if data else 'EMPTY_VALID',items=data[start:end],total=len(data),offset=offset,limit=limit,has_next=start>0,period=period,price_basis=basis,as_of=day,volume_unit='SHARES',amount_unit='CNY',source=manifest['source_bindings']['history'],series_index=manifest['history_index'],adjustment='TDX_NATIVE_AFFINE_T0_COORDINATE' if basis=='QFQ' else 'NONE',historical_membership='RECONSTRUCTED_NOT_STRICT_PIT',earliest_valid_date=bars[0]['trade_date'] if bars else None)
        if self.isolated_history is not None:
            response['production_accepted']=False
            response['context'].update(production_accepted=False,read_scope='ISOLATED_ENGINEERING_HISTORY',isolated_authority_sha256=self.isolated_history[2])
        return 200,response

    def _get_product(self,path,query):
        q=dict(query);q.setdefault('trade_date',self.api.candidate['accepted_trade_date']);day=q['trade_date']
        # Base route validation applies before any product-specific read.
        from workbench_db.v4_read_index_r2 import validate_query
        validate_query({k:v for k,v in q.items() if k not in ('event_state','events_offset')},
                       self.api.token,self.api.candidate['published_sessions'],
                       self.api.candidate['accepted_trade_date'],path)
        if path!='/api/v4/context' and q.get('context_token')!=self.api.token:raise ValueError('CONTEXT_TOKEN_MISMATCH')
        p=[unquote(x) for x in path.removeprefix('/api/v4/').split('/')]
        if p[0]=='candidates' and (p[1:]==['cohort'] or len(p)==3 and p[1]=='sectors'):
            from .candidate_research_read_v2 import read_candidates
            data=read_candidates(self.api.root,head=self.api.candidate,token=self.api.token,day=day,
                                 sector_id=p[2] if len(p)==3 else None)
            return 200,self.envelope(day,status='READY',candidate_research=data,
                contract_id='OPERATIONAL_CANDIDATE_DISPLAY_READ_V2',production=False,formal_consumer_enabled=False)
        if p[0] in ('stocks','focus') and len(p)>1 and p[1] not in ('events',):
            match=self.resolve_dated_object('stocks',day,p[1])
            if match is not None:
                p[1]=match['entity_id'];path='/api/v4/'+'/'.join(p)
        if p[0]=='stocks' and len(p)==3 and p[2]=='chart':return self.chart(day,p[1],q)
        if p[0]=='stocks' and len(p)==3 and p[2] in ('profile','why-not','why-not-prewatch','evidence'):
            code,data=super().get(path,self._base_query(q))
            if code!=200:return code,data
            item=data['item'];fields=item['fields'];eligibility=fields.get('final_eligibility',{}).get('value')
            classified='NOT_ELIGIBLE' if eligibility=='FALSE' else 'ELIGIBLE' if eligibility=='TRUE' else 'NOT_IMPLEMENTED' if 'NOT_IMPLEMENTED' in str(fields.get('detector_statuses',{})) else 'UNKNOWN'
            data['selection_explanation']=dict(status=classified,d2=d2_selection_explanation(fields,self.api.candidate['owners'][day]['focus']),meaning='资格状态来自真实 reducer；不在列表不代表无画像；未知不等于未满足')
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
            code,data=super().get(path,self._base_query(q))
            if code!=200:return code,data
            indexed_why_now=data.get('item',{}).get('why_now')
            if indexed_why_now is not None:
                data['why_now']=indexed_why_now
            else:
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
            code,data=super().get(path,self._base_query(q));native=next((r for r in self.source('sector',day) if r['sector_id']==p[1]),None)
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
            code,response=self.paged(day,data,q,source=self.api.candidate['owners'][day]['forward'],contract_id='FOCUS_LAYERED_DATED_READ_R1',focus_scope='RECONSTRUCTED_READ_ONLY_NOT_VALIDATION_COHORT',write_authorized=False,PIT_ELIGIBLE=False)
            index=self._read_index_r2(day)
            if index is not None:
                response['focus_item']=index.detail('focus',p[1])
                if response['focus_item'] is None:response['focus_item_quality']={'quality':'SOURCE_INCOMPLETE','reason':'FOCUS_DETAIL_NOT_PRESENT_IN_R2_INDEX'}
            else:response['focus_detail_capability']=self._read_index_r2_state(day)
            return code,response
        if p==['focus','events']:
            rows=list(self.source('forward',day).get('events',[]));event=q.get('event');validity=q.get('validity');needle=q.get('q','').strip().casefold()
            identities=self._display_identity_map(day,rows) if needle else {}
            if event:rows=[r for r in rows if r.get('event')==event]
            if validity:rows=[r for r in rows if r.get('validity')==validity]
            if needle:rows=[r for r in rows if needle in str(r.get('entity_id','')).casefold() or needle in str(identities.get(r.get('entity_id'),{}).get('symbol') or '').casefold() or needle in str(identities.get(r.get('entity_id'),{}).get('display_name') or '').casefold()]
            rows.sort(key=lambda r:(r.get('trade_date',''),r.get('entity_id',''),r.get('event','')))
            code,data=self.paged(day,rows,q,source=self.api.candidate['owners'][day]['forward'],contract_id='FOCUS_EVENT_PAGE_R1',focus_scope='READ_ONLY_NOT_VALIDATION_COHORT',PIT_ELIGIBLE=False)
            data['items']=self._enrich_display_names(day,data['items'])
            return code,data
        if p[0]=='market' and len(p)==2:
            pack=self.pack(day)
            if not pack:return self.missing(day,'/'.join(p),'DATED_MARKET_FACT_PACK_NOT_BOUND')
            manifest,facts=pack;kind=p[1]
            if facts is None:return self.missing(day,'/'.join(p),'DATED_MARKET_FACT_PACK_NOT_BOUND')
            if kind=='breadth':return 200,self.envelope(day,status='READY',data=facts['breadth'],source=facts['sources'],contract_id=facts['contract_id'])
            if kind=='indices':return self.paged(day,facts['indices'],q,source=facts['sources']['package'])
            if kind=='limits':
                rows=facts['limits']['rows'];state=q.get('limit_state')
                if state:rows=[row for row in rows if row.get('limit_state')==state]
                counts=facts['limits']['counts']
                return self.paged(day,rows,q,counts=counts,filter_state=state,filter_total=len(rows),
                    classifiable_denominator=sum(v for k,v in counts.items() if k!='UNKNOWN'),
                    tradable_rule_evaluable_denominator=counts.get('LIMIT_UP',0)+counts.get('LIMIT_DOWN',0)+counts.get('NOT_LIMIT',0),
                    source=facts['sources']['limits_0'])
            if kind=='ladders':
                code,data=self.paged(day,facts['ladders'],q,source={k:v for k,v in facts['sources'].items() if k.startswith('limits_')},intraday_touch='NOT_OBSERVABLE_FROM_DAILY')
                data['items']=self._enrich_display_names(day,data['items'])
                return code,data
        if path=='/api/v4/home':
            code,data=super().get(path,self._base_query(q));fw=self.source('forward',day);events=fw['events'];stocks={r['entity_id']:r for r in self.project('stocks',day)}
            # Explicit owner events only. NEW maps to Focus NEW, not PREWATCH/confirmation.
            # Select before copying the large stock field projection. This is the
            # same stable priority/entity order as prioritize_home_changes.
            selected_events={}
            for e in sorted((e for e in events if e.get('event') in HOME_EVENT_PRIORITY and e['entity_id'] in stocks),key=lambda e:(HOME_EVENT_PRIORITY[e['event']],e['entity_id'])):
                selected_events.setdefault(e['entity_id'],e)
            changes=[]
            for e in selected_events.values():
                row=dict(stocks[e['entity_id']]);row['fields']=dict(row['fields']);row['fields'].update(effective_event=owner_cell(e['event'],self.api.candidate['owners'][day]['forward'],'events.event',day),trade_date=owner_cell(day,self.api.candidate['owners'][day]['forward'],'events.trade_date',day));changes.append(row)
            sectors=self.project('sectors',day);native={r['sector_id']:r for r in self.source('sector',day)}
            rotations=[r for r in sectors if r['fields']['output_state']['value'] in ROTATIONS and r['fields']['output_state']['value']!=r['fields']['prior_rotation_state']['value']]
            rotations.sort(key=lambda r:(0 if r['fields']['output_state']['value'] in ('ROTATION_OUT','ROTATION_FAILED') else 1,-(r['fields'].get('sector_rs5',{}).get('value') or 0),r['entity_id']))
            covered=set();cards=[]
            for row in rotations[:10]:
                members=set(native[row['entity_id']]['member_ids']);related=[r for r in changes if r['entity_id'] in members];fresh=[r for r in related if r['entity_id'] not in covered]
                covered.update(r['entity_id'] for r in related)
                cards.append(dict(item=row,member_previews=related[:5],member_total=len(members),net_information_count=len(fresh),change_counts=dict(Counter(r['fields']['effective_event']['value'] for r in related))))
            independent=[r for r in changes if r['entity_id'] not in covered]
            data.update(
                changes=[home_summary(r,HOME_STOCK_SUMMARY_FIELDS) for r in independent[:30]],
                change_total=len(independent),
                risks=[home_summary(r,HOME_STOCK_SUMMARY_FIELDS) for r in changes if r['fields']['effective_event']['value'] in RISK_EVENTS][:30],
                net_information_count=len(changes),
                persistent_count=sum(e.get('event')=='PERSISTENT' for e in events),
                change_scope='EXPLICIT_FOCUS_EVENTS_AND_ROTATION_OWNER_DELTAS; FULL_STRUCTURE_CHANGE_DEBT_OPEN',
                sector_changes=[dict(item=home_summary(card['item'],HOME_SECTOR_SUMMARY_FIELDS),
                    member_previews=[home_summary(r,HOME_STOCK_SUMMARY_FIELDS) for r in card['member_previews']],
                    member_total=card['member_total'],net_information_count=card['net_information_count'],
                    change_counts=card['change_counts']) for card in cards],
                sector_change_total=len(rotations),
                rotations=[home_summary(r,HOME_SECTOR_SUMMARY_FIELDS) for r in rotations[:10]],
                rotation_total=len(rotations),
                source_bindings=dict(stock_changes=self.api.candidate['owners'][day]['forward'],sector_changes=self.api.candidate['owners'][day]['rotation']),
                rotation_validation='VALIDATION_ONGOING; NOT_INDEPENDENTLY_ACCEPTED')
            if isinstance(data.get('market'),dict):
                data['market']['regime_publication_status']='NOT_PUBLISHED_V4_03'
                data['market']['formal_risk_status']='SOURCE_INCOMPLETE'
                data['market']['formal_risk_reason']='DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT'
            data.setdefault('counts',{})
            data['counts']['radar']=dict(value=len(independent),quality='KNOWN',status='PARTIAL',scope='ACCEPTED_FOCUS_CHANGE_EVENTS_WITHOUT_TOP_ROTATION_COVERAGE',source=self.api.candidate['owners'][day].get('forward'),reason='FORMAL_RADAR_PRIORITY_NOT_PUBLISHED',href='/v4/research/radar')
            data['counts']['forward']=dict(value=None,quality='SOURCE_INCOMPLETE',status='NOT_GRANTED',scope='FORMAL_VALIDATION_COHORT',source=self.api.candidate['owners'][day].get('validation_cohort'),reason='NO_AUTHORIZED_COHORT_OWNER',href='/v4/research/focus#forward-cohort')
            data['gaps']=[g for g in data['gaps'] if g['domain'] not in ('home/changes','home/risks','home/net-information')]
            return code,annotate_home_readiness(data,
                cohort_authorized=bool(self.api.candidate['owners'][day].get('validation_cohort')))
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
            domain='stocks' if mode.startswith('stock') else 'sectors'
            a=self.resolve_dated_object(domain,asof,left)
            b=self.resolve_dated_object(domain,asof,right) if mode.endswith(('stock','sector')) else self.source('market',asof)
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
        return super().get(path,self._base_query(q))
