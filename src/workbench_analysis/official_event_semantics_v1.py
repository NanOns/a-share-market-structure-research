"""Document semantics with no filename-derived trading authority."""
from __future__ import annotations
import re
from .source_authority_accepted_owners_v1 import exact_json

CONTRACT='OFFICIAL_EVENT_SEMANTICS_V1'
EVENT_TYPES={
    'LISTED_STOCK_TRADING_SUSPENSION','LISTED_STOCK_RESUMPTION',
    'IPO_ISSUANCE_POSTPONEMENT','IPO_LISTING_POSTPONEMENT','IPO_TERMINATION',
    'DELISTING_PHASE','RISK_WARNING_CHANGE','LISTING','CODE_CHANGE',
    'OTHER_OFFICIAL_NOTICE','UNKNOWN_EVENT_SEMANTICS'}
TRADING_TYPES={'LISTED_STOCK_TRADING_SUSPENSION','LISTED_STOCK_RESUMPTION'}

def parse_document_semantics(text):
    """Classify explicit document statements; ambiguous text stays unknown.

    This parser does not authorize a field value, identify an issuer, or prove
    an effective date. Those require the independent evidence binding below.
    """
    if not isinstance(text,str) or not text.strip():
        raise ValueError('FILENAME_ONLY_EVENT_INFERENCE_REJECTED')
    compact=re.sub(r'\s+','',text)
    title=compact[:2500]
    event='UNKNOWN_EVENT_SEMANTICS';evidence=None
    patterns=[
        ('IPO_LISTING_POSTPONEMENT',r'暂缓[^。；]{0,60}(?:科创板上市|上市的决定)'),
        ('IPO_ISSUANCE_POSTPONEMENT',r'(?:暂缓首次公开发行股票发行工作|暂缓后续发行工作|暂停IPO发行程序)'),
        ('IPO_TERMINATION',r'(?:终止首次公开发行|终止IPO发行)'),
        ('DELISTING_PHASE',r'(?:进入退市整理期|退市整理期交易|退市整理期首个交易日)'),
        ('CODE_CHANGE',r'(?:变更证券代码|证券代码变更|证券简称及证券代码变更)'),
        ('RISK_WARNING_CHANGE',r'(?:撤销其他风险警示|实施退市风险警示|撤销退市风险警示)'),
        ('LISTING',r'(?:首次公开发行[^。；]{0,80}上市公告|于[^。；]{0,30}(?:主板|创业板|科创板)上市|于\d{4}年\d{1,2}月\d{1,2}日登陆(?:主板|创业板|科创板))'),
        ('OTHER_OFFICIAL_NOTICE',r'首次公开发行股票并在(?:主板|创业板|科创板)上市(?:发行公告|提示公告)'),
    ]
    for candidate,pattern in patterns:
        match=re.search(pattern,title)
        if match:event=candidate;evidence=match.group();break
    if event=='UNKNOWN_EVENT_SEMANTICS':
        suspension=re.search(r'(?:公司|本公司)股票[^。；]{0,80}(?:停牌|暂停交易)',compact)
        resumption=re.search(r'(?:公司|本公司)股票[^。；]{0,80}(?:复牌|恢复交易)',compact)
        # A notice containing both needs explicit dated subevents; no singleton inference.
        if bool(suspension)!=bool(resumption):
            event='LISTED_STOCK_TRADING_SUSPENSION' if suspension else 'LISTED_STOCK_RESUMPTION'
            evidence=(suspension or resumption).group()
    return dict(contract_id=CONTRACT,actual_event_type=event,semantic_evidence=evidence,
                dated_trading_statements=(parse_dated_trading_statements(text) if event in TRADING_TYPES | {'DELISTING_PHASE','RISK_WARNING_CHANGE'} else []),
                classification_basis='EXPLICIT_DOCUMENT_STATEMENT',formal_consumer_authorization=False)

def parse_dated_trading_statements(text):
    compact=re.sub(r'\s+','',text)
    statements=[]
    pattern=r'(?:公司|本公司)股票(?:将)?(?:自|于)(\d{4})年(\d{1,2})月(\d{1,2})日[^。；]{0,45}?(停牌|复牌|恢复交易)'
    for match in re.finditer(pattern,compact):
        from datetime import date
        effective=date(*(int(match.group(i)) for i in (1,2,3))).isoformat()
        event='LISTED_STOCK_TRADING_SUSPENSION' if match.group(4)=='停牌' else 'LISTED_STOCK_RESUMPTION'
        statements.append(dict(actual_event_type=event,event_effective_date=effective,semantic_evidence=match.group(),formal_consumer_authorization=False))
    return statements

def require_trading_event(root,accepted_sidecar_binding,raw_binding,*,security_key,effective_date):
    if accepted_sidecar_binding is None:
        raise ValueError('ACCEPTED_EVENT_SEMANTICS_REQUIRED')
    from pathlib import Path
    import hashlib
    path='data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json'
    try:
        head=exact_json(root,dict(path=path,sha256=hashlib.sha256((Path(root)/path).read_bytes()).hexdigest()))
    except (OSError,ValueError) as exc:
        raise ValueError('ACCEPTED_EVENT_SEMANTICS_REQUIRED') from exc
    if head.get('contract_id')!='OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_V1' or head.get('external_acceptance')!='EXTERNALLY_ACCEPTED' or head.get('sidecar')!=accepted_sidecar_binding:
        raise ValueError('ACCEPTED_EVENT_SEMANTICS_REQUIRED')
    sidecar=exact_json(root,accepted_sidecar_binding)
    if sidecar.get('contract_id')!=CONTRACT or sidecar.get('external_acceptance')!='EXTERNALLY_ACCEPTED':
        raise ValueError('ACCEPTED_EVENT_SEMANTICS_REQUIRED')
    matches=[e for e in sidecar['entries'] if e['raw_artifact']==raw_binding
             and e['security_key']==security_key and e['event_effective_date']==effective_date
             and e['actual_event_type'] in TRADING_TYPES]
    if len(matches)!=1:
        raise ValueError('OFFICIAL_NOTICE_NOT_A_DATED_TRADING_EVENT')
    event=matches[0]
    if event['consumer_permissions'].get('TRADING_STATUS_TRUTH') is not True or not event.get('semantic_evidence') or not event.get('identity_evidence'):
        raise ValueError('DATED_EVENT_SEMANTIC_PROOF_INCOMPLETE')
    from .source_authority_producers_r3 import binding_bytes
    binding_bytes(root,raw_binding)
    binding_bytes(root,event['identity_evidence'])
    text=binding_bytes(root,event['semantic_text_binding']).decode('utf8')
    if parse_document_semantics(text)['actual_event_type'].startswith('IPO_'):
        raise ValueError('OFFICIAL_NOTICE_NOT_A_DATED_TRADING_EVENT')
    if security_key.split('.')[-1] not in re.sub(r'\s+','',text):
        raise ValueError('DATED_EVENT_ISSUER_IDENTITY_UNPROVEN')
    statements=parse_dated_trading_statements(text)
    if not any(s['actual_event_type']==event['actual_event_type'] and s['event_effective_date']==effective_date and s['semantic_evidence']==event['semantic_evidence'] for s in statements):
        raise ValueError('DATED_EVENT_DOCUMENT_STATEMENT_MISMATCH')
    return event
