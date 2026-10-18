"""FP03 BFF routing: one immutable snapshot per reader and request."""
import json
import os
import threading
import time
import psycopg
from collections import defaultdict, deque
from urllib.parse import unquote
from .production_v4 import ProductionV4ResearchReader
from .current_v4_context import SourceInvalid, digest
from .v4_daily_refresh import refresh_status
from .domain_views import home,sector_view
from .stock_views import chart,explanation
from .diagnostic_views import diagnostic
from .replay_views import replay,compare
from .focus_views import focus_view,KINDS
from .stock_views import timeline

class ResearchBFF:
    def __init__(self,root):
        self.root=root;self.lock=threading.RLock();self.reader=None;self.pointer_digest=None
        self.requests=defaultdict(deque)

    def current(self):
        with self.lock:
            schema=os.environ.get('V4_PG_RESEARCH_CANDIDATE_SCHEMA')
            if not schema:raise SourceInvalid('PG_CANDIDATE_SCHEMA_REQUIRED_NO_WORKSPACE_AUTHORITY')
            if self.reader is None or schema!=self.pointer_digest:
                self.reader=ProductionV4ResearchReader(self.root,pg_candidate_schema=schema)
                self.pointer_digest=schema
            return self.reader

    def allowed(self,host):
        with self.lock:
            now=time.monotonic();queue=self.requests[host]
            while queue and queue[0]<now-60:queue.popleft()
            if len(queue)>=240:return False
            queue.append(now);return True

    def get(self,path,query):
        from .production_v4 import snapshot_request_scope
        with snapshot_request_scope():
            return self._get(path,query)

    def get_with_reader(self,path,query,reader):
        """Serve one route through an explicitly injected candidate reader."""
        from .production_v4 import snapshot_request_scope
        with snapshot_request_scope():
            return self._get(path,query,reader=reader)

    def _get(self,path,query,reader=None):
        try:
            r=reader or self.current()
            # Validate context and parameter contracts even for singleton/diagnostic routes.
            parts=[unquote(p) for p in path.removeprefix('/api/v4/').split('/') if p]
            chart_route=len(parts)==3 and parts[0]=='stocks' and parts[2]=='chart'
            selection_route=len(parts)==1 and parts[0] in ('replay','compare')
            selection_keys={'as_of','view','left','snapshot_token','followup'} if parts and parts[0]=='replay' else {'as_of','view','mode','left','right','snapshot_token'}
            base_query={k:v for k,v in query.items() if not (chart_route and k in ('period','price_basis')) and not (selection_route and k in selection_keys)}
            validation=r.query('sources',base_query)
            if selection_route:
                for key in selection_keys:
                    if key in query and (not isinstance(query[key],str) or len(query[key])>120):raise ValueError('SELECTION_PARAMETER_BOUND')
                return 200,(replay if parts[0]=='replay' else compare)(r,query)
            if not parts:return 404,r.envelope(status='NOT_FOUND',code='ROUTE_NOT_FOUND')
            name=parts[0]
            if name=='context':
                if getattr(r,'pg_candidate_schema',None):
                    control=dict(status='SNAPSHOT_ONLY',next_completed_session=None,source_requests=0,
                        data_preserved=True,scope='PG_SNAPSHOT_ONLY_NO_DAILY_WORKER_STATUS',
                        accepted_input_date=r.context['accepted_trade_date'],indexed_trade_date=r.context['accepted_trade_date'])
                else:
                    progress=refresh_status(self.root)
                    control={k:progress[k] for k in ('status','next_completed_session','source_requests','data_preserved')}
                    control.update(scope='INPUT_PROGRESS_NOT_RESEARCH_CONTEXT',accepted_input_date=progress['context']['context']['accepted_trade_date'],indexed_trade_date=r.context['accepted_trade_date'])
                return 200,r.envelope(status='READY',counts=r.manifest['counts'],gaps=r.manifest['gaps'],daily_refresh=control)
            if name=='home':return 200,home(r)
            if name=='candidates' and len(parts)==2 and parts[1]=='cohort':
                # Keep the candidate endpoint on the same snapshot reader and
                # PG transaction as the rest of the V4 research API. It is a
                # read projection only; it does not enroll a formal cohort or
                # claim PIT/production authority.
                if not getattr(r,'pg_candidate_schema',None):
                    return 409,r.envelope(status='BLOCKED',code='PG_CANDIDATE_SNAPSHOT_REQUIRED',items=[])
                payload=r.query('forward',query)
                try:
                    from workbench_db.forward_r7_store import ForwardR7Store
                    audit=ForwardR7Store.read_candidate_source_audit(self.root,
                        trade_date=r.context['accepted_trade_date'],
                        limit=int(query.get('limit',100)),offset=int(query.get('offset',0)))
                except Exception as exc:
                    audit=dict(status='SOURCE_INCOMPLETE',items=[],total=0,
                        reason='R7_CANDIDATE_AUDIT_READ_FAILED',detail=type(exc).__name__,
                        binding='CANDIDATE_TRADE_DATE_ONLY',evidence_class='RETROSPECTIVE_RESEARCH')
                candidate_research=payload.get('candidate_research')
                if not isinstance(candidate_research,dict):candidate_research={}
                candidate_research['r7_source_audit']=audit
                payload['candidate_research']=candidate_research
                payload['r7_source_audit']=audit
                payload['r7_source_status']=audit['status']
                payload.update(contract_id='V4_PG_CANDIDATE_COHORT_READ_R1',
                    source_mode=r.context.get('source_mode'),production_accepted=False,
                    cohort_enrollment_enabled=False,PIT_ELIGIBLE=False)
                return 200,payload
            if name=='forward' and len(parts)>1 and parts[1] in ('statistics','plans','fep','risk'):
                publication=r.manifest.get('domain_features',{}).get('forward')
                if not publication:
                    if parts[1]=='statistics':
                        return 200,r.envelope(status='SOURCE_INCOMPLETE',data=dict(
                            enrollment_denominator=None,planned_horizon_denominator=None,
                            published_outcomes=None,published_enrollment_count=None,
                            mature_eligible_count=None,
                            reason='FORWARD_OWNER_PUBLICATION_NOT_BOUND_TO_CANDIDATE'))
                    return 200,r.envelope(status='SOURCE_INCOMPLETE',items=[],total=0,
                        offset=int(query.get('offset',0)),limit=int(query.get('limit',30)),
                        has_next=False,reason='FORWARD_OWNER_PUBLICATION_NOT_BOUND_TO_CANDIDATE')
                if parts[1]=='fep':return 200,r.envelope(status='SOURCE_INCOMPLETE',data=dict(publication['fep'],production_binding='NOT_BOUND_TO_CURRENT_PRODUCTION'),reason='NO_CURRENT_DAY_MODEL_INFERENCE_OWNER')
                if parts[1]=='statistics':return 200,r.envelope(status='READY',data=publication['statistics'])
                if parts[1]=='risk':return 200,r.query('stocks',query,summary=False)
                rows=publication['plans'];offset=int(query.get('offset',0));limit=int(query.get('limit',30))
                return 200,r.envelope(status='READY',items=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit,has_next=offset+limit<len(rows),scope='DUE_PLAN_ONLY_NOT_OUTCOMES')
            if name=='market' and len(parts)==2 and parts[1] in ('indices','breadth','limits','ladders','facts-events'):
                center=r.manifest.get('domain_features',{}).get('market_center')
                if not center:return 200,r.envelope(status='SOURCE_INCOMPLETE',reason='MARKET_CENTER_NOT_BOUND',items=[])
                key=parts[1].replace('-','_');payload=center[key];offset=int(query.get('offset',0));limit=int(query.get('limit',30))
                if isinstance(payload,list):return 200,r.envelope(status='READY',items=payload[offset:offset+limit],total=len(payload),offset=offset,limit=limit,has_next=offset+limit<len(payload),sources=center['sources'],mode=center['mode'])
                if key=='limits':return 200,r.envelope(status='READY',items=payload['rows'][offset:offset+limit],total=len(payload['rows']),offset=offset,limit=limit,has_next=offset+limit<len(payload['rows']),counts=payload['counts'],rule_ids=payload['rule_ids'],sources=center['sources'])
                return 200,r.envelope(status=payload.get('status','READY'),data=payload,sources=center['sources'],mode=center['mode'])
            if name=='focus' and len(parts)>1:
                if len(parts)==3 and parts[2] in KINDS:
                    return 200,focus_view(r,parts[1],parts[2],query)
                publication=r.manifest.get('domain_features',{}).get('focus')
                if publication:
                    if parts[1]=='events':
                        rows=[x for x in publication['events'] if x['trade_date']==r.context['trade_date']];offset=int(query.get('offset',0));limit=int(query.get('limit',30))
                        return 200,r.envelope(status='READY',items=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit,has_next=offset+limit<len(rows),permissions=publication['permissions'])
                    if len(parts)==3 and parts[2] in ('episodes','timeline','anchors','observations','outcomes'):
                        rows=[x for x in publication['episodes'] if x['entity_id']==parts[1]]
                        return 200,r.envelope(status='READY' if rows else 'EMPTY_VALID',items=rows,total=len(rows),has_next=False,permissions=publication['permissions'],write_block_reason=publication['write_block_reason'],legacy_history=publication['legacy_history'])
                elif parts[1]=='events':
                    return 200,r.envelope(status='SOURCE_INCOMPLETE',items=[],total=0,
                        offset=int(query.get('offset',0)),limit=int(query.get('limit',30)),
                        has_next=False,reason='FOCUS_OWNER_PUBLICATION_NOT_BOUND_TO_CANDIDATE')
            if name=='market' and len(parts)==1:return 200,r.envelope(status='READY' if r.manifest.get('domain_features',{}).get('market') else 'SOURCE_INCOMPLETE',market=r.manifest.get('domain_features',{}).get('market'))
            if name=='diagnostics':
                if len(parts)>1:
                    scoped=diagnostic(r,parts[1])
                    if scoped is not None:return 200,scoped
                if len(parts)>1 and parts[1]=='fields':return 200,r.envelope(status='READY',fields=r.manifest['field_registry'])
                if len(parts)>1 and parts[1]=='rules':return 200,r.envelope(status='READY',owners=r.manifest['owners'],source_contract_digest=r.manifest['source_contract_digest'])
                if len(parts)>1 and parts[1]=='parameters':return 200,r.envelope(status='READY',parameter_set_ids=['V4_08_ALGORITHM_PARAMETER_SET_R5'],scope='BOUND_SECTOR_OUTPUT_PARAMETERS',missing_scope='OTHER_PARAMETER_SETS_NOT_YET_PROJECTED')
                if len(parts)>1 and parts[1]=='legacy':return 200,r.envelope(status='READY',legacy_summary='/v4/legacy-summary',shadow='/v4/shadow',legacy_database='RETIRED')
                return 200,r.envelope(status='READY',sources=r.manifest['sources'],gaps=r.manifest['gaps'],publication_scope=r.manifest['publication_scope'])
            if name=='data-sources':return 200,r.query('sources',query)
            if name in ('replay','compare'):return 501,r.envelope(status='ENGINEERING_NOT_READY',code='FP12_CONTEXT_SELECTION_REQUIRED',items=[],total=0,has_next=False)
            if name=='radar' and len(parts)>1:
                return 200,r.query({'sectors':'sectors','stocks':'radar','events':'events'}.get(parts[1],''),query,summary=True)
            if name=='forward' and len(parts)>1 and parts[1] in ('settlement','outcomes'):return 200,r.query('settlement',query)
            if name not in ('stocks','sectors','events','radar','forward','focus','market','sources'):return 404,r.envelope(status='NOT_FOUND',code='ROUTE_NOT_FOUND')
            if len(parts)==1:return 200,r.query(name,query,summary=True)
            identity_query={k:v for k,v in base_query.items() if k in ('context_token','trade_date','release_id','model_namespace')}
            detail=r.query(name,identity_query,entity=parts[1])
            if not detail['total']:
                outside=name=='stocks' and r.known_identity(parts[1])
                return 404,r.envelope(status='OUTSIDE_CURRENT_POOL' if outside else 'NOT_FOUND',code='IDENTITY_OUTSIDE_CURRENT_DAILY_UNIVERSE' if outside else 'ENTITY_NOT_FOUND',items=[])
            item=detail['items'][0]
            if chart_route:return 200,chart(r,item,query)
            if name=='stocks' and len(parts)==3 and parts[2]=='timeline':return 200,timeline(r,item,query)
            if name=='stocks' and len(parts)>2 and parts[2] in ('profile','evidence','why-not','why-not-prewatch'):return 200,explanation(r,item)
            if name=='sectors' and len(parts)>2 and parts[2] in ('timeline','rotation-timeline','overlap'):return 200,sector_view(r,item,parts[2],query)
            if len(parts)==2 or parts[2] in ('profile','evidence','why-not','why-not-prewatch','rotation'):
                return 200,r.envelope(status='READY',item=item,eligibility=item['fields'].get('final_eligibility'),pool_membership='CURRENT_UNIVERSE',research_pool_eligibility='SEE_OWNER_FIELD')
            if parts[2]=='members' and name=='sectors':return 200,r.query('stocks',query,sector=item['entity_id'],summary=True)
            if parts[2] in ('anchors','structure-events') and name=='stocks':
                key='structure_events' if parts[2]=='structure-events' else 'anchor_view_asof_t'
                field=item['fields'].get(key);value=field.get('value') if field else None
                rows=value if isinstance(value,list) else ([value] if value is not None else [])
                return 200,r.envelope(status='SOURCE_INCOMPLETE' if not field or field['quality']=='UNKNOWN' else 'READY',field=field,items=rows,total=len(rows),has_next=False)
            if parts[2] in ('timeline','rotation-timeline','chart'):
                return 501,r.envelope(status='ENGINEERING_NOT_READY',code='HISTORICAL_INDEX_REQUIRES_FP06_FP07',items=[],total=0,has_next=False)
            return 404,r.envelope(status='NOT_FOUND',code='ROUTE_NOT_FOUND')
        except (psycopg.Error,RuntimeError):return 503,dict(status='SOURCE_INCOMPLETE',code='V4_PG_UNAVAILABLE',fallback=False,items=[])
        except SourceInvalid as e:return 409,dict(status='CONTEXT_CONFLICT',code=str(e),items=[])
        except (ValueError,TypeError) as e:return 400,dict(status='INVALID_REQUEST',code=str(e),items=[])
        except (OSError,KeyError,json.JSONDecodeError) as e:return 503,dict(status='SOURCE_INCOMPLETE',code=type(e).__name__,items=[])
