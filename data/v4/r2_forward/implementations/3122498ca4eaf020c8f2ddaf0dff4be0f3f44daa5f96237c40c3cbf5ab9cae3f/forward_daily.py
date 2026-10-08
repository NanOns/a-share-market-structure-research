"""Corrected, accepted-input Forward adapter; immutable T0 and bounded evaluation."""
import copy,json,math,sqlite3
from decimal import Decimal
from pathlib import Path
from adjustment.tdx_adjustment import build_affine_factors,xrxd_from_gbbq
from focus_tracker.v4_path_adapter import AcceptedPaths,checked
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_15_settlement import VectorPriceSource,due_plan
from .current_v4_context import SourceInvalid,canonical,digest
from .v4_daily_refresh import atomic_bytes
from .production_v4 import reference

CONTRACT='R2_FORWARD_DUE_LOCAL_CORRECTED_V1'

def calendar_extension(frozen,current,t0,cutoff):
    if current!=sorted(set(current)) or frozen!=sorted(set(frozen)):
        raise SourceInvalid('FORWARD_CALENDAR_NOT_ORDERED_UNIQUE')
    if t0 not in frozen or t0 not in current or cutoff not in current:
        raise SourceInvalid('FORWARD_CALENDAR_BOUNDS')
    prefix=[d for d in frozen if d<=t0]
    if [d for d in current if d<=t0]!=prefix:
        raise SourceInvalid('FORWARD_T0_CALENDAR_PREFIX_REWRITE')
    # Any already frozen future sessions also remain exact when known locally.
    overlap=[d for d in frozen if d<=min(frozen[-1],current[-1])]
    if [d for d in current if d<=min(frozen[-1],current[-1])]!=overlap:
        raise SourceInvalid('FORWARD_FROZEN_CALENDAR_REWRITE')
    return [d for d in current if d<=cutoff]

class OperationalForwardAuthority(CurrentStageAuthority):
    """Explicit operational successor, without changing historical stage grants."""
    def __init__(self,root,sessions,bindings):
        self.root=Path(root).resolve();self.sessions=sessions;self.operational_bindings=bindings
    def bindings(self):return copy.deepcopy(self.operational_bindings)

class ForwardStore:
    def __init__(self,root,folder):self.root=Path(root).resolve();self.folder=self.root/folder
    def read(self,binding):return json.loads(checked(self.root,binding).read_bytes())
    def append(self,kind,key,value):
        path=self.folder/kind/(key+'.json');raw=canonical(value)
        if path.exists() and path.read_bytes()!=raw:raise SourceInvalid('FORWARD_APPEND_IDENTITY_CONFLICT')
        if not path.exists():atomic_bytes(path,raw)
        return reference(self.root,path)
    def refs(self,kind):return [reference(self.root,p) for p in sorted((self.folder/kind).glob('*.json'))]

class LocalForwardPriceSource(VectorPriceSource):
    evidence_class='REAL_ACCEPTED_LOCAL_CORRECTED_FORWARD'
    def __init__(self,root,inputs,t0,cutoff,t0_coordinates=None,kernel=None,accepted_paths=None):
        self.paths=accepted_paths or AcceptedPaths(root,inputs);self.t0=t0;self.cutoff=cutoff
        if self.paths.bindings!=inputs:raise SourceInvalid('FORWARD_SHARED_INPUT_MISMATCH')
        self.coordinates=t0_coordinates or {};self.cache={};self.read_log=[]
        self.binding=dict(contract_id=CONTRACT,sha256=digest(canonical(dict(inputs=inputs,t0=t0,cutoff=cutoff,
            calendar=self.paths.calendar,kernel=kernel))),sources=inputs,cutoff=cutoff,T0=t0,
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,strict_pit=False)
    def _rows(self,sid,basis):
        key=(sid,basis)
        if key in self.cache:return self.cache[key]
        if basis>self.cutoff or self.t0>basis:raise SourceInvalid('FORWARD_FUTURE_BASIS')
        with sqlite3.connect(self.paths.series.as_uri()+'?mode=ro',uri=True) as db:
            bars={day:json.loads(payload) for day,payload in db.execute(
                'SELECT day,payload FROM bars WHERE security=? AND day>=? AND day<=?',(sid,self.t0,basis))}
        if self.t0 not in bars:self.cache[key]={};return {}
        symbol=bars[self.t0]['symbol'];events=[e for e in self.paths.events[symbol]
            if int(self.t0.replace('-',''))<e.event_date<=int(basis.replace('-',''))]
        blocked=any(self.paths.dispositions.get(str(e.category),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT')
            in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT') for e in events)
        factors=build_affine_factors([int(d.replace('-','')) for d in sorted(bars)],
            [xrxd_from_gbbq(e) for e in events if e.category==1])
        coord=self.coordinates.get(sid,dict(qfq_mul='1',qfq_add='0'))
        mul,add=float(coord['qfq_mul']),float(coord['qfq_add'])
        if not math.isfinite(mul) or mul<=0 or not math.isfinite(add):raise SourceInvalid('FORWARD_T0_COORDINATE_UNKNOWN')
        t0factor=factors[int(self.t0.replace('-',''))]
        t0transform=dict(alpha=float(t0factor.qfq_mul)/mul,beta=float(t0factor.qfq_add)-float(t0factor.qfq_mul)*add/mul)
        result={}
        for day in [d for d in self.paths.calendar if self.t0<d<=basis]:
            status=self.paths.status.get(day,{}).get(sid,{})
            bar=bars.get(day);valid=not status.get('status_conflict') and bool(status)
            row=dict(trade_date=day,evaluation_basis_date=basis,source_asof=day,available_at=None,
                knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False,
                verified_identity=valid,verified_adjustment=not blocked,T0_basis_verified=True,
                adjustment_identity=coord.get('adjustment_identity',self.paths.bindings['gbbq']['sha256']),T0_transform_coefficients=t0transform)
            if bar:
                raw=[float(Decimal(x)) for x in bar['raw_ohlc']]
                validprice=all(math.isfinite(x) and x>0 for x in raw) and raw[2]<=min(raw[0],raw[3])<=max(raw[0],raw[3])<=raw[1]
                f=factors[int(day.replace('-',''))]
                row.update(open=raw[0],high=raw[1],low=raw[2],close=raw[3],status='ACTUAL_TRADED',
                    verified_identity=valid and status.get('actual_bar_present') is True and status.get('source_security_key')==symbol,
                    verified_adjustment=not blocked and validprice,transform_coefficients=dict(alpha=float(f.qfq_mul),beta=float(f.qfq_add)))
            elif valid and status.get('status')=='SUSPENDED' and status.get('actual_bar_present') is False:
                row.update(status='CONFIRMED_SUSPENSION',transform_coefficients=dict(alpha=1.,beta=0.))
            else:row.update(status='DATA_MISSING',verified_identity=False,transform_coefficients=dict(alpha=1.,beta=0.))
            result[day]=row
        self.cache[key]=result;return result
    def read(self,sid,day,basis,cutoff):
        if cutoff!=self.cutoff or day>cutoff or basis>cutoff or day<=self.t0:raise SourceInvalid('FORWARD_PRICE_READ_OUTSIDE_ACCEPTED_WINDOW')
        self.read_log.append(dict(security_id=sid,trade_date=day,basis_date=basis,cutoff=cutoff))
        return copy.deepcopy(self._rows(sid,basis).get(day,dict(trade_date=day,evaluation_basis_date=basis)))

def verify_due_settlement(publication,cutoff):
    due=[p for p in publication['plans'] if p.get('due_date') and p['due_date']<=cutoff]
    rows={(o['enrollment_id'],o['horizon']):o for o in publication['outcomes']
          if o.get('adapter_contract_id')==CONTRACT and o.get('report_cutoff')==cutoff}
    for plan in due:
        row=rows.get((plan['enrollment_id'],plan['horizon']))
        if not row or row['outcome_status']=='PENDING' or row['due_date']!=plan['due_date']:
            raise SourceInvalid('DAILY_FORWARD_DUE_REQUIRES_ACCEPTED_SETTLEMENT_OWNER')
    return len(due)
