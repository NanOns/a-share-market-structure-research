"""FP03 BFF routing: one immutable snapshot per reader and request."""
import json
import threading
import time
from collections import defaultdict, deque
from urllib.parse import unquote
from .production_v4 import ProductionV4ResearchReader, POINTER
from .current_v4_context import SourceInvalid, digest
from .v4_daily_refresh import refresh_status
from .domain_views import home,sector_view

class ResearchBFF:
    def __init__(self,root):
        self.root=root;self.lock=threading.RLock();self.reader=None;self.pointer_digest=None
        self.requests=defaultdict(deque)

    def current(self):
        with self.lock:
            signature=digest((self.root/POINTER).read_bytes())
            if self.reader is None or signature!=self.pointer_digest:
                candidate=ProductionV4ResearchReader(self.root)
                self.reader=candidate;self.pointer_digest=signature
            return self.reader

    def allowed(self,host):
        with self.lock:
            now=time.monotonic();queue=self.requests[host]
            while queue and queue[0]<now-60:queue.popleft()
            if len(queue)>=240:return False
            queue.append(now);return True

    def get(self,path,query):
        try:
            r=self.current()
            # Validate context and parameter contracts even for singleton/diagnostic routes.
            validation=r.query('sources',query)
            parts=[unquote(p) for p in path.removeprefix('/api/v4/').split('/') if p]
            if not parts:return 404,r.envelope(status='NOT_FOUND',code='ROUTE_NOT_FOUND')
            name=parts[0]
            if name=='context':
                progress=refresh_status(self.root)
                control={k:progress[k] for k in ('status','next_completed_session','source_requests','data_preserved')}
                control.update(scope='INPUT_PROGRESS_NOT_RESEARCH_CONTEXT',accepted_input_date=progress['context']['context']['accepted_trade_date'],indexed_trade_date=r.context['accepted_trade_date'])
                return 200,r.envelope(status='READY',counts=r.manifest['counts'],gaps=r.manifest['gaps'],daily_refresh=control)
            if name=='home':return 200,home(r)
            if name=='market' and len(parts)==1:return 200,r.envelope(status='READY' if r.manifest.get('domain_features',{}).get('market') else 'SOURCE_INCOMPLETE',market=r.manifest.get('domain_features',{}).get('market'))
            if name=='diagnostics':
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
            detail=r.query(name,query,entity=parts[1])
            if not detail['total']:
                outside=name=='stocks' and r.known_identity(parts[1])
                return 404,r.envelope(status='OUTSIDE_CURRENT_POOL' if outside else 'NOT_FOUND',code='IDENTITY_OUTSIDE_CURRENT_DAILY_UNIVERSE' if outside else 'ENTITY_NOT_FOUND',items=[])
            item=detail['items'][0]
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
        except SourceInvalid as e:return 409,dict(status='CONTEXT_CONFLICT',code=str(e),items=[])
        except (ValueError,TypeError) as e:return 400,dict(status='INVALID_REQUEST',code=str(e),items=[])
        except (OSError,KeyError,json.JSONDecodeError) as e:return 503,dict(status='SOURCE_INCOMPLETE',code=type(e).__name__,items=[])
