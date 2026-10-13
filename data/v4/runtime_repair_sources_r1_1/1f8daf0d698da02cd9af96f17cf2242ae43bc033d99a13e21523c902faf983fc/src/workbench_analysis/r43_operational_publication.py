"""Operational reconstructed publication: explicit external admission, separate PIT."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import re
from .scoped_successor_r421 import sha,canonical,atomic
from .r43_operational_sources import checked,DATES
from .tdx_member_retro_r43 import validate_snapshot,metadata

POLICY='V4_DATED_OPERATIONAL_RECONSTRUCTED_OWNER_V1'

def digest(value):return hashlib.sha256(canonical(value)).hexdigest()

def validate(root,candidate):
    if candidate.get('contract_id')!=POLICY:raise ValueError('WRONG_OPERATIONAL_CONTRACT')
    if candidate.get('dates')!=DATES:raise ValueError('FOUR_SESSION_DATE_SCOPE_REQUIRED')
    if candidate.get('historical_PIT_permission') is not False or candidate.get('AS_RECORDED') is not False:raise ValueError('PIT_ESCALATION_FORBIDDEN')
    if candidate.get('membership_mode')!='TDX_LATEST_MEMBER_RETRO_V1' or candidate.get('taxonomy')!='TDX_INDUSTRY_CONCEPT':raise ValueError('TDX_LATEST_PRIMARY_MEMBERSHIP_REQUIRED')
    snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
    validate_snapshot(snapshot,root)
    if candidate.get('membership_snapshot_id')!=snapshot['membership_snapshot_id']:raise ValueError('CANDIDATE_SNAPSHOT_ID_MISMATCH')
    registry=json.loads(checked(root,candidate['registry']).read_bytes())
    if registry.get('contract_id')!='R43_OPERATIONAL_BUILDER_REGISTRY_V1' or registry.get('historical_PIT_permission') is not False:raise ValueError('OPERATIONAL_REGISTRY_REQUIRED')
    for binding in registry['bindings']:checked(root,binding)
    if registry.get('owner_bindings')!=candidate['owners'] or registry.get('input_snapshot')!=candidate['membership_snapshot']:raise ValueError('REGISTRY_OWNER_INPUT_MISMATCH')
    for binding in candidate['accepted_product_scope']['contracts']:checked(root,binding)
    for day in DATES:
        if not {'raw','core','profile','sector','relative_sector','rotation','lifecycle','special_phase'}<=set(candidate['owners'][day]):raise ValueError('REQUIRED_OPERATIONAL_OWNER_MISSING')
        for binding in candidate['owners'][day].values():checked(root,binding)
        receipt=json.loads(checked(root,candidate['owners'][day]['sector_receipt']).read_bytes())
        item=next(r for r in receipt['owners'] if r['trade_date']==day)
        if item['membership_snapshot_id']!=snapshot['membership_snapshot_id'] or item['source_bindings']['membership_snapshot']!=candidate['membership_snapshot']:
            raise ValueError('OWNER_MEMBERSHIP_SNAPSHOT_MISMATCH')
        for domain,key in [('sector','native'),('relative_sector','relative_sector'),('rotation','rotation')]:
            if item[key]!=candidate['owners'][day][domain]:raise ValueError('OWNER_ARTIFACT_BINDING_MISMATCH')
    return True

def cas(root,head_path,candidate,expected_sha,*,external_acceptance=None,user_authorization=None,staging=False,inject_failure=False):
    root=Path(root).resolve();head_path=Path(head_path).resolve()
    if not head_path.is_relative_to(root):raise ValueError('HEAD_OUTSIDE_PUBLICATION_ROOT')
    validate(root,candidate)
    if staging:
        if root.drive.upper()!='E:':raise ValueError('STAGING_MUST_BE_ISOLATED_E_DRIVE')
    else:
        if head_path!=(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').resolve():raise ValueError('LEGACY_OR_WRONG_PRODUCTION_HEAD_FORBIDDEN')
        if candidate.get('authority_mode')=='USER_AUTHORIZED_SCOPED_OPERATIONAL_V1':
            if user_authorization is None:raise ValueError('EXACT_USER_AUTHORIZATION_REQUIRED')
            if checked(root,user_authorization)!=(root/'data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json').resolve():raise ValueError('FIXED_USER_AUTHORITY_REQUIRED')
            from .r43_release_control import verify_user_authorization
            verify_user_authorization(root,candidate,json.loads(checked(root,user_authorization).read_bytes()))
        else:
            _verify_external_for_cas(root,candidate,external_acceptance)
    head_path.parent.mkdir(parents=True,exist_ok=True);lock=head_path.with_suffix('.lock')
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.close(fd);raw=canonical(candidate)
        current=sha(head_path) if head_path.exists() else None
        if current!=expected_sha:raise ValueError('STALE_OPERATIONAL_HEAD_CAS')
        if head_path.exists() and head_path.read_bytes()==raw:return dict(status='NOOP_IDENTICAL',sha256=current)
        if head_path.exists():atomic(head_path.parent/'predecessors'/(current+'.json'),head_path.read_bytes())
        if inject_failure:raise ValueError('INJECTED_BEFORE_ATOMIC_REPLACE')
        atomic(head_path,raw)
        return dict(status='STAGING_OPERATIONAL_UPDATED' if staging else 'OPERATIONAL_PROMOTED',sha256=sha(head_path),predecessor=current)
    finally:lock.unlink()

def _verify_external_for_cas(root,candidate,external_acceptance):
        if external_acceptance is None:raise ValueError('INDEPENDENT_EXTERNAL_ACCEPTANCE_REQUIRED')
        if checked(root,external_acceptance)!=(root/'data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json').resolve():raise ValueError('FIXED_OPERATIONAL_EXTERNAL_AUTHORITY_REQUIRED')
        record=json.loads(checked(root,external_acceptance).read_bytes())
        if record.get('status')!='EXTERNALLY_ACCEPTED_R43_OPERATIONAL' or record.get('candidate_digest')!=digest(candidate) or record.get('historical_PIT_permission') is not False:
            raise ValueError('EXTERNAL_ACCEPTANCE_SCOPE_MISMATCH')
        if candidate.get('external_review_contract'):
            from .r43_release_control import verify_record
            verify_record(root,candidate,record)

def rows(root,binding):
    p=checked(root,binding)
    if p.suffix=='.jsonl':return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x.strip()]
    if p.name.endswith('.gz'):
        with gzip.open(p,'rt',encoding='utf8') as stream:
            if '.jsonl.' in p.name:return [json.loads(x) for x in stream if x.strip()]
            payload=json.load(stream)
            return payload.get('rows',payload) if isinstance(payload,dict) else payload
    x=json.loads(p.read_bytes())
    for key in ('rows','target_bars','sectors'):
        if isinstance(x.get(key),list):return x[key]
    return x

def rollback_staging(root,head_path,current_sha,predecessor_sha):
    root=Path(root).resolve();head_path=Path(head_path).resolve()
    if root.drive.upper()!='E:' or not head_path.is_relative_to(root):raise ValueError('ISOLATED_STAGING_ROLLBACK_REQUIRED')
    if not all(re.fullmatch('[0-9a-f]{64}',x or '') for x in [current_sha,predecessor_sha]):raise ValueError('EXACT_PREDECESSOR_REQUIRED')
    lock=head_path.with_suffix('.lock');fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.close(fd);archive=head_path.parent/'predecessors'/(predecessor_sha+'.json')
        if sha(head_path)!=current_sha or not archive.is_file() or sha(archive)!=predecessor_sha:raise ValueError('EXACT_PREDECESSOR_REQUIRED')
        atomic(head_path,archive.read_bytes());return dict(status='EXACT_PREDECESSOR_RESTORED',sha256=sha(head_path))
    finally:lock.unlink()

class CandidateReadV2:
    """Same-token candidate read API; no fallback to different-date production fields."""
    def __init__(self,root,candidate):
        self.root=Path(root);self.candidate=candidate;validate(root,candidate)
        self.token=digest(candidate);self.cache={};self.snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
    def context(self):
        rotation_state=('INDEPENDENTLY_ACCEPTED_FULL_ROTATION' if getattr(self,'domain_disposition',{}).get('rotation')=='ACCEPTED' else 'VALIDATION_ONGOING') if self.candidate.get('external_review_contract') else 'ENGINEERING_REPORTED_NOT_EXTERNAL_FULL_VALIDATION'
        return dict(metadata(self.snapshot,'2026-10-08'),contract_id='V4_CURRENT_ACCEPTED_READ_V2',context_token=self.token,publication_id=self.token,accepted_trade_date='2026-10-08',available_trade_dates=DATES,read_scope='OPERATIONAL_CANDIDATE_NOT_LIVE',membership_snapshot=self.candidate['membership_snapshot'],historical_PIT_permission=False,member_label='通达信最新成员回算；非历史当日成员',field_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP',external_domain_disposition=getattr(self,'domain_disposition',{}),rotation_validation_state=rotation_state)
    def read(self,domain,day,token):
        if token!=self.token:raise ValueError('CONTEXT_TOKEN_MISMATCH')
        if day not in DATES:raise ValueError('TARGET_DATE_NOT_GRANTED')
        if hasattr(self,'domain_disposition') and self.domain_disposition.get(domain)!='ACCEPTED' and not getattr(self,'user_authorized_cutover',False):
            return dict(metadata(self.snapshot,day),context_token=token,publication_id=token,domain=domain,status='SOURCE_INCOMPLETE',validation_state=self.domain_disposition.get(domain,'NOT_VERIFIABLE'),reason='DOMAIN_NOT_INDEPENDENTLY_ACCEPTED',rows=[],total=0)
        binding=self.candidate['owners'][day].get(domain)
        if binding is None:return dict(metadata(self.snapshot,day),context_token=token,publication_id=token,domain=domain,status='UNKNOWN',reason='NO_ACCEPTED_OPERATIONAL_OWNER_FOR_DOMAIN')
        key=(day,domain)
        if key not in self.cache:self.cache[key]=rows(self.root,binding)
        content=self.cache[key]
        if domain=='profile' and isinstance(content,list):
            relative_key=(day,'relative_sector')
            if relative_key not in self.cache:self.cache[relative_key]=rows(self.root,self.candidate['owners'][day]['relative_sector'])
            index={r['security_id']:r for r in self.cache[relative_key]}
            content=[dict(r,relative_sector_state=index.get(r['security_id'],dict(quality='UNKNOWN',reason='NO_TDX_LATEST_LOO_OWNER_FOR_SECURITY')),relative_sector_namespace='TDX_INDUSTRY_CONCEPT',relative_sector_membership_snapshot_id=self.snapshot['membership_snapshot_id']) for r in content]
        if domain=='forward' and isinstance(content,dict):
            content={k:v for k,v in content.items() if k not in ['episodes','events']}
            original=self.cache[key]
            content['events']=[x for x in original.get('events',[]) if x.get('trade_date',x.get('event_date'))==day]
            episodes=[]
            for x in original.get('episodes',[]):
                if x.get('start_date',x.get('T0','9999'))>day:continue
                observations=[o for o in x.get('observations',[]) if o.get('trade_date','9999')<=day]
                episodes.append(dict(x,observations=observations,anchors=[a for a in x.get('anchors',[]) if a.get('trade_date','9999')<=day],outcomes=[o for o in x.get('outcomes',[]) if o.get('trade_date','9999')<=day],end_date=x.get('end_date') if x.get('end_date') and x['end_date']<=day else None,membership=observations[-1].get('membership') if observations else None))
            content['episodes']=episodes
        if isinstance(content,list):content=[r for r in content if not r.get('trade_date') or r['trade_date']==day]
        return dict(metadata(self.snapshot,day),context_token=token,publication_id=token,domain=domain,status='READY',validation_state=getattr(self,'domain_disposition',{}).get(domain,'ENGINEERING_REPORTED'),independent_external_acceptance=getattr(self,'independent_external_acceptance',False),lineage='RECONSTRUCTED_LATEST_MEMBERSHIP' if domain in ['sector','relative_sector','rotation'] else 'RECONSTRUCTED_CORRECTED',membership_snapshot=self.candidate['membership_snapshot'],rows=content)
    def dispatch(self,url,token=None):
        from urllib.parse import urlparse,parse_qs
        parsed=urlparse(url);params=parse_qs(parsed.query,keep_blank_values=True)
        if any(len(v)!=1 for v in params.values()):raise ValueError('DUPLICATE_QUERY_PARAMETER')
        if set(params)-{'trade_date','context_token','limit','offset'}:raise ValueError('UNKNOWN_QUERY_PARAMETER')
        if parsed.path=='/api/v4/context':return self.context()
        parts=parsed.path.removeprefix('/api/v4/').split('/');domain=parts[0]
        aliases={'stocks':'profile','sectors':'sector','diagnostics':'diagnostic'}
        response=self.read(aliases.get(domain,domain),params.get('trade_date',['2026-10-08'])[0],token or params.get('context_token',[''])[0])
        offset=int(params.get('offset',['0'])[0]);limit=int(params.get('limit',['100'])[0])
        if offset<0 or not 1<=limit<=500:raise ValueError('PAGINATION_BOUND')
        if isinstance(response.get('rows'),list):
            rs=response['rows']
            if len(parts)>1 and domain in ['stocks','sectors']:
                rs=[r for r in rs if r.get('security_id',r.get('sector_id'))==parts[1]]
            offset=int(params.get('offset',['0'])[0]);limit=int(params.get('limit',['100'])[0])
            if offset<0 or not 1<=limit<=500:raise ValueError('PAGINATION_BOUND')
            response.update(items=rs[offset:offset+limit],total=len(rs),count=len(rs[offset:offset+limit]),offset=offset,limit=limit,has_next=offset+limit<len(rs))
            response['rows']=response['items']
        elif isinstance(response.get('rows'),dict):
            content=response['rows'];bounded={};counts={}
            for key,value in content.items():
                if isinstance(value,list):counts[key]=len(value);bounded[key]=value[offset:offset+limit]
                else:bounded[key]=value
            response.update(rows=bounded,total_by_collection=counts,offset=offset,limit=limit)
        return response

def accepted_api(root):
    """Return operational reader only for an exact independently admitted new head."""
    root=Path(root);pointer=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    if not pointer.is_file():return None
    head=json.loads(pointer.read_bytes());user_mode=head.get('authority_mode')=='USER_AUTHORIZED_SCOPED_OPERATIONAL_V1'
    authority=root/('data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json' if user_mode else 'data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json')
    if not authority.is_file():raise ValueError('OPERATIONAL_EXTERNAL_AUTHORITY_MISSING')
    record=json.loads(authority.read_bytes())
    if user_mode:
        from .r43_release_control import verify_user_authorization
        verify_user_authorization(root,head,record)
    elif record.get('status')!='EXTERNALLY_ACCEPTED_R43_OPERATIONAL' or record.get('candidate_digest')!=digest(head) or record.get('historical_PIT_permission') is not False:raise ValueError('EXTERNAL_ACCEPTANCE_SCOPE_MISMATCH')
    elif head.get('external_review_contract'):
        from .r43_release_control import verify_record
        verify_record(root,head,record)
    api=CandidateReadV2(root,head)
    if head.get('external_review_contract'):api.domain_disposition=record['domain_disposition']
    api.user_authorized_cutover=user_mode;api.independent_external_acceptance=not user_mode
    oldcontext=api.context
    def current_context():return dict(oldcontext(),read_scope='USER_AUTHORIZED_OPERATIONAL' if user_mode else 'INDEPENDENTLY_ACCEPTED_OPERATIONAL',production_accepted=True,independent_external_acceptance=not user_mode,authorization_mode='DIRECT_HUMAN_USER' if user_mode else 'INDEPENDENT_EXTERNAL_REVIEW')
    api.context=current_context
    return api
