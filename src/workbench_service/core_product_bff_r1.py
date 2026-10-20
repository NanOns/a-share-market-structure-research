"""Dated read adapter over accepted owners. No permission or immutable head changes."""
from pathlib import Path
from urllib.parse import unquote
from collections import Counter
from copy import deepcopy
import json, gzip, re
from .operational_successor_bff_v1 import OperationalSuccessorBFFV1
from .r43_operational_bff import owner_cell
from .stock_views import aggregate
from .domain_views import CHANGE_EVENTS, RISK_EVENTS, ROTATIONS
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.validation_cohort_read_contract_r3 import read_statistics, read_authorized_statistics
from .research_hypotheses_r3 import competing_explanations
from .operational_risk_v1 import build_stock_family,build_sector_family,build_market_family

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
        market.setdefault('regime_publication_status','NOT_PUBLISHED_V4_03')
        market.setdefault('formal_risk_status','SOURCE_INCOMPLETE')
        market.setdefault('formal_risk_reason','DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT')
    # Focus weakens remain useful evidence, but they do not establish the
    # independent stock-structure, sector-ecology and market-pressure families.
    result['focus_risk_events']=result.get('focus_risk_events') or result.get('risks') or []
    result['focus_risk_scope']='FOCUS_OWNER_RISK_EVENTS_ONLY; NOT_COMPLETE_RISK_FAMILIES'
    if not result.get('risk_families'):
        result['risks']=[]
        result['risk_families']={key:dict(status='SOURCE_INCOMPLETE',numerator=0,denominator=0,coverage=0.0,value=None,
            reason='DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT')
            for key in ('STOCK_STRUCTURE_RISK','SECTOR_ECOLOGY_RISK','MARKET_PRESSURE_RISK')}
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

def mark_evaluated_sector_lifecycle(response):
    """Expose tested NONE states as evaluated, including prebuilt PG pages."""
    rows=list(response.get('items') or [])
    if isinstance(response.get('item'),dict):rows.append(response['item'])
    for row in rows:
        fields=row.get('fields') or {}
        for name in ('maturity','health'):
            cell=fields.get(name)
            if isinstance(cell,dict):
                cell['evaluated']=cell.get('quality')=='KNOWN' and cell.get('value') not in (None,'UNKNOWN')
    return response

def mark_stock_d2_semantics(response):
    rows=list(response.get('items') or [])
    if isinstance(response.get('item'),dict):rows.append(response['item'])
    for row in rows:
        fields=row.get('fields') or {};scenario=fields.get('scenario') or {};status=fields.get('scenario_status') or {}
        if isinstance(scenario,dict) and scenario.get('value')=='NONE':
            scenario['evaluated']=status.get('value')=='KNOWN' or status.get('quality')=='KNOWN'
        value=(fields.get('final_eligibility') or {}).get('value')
        detectors=(fields.get('detector_statuses') or {}).get('value')
        if value in ('TRUE','FALSE'):state=value;reason='OWNER_REDUCER_QUALIFICATION'
        elif 'NOT_IMPLEMENTED' in str(detectors):state='NOT_IMPLEMENTED';reason='REQUIRED_DETECTOR_NOT_IMPLEMENTED'
        else:state='UNKNOWN';reason='QUALIFICATION_INPUT_OR_DETECTOR_UNKNOWN'
        fields['qualification_state']=dict(value=state,quality='KNOWN' if state in ('TRUE','FALSE') else state,
            reason=reason,source=(fields.get('final_eligibility') or {}).get('source'))
    return response

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
    state='CURRENT_IDENTITY_PRESENT' if identity else 'CURRENT_IDENTITY_UNKNOWN'
    return dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value=state,quality='KNOWN' if identity else 'UNKNOWN',unit='state',as_of=day,
        reason=None if identity else 'CURRENT_IDENTITY_ROW_NOT_FOUND',source=source)

def identity_link_presentation(identity,aliases,symbol,source,day):
    """Describe the current code-to-security link, including historical aliases."""
    if not identity:
        return dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value='UNKNOWN',quality='SOURCE_INCOMPLETE',unit='state',as_of=day,
            reason='CURRENT_IDENTITY_ROW_NOT_FOUND',source=source)
    current=str(symbol or '').upper()
    code_aliases={str(value).upper() for value in (aliases or [])
        if isinstance(value,str) and re.fullmatch(r'(?:SH|SZ|BJ)\.\d{6}',value.upper())}
    for value in (identity.get('symbol'),identity.get('source_security_key')):
        if isinstance(value,str) and re.fullmatch(r'(?:SH|SZ|BJ)\.\d{6}',value.upper()):
            code_aliases.add(value.upper())
    if current and current in code_aliases:
        value='HISTORICAL_CODE_ALIAS_LINKED' if any(alias!=current for alias in code_aliases) else 'CURRENT_CODE_LINKED'
        reason='CURRENT_CODE_AND_DATED_ALIAS_RESOLVE_TO_ONE_SECURITY' if value.startswith('HISTORICAL') else 'CURRENT_CODE_MATCHES_IDENTITY'
    else:
        value='UNKNOWN';reason='CURRENT_CODE_NOT_LINKED_IN_IDENTITY_ALIASES'
    return dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value=value,quality='KNOWN' if value!='UNKNOWN' else 'SOURCE_INCOMPLETE',unit='state',as_of=day,reason=reason,source=source)

def code_status_presentation(identity,source,day):
    """Render whether the current symbol itself is new as of this date.

    Older Owner versions populated ``code_status=NEW_CODE_OBSERVED`` for rows
    merely present in the identity acquisition batch. That batch-level value
    cannot establish per-security code novelty, so dated identity facts are
    authoritative here; the raw Owner value remains available separately.
    """
    identity=identity or {}
    list_date=identity.get('list_date')
    first_seen=identity.get('first_seen_date')
    if list_date and list_date < day:
        value='EXISTING_VERIFIED_IDENTITY';quality='KNOWN';reason='DATED_IDENTITY_PREDATES_CURRENT_TRADE_DATE'
    elif list_date==day or first_seen==day:
        value='NEW_CODE_OBSERVED';quality='KNOWN'
        reason='LISTED_ON_CURRENT_TRADE_DATE' if list_date==day else 'FIRST_OBSERVED_ON_CURRENT_TRADE_DATE'
    else:
        value='UNKNOWN';quality='SOURCE_INCOMPLETE';reason='DATED_CODE_STATUS_NOT_PROVEN_BY_IDENTITY_DATES'
    return dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value=value,quality=quality,unit='state',as_of=day,reason=reason,source=source)

def identity_date_statuses(identity,source,day,owner_code_status=None):
    """Keep listing and first observation separate from per-symbol code status."""
    identity=identity or {}
    listing=identity.get('list_date')
    first_seen=identity.get('first_seen_date')
    confirmed_ipo=identity.get('confirmed_ipo_date')
    if listing==day: listing_value='LISTED_TODAY';listing_reason='LIST_DATE_EQUALS_TRADE_DATE'
    elif listing and listing<day: listing_value='LISTED_BEFORE';listing_reason='LIST_DATE_PRECEDES_TRADE_DATE'
    elif listing and listing>day: listing_value='NOT_YET_LISTED';listing_reason='LIST_DATE_AFTER_TRADE_DATE'
    else: listing_value='UNKNOWN';listing_reason='LIST_DATE_NOT_AVAILABLE'
    if first_seen==day: first_value='FIRST_OBSERVED_TODAY';first_reason='FIRST_SEEN_DATE_EQUALS_TRADE_DATE'
    elif first_seen and first_seen<day: first_value='OBSERVED_BEFORE';first_reason='FIRST_SEEN_DATE_PRECEDES_TRADE_DATE'
    else: first_value='UNKNOWN';first_reason='FIRST_SEEN_DATE_NOT_AVAILABLE_OR_AFTER_TRADE_DATE'
    if confirmed_ipo==day: ipo_value='CONFIRMED_IPO';ipo_reason='CONFIRMED_IPO_DATE_EQUALS_TRADE_DATE'
    elif listing==day: ipo_value='IPO_NOT_INDEPENDENTLY_CONFIRMED';ipo_reason='LIST_DATE_PRESENT_WITHOUT_CONFIRMED_IPO_DATE'
    elif listing and listing<day: ipo_value='NOT_IPO_TODAY';ipo_reason='LIST_DATE_PRECEDES_TRADE_DATE'
    else: ipo_value='UNKNOWN';ipo_reason='IPO_CONFIRMATION_DATE_NOT_AVAILABLE'
    owner_cell=owner_code_status if isinstance(owner_code_status,dict) else None
    raw=owner_cell.get('value') if owner_cell else identity.get('code_status')
    raw_source=(owner_cell.get('source') or source) if owner_cell else source
    return {
        'listing_status':dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value=listing_value,quality='KNOWN' if listing_value!='UNKNOWN' else 'SOURCE_INCOMPLETE',unit='state',as_of=day,reason=listing_reason,source=source),
        'first_seen_status':dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value=first_value,quality='KNOWN' if first_value!='UNKNOWN' else 'SOURCE_INCOMPLETE',unit='state',as_of=day,reason=first_reason,source=source),
        'ipo_confirmation_status':dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value=ipo_value,quality='KNOWN' if ipo_value not in ('UNKNOWN','IPO_NOT_INDEPENDENTLY_CONFIRMED') else 'SOURCE_INCOMPLETE',unit='state',as_of=day,reason=ipo_reason,source=source),
        'owner_code_status':dict(contract_id='V4_IDENTITY_PRESENTATION_R2',value=raw,quality=(owner_cell.get('quality') if owner_cell else None) or ('OBSERVED' if raw is not None else 'SOURCE_INCOMPLETE'),unit='source_state',as_of=day,reason='RAW_OWNER_CODE_STATUS_PRESERVED_WITHOUT_IDENTITY_INTERPRETATION' if raw is not None else 'OWNER_CODE_STATUS_MISSING',source=raw_source),
    }

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
        fields.update(identity_date_statuses(observation,source,day,
            # A presentation value from an older index is never evidence for
            # the distinct raw Owner field. Missing raw provenance stays null.
            owner_code_status=observation.get('owner_code_status') if isinstance(observation,dict) else None))
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

    def _rotation_owner_summary(self,day):
        rows=self.source('rotation',day)
        values=[r.get('rotation',{}) for r in rows]
        current=Counter(str(r.get('output_state') or 'UNKNOWN') for r in values)
        prior=Counter(str(r.get('prior_rotation_state') or 'UNKNOWN') for r in values)
        reasons=Counter(code for r in values for code in (r.get('reason_codes') or []))
        owner=self.api.candidate['owners'][day].get('rotation')
        sector_rows=self.source('sector',day)
        from workbench_analysis.operational_successor_v1 import rotation_display_completeness
        coverage=rotation_display_completeness(rows,sector_rows or [],rotation_owner_bound=bool(owner),
            sector_owner_bound=bool(self.api.candidate['owners'][day].get('sector')))
        complete=bool(coverage['complete'])
        return dict(owner_bound=bool(owner),owner_bytes=owner.get('bytes') if owner else None,
            owner_sha256=owner.get('sha256') if owner else None,
            total=len(values),current_states=dict(current),prior_states=dict(prior),
            expected_total=coverage['expected_total'],covered_total=coverage['covered_total'],
            missing_total=coverage['missing_total'],unexpected_total=coverage['unexpected_total'],
            duplicate_total=coverage['duplicate_total'],
            unknown_reasons=dict(reasons),
            automatic_acceptance_contract='V4_ROTATION_PIPELINE_AUTO_ACCEPTANCE_R1',
            automatic_acceptance_state='AUTO_ACCEPTED_WITH_LIMITATIONS' if complete else 'BLOCKED_INCOMPLETE_OWNER_OUTPUT',
            automatic_acceptance_scope='OWNER_DATA_COMPLETE_FOR_DISPLAY_ONLY' if complete else 'INCOMPLETE_OR_UNBOUND',
            numeric_acceptance='NOT_INDEPENDENTLY_VALIDATED',formal_publication=False,
            validation='OWNER_DATA_COMPLETE_FOR_DISPLAY_ONLY' if complete else 'OWNER_PIPELINE_INCOMPLETE')

    def _apply_rotation_auto_acceptance(self,response,day):
        """Replace only the old human-review mask with bound Owner values."""
        if getattr(self.api,'automatic_domain_disposition',{}).get('rotation')!='AUTO_ACCEPTED_WITH_LIMITATIONS':
            return response
        result=deepcopy(response)
        owner=self.api.candidate['owners'][day]['rotation']
        rotation_rows={row['sector_id']:row.get('rotation',{}) for row in self.source('rotation',day)}
        page_rows=result.get('items')
        rows=list(page_rows or [])
        item=result.get('item')
        if isinstance(item,dict) and not any(row is item for row in rows):rows.append(item)
        for row in rows:
            fields=row.get('fields') or {}
            rotation=rotation_rows.get(row.get('entity_id'))
            if not rotation:continue
            reason_codes=rotation.get('reason_codes') or []
            for name in ('output_state','prior_rotation_state'):
                cell=fields.get(name) or {}
                if cell.get('reason')!='FULL_ROTATION_NOT_INDEPENDENTLY_ACCEPTED':continue
                value=rotation.get(name,'UNKNOWN')
                unknown=value in (None,'UNKNOWN')
                fields[name]=owner_cell(dict(value=value,quality='UNKNOWN' if unknown else 'KNOWN',
                    reason=(reason_codes[0] if reason_codes else 'REQUIRED_QUALITY_UNAVAILABLE') if unknown else None,
                    unit='state'),owner,'rotation.'+name,day)
        return result

    @staticmethod
    def _base_query(query):
        # These filters are validated and consumed by their product routes. The
        # legacy Context allowlist is intentionally kept narrow. Focus page
        # controls also carry their event filter and event-page offset in the
        # URL; those parameters belong only to /focus/events and must not make
        # the independent Focus list request fail validation.
        return {k:v for k,v in query.items() if k not in
                ('event','validity','limit_state','event_state','events_offset')}

    def _display_identity_map(self,day,rows,*,key_fields=('entity_id','security_id'),domain='stocks'):
        keys=[next((row.get(k) for k in key_fields if row.get(k)),None) for row in rows]
        index=self._read_index_r2(day)
        if index is not None:return index.display_identities(domain,keys)
        from workbench_db.v4_read_index_r1 import load as load_index_r1
        legacy=load_index_r1(self.api.root,self.api.token,day,
            allow_missing=day!=self.api.candidate['accepted_trade_date'])
        if legacy is None:return {}
        return legacy.display_identities(domain,keys)

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
        base=self._bind_live_head_scope(base)
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

    def _bind_live_head_scope(self,response):
        """Bind immutable indexed rows to the current formal-head decision."""
        result=deepcopy(response)
        context_reader=getattr(self.api,'context',None)
        if not callable(context_reader):return result
        live=context_reader()
        result['production_accepted']=bool(live.get('production_accepted'))
        current=result.get('context')
        if isinstance(current,dict):
            current=deepcopy(current)
            for key in ('read_scope','formal_head_match','formal_head_date',
                        'production_accepted','independent_external_acceptance',
                        'rotation_validation_state'):
                if key in live:
                    current[key]=live[key]
            result['context']=current
        return result

    def _forward_candidate_late_preview(self):
        """Read-only R7 preview over the current candidate's late-captured Owners."""
        cached=getattr(self,"_forward_candidate_late_preview_cache",None)
        candidate=self.api.candidate
        day=candidate.get('accepted_trade_date')
        token=self.api.token
        cache_key=(token,day)
        if isinstance(cached,dict) and cache_key in cached:return cached[cache_key]
        from collections import Counter
        from workbench_analysis.r43_owner_replay import checked,load
        from workbench_analysis.r43_operational_publication import digest
        from workbench_analysis.market_source_acquisition import official_sessions
        from workbench_analysis.forward_r7 import build_daily_universe,make_observation_id
        from workbench_analysis.forward_r7_pipeline import (accepted_prices_with_status,
            build_schedules, summarize_universe)
        root=self.api.root
        if not day or not candidate.get('source_registry',{}).get(day):
            raise ValueError('FORWARD_CANDIDATE_SOURCE_REGISTRY_REQUIRED')
        if digest(candidate)!=token:
            raise ValueError('FORWARD_LATE_CANDIDATE_BINDING_MISMATCH')
        freeze_binding=candidate['source_registry'][day].get('freeze')
        if not freeze_binding:
            raise ValueError('FORWARD_CANDIDATE_FREEZE_BINDING_REQUIRED')
        freeze=load(checked(root,freeze_binding))
        captured_at=freeze.get('observed_at')
        if (freeze.get('target_session')!=day or not captured_at
                or freeze.get('AS_RECORDED') is not False or freeze.get('PIT_ELIGIBLE') is not False):
            raise ValueError('FORWARD_LATE_CAPTURE_CLOCK_REQUIRED')
        sessions=official_sessions(root)
        candidate_dates=candidate.get('published_sessions',[])
        if day not in sessions or day not in candidate_dates:
            raise ValueError('FORWARD_CANDIDATE_DATE_NOT_IN_SESSION_CHAIN')
        candidate_index=candidate_dates.index(day)
        if candidate_index<1:
            raise ValueError('FORWARD_CANDIDATE_PREDECESSOR_REQUIRED')
        previous=candidate_dates[candidate_index-1]
        read=lambda domain,target:self.api.read(domain,target,token)
        current={name:read(name,day)['rows'] for name in ('raw','core','sector','lifecycle')}
        prior={name:read(name,previous)['rows'] for name in ('raw','core','sector','lifecycle')}
        rows=build_daily_universe(trade_date=day,stock_rows=current['core'],raw_rows=current['raw'],
            sector_rows=current['sector'],prior_stock_rows=prior['core'],prior_raw_rows=prior['raw'],
            prior_sector_rows=prior['sector'],bindings=self.api.candidate['owners'][day],
            captured_at=captured_at,lane='LATE_OBSERVED_NOT_PIT',membership_basis='MEMBERSHIP_RETRO')
        for row in rows:
            row['evidence_class']='LATE_OBSERVED_NOT_PIT'
            row['evidence_lane']='LATE_OBSERVED_NOT_PIT'
            row['PIT_ELIGIBLE']=False
        formal=json.loads((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
        formal_dates=formal.get('published_sessions',[])
        prices={previous:accepted_prices_with_status(prior['raw'],prior.get('lifecycle')),
                day:accepted_prices_with_status(current['raw'],current.get('lifecycle'))}
        schedules=build_schedules(rows,day,sessions,prices,captured_at,accepted_source_dates=formal_dates)
        schedule_counts=dict(Counter(item['schedule_status'] for item in schedules))
        observations={make_observation_id(row):row for row in rows}
        settlement_items=[]
        for schedule in schedules[:30]:
            row=observations[schedule['observation_id']]
            settlement_items.append(dict(schedule,T0=day,entity_id=row['entity_id'],
                display_name=row.get('display_name') or row.get('symbol') or row.get('sector_id'),
                event_code=row['event_code'],evidence_class='LATE_OBSERVED_NOT_PIT'))
        ranked=sorted(rows,key=lambda item:(item['status']!='MATCH',item['status']=='UNKNOWN',
            item['entity_type']!='STOCK',item['entity_id']))
        preview=ranked[:30]
        identities={}
        index=self._read_index_r2(day)
        if index is not None:
            identities.update(index.display_identities('stocks',[row['entity_id'] for row in preview
                if row['entity_type']=='STOCK']))
            identities.update(index.display_identities('sectors',[row['entity_id'] for row in preview
                if row['entity_type']=='SECTOR']))
        for row in preview:
            row['display_name']=identities.get(row['entity_id'],{}).get('display_name') or row.get('symbol') or row.get('sector_id')
        names={row['entity_id']:row['display_name'] for row in preview}
        for row in settlement_items:
            row['display_name']=names.get(row['entity_id'],row['display_name'])
        result=dict(status='CANDIDATE_ONLY_LATE_OBSERVED',trade_date=day,captured_at=captured_at,
            lane='LATE_OBSERVED_NOT_PIT',PIT_ELIGIBLE=False,AS_RECORDED=False,
            source_contract='V4_FORWARD_PIPELINE_R7_R1',source_hashes={k:v['sha256'] for k,v in self.api.candidate['owners'][day].items()
                if isinstance(v,dict) and v.get('sha256')},total=len(rows),
            summary=summarize_universe(rows),status_counts=dict(Counter(row['status'] for row in rows)),
            event_counts=dict(Counter(row['event_code'] for row in rows)),
            settlement_schedule_counts=schedule_counts,
            settlement_total=len(schedules),settlement_items=settlement_items,
            settlement_source_state='DUE_SESSIONS_NOT_ACCEPTED_BY_FORMAL_HEAD',
            items=preview,limit=30,offset=0,has_next=len(rows)>30,
            status_scope='CANDIDATE_OBSERVATION_ONLY; NOT_FORMALLY_PUBLISHED; NOT_PIT')
        if not isinstance(cached,dict):cached={}
        cached[cache_key]=result
        self._forward_candidate_late_preview_cache=cached
        return result

    def _forward_r7_read(self,path,q,day):
        if path not in ('/api/v4/forward/statistics','/api/v4/forward/observations',
                        '/api/v4/forward/settlement','/api/v4/forward/fep'):
            return None
        if path=='/api/v4/forward/observations':
            lane_alias={'historical':'RETROSPECTIVE_RESEARCH','live':'LIVE_OOS'}
            lane=q.get('lane')
            if lane not in lane_alias:
                raise ValueError('INVALID_FORWARD_EVIDENCE_LANE')
            try:
                from workbench_db.forward_r7_store import ForwardR7Store
                result=ForwardR7Store(self.api.root).read_universe(
                    lane=lane_alias[lane],trade_date=q.get('trade_date',day),rule=q.get('rule'),
                    status=q.get('status'),limit=int(q.get('limit',30)),offset=int(q.get('offset',0)),
                    revision=int(q['revision']) if q.get('revision') else None)
                return 200,self.envelope(day,status=result['status'],data=result,items=result['items'],
                    total=result['total'],offset=result['offset'],limit=result['limit'],
                    has_next=result['has_next'],lane=lane,evidence_class=lane_alias[lane],
                    research_contract_id='V4_FORWARD_PIPELINE_R7_R1')
            except Exception as exc:
                return 200,self.envelope(day,status='ERROR',reason='FORWARD_PG_READ_FAILED',
                    error_code=type(exc).__name__,data=dict(status='ERROR',items=None,total=None,observed_count=None),
                    items=None,total=None,write_authorized=False,PIT_ELIGIBLE=False)
        if path=='/api/v4/forward/statistics':
            try:
                from workbench_db.forward_r7_store import ForwardR7Store
                store=ForwardR7Store(self.api.root)
                counts=store.read_counts()
                matured_count=store.read_matured_count()
                historical=store.read_universe(lane='RETROSPECTIVE_RESEARCH',trade_date=q.get('trade_date',day),
                    rule=q.get('rule'),status=q.get('status'),limit=min(30,int(q.get('limit',30))),
                    offset=int(q.get('offset',0)))
                live=store.read_universe(lane='LIVE_OOS',trade_date=q.get('trade_date',day),
                    rule=q.get('rule'),status=q.get('status'),limit=min(30,int(q.get('limit',30))),
                    offset=int(q.get('offset',0)))
                plan=__import__('workbench_analysis.forward_r7_pipeline',
                    fromlist=['next_capture_plan']).next_capture_plan(self.api.root)
                data=dict(status='READY',
                    historical=dict((counts.get('historical') or {}),items=historical['items'],
                        page_total=historical['total'],offset=historical['offset'],limit=historical['limit'],
                        has_next=historical['has_next'],evidence_class='RETROSPECTIVE_RESEARCH'),
                    live=dict((counts.get('live') or {}),items=live['items'],page_total=live['total'],
                        offset=live['offset'],limit=live['limit'],has_next=live['has_next'],
                        next_capture=plan,evidence_class='LIVE_OOS',late=counts.get('late')),
                    published_generation=counts.get('published_generation'),
                    published_t0=counts.get('published_t0'),matured_settlement_count=matured_count,
                    source=counts.get('source_run_id'))
                try:
                    data['candidate_late_observation']=self._forward_candidate_late_preview()
                except Exception as exc:
                    data['candidate_late_observation']=dict(status='UNAVAILABLE',
                        error_code=type(exc).__name__,PIT_ELIGIBLE=False)
                return 200,self.envelope(day,status='READY',data=data,
                    contract_id='V4_FORWARD_STATISTICS_R7_R1',source='PG_PUBLISHED_READ_INDEX',
                    write_authorized=False,PIT_ELIGIBLE=False)
            except Exception as exc:
                data=dict(status='ERROR',historical=None,live=None,observed_count=None,
                    reason='PG_FORWARD_READ_INDEX_UNAVAILABLE',error_code=type(exc).__name__)
                return 200,self.envelope(day,status='ERROR',data=data,
                    contract_id='V4_FORWARD_STATISTICS_R7_R1',source=None,
                    write_authorized=False,PIT_ELIGIBLE=False)
        if path=='/api/v4/forward/fep':
            from workbench_analysis.fep_r7_read import read_r7_fep
            try:
                from workbench_db.forward_r7_store import ForwardR7Store
                store=ForwardR7Store(self.api.root)
                counts=store.read_counts()
                projections=store.read_fep_projections()
                result=read_r7_fep(self.api.root,current_counts=counts)
                if projections.get('items'):
                    result['pg_projection_status']='READY'
                    result['pg_historical_baselines']=projections['items']
                else:
                    result['pg_projection_status']='DATA_MISSING'
                    result['historical_baselines']=[]
                    result['missing_inputs'].append('PG_PUBLISHED_FEP_RESEARCH_PROJECTION')
                return 200,self.envelope(day,status='READY' if result['models'] else 'DATA_MISSING',
                    data=result,contract_id='V4_FORWARD_FEP_RESEARCH_READ_R7_R1',
                    source=result.get('source'),priority_v1_unchanged=True,
                    write_authorized=False,PIT_ELIGIBLE=False)
            except Exception as exc:
                result=read_r7_fep(self.api.root)
                result['historical_baselines']=[]
                result['pg_projection_status']='ERROR'
                result['missing_inputs'].append('PG_PUBLISHED_FEP_RESEARCH_PROJECTION')
                return 200,self.envelope(day,status='DATA_MISSING',data=result,
                    contract_id='V4_FORWARD_FEP_RESEARCH_READ_R7_R1',error_code=type(exc).__name__,
                    source=result.get('source'),priority_v1_unchanged=True)
        lane_alias={'historical':'RETROSPECTIVE_RESEARCH','live':'LIVE_OOS'}
        try:
            from workbench_db.forward_r7_store import ForwardR7Store
            result=ForwardR7Store(self.api.root).read_settlement(
                lane=lane_alias.get(q.get('lane')) if q.get('lane') else None,
                trade_date=q.get('trade_date',day),horizon=int(q['horizon']) if q.get('horizon') else None,
                status=q.get('status'),limit=int(q.get('limit',30)),offset=int(q.get('offset',0)),
                revision=int(q['revision']) if q.get('revision') else None,
                settlement_revision=int(q['settlement_revision']) if q.get('settlement_revision') else None)
            return 200,self.envelope(day,status=result['status'],data=result,items=result['items'],
                total=result['total'],offset=result['offset'],limit=result['limit'],
                has_next=result['has_next'],counts=result['counts'],aggregates=result['aggregates'],
                price_basis='NOMINAL_UNADJUSTED_CLOSE',write_authorized=False)
        except Exception as exc:
            return 200,self.envelope(day,status='ERROR',reason='FORWARD_SETTLEMENT_PG_READ_FAILED',
                error_code=type(exc).__name__,data=dict(observed_count=None,matured_count=None,outcomes=None),
                items=None,total=None,write_authorized=False)

    def get(self,path,query):
        from workbench_db.v4_read_index_r2 import validate_query
        from workbench_db.v4_read_index_r1 import load as load_index_r1
        day=validate_query({k:v for k,v in query.items() if k not in ('event_state','events_offset','scope','rankability')},
                           self.api.token,self.api.candidate['published_sessions'],
                           self.api.candidate['accepted_trade_date'],path)
        forward_response=self._forward_r7_read(path,query,day)
        if forward_response is not None:return forward_response
        index_route=(path in ('/api/v4/context','/api/v4/home','/api/v4/stocks','/api/v4/sectors','/api/v4/focus','/api/v4/radar','/api/v4/radar/priority') or
                     path.startswith('/api/v4/stocks/') or path.startswith('/api/v4/sectors/') or path.startswith('/api/v4/focus/'))
        index_r2=self._read_index_r2(day) if index_route else None
        if path=='/api/v4/radar/priority' and not getattr(self,'building_read_index',False):
            if index_r2 is None:raise ValueError('READ_INDEX_R2_PRIORITY_CONTEXT_NOT_PREPARED')
            context=index_r2.response('/api/v4/context')
            if context is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
            from workbench_db.v4_operational_risk_pg_r1 import load_priority
            binding,priority=load_priority(self.api.root,self.api.token,day)
            scope=query.get('scope','stocks')
            if scope not in ('stocks','sectors'):raise ValueError('RESEARCH_PRIORITY_SCOPE_INVALID')
            subset=priority[scope];rankability=query.get('rankability','RANKABLE')
            if rankability not in ('RANKABLE','NOT_RANKABLE'):raise ValueError('RESEARCH_PRIORITY_RANKABILITY_INVALID')
            rows=subset.get('all_items',[]) if rankability=='RANKABLE' else subset.get('not_rankable_rows',[])
            offset=int(query.get('offset',0));limit=int(query.get('limit',30))
            if not 0<=offset<=1000000 or not 1<=limit<=200:raise ValueError('INVALID_QUERY_BOUND')
            items=rows[offset:offset+limit]
            response={k:context[k] for k in ('context','context_token','production_accepted','source_quality') if k in context}|{
                'status':'READY' if items or not rows else 'EMPTY_VALID','contract_id':priority['contract_id'],
                'priority_owner':binding,'rule':priority['rule'],'market_permission':priority['market_permission'],
                'scope':scope,'rankability':rankability,'total':len(rows),'rankable_total':subset['rankable'],
                'not_rankable_total':subset['not_rankable'],'offset':offset,'limit':limit,
                'has_next':offset+len(items)<len(rows),'items':items,'T0':day,'context_token':self.api.token}
            return 200,self._bind_live_head_scope(response)
        if (index_r2 is not None and path.startswith('/api/v4/stocks/') and
                path.endswith(('/profile','/evidence','/why-not','/why-not-prewatch'))):
            parts=[unquote(part) for part in path.split('/') if part]
            if len(parts)==5:return self._r2_stock_profile(index_r2,day,parts[3])
        if path=='/api/v4/radar' and not getattr(self,'building_read_index',False):
            if index_r2 is None:raise ValueError('READ_INDEX_R2_RADAR_NOT_PREPARED')
            context=index_r2.response('/api/v4/context')
            if context is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
            page=index_r2.page('radar',query)
            response={k:context[k] for k in ('context','context_token','production_accepted','source_quality') if k in context}|page|{
                'contract_id':'V4_ACCEPTED_FOCUS_RADAR_PAGE_R1','source':self.api.candidate['owners'][day].get('forward'),
                'scope':'ACCEPTED_FOCUS_EVENTS_WITHOUT_TOP_ROTATION_COVERAGE','producer_status':'FORMAL_RADAR_PRIORITY_NOT_PUBLISHED'}
            return 200,self._bind_live_head_scope(response)
        index=index_r2 if index_r2 is not None else None if getattr(self,'building_read_index',False) or not index_route or path=='/api/v4/radar' else load_index_r1(self.api.root,self.api.token,day,allow_missing=day!=self.api.candidate['accepted_trade_date'])
        if index is not None and path in ('/api/v4/context','/api/v4/home','/api/v4/stocks','/api/v4/sectors','/api/v4/focus'):
            if path in ('/api/v4/context','/api/v4/home'):
                response=index.response(path)
                if response is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
                for gap in response.get('gaps',[]):
                    domain=gap.get('domain')
                    owner_name={'rotation':'rotation','forward':'forward','sectors':'sector','stocks':'core','focus':'forward'}.get(domain)
                    owner=self.api.candidate['owners'][day].get(owner_name) if owner_name else None
                    if owner:
                        gap['producer_binding_status']='BOUND'
                        gap['ui_presentation']='来源已接入；当前域仍在独立验证，未作为已接受结果发布'
                        gap['next_task']='Complete source QA and independent validation before publishing this domain'
                        gap.pop('missing_owner',None)
                if index_r2 is None:response=dict(response,read_index_status=self._read_index_r2_state(day),
                    read_index_capability=LEGACY_R1_READ_CAPABILITY)
                if path=='/api/v4/home':
                    response['rotation_owner_summary']=self._rotation_owner_summary(day)
                    cohort_ref=self.api.candidate['owners'][day].get('validation_cohort')
                    response=annotate_home_readiness(response,cohort_authorized=bool(cohort_ref))
                    try:
                        from workbench_db.v4_operational_risk_pg_r1 import load as load_risk_owner
                        risk_binding,risk_owner=load_risk_owner(self.api.root,self.api.token,day)
                        families=risk_owner['families'];response['risk_families']=families;response['risk_owner_source']=risk_binding
                        response['focus_risk_scope']='FOCUS_OWNER_RISK_EVENTS_ONLY; NOT_COMPLETE_RISK_FAMILIES'
                        response['risks']=[home_summary(dict(entity_id=item.get('entity_id'),display_name=item.get('display_name'),symbol=item.get('symbol'),
                            fields={'effective_event':{'value':item['change'],'quality':'KNOWN','reason':item.get('reason_code')},
                                'prior_state':{'value':item.get('prior_state'),'quality':'KNOWN' if item.get('prior_state') else 'SOURCE_INCOMPLETE'},
                                'current_state':{'value':item.get('current_state'),'quality':'KNOWN'},
                                'risk_family':{'value':family_name,'quality':'KNOWN'}},source=item.get('source')),
                                HOME_STOCK_SUMMARY_FIELDS)
                            for family_name,family in families.items() for item in family.get('changes',[])][:30]
                        if isinstance(response.get('market'),dict):
                            market_family=families.get('MARKET_PRESSURE_RISK',{})
                            response['market']['regime_publication_status']='FACT_AXES_OBSERVED_COMPOSITE_UNACCEPTED'
                            response['market']['formal_risk_status']=market_family.get('status','SOURCE_INCOMPLETE')
                            response['market']['four_axis_scope']='OBSERVED_V4_FACT_AXES; COMPOSITE_REGIME_CANDIDATE_UNACCEPTED'
                    except (OSError,ValueError,KeyError,TypeError):
                        response['risk_owner_source']={'status':'SOURCE_INCOMPLETE','reason':'IMMUTABLE_PG_RISK_OWNER_NOT_BOUND'}
                    try:
                        from workbench_db.forward_r7_store import ForwardR7Store
                        forward_store=ForwardR7Store(self.api.root)
                        forward_counts=forward_store.read_counts()
                        settled_count=forward_store.read_matured_count()
                        history=forward_counts.get('historical')
                        live=forward_counts.get('live')
                        response.setdefault('counts',{})['forward']=dict(
                            value=(history or {}).get('count'),quality=forward_counts.get('status'),
                            matured_settlement_count=settled_count,
                            latest_live_observation_T0=(live or {}).get('latest_t0'),
                            last_successful_increment_T0=forward_counts.get('published_t0'),
                            source=forward_counts.get('source_run_id'),
                            historical_research_count=(history or {}).get('count'),
                            live_frozen_count=(live or {}).get('count'),updated_at=response.get('updated_at'),
                            href='/v4/research/forward')
                    except Exception as exc:
                        response.setdefault('counts',{})['forward']=dict(
                            value=None,quality='ERROR',status='DATA_MISSING',scope='R7_LANES',
                            historical_research_count=None,live_frozen_count=None,
                            matured_settlement_count=None,reason=type(exc).__name__,
                            updated_at=response.get('updated_at'),href='/v4/research/forward')
                return 200,self._bind_live_head_scope(response)
            response=index.response('/api/v4/context')
            if response is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
            response={k:v for k,v in response.items() if k in ('context','context_token','production_accepted','source_quality')}
            response.update(index.page(path.rsplit('/',1)[-1],query))
            if path=='/api/v4/stocks':response=mark_stock_d2_semantics(normalize_indexed_code_status(response,day))
            if index_r2 is None:response.update(read_index_status=self._read_index_r2_state(day),
                read_index_capability=LEGACY_R1_READ_CAPABILITY)
            if path=='/api/v4/focus':
                extra=index.response('/api/v4/focus-meta')
                if extra is None:raise ValueError('READ_INDEX_FOCUS_NOT_PREPARED')
                response.update(extra)
            if path=='/api/v4/sectors':
                response=self._apply_rotation_auto_acceptance(response,day)
                response=mark_evaluated_sector_lifecycle(response)
            return 200,self._bind_live_head_scope(response)
        code,data=self._get_product(path,query)
        if path=='/api/v4/candidates/cohort' and code==200:
            try:
                from workbench_db.forward_r7_store import ForwardR7Store
                audit=ForwardR7Store(self.api.root).read_audit_dates(
                    limit=int(query.get('limit',30)),offset=int(query.get('offset',0)))
                data['r7_source_audit']=audit
                data['r7_capture_plan']=__import__('workbench_analysis.forward_r7_pipeline',
                    fromlist=['next_capture_plan']).next_capture_plan(self.api.root)
                data['r7_source_status']=audit['status']
            except Exception as exc:
                data['r7_source_status']='ERROR'
                data['r7_source_audit']=dict(status='ERROR',items=None,total=None,reason=type(exc).__name__)
                data['r7_capture_plan']=dict(status='PENDING_REAL_SESSION',
                    planned_trade_date=None,reason='OFFICIAL_CALENDAR_UNAVAILABLE')
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
        if path.startswith('/api/v4/sectors/') and code==200:data=mark_evaluated_sector_lifecycle(data)
        if path.startswith('/api/v4/stocks/') and code==200:data=mark_stock_d2_semantics(data)
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
        sector_lifecycle={}
        if domain=='sectors':
            lifecycle_key=('sector-lifecycle-pg-owner-r1',self.api.token,day)
            if lifecycle_key not in self.api.cache:
                try:
                    from workbench_db.v4_sector_lifecycle_pg_r1 import load as load_sector_lifecycle
                    self.api.cache[lifecycle_key]=load_sector_lifecycle(self.api.root,self.api.token,day)
                except Exception as error:
                    # The independently published lifecycle feature degrades
                    # to explicit UNKNOWN if its PG owner is unavailable; it
                    # must not take down the otherwise valid sector route.
                    self.api.cache[lifecycle_key]=('UNAVAILABLE',type(error).__name__)
            loaded=self.api.cache[lifecycle_key]
            if loaded and loaded[0]!='UNAVAILABLE':sector_lifecycle=loaded[1]
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
                    raw_code_status=row['fields'].get('code_status')
                    row['identity_observation']={k:ident.get(k) for k in
                        ('first_seen_date','list_date','confirmed_ipo_date','code_status','metadata_status','alias_status')}
                    row['identity_observation']['owner_code_status']=raw_code_status
                    row['fields']['code_status']=code_status_presentation(ident,identity_ref_current,day)
                    row['fields'].update(identity_date_statuses(ident,identity_ref_current,day,owner_code_status=raw_code_status))
                    if ident.get('name'):
                        row.update(display_name=ident['name'],display_name_scope='OBSERVED_METADATA_NOT_PIT',
                                   display_name_source=identity_ref_current,display_name_quality='KNOWN')
                row['fields']['identity_status']=current_identity_presentation(ident,identity_ref_current,day)
                row['search_aliases']=sorted(aliases.get(row['entity_id'],set()))
                row['fields']['identity_link_status']=identity_link_presentation(ident,row['search_aliases'],row.get('symbol'),identity_ref_current,day)
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
                lifecycle=sector_lifecycle.get(row['entity_id'])
                if lifecycle:
                    pg_binding=loaded[0]
                    lifecycle_source=dict(contract_id=pg_binding['contract_id'],engine='postgresql',schema=pg_binding['schema'],
                        digest=pg_binding['digest'],producer_sha256=pg_binding['producer_sha256'],parameter_digest=pg_binding['parameter_digest'],
                        input_digest=lifecycle['input_digest'],T0=day)
                    for key in ('maturity','health'):
                        value=lifecycle[key]
                        row['fields'][key]=dict(value=value['current'],quality='KNOWN' if value['current'] not in ('UNKNOWN',None) else 'SOURCE_INCOMPLETE',
                            reason=';'.join(value['reason_codes']) if value['reason_codes'] else None,unit='state',as_of=day,source=lifecycle_source,
                            field=key,prior=value['prior'],current=value['current'],state_reason=lifecycle['state_reason'][key],
                            matched_predicates=value['matches'],unknown_predicates=value['unknown_predicates'],
                            evaluated=value['current'] not in ('UNKNOWN',None))
                    row['fields']['lifecycle_evidence_scope']=dict(value=lifecycle['evidence_scope'],quality='KNOWN',unit='scope',as_of=day,source=lifecycle_source)
                    row.setdefault('__detail_extras__',{})['lifecycle']=dict(contract_id=lifecycle['contract_id'],version=lifecycle['version'],
                        maturity=lifecycle['maturity'],health=lifecycle['health'],state_reason=lifecycle['state_reason'],
                        prior_state_reason=lifecycle['prior_state_reason'],failure_boundary=lifecycle['failure_boundary'],
                        input_completeness=lifecycle['input_completeness'],session_window=lifecycle['session_window'],
                        evidence_scope=lifecycle['evidence_scope'],AS_RECORDED=False,PIT_ELIGIBLE=False,source=lifecycle_source)
                elif loaded and loaded[0]=='UNAVAILABLE':
                    for key in ('maturity','health'):
                        row['fields'][key].update(value='UNKNOWN',quality='SOURCE_INCOMPLETE',reason='SECTOR_LIFECYCLE_PG_OWNER_UNAVAILABLE')
                    row.setdefault('__detail_extras__',{})['lifecycle']=dict(status='SOURCE_INCOMPLETE',reason='SECTOR_LIFECYCLE_PG_OWNER_UNAVAILABLE',
                        evidence_scope='CURRENT_RECONSTRUCTED_RESEARCH_ONLY',AS_RECORDED=False,PIT_ELIGIBLE=False)
                rotation=sector_rotation.get(row['entity_id'],{})
                row.setdefault('__detail_extras__',{})['why_now']=dict(prior_state=rotation.get('prior_rotation_state'),current_state=rotation.get('output_state'),
                    reason_codes=rotation.get('reason_codes',[]),predicates=rotation.get('predicates',{}),
                    fields={k:rotation.get('fields',{}).get(k) for k in ('dq5','breadth_delta1','breadth_delta3','ma20_delta3','base_seed_width_adjusted')},
                    source=self.api.candidate['owners'][day]['rotation'],scope='Observed reconstructed rule facts; not strict PIT or independently accepted full episode reduction')
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
                    response=normalize_indexed_code_status(response,day) if domain=='stocks' else response
                    return self._apply_rotation_auto_acceptance(response,day) if domain=='sectors' else response
                context=index.response('/api/v4/context')
                if context is None:raise ValueError('READ_INDEX_RESPONSE_NOT_PREPARED')
                base={k:v for k,v in context.items() if k in ('context','context_token','production_accepted','source_quality')}
                response={**base,**index.page(domain,q,entity=entity,sector=sector)}
                response=normalize_indexed_code_status(response,day) if domain=='stocks' else response
                return self._apply_rotation_auto_acceptance(response,day) if domain=='sectors' else response
            from workbench_db.v4_read_index_r1 import load as load_index
            index=load_index(self.api.root,self.api.token,day,allow_missing=day!=self.api.candidate['accepted_trade_date'])
            if index is not None:
                context=index.response('/api/v4/context')
                response={**{k:v for k,v in context.items() if k in ('context','context_token','production_accepted','source_quality')},
                        **index.page(domain,q,entity=entity,sector=sector),
                        'read_index_status':self._read_index_r2_state(day),
                        'read_index_capability':'R1 legacy summary; D2 detail fields may be unavailable'}
                return self._apply_rotation_auto_acceptance(response,day) if domain=='sectors' else response
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
            from .focus_episode_state_r1 import classify_episode
            owner_events=[e for e in self.source('forward',day).get('events',[]) if e.get('trade_date','9999')<=day]
            episodes=[dict(e,owner_event_state=classify_episode(e,owner_events)) for e in episodes]
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
                stock_identities=self._display_identity_map(day,data['items'])
                industry_ids=sorted({identity.get('primary_industry_id') for identity in stock_identities.values() if identity.get('primary_industry_id')})
                industry_identities=self._display_identity_map(day,[{'entity_id':value} for value in industry_ids],
                                                               key_fields=('entity_id',),domain='sectors')
                for item in data['items']:
                    identity=stock_identities.get(item.get('entity_id'),{})
                    industry_id=identity.get('primary_industry_id')
                    industry=industry_identities.get(industry_id,{}) if industry_id else {}
                    item['primary_industry_id']=industry_id
                    item['primary_industry_name']=industry.get('display_name')
                    item['primary_industry_status']='KNOWN' if industry.get('display_name') else 'UNKNOWN'
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
            # Keep accepted transitions distinct from a bound owner's observed
            # candidate state. Unknown required inputs must not be displayed as
            # an accepted event or as a missing source.
            rotation_owner_summary=self._rotation_owner_summary(day)
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
                rotation_owner_summary=rotation_owner_summary,
                source_bindings=dict(stock_changes=self.api.candidate['owners'][day]['forward'],sector_changes=self.api.candidate['owners'][day]['rotation']),
                rotation_validation=rotation_owner_summary['automatic_acceptance_state'])
            if isinstance(data.get('market'),dict):
                data['market']['regime_publication_status']='NOT_PUBLISHED_V4_03'
                data['market']['formal_risk_status']='SOURCE_INCOMPLETE'
                data['market']['formal_risk_reason']='DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT'
            data.setdefault('counts',{})
            # Three descriptive risk families use accepted V4 facts and their
            # own coverage denominators. Focus events remain a fourth view.
            risk_source={'stock_current':self.api.candidate['owners'][day].get('core'),
                'sector_current':self.api.candidate['owners'][day].get('sector'),
                'sector_lifecycle':self.api.candidate['owners'][day].get('sector'),
                'market':self.api.candidate['owners'][day].get('market')}
            sessions=self.api.candidate.get('published_sessions',[]);prior_day=None
            if day in sessions and sessions.index(day)>0:prior_day=sessions[sessions.index(day)-1]
            prior_stocks=self.project('stocks',prior_day) if prior_day else []
            risk_stock=build_stock_family(list(stocks.values()),prior_stocks,
                dict(current=risk_source['stock_current'],prior=self.api.candidate['owners'][prior_day].get('core') if prior_day else None),day)
            lifecycle={r['entity_id']:{'health':{'current':r.get('fields',{}).get('health',{}).get('value'),
                'prior':r.get('fields',{}).get('health',{}).get('prior')}} for r in sectors}
            risk_sector=build_sector_family(sectors,lifecycle,risk_source,day)
            risk_market=build_market_family(data.get('market'),risk_source['market'],day)
            families=(risk_stock,risk_sector,risk_market)
            family_payload={family['family']:family for family in families}
            try:
                from workbench_db.v4_operational_risk_pg_r1 import load as load_risk_owner
                risk_binding,risk_owner=load_risk_owner(self.api.root,self.api.token,day)
                family_payload=risk_owner['families']
                data['risk_owner_source']=risk_binding
            except (OSError,ValueError,KeyError,TypeError):
                data['risk_owner_source']={'status':'UNMATERIALIZED_CANDIDATE','reason':'IMMUTABLE_PG_RISK_OWNER_NOT_BOUND'}
            data['risk_families']=family_payload
            data['risks']=[home_summary(dict(entity_id=item['entity_id'],display_name=item.get('display_name'),symbol=item.get('symbol'),
                fields={'effective_event':{'value':item['change'],'quality':'KNOWN','reason':item['reason_code']},
                    'prior_state':{'value':item.get('prior_state'),'quality':'KNOWN' if item.get('prior_state') else 'SOURCE_INCOMPLETE'},
                    'current_state':{'value':item.get('current_state'),'quality':'KNOWN'},
                    'risk_family':{'value':family['family'],'quality':'KNOWN'}},source=item.get('source')),
                    HOME_STOCK_SUMMARY_FIELDS)
                for family in families for item in family.get('changes',[])][:30]
            data['focus_risk_events']=data.get('risks') or []
            data['focus_risk_scope']='FOCUS_OWNER_RISK_EVENTS_ONLY; NOT_COMPLETE_RISK_FAMILIES'
            if isinstance(data.get('market'),dict):
                data['market']['regime_publication_status']='FACT_AXES_OBSERVED_COMPOSITE_UNACCEPTED'
                data['market']['formal_risk_status']=risk_market['status']
                data['market']['formal_risk_reason']=risk_market.get('reason')
                data['market']['four_axis_scope']='OBSERVED_V4_FACT_AXES; COMPOSITE_REGIME_CANDIDATE_UNACCEPTED'
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
        if path=='/api/v4/forward':
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
        return super().get(path,self._base_query(q))
