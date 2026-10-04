"""Successor input authority. The frozen V2 loader supplies algorithms only.

No V2 calendar/data acceptance is used to authorize a successor target session.
The exact, externally accepted per-session head supplies all runtime inputs.
"""
import copy, hashlib, json
from datetime import datetime
from .v4_current_stage_authority import CurrentStageAuthority

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()

def require(value,reason):
    if not value:raise ValueError(reason)

def timestamp(value):
    require(isinstance(value,str) and value.endswith('Z'),'UTC_TIMESTAMP_REQUIRED')
    return datetime.fromisoformat(value.replace('Z','+00:00'))

def source_trade_dates(payload):
    dates=[]
    if isinstance(payload,dict):
        for key,value in payload.items():
            if key in ('trade_date','event_trade_date','source_trade_date','source_asof','evaluation_basis_date','max_source_trade_date') and isinstance(value,str):
                dates.append(value[:10])
            elif isinstance(value,(dict,list)):dates.extend(source_trade_dates(value))
    elif isinstance(payload,list):
        for value in payload:dates.extend(source_trade_dates(value))
    return dates

class GoForwardInputAuthority(CurrentStageAuthority):
    def __init__(self, root, contract_binding, daily_binding, grant, boundary, simulation=False):
        # Explicit immutable algorithm view. Never invoke its target-date gate.
        immutable=CurrentStageAuthority(root)
        self.__dict__=copy.copy(immutable.__dict__)
        self.immutable_bindings=immutable.bindings()
        self.forward_contract=json.loads(self.read(contract_binding))
        self.daily_ref=daily_binding
        daily=json.loads(self.read(daily_binding)); self.daily=daily
        require(daily['contract_id']==self.forward_contract['contract_id'],'DAILY_CONTRACT_MISMATCH')
        require(daily['environment_class']==('ACTIVATION_SIMULATION' if simulation else 'REAL'),'DAILY_ENVIRONMENT_MISMATCH')
        require(daily['daily_input_digest']==digest({k:v for k,v in daily.items() if k!='daily_input_digest'}),'DAILY_INPUT_DIGEST_MISMATCH')
        require(grant['daily_input_authority']==daily_binding and grant['daily_input_digest']==daily['daily_input_digest'],'GRANT_DAILY_INPUT_MISMATCH')
        target=daily['target_trade_date']
        require(target==grant['target_trade_date'],'TARGET_DATE_MISMATCH')
        require(isinstance(daily['revision'],int) and daily['revision']>=grant['minimum_daily_input_revision']>=1,'DAILY_REVISION_ROLLBACK')
        require(timestamp(daily['accepted_at'])<=timestamp(boundary),'DAILY_ACCEPTED_AFTER_BOUNDARY')
        require(set(self.forward_contract['required_fields'])<=daily.keys(),'DAILY_HEAD_INCOMPLETE')
        require(daily['immutable_algorithm_bindings']==self.forward_contract['immutable_algorithm_bindings'],'IMMUTABLE_ALGORITHM_MISMATCH')
        for binding in daily['immutable_algorithm_bindings'].values():self.read(binding)
        for k,v in self.forward_contract['model_identity'].items():
            require(daily[k]==grant[k]==v,'MODEL_PARAMETER_MISMATCH')
        self.calendar_ref=daily['calendar']; self.calendar=json.loads(self.read(self.calendar_ref))
        self.sessions=[s['trade_date'] if isinstance(s,dict) else s for s in self.calendar['session_dates']]
        require(self.sessions==sorted(set(self.sessions)),'INVALID_CALENDAR_ORDER')
        require(target in self.sessions and daily['target_session_confirmed'] is True,'TARGET_NOT_ACCEPTED_SESSION')
        i=self.sessions.index(target)
        require(i>0 and self.sessions[i-1]==daily['previous_trade_date'],'PREVIOUS_SESSION_MISMATCH')
        self.identity_ref=daily['identity']; identity=json.loads(self.read(self.identity_ref))
        require(identity['accepted'] is True and identity['target_trade_date']==target,'UNACCEPTED_IDENTITY_UNIVERSE')
        require(isinstance(identity.get('universe'),list) and identity['universe'] and len(identity['universe'])==len(set(identity['universe'])),'EXPLICIT_UNIVERSE_REQUIRED')
        self.universe=set(identity['universe'])
        self.membership_ref=daily['membership']
        required=any(c in self.forward_contract['membership_required_capabilities'] for c in grant['capability_scope'])
        require(not required or isinstance(self.membership_ref,dict),'REQUIRED_MEMBERSHIP_MISSING')
        if isinstance(self.membership_ref,dict):
            membership=json.loads(self.read(self.membership_ref))
            require(membership['accepted'] is True and membership['target_trade_date']==target,'MEMBERSHIP_DATE_MISMATCH')
        else:require(self.membership_ref=='NOT_REQUIRED_FOR_SCOPE' and not required,'MEMBERSHIP_SCOPE_MISMATCH')
        sources=daily['sources']
        require(set(self.forward_contract['mandatory_pure_core_sources'])<=sources.keys(),'MANDATORY_PURE_CORE_MISSING')
        for family,source in sources.items():
            require(source['target_trade_date']==target and source['max_source_trade_date']<=target,'SOURCE_DATE_OR_FUTURE_LEAK')
            require(timestamp(source['provider_observed_at'])<=timestamp(source['system_available_at'])<=timestamp(source['accepted_at'])<=timestamp(boundary),'SOURCE_ACCEPTANCE_BOUNDARY')
            require(source['quality']=='ACCEPTED' and source['capability']=='PURE_CORE_STOCK','SOURCE_QUALITY_CAPABILITY')
            payload=json.loads(self.read(source['binding']))
            require(payload['trade_date']==target and payload.get('max_source_trade_date',target)<=target,'STALE_OR_FUTURE_DAY_PACKAGE')
            require(max(source_trade_dates(payload),default=target)==source['max_source_trade_date'],'SOURCE_PAYLOAD_MAX_DATE_MISMATCH')
        require(daily['max_source_trade_date']==max(s['max_source_trade_date'] for s in sources.values())<=target,'MAX_SOURCE_DATE_MISMATCH')
        require(daily['source_manifest_digest']==digest(sources),'SOURCE_MANIFEST_DIGEST_MISMATCH')
        package=json.loads(self.read(daily['day_package']))
        require(package['trade_date']==target and package['snapshot_identity']==daily['snapshot_identity'] and package['sources']==sources,'STALE_DAY_PACKAGE')
        require(daily['quality_capability_matrix']=={k:dict(quality=v['quality'],capability=v['capability']) for k,v in sources.items()},'QUALITY_MATRIX_MISMATCH')
        # Runtime interfaces replace frozen inputs while preserving algorithm contracts.
        self.data_ref=daily_binding
        self.data=dict(accepted_trade_date=target,calendar=self.calendar_ref,identity=self.identity_ref,
                      component_artifacts={'ADJUSTED_DAILY':sources['ADJUSTED_DAILY']['binding']})

    def bindings(self):
        result=super().bindings()
        result.update(immutable_algorithm_authority=self.immutable_bindings,
                      daily_input_authority=self.daily_ref,daily_input_digest=self.daily['daily_input_digest'])
        return result
