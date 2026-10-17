"""Append-only observed-code admission; metadata never invents history or aliases."""
from pathlib import Path
from datetime import datetime,timezone,date
from types import SimpleNamespace
import json
from .r43_owner_replay import checked,ref,load
from .tdx_official_daily_source import sha256_file,sha256_bytes,_json_bytes
from .operational_daily_storage_v1 import atomic_json
from .operational_owner_adapter_v1 import private_scope
from .security_entity_identity import stable_security_id

CONTRACT='V4_CURRENT_OPERATIONAL_NEW_CODE_R2'
PATH='config/v4_operational_new_listing_r1.json'

def request_ledger_path(root):
    """Keep the existing durable budget ledger while adopting configured cache paths."""
    from common.paths import resolve_baostock_request_ledger
    return resolve_baostock_request_ledger(root)

def validate_basic(code,day,rows,existing_ids):
    if len(rows)!=1:raise ValueError('IPO_BASIC_SINGLE_RECORD_REQUIRED')
    row=rows[0]
    if row.get('code','').upper()!=code or row.get('type')!='1' or row.get('status')!='1':
        raise ValueError('IPO_BASIC_CODE_TYPE_STATUS_MISMATCH')
    if row.get('ipoDate')!=day or row.get('outDate'):raise ValueError('IPO_CURRENT_DAY_LISTING_REQUIRED')
    date.fromisoformat(day)
    exchange=code.split('.')[0];number=code.split('.')[1]
    if exchange=='SZ':board='CHINEXT' if number.startswith('30') else 'SZ_MAIN'
    elif exchange=='SH':board='STAR' if number.startswith(('688','689')) else 'SH_MAIN'
    else:raise ValueError('IPO_UNSUPPORTED_EXCHANGE')
    sid=stable_security_id(exchange,code,day)
    if sid in existing_ids:raise ValueError('IPO_STABLE_ID_COLLISION')
    return dict(source_security_key=code,security_id=sid,exchange=exchange,symbol=code,
        list_date=day,delist_date=None,board_scope=board,security_type='A_STOCK',
        name=row.get('code_name'),identity_status='IDENTITY_BOUND',trade_date=day,
        knowledge_lineage='CURRENT_DATED_OPERATIONAL_PROVIDER_FACT',AS_RECORDED=False,
        PIT_ELIGIBLE=False,absence_is_delisting_evidence=False,bao_daily_row_is_identity_authority=False)

def observed_identity(code,day,rows,existing_ids,trade_status='1'):
    """The proven first observation bounds history; IPO date is separate metadata."""
    import re
    date.fromisoformat(day)
    if not re.fullmatch(r'(SH\.6\d{5}|SZ\.(00|30)\d{4})',code):
        raise ValueError('NEW_CODE_UNSUPPORTED_A_SHARE')
    if trade_status not in {'0','1'}:raise ValueError('NEW_CODE_TRADING_STATUS_REQUIRED')
    exchange,number=code.split('.')
    board=('CHINEXT' if number.startswith('30') else 'SZ_MAIN') if exchange=='SZ' else ('STAR' if number.startswith(('688','689')) else 'SH_MAIN')
    sid=stable_security_id(exchange,code,day)
    if sid in existing_ids:raise ValueError('NEW_CODE_STABLE_ID_COLLISION')
    metadata=None
    if len(rows)==1:
        r=rows[0]
        if r.get('code','').upper()==code and r.get('type')=='1' and r.get('status')=='1' and not r.get('outDate'):
            try:
                if date.fromisoformat(r.get('ipoDate',''))<=date.fromisoformat(day):metadata=r
            except (ValueError,TypeError):pass
    if trade_status=='0' and metadata is None:raise ValueError('SUSPENDED_NEW_CODE_POOL_UNPROVED')
    ipo=metadata.get('ipoDate') if metadata else None
    return dict(source_security_key=code,security_id=sid,exchange=exchange,symbol=code,
        list_date=day,first_seen_date=day,confirmed_ipo_date=ipo,delist_date=None,
        board_scope=board,security_type='A_STOCK',name=metadata.get('code_name') if metadata else None,
        identity_status='IDENTITY_BOUND',trade_date=day,observation_status='SUSPENDED' if trade_status=='0' else 'ACTIVE',
        code_status='CONFIRMED_IPO' if ipo==day else 'NEW_CODE_UNLINKED',
        metadata_status='VERIFIED' if metadata else 'METADATA_PENDING',alias_status='UNVERIFIED',
        knowledge_lineage='CURRENT_DATED_OPERATIONAL_PROVIDER_FACT',AS_RECORDED=False,PIT_ELIGIBLE=False,
        absence_is_delisting_evidence=False,bao_daily_row_is_identity_authority=False)


def classify_codes(accepted_codes,daily,native,day):
    """Per-object diagnostics using the existing exact two-source OHLCV contract."""
    from collections import Counter
    import re
    from decimal import Decimal,InvalidOperation
    accepted=set(accepted_codes);dcounts=Counter(r.get('code','').upper() for r in daily)
    ncounts=Counter(r.get('source_security_key','').upper() for r in native)
    drows={r.get('code','').upper():r for r in daily};nrows={r.get('source_security_key','').upper():r for r in native}
    observed=set(drows)|set(nrows);valid=[];invalid=[]
    for code in sorted(observed):
        if not code.startswith(('SH.','SZ.')):continue
        errors=[];row=drows.get(code);bar=nrows.get(code)
        if not re.fullmatch(r'(SH\.6\d{5}|SZ\.(00|30)\d{4})',code):errors.append('UNSUPPORTED_A_SHARE')
        if dcounts[code]>1 or ncounts[code]>1:errors.append('DUPLICATE_CODE')
        if row is None:errors.append('DAILY_SOURCE_MISSING')
        elif row.get('date')!=day:errors.append('TARGET_DATE_MISMATCH')
        elif row.get('tradestatus')=='0':
            if code not in accepted:errors.append('SUSPENDED_NEW_CODE_POOL_UNPROVED')
            if bar:errors.append('SUSPENDED_WITH_TARGET_BAR')
        elif row.get('tradestatus')=='1':
            if bar is None:errors.append('ACTIVE_NATIVE_BAR_MISSING')
            elif bar.get('trade_date')!=day:errors.append('TARGET_DATE_MISMATCH')
            else:
                for field in ('open','high','low','close','volume'):
                    try:
                        left=Decimal(str(row[field]));right=Decimal(str(bar[field]))
                        if not left.is_finite() or not right.is_finite() or left!=right:errors.append('NATIVE_VALUE_MISMATCH:'+field)
                    except (KeyError,InvalidOperation,ValueError):errors.append('INVALID_NATIVE_VALUE:'+field)
                try:
                    prices={field:Decimal(str(row[field])) for field in ('open','high','low','close')}
                    if (any(not value.is_finite() or value<=0 for value in prices.values()) or
                            not prices['low']<=min(prices['open'],prices['close'])<=max(prices['open'],prices['close'])<=prices['high'] or
                            not Decimal(str(row['volume'])).is_finite() or Decimal(str(row['volume']))<0):
                        errors.append('SELF_CONTRADICTORY_OHLCV')
                except (KeyError,InvalidOperation,ValueError):errors.append('SELF_CONTRADICTORY_OHLCV')
        else:errors.append('UNKNOWN_TRADING_STATUS')
        if errors:invalid.append(dict(code=code,reasons=sorted(set(errors)),usable_bar=False))
        else:valid.append(code)
    target=set(valid)
    return dict(contract_id=CONTRACT,new_codes=sorted(target-accepted),still_codes=sorted(target&accepted),
        absent_codes=sorted(accepted-observed),invalid_codes=invalid,valid_codes=valid,
        identity_coverage='PARTIAL_READY' if invalid else 'COMPLETE',absence_is_delisting_evidence=False)


def admitted_identity(root,day,gate,freeze):
    root=Path(root);contract=load(root/PATH)
    if contract.get('contract_id')!=CONTRACT or contract.get('full_product_release') is not False:
        raise ValueError('NEW_CODE_OPERATIONAL_SCOPE_CONTRACT_REQUIRED')
    deps=gate['dependency_bindings'];adds=deps['unknown_codes']
    if len(adds)>contract['max_new_listings_per_session']:raise ValueError('NEW_CODE_REQUEST_BOUND_EXCEEDED')
    facts=gate['native_provider_facts']
    if facts['status']!='NATIVE_PROVIDERS_RECONCILED':raise ValueError('NEW_CODE_NATIVE_FACTS_NOT_RECONCILED')
    previous=load(checked(root,deps['identity']));ids={r['security_id'] for r in previous['rows']}
    daily={r['code'].upper():r for r in freeze['normalized']['daily']['rows']}
    folder=root/'data/v4/dynamic_daily_sources/new_listing_r1'/day
    evidence=[];new=[];metadata_errors=[]
    pending=[code for code in adds if not (folder/(code+'.json')).is_file()]
    if pending:
        try:
            from .baostock_supplemental import RequestBudget
            from .operational_baostock_client_v1 import BaoStockClient
            from .operational_runtime_acceptance_v2 import load as runtime_manifest
            manifest=runtime_manifest(checked(root,freeze['runtime_manifest']),project_root=root)
            with BaoStockClient(RequestBudget(request_ledger_path(root)),auth_mode=manifest['auth_mode'],runtime_acceptance_manifest=manifest) as client:
                for code in pending:
                    started=datetime.now(timezone.utc).isoformat()
                    try:
                        rows,metadata=client.query_rows('operational_new_listing_basic','query_stock_basic',code=code.lower(),max_rows=2,max_pages=1)
                        if metadata['error_code']!='0':raise ValueError('NEW_CODE_METADATA_PROVIDER_NOT_READY')
                        atomic_json(root,folder/(code+'.json'),dict(contract_id=CONTRACT,target_session=day,code=code,rows=rows,metadata=metadata,requested_at=started,received_at=datetime.now(timezone.utc).isoformat()))
                    except Exception as exc:metadata_errors.append(dict(code=code,error_type=type(exc).__name__))
        except Exception as exc:metadata_errors.extend(dict(code=code,error_type=type(exc).__name__) for code in pending)
    for code in adds:
        if code not in daily:raise ValueError('NEW_CODE_DAILY_FACT_REQUIRED')
        p=folder/(code+'.json');record=load(p) if p.is_file() else None
        if record and (record['target_session']!=day or record['code']!=code):raise ValueError('NEW_CODE_CACHE_DATE_CODE_MISMATCH')
        row=observed_identity(code,day,record['rows'] if record else [],ids,daily[code]['tradestatus'])
        if record:
            row['source_binding']=ref(root,p);row['knowledge_time']=record['received_at'];evidence.append(ref(root,p))
        new.append(row);ids.add(row['security_id'])
    document=dict(previous,contract_id=CONTRACT,trade_date=day,predecessor_identity=deps['identity'],
        rows=previous['rows']+new,new_listings=new,new_codes=adds,absent_codes=deps['missing_codes'],
        code_observations=[dict(code=code,status='NOT_OBSERVED',absence_is_delisting_evidence=False) for code in deps['missing_codes']],
        metadata_errors=metadata_errors,provider_evidence=evidence,policy=ref(root,root/PATH),
        roster_source=freeze['native_baostock'],native_source=freeze['tdx'],full_product_release=False,PIT_ELIGIBLE=False,AS_RECORDED=False)
    key=sha256_bytes(_json_bytes(document));p=folder/'identities'/key/'IDENTITY.json'
    if not p.exists():atomic_json(root,p,document)
    return ref(root,p)


def filtered_freeze(root,day,artifact,result,changes):
    """Seal an explicit partial candidate view; original provider bytes stay intact."""
    from copy import deepcopy
    root=Path(root);valid=set(changes['valid_codes'])
    if not valid:raise ValueError('PARTIAL_VALID_UNIVERSE_EMPTY')
    original=checked(root,result['source_freeze'])
    if load(original)!=artifact:raise ValueError('PARTIAL_ORIGINAL_FREEZE_BINDING_MISMATCH')
    native_path=Path(artifact['tdx']['path'])
    if not native_path.is_absolute():native_path=root/native_path
    if sha256_file(native_path)!=artifact['tdx']['sha256']:raise ValueError('PARTIAL_NATIVE_DIGEST_MISMATCH')
    native=load(native_path);view=deepcopy(artifact)
    quality=dict(contract_id='V4_DAILY_EFFECTIVE_UNIVERSE_PARTIAL_R1',status='PARTIAL_READY',
        full_identity_coverage=False,valid_codes=sorted(valid),effective_universe_count=len(valid),
        invalid_codes=changes['invalid_codes'],absent_codes=changes['absent_codes'],
        original_source_freeze=result['source_freeze'],original_tdx=artifact['tdx'],
        exclusion_policy='NO_INVALID_BAR; PRESERVE_ENTITY_HISTORY; NO_DELISTING_INFERENCE',
        statistics_denominator='CURRENT_VERIFIED_EFFECTIVE_UNIVERSE',unmapped_policy='UNKNOWN_NO_INVENTED_MEMBERSHIP')
    key=sha256_bytes(_json_bytes(quality));folder=root/'data/v4/dynamic_daily_sources/effective_universe_r1'/day/key
    native_view=dict(native,target_bars=[r for r in native['target_bars'] if r['source_security_key'].upper() in valid],
        source_quality=quality,original_native_binding=artifact['tdx'])
    np=folder/'NATIVE_VIEW.json'
    if not np.exists():atomic_json(root,np,native_view)
    view['tdx']=dict(ref(root,np),bytes=np.stat().st_size)
    # The Owner currently consumes an absolute TDX path. Hash still binds this view.
    view['tdx']['path']=str(np.resolve())
    view['normalized']['daily']['rows']=[r for r in view['normalized']['daily']['rows'] if r['code'].upper() in valid]
    view['source_quality']=quality
    view['contract_id']='DYNAMIC_DAILY_EFFECTIVE_UNIVERSE_FREEZE_R1'
    fp=folder/'FREEZE.json'
    if not fp.exists():atomic_json(root,fp,view)
    return view,dict(result,source_freeze=ref(root,fp),source_quality=quality,
        baostock_row_count=len(view['normalized']['daily']['rows']),tdx_bar_count=len(native_view['target_bars']),
        identity_coverage='PARTIAL_READY',first_capture_source_candidate={})

def gate_adapter(original,root,day,artifact,result,now=None):
    result,gate=original(root,day,artifact,result,now)
    changes=gate.get('dependency_bindings',{}).get('code_changes',{})
    if changes.get('invalid_codes') and not artifact.get('source_quality'):
        artifact,result=filtered_freeze(root,day,artifact,result,changes)
        result,gate=original(root,day,artifact,result,now)
    if artifact.get('source_quality'):
        gate=dict(gate,source_quality=artifact['source_quality'],identity_coverage='PARTIAL_READY')
    if gate['status']!='WAIT_DATED_IDENTITY_AUTHORITY' or not (gate['dependency_bindings'].get('unknown_codes') or gate['dependency_bindings'].get('missing_codes')):
        if artifact.get('source_quality'):
            p=Path(root)/'data/v4/dynamic_daily_sources/source_readiness'/day/(sha256_bytes(_json_bytes(gate))+'.json')
            if not p.exists():atomic_json(root,p,gate)
            result=dict(result,source_readiness=ref(root,p),source_quality=artifact['source_quality'])
        return result,gate
    identity=admitted_identity(root,day,gate,artifact)
    from .source_readiness_v2 import source_readiness
    sources=dict(gate['sources']);old=sources.pop('dated_identity_authority')
    readiness=source_readiness(day,now or datetime.now(timezone.utc),sources)
    deps=dict(gate['dependency_bindings'],identity=identity,predecessor_identity=gate['dependency_bindings']['identity'],
        new_listing_identity=identity,accepted_pool_count=len(old['actual_codes']),entity_pool_count=len(load(checked(root,identity))['rows']),
        absent_codes=gate['dependency_bindings']['missing_codes'],active_universe=sorted(old['actual_codes']),
        accepted_pool_sha256=sha256_bytes(_json_bytes(sorted(old['actual_codes']))),
        unknown_codes=[],missing_codes=[],newly_admitted_codes=sorted(set(old['actual_codes'])-set(old['expected_codes'])))
    if artifact.get('source_quality'):readiness.update(source_quality=artifact['source_quality'],identity_coverage='PARTIAL_READY')
    readiness.update(source_freeze=result['source_freeze'],dependency_bindings=deps,
        native_provider_facts=gate['native_provider_facts'],AS_RECORDED=False,PIT_ELIGIBLE=False,
        dated_identity_authority=dict(contract_id=CONTRACT,status='CURRENT_DAY_OBSERVED_CODE_BOUND',identity=identity,predecessor=gate['dependency_bindings']['identity']))
    # New identity participates in every generation/source key. Old readiness
    # is retained; append a new receipt, never replace an accepted source.
    p=Path(root)/'data/v4/dynamic_daily_sources/source_readiness'/day/(sha256_bytes(_json_bytes(readiness))+'.json')
    if not p.exists():atomic_json(root,p,readiness)
    return dict(result,source_readiness=ref(root,p),source_ready=readiness['source_ready']),readiness

def ready_build(root,freeze_binding,**kwargs):
    from . import operational_daily_ready_owner_v2 as ready
    from . import operational_daily_owner_v1 as owner
    from .operational_owner_adapter_v1 import replay
    gate=load(checked(root,kwargs['source_readiness']));identity=gate['dependency_bindings'].get('new_listing_identity')
    if not identity:return ready.build(root,freeze_binding,**kwargs)
    root=Path(root).resolve();parent=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    life=parent['owners'][parent['accepted_trade_date']]['lifecycle'];life_path=checked(root,life)
    overlay=root/'data/v4/dynamic_daily_sources/new_listing_r1'/load(checked(root,freeze_binding))['target_session']/'overlays'/identity['sha256']
    atomic_json(root,overlay/'LIFECYCLE.json',dict(load(life_path),identity=identity))
    data_head=load(root/'data/v4/V4_DATA_ACCEPTED_HEAD.json')
    data_head['component_artifacts']['IDENTITY_UNIVERSE']=identity
    atomic_json(root,overlay/'DATA_HEAD.json',data_head)
    def mapped_load(path):
        return load(overlay/'LIFECYCLE.json') if Path(path).resolve()==life_path.resolve() else load(path)
    prepared=private_scope(owner,dict(load=mapped_load))['prepare']
    def prepare(*args,**kw):
        context=prepared(*args,**kw)
        context['mappings'][str((root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').resolve())]=str(overlay/'DATA_HEAD.json')
        # Identity is date-bounded: replay excludes this listing before IPO day.
        return context
    proxy=SimpleNamespace(**vars(owner));proxy.prepare=prepare
    return private_scope(ready,dict(owner=proxy))['build'](root,freeze_binding,**kwargs)
