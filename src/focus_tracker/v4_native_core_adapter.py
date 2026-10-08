"""New Focus namespace for observation-dated, hash-bound native Core facts."""
import gzip,json,math,sqlite3
from .v4_path_adapter import AcceptedPaths as PricePaths,enriched_project as price_project,checked
from .path_state_v2 import STOCK_PRIORITY,classify_stock_v2
from .predicates import Tri
from workbench_service.current_v4_context import SourceInvalid
CONTRACT='R2_V4_FOCUS_NATIVE_CORE_PATH_V1'
CAPABILITY='R2_V4_FOCUS_NATIVE_CORE_FACTS_V1'

class AcceptedPaths(PricePaths):
    def __init__(self,root,bindings):
        super().__init__(root,bindings)
        self.native={}
        for day,owner in bindings.get('native_core',{}).items():
            if owner.get('contract_id')!=CAPABILITY or owner.get('trade_date')!=day or owner.get('price_basis')!='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE':
                raise SourceInvalid('FOCUS_NATIVE_CORE_CONTRACT_OR_COORDINATE')
            result={}
            for kind in ('factors','profiles'):
                with gzip.open(checked(root,owner[kind]),'rt',encoding='utf8') as stream:
                    for line in stream:
                        row=json.loads(line)
                        if row['trade_date']!=day:raise SourceInvalid('FOCUS_NATIVE_CORE_DATE_MIX')
                        if kind=='profiles' and row['source_cutoff']!=day:raise SourceInvalid('FOCUS_NATIVE_PROFILE_CUTOFF')
                        sid=row['security_id'];values=result.setdefault(sid,{})
                        cells=row['fields'] if kind=='factors' else row['states']
                        for key in (('ma20','ret5') if kind=='factors' else ('severe_extension',)):
                            cell=cells.get(key)
                            if not cell:raise SourceInvalid('FOCUS_NATIVE_CORE_PROVIDER_MISSING:'+key)
                            parameter='V4_03_CORE_FACTOR_PARAMETER_SET_V1' if kind=='factors' else 'V4_04_CORE_PROFILE_PARAMETER_SET_V1'
                            if cell.get('parameter_set_id')!=parameter:raise SourceInvalid('FOCUS_NATIVE_CORE_PARAMETER:'+key)
                            if kind=='factors' and cell.get('value') is not None and not cell.get('unknown_reason') and cell.get('window_end_trade_date')!=day:raise SourceInvalid('FOCUS_NATIVE_CORE_WINDOW_END:'+key)
                            value=cell.get('value')
                            if cell.get('unknown_reason'):value=None
                            if key=='severe_extension':
                                if value is not None and type(value) is not bool:raise SourceInvalid('FOCUS_NATIVE_CORE_BOOLEAN')
                            elif value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
                                raise SourceInvalid('FOCUS_NATIVE_CORE_NUMBER')
                            values[key]=value
            with sqlite3.connect(checked(root,owner['series']).as_uri()+'?mode=ro',uri=True) as db:
                for sid,payload in db.execute('SELECT security,payload FROM bars WHERE day=?',(day,)):
                    bar=json.loads(payload);raw=bar.get('raw_ohlc');qfq=bar.get('qfq_ohlc')
                    if sid in result and raw and qfq:
                        if not math.isclose(float(raw[3]),float(qfq[3]),rel_tol=1e-12,abs_tol=1e-9):raise SourceInvalid('FOCUS_NATIVE_SERIES_TARGET_COORDINATE')
                        result[sid]['close']=float(qfq[3])
            self.native[day]=(owner,result)

    def native_facts(self,sid,day,path):
        if day not in self.native:return dict(contract_id=CAPABILITY,status='UNAVAILABLE',reason='OBSERVATION_DAY_NATIVE_CORE_NOT_BOUND',facts={})
        owner,rows=self.native[day];row=rows.get(sid)
        if row is None:return dict(contract_id=CAPABILITY,status='UNAVAILABLE',reason='SECURITY_NATIVE_CORE_NOT_BOUND',facts={},source=owner)
        if path['quality']!='READY':return dict(contract_id=CAPABILITY,status='UNAVAILABLE',reason='ACTUAL_PRICE_PATH_NOT_READY',facts={},source=owner)
        if row.get('close') is None:return dict(contract_id=CAPABILITY,status='UNAVAILABLE',reason='NATIVE_SERIES_OBSERVATION_BAR_NOT_BOUND',facts={},source=owner)
        if not math.isclose(float(path['close']),row['close'],rel_tol=1e-12,abs_tol=1e-9):
            raise SourceInvalid('FOCUS_NATIVE_PRICE_COORDINATE_END_MISMATCH')
        return dict(contract_id=CAPABILITY,status='BOUND',source=owner,trade_date=day,
                    facts=dict(ma20=row.get('ma20'),r5=row.get('ret5'),source_extended=row.get('severe_extension')))


def enriched_project(days,paths):
    result=price_project(days,paths)
    rows={day:{r['entity_id']:r for r in values} for day,values in days.items()}
    events={(e['episode_id'],e['trade_date']):e for e in result['events']}
    for episode in result['episodes']:
        for obs in episode['observations']:
            day=obs['trade_date'];row=rows[day].get(episode['entity_id']) or {};path=obs['price_path']
            native=paths.native_facts(episode['entity_id'],day,path)
            invalidation={'INVALID':Tri.TRUE,'VALID':Tri.FALSE}.get(row.get('validity'),Tri.UNKNOWN)
            confirmed=(row.get('raw_qualification') or {}).get('CONFIRMED')
            facts=dict(has_actual_bar=path['quality']=='READY',close=path.get('close'),
                drawdown_current=(path['metrics'] or {}).get('drawdown_current'),mfe=(path['metrics'] or {}).get('mfe'),
                launch_confirm={'TRUE':True,'FALSE':False}.get(confirmed),
                exited=episode['end_date'] is not None and day>=episode['end_date'],
                early_or_setup=obs.get('membership')=='EARLY',waiting_evaluable=bool(row),**native['facts'])
            decision=classify_stock_v2(facts,invalidation=invalidation,applicable=frozenset(STOCK_PRIORITY))
            obs.update(path_state=decision.resolved_primary_state,best_confirmed_state=decision.best_confirmed_state,
                path_resolution=decision.path_resolution,path_reason='HIGHER_PRIORITY_UNRESOLVED' if decision.higher_priority_unresolved else None,
                higher_priority_unresolved=list(decision.higher_priority_unresolved),predicate_evidence=decision.predicate_evidence,
                native_core_evidence=native,path_contract_id=CONTRACT)
            if (episode['episode_id'],day) in events:events[(episode['episode_id'],day)].update(obs)
    return result
