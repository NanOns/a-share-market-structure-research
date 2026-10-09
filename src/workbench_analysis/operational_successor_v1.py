"""Versioned dynamic operational owner admission and date-dispatched reader."""
from copy import deepcopy
from pathlib import Path
from types import FunctionType
import json
from .r43_operational_publication import CandidateReadV2, digest, accepted_api as frozen_api
from .r43_owner_replay import checked
from .market_source_acquisition import official_sessions

CONTRACT = 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1'
REQUIRED = frozenset(('raw','adjusted','core','profile','sector','relative_sector','market','focus','forward',
                      'rotation','lifecycle','special_phase','period_raw','period_adjusted','diagnostic'))


def validate(root, candidate):
    root=Path(root)
    if candidate.get('contract_id')!=CONTRACT:
        raise ValueError('WRONG_SUCCESSOR_CONTRACT')
    dates=candidate.get('published_sessions',[])
    if not dates or dates!=sorted(set(dates)) or candidate.get('dates')!=dates:
        raise ValueError('SUCCESSOR_SESSION_ORDER')
    sessions=official_sessions(root)
    if any(d not in sessions for d in dates) or dates!=sessions[sessions.index(dates[0]):sessions.index(dates[-1])+1]:
        raise ValueError('SUCCESSOR_SESSION_DISCONTINUITY')
    if candidate.get('accepted_trade_date')!=dates[-1] or candidate.get('data_cutoff_date')!=dates[-1]:
        raise ValueError('SUCCESSOR_CUTOFF_MISMATCH')
    if any(candidate.get(k) is not False for k in ('historical_PIT_permission','AS_RECORDED','PIT_ELIGIBLE')):
        raise ValueError('SUCCESSOR_PIT_ESCALATION')
    predecessor=json.loads(checked(root,candidate['predecessor']).read_bytes())
    olddates=predecessor.get('published_sessions',predecessor['dates'])
    if dates[:-1]!=olddates:
        raise ValueError('SUCCESSOR_MUST_EXTEND_ONE_SESSION')
    for day in olddates:
        if candidate['owners'].get(day)!=predecessor['owners'][day]:
            raise ValueError('SUCCESSOR_FROZEN_OWNER_CHANGED')
    if set(candidate['source_registry'])!=set(dates):
        raise ValueError('SUCCESSOR_DATED_SOURCE_REGISTRY_REQUIRED')
    day=dates[-1]; owners=candidate['owners'][day]
    if not REQUIRED<=set(owners):
        raise ValueError('SUCCESSOR_REQUIRED_OWNER_MISSING')
    for binding in owners.values():checked(root,binding)
    for binding in candidate['source_registry'][day].values():checked(root,binding)
    qa=json.loads(checked(root,candidate['day_receipt']).read_bytes())
    if qa.get('target_session')!=day or qa.get('acceptance')!='DERIVED_READY' or qa.get('owners')!=owners:
        raise ValueError('SUCCESSOR_NUMERIC_DAY_RECEIPT_REQUIRED')
    core=json.loads(checked(root,qa['numeric_core_oracle']).read_bytes())
    target_oracles=[row for row in core['oracle'] if row['trade_date']==day]
    if len(target_oracles)!=1 or target_oracles[0].get('result')!='PASS' or target_oracles[0].get('errors'):
        raise ValueError('SUCCESSOR_CORE_ORACLE_NOT_VERIFIED')
    target_owners=[row for row in core['owners'] if row['trade_date']==day]
    if len(target_owners)!=1 or target_owners[0]['actual_raw_rows']!=qa['source_counts'].get('ACTUAL_TRADED',0):
        raise ValueError('SUCCESSOR_SOURCE_BAR_CONSERVATION')
    if any(target_owners[0][name]!=owners[name] for name in ('raw','adjusted','core')):
        raise ValueError('SUCCESSOR_CORE_OWNER_BINDING_MISMATCH')
    sector=json.loads(checked(root,qa['sector_oracle']).read_bytes())
    if not any(row.get('trade_date')==day for row in sector.get('oracle',[])) or any(row.get('passed') is not True for row in sector['oracle']):
        raise ValueError('SUCCESSOR_SECTOR_ORACLE_NOT_VERIFIED')
    freeze=json.loads(checked(root,qa['source_freeze']).read_bytes())
    if freeze.get('target_session')!=day:raise ValueError('SUCCESSOR_SOURCE_FREEZE_DATE_MISMATCH')
    checked(root,qa['period_kernel'])
    period=json.loads(checked(root,candidate['period_numeric_oracle']).read_bytes())
    if period.get('target_session')!=day or period.get('acceptance')!='PASS' or period.get('errors') or period.get('checks',0)<=0:
        raise ValueError('SUCCESSOR_PERIOD_ORACLE_NOT_VERIFIED')
    if period.get('owners')!={k:owners[k] for k in ('period_raw','period_adjusted')}:
        raise ValueError('SUCCESSOR_PERIOD_ORACLE_BINDING_MISMATCH')
    if period.get('input_history')!=target_owners[0]['history']:
        raise ValueError('SUCCESSOR_PERIOD_HISTORY_BINDING_MISMATCH')
    checked(root,period['input_history']);checked(root,period['verifier'])
    snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
    if snapshot.get('membership_snapshot_id')!=candidate['membership_snapshot_id'] or snapshot.get('PIT_ELIGIBLE') is not False:
        raise ValueError('SUCCESSOR_MEMBERSHIP_LINEAGE_MISMATCH')
    checked(root,snapshot['memberships']);checked(root,snapshot['identity_source'])
    registry=json.loads(checked(root,candidate['registry']).read_bytes())
    if registry.get('owner_bindings')!=candidate['owners']:
        raise ValueError('SUCCESSOR_OWNER_REGISTRY_MISMATCH')
    for binding in registry['bindings']:checked(root,binding)
    return True


class OperationalSuccessorReaderV1(CandidateReadV2):
    def __init__(self,root,candidate):
        self.root=Path(root);self.candidate=candidate;validate(root,candidate)
        self.token=digest(candidate);self.cache={}
        self.snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
        self.user_authorized_cutover=True;self.independent_external_acceptance=False
        self.domain_disposition={'rotation':'VALIDATION_ONGOING','forward':'VALIDATION_ONGOING'}

    def context(self):
        from .tdx_member_retro_r43 import metadata
        day=self.candidate['accepted_trade_date']
        current=json.loads(checked(self.root,self.candidate['membership_snapshot']).read_bytes())
        return dict(metadata(current,day),contract_id=CONTRACT,context_token=self.token,publication_id=self.token,
                    accepted_trade_date=day,data_cutoff_date=day,available_trade_dates=self.candidate['published_sessions'],
                    membership_snapshot=self.candidate['membership_snapshot'],historical_PIT_permission=False,
                    read_scope='USER_AUTHORIZED_OPERATIONAL_DAILY',production_accepted=True,
                    independent_external_acceptance=False,external_domain_disposition=self.domain_disposition,
                    rotation_validation_state='VALIDATION_ONGOING')

    def read(self,domain,day,token):
        # Reuse frozen field/forward slicing in a private per-instance date scope.
        original=CandidateReadV2.read
        scope=dict(original.__globals__,DATES=self.candidate['published_sessions'])
        return FunctionType(original.__code__,scope)(self,domain,day,token)

    def dispatch(self,url,token=None):
        from urllib.parse import urlparse,parse_qs,urlencode
        parsed=urlparse(url);q=parse_qs(parsed.query,keep_blank_values=True)
        if 'trade_date' not in q:q['trade_date']=[self.candidate['accepted_trade_date']]
        return super().dispatch(parsed.path+'?'+urlencode(q,doseq=True),token)


def accepted_api(root):
    root=Path(root);head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    if not head.is_file():return None
    candidate=json.loads(head.read_bytes())
    if candidate.get('contract_id')!=CONTRACT:return frozen_api(root)
    from .operational_successor_release_v1 import verify_policy
    verify_policy(root,candidate)
    return OperationalSuccessorReaderV1(root,candidate)
