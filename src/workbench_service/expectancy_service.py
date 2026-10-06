"""Read-only engineering API. Explicit ledger injection; no production/default activation."""
from urllib.parse import urlparse,parse_qs
from http.server import BaseHTTPRequestHandler
import json
from workbench_analysis.fep_e5 import contracts as c
from workbench_analysis.fep_e5.projection import first_accepted

def context(prediction):
    fields=('publication_id','prediction_slot_id','feature_snapshot_id','feature_snapshot_digest','model_set_id','model_id','run_id','revision','input_digest','prediction_digest')
    token={k:prediction[k] for k in fields};token['context_digest']=c.logical(token);return token

class ExpectancyReadAPI:
    def __init__(self,ledger,at):self.ledger=ledger;self.at=at
    def bootstrap(self,slot_id):
        prediction=first_accepted(self.ledger,slot_id)
        return dict(status='CONTEXT_READY_ENGINEERING_ONLY',context=context(prediction),production=False) if prediction else dict(status='NOT_READY')
    def projection(self,slot_id,token,*,diagnostic=False,mode='HISTORICAL_AS_OF'):
        prediction=first_accepted(self.ledger,slot_id)
        if prediction is None:return dict(status='NOT_READY')
        if token!=context(prediction):return dict(status='CONTEXT_MISMATCH')
        if mode!='HISTORICAL_AS_OF':return dict(status='NOT_APPLICABLE_ENTRY_IS_NOT_TODAY_DAILY')
        model=self.ledger.get('models',prediction['model_id']);shadow=self.ledger.allowed(model['model_id'],c.permission_key(model,'SHADOW_INFERENCE'),self.at)
        result={k:prediction[k] for k in ('scope_id','observation_scope','trade_date','entity_id','target_id','horizon','feature_variant',
            'projection_state','quality_state','support_state','OOD_state','coherence_state','evidence_class','model_id','model_family','model_set_id',
            'prediction_slot_id','prediction_evidence','execution_mode','input_digest','prediction_digest','feature_snapshot_id','threshold_state')}
        result.update(status='ENGINEERING_DIAGNOSTIC' if diagnostic and shadow else 'NOT_ENABLED_MODEL_DISPLAY_UNGRANTED',
            axes=prediction['axes'] if diagnostic and shadow else None,diagnostic=bool(diagnostic and shadow),permission='SHADOW_INFERENCE_ONLY' if diagnostic and shadow else 'UNGRANTED',
            permissions=dict(shadow_inference=shadow,descriptive_display=False,model_display=False,priority_use=False),
            historical_as_of=True,FIRST_OBSERVED=False,REAL_OOS=False,production=False,priority=dict(v1_rank=None,v2_shadow_rank=None,v2_active=False))
        return result
    def priority(self,fixture_id=None):
        if fixture_id is None:return dict(status='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE',v2_active=False,REAL_PRIORITY_SHADOW='NOT_GRANTED',priority_use=False)
        stored=self.ledger.get('priority_projection',fixture_id)
        if stored is None:return dict(status='NOT_READY',v2_active=False)
        return dict(stored,diagnostic=True,permission='ENGINEERING_FIXTURE_ONLY',v2_active=False)
    def route(self,path):
        url=urlparse(path);query=parse_qs(url.query);slot=query.get('slot_id',[''])[0]
        if url.path=='/api/v4/expectancy/context':return self.bootstrap(slot)
        if url.path=='/api/v4/expectancy/priority-shadow':return self.priority(query.get('fixture_id',[None])[0])
        if url.path in ('/api/v4/expectancy/projection','/api/v4/expectancy/diagnostic'):
            try:token=json.loads(query.get('context',['{}'])[0])
            except (ValueError,TypeError):return dict(status='CONTEXT_MISMATCH')
            return self.projection(slot,token,diagnostic=url.path.endswith('/diagnostic'))
        return dict(status='NOT_FOUND')

def handler_factory(api):
    """Optional localhost engineering adapter; existing application routes remain untouched."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body=json.dumps(api.route(self.path),allow_nan=False).encode();self.send_response(200)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    return Handler
