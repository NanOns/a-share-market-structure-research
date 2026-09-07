"""Snapshot normalization adapter; keeps the sealed Decimal affine engine intact."""
from decimal import Decimal
import numpy as np
import pandas as pd
import pyarrow as pa
from adjustment.tdx_adjustment import build_affine_factors

DAY_DTYPE = np.dtype([('date','<u4'),('open','<u4'),('high','<u4'),('low','<u4'),
                      ('close','<u4'),('amount','<f4'),('volume','<u4'),('reserved','<u4')])


def validate_raw(rows):
    if not len(rows):
        raise ValueError('EMPTY_DAY')
    if np.any(np.diff(rows['date'].astype('int64')) <= 0):
        raise ValueError('DUPLICATE_OR_UNSORTED_DAY')
    if np.any(rows['low'] > np.minimum(rows['open'],rows['close'])) or np.any(rows['high'] < np.maximum(rows['open'],rows['close'])):
        raise ValueError('INVALID_OHLC_ORDER')
    if not np.isfinite(rows['amount']).all() or np.any(rows['amount'] < 0):
        raise ValueError('INVALID_AMOUNT')
    pd.to_datetime(rows['date'].astype(str),format='%Y%m%d',errors='raise')


def exact_adjust_cents(cents, factor):
    """Vector fast path with conservative numerical-error band and Decimal tie fallback."""
    raw = np.asarray(cents,dtype=np.int64)
    a,b = np.longdouble(str(factor.qfq_mul)),np.longdouble(str(factor.qfq_add))
    y = a*raw + 100*b
    bound = 64*np.finfo(np.longdouble).eps*(np.abs(a*raw)+np.abs(100*b)+1)+1e-8
    fallback = np.abs(np.abs(y)-np.floor(np.abs(y))-.5) <= bound
    if not np.isfinite(y).all() or np.any(np.abs(y)>9e15):
        raise ValueError('ADJUSTED_PRICE_OVERFLOW')
    out=(np.sign(y)*np.floor(np.abs(y)+.5)).astype('int64')
    for i in np.flatnonzero(fallback):
        out[i]=int(factor.qfq_price(Decimal(int(raw[i]))/100)*100)
    return out


def decimal_prices(cents, valid):
    cents=np.asarray(cents,dtype='int64')
    storage=np.zeros((len(cents),2),dtype='<i8')
    storage[:,0]=cents
    storage[:,1]=np.where(cents<0,-1,0)
    validity=pa.py_buffer(np.packbits(np.asarray(valid,dtype='uint8'),bitorder='little'))
    return pa.Array.from_buffers(pa.decimal128(18,2),len(cents),[validity,pa.py_buffer(storage)])


def normalize(sid, rows, sessions, events, current_member=True, confirmed_suspension_dates=None):
    """Historical rows are a single cutoff snapshot, never historical PIT factor inputs."""
    confirmed_suspension_dates=set(int(value) for value in (confirmed_suspension_dates or ()))
    cutoff=int(sessions[-1])
    rows=rows[rows['date']<=cutoff]
    if len(rows):
        validate_raw(rows)
        start=min(int(rows['date'][0]),int(sessions[max(0,len(sessions)-251)]))
        dates=np.union1d(sessions[sessions>=start],rows['date'])
    else:
        dates=sessions[-251:]
    n=len(dates)
    master=np.isin(dates,sessions)
    loc=np.searchsorted(dates,rows['date'])
    actual=np.zeros(n,dtype=bool); actual[loc]=True
    state=np.full(n,'FILE_MISSING' if not len(rows) else 'MISSING_DATA',dtype=object)
    if len(rows):
        state[dates<rows['date'][0]]='NOT_LISTED_YET'
        state[(dates>=rows['date'][0])&(dates<=rows['date'][-1])]='INFERRED_GAP'
        if not current_member:
            state[dates>rows['date'][-1]]='DELISTED_OR_INACTIVE'
        state[actual]='BAR'
        confirmed=np.isin(dates,list(confirmed_suspension_dates)) & ~actual & master
        state[confirmed]='CONFIRMED_SUSPENSION'
    synthetic=state=='CONFIRMED_SUSPENSION'
    counts=np.isin(sessions[-20:],rows['date']).sum()
    normal=bool(current_member and len(rows)>=120 and len(rows) and rows['date'][-1]==cutoff and counts/len(sessions[-20:])>=.75)
    ua='IN_NORMAL_UNIVERSE' if normal else 'OUTSIDE_NORMAL_UNIVERSE'
    # Only query the engine at interval representatives, then reuse its exact factors.
    # QFQ is constant between event dates; no new adjustment implementation is introduced.
    query={int(rows['date'][0]),int(rows['date'][-1])} if len(rows) else set()
    for e in events:
        if len(rows) and e.ex_day<=rows['date'][-1]:
            j=np.searchsorted(rows['date'],e.ex_day)
            if j<len(rows): query.add(int(rows['date'][j]))
    factors=build_affine_factors(sorted(query),events)
    reps=np.array(sorted(factors),dtype='int64')
    which=np.searchsorted(reps,rows['date'],side='right')-1
    adj={f:np.zeros(n,dtype='int64') for f in ('open','high','low','close')}
    mul=np.full(n,None,dtype=object); add=np.full(n,None,dtype=object)
    for k,d in enumerate(reps):
        mask=which==k; dest=loc[mask]; fac=factors[int(d)]
        mul[dest]=str(fac.qfq_mul); add[dest]=str(fac.qfq_add)
        for f in adj: adj[f][dest]=exact_adjust_cents(rows[f][mask],fac)
    close=np.where(actual,adj['close']/100,np.nan)
    aligned=pd.Series(close).ffill().to_numpy(copy=True)
    aligned[~(actual|synthetic)]=np.nan
    volume=np.full(n,np.nan); amount=np.full(n,np.nan)
    volume[loc]=rows['volume']; amount[loc]=rows['amount'].astype('float64')
    aligned_volume=volume.copy(); aligned_volume[synthetic]=0
    aligned_amount=amount.copy(); aligned_amount[synthetic]=0
    flags=state.copy(); flags[actual]='OK'
    nonpositive=actual & (adj['close']<=0); flags[nonpositive]='NONPOSITIVE_QFQ'
    flags[~master]=['OFF_MASTER_CALENDAR' if f=='OK' else str(f)+'|OFF_MASTER_CALENDAR' for f in flags[~master]]
    columns={'security_id':pa.array([sid]*n),
        'date':pa.array(pd.to_datetime(dates.astype(str),format='%Y%m%d').date,type=pa.date32())}
    for f in adj:
        raw=np.zeros(n,dtype='int64'); raw[loc]=rows[f]
        columns['raw_'+f]=decimal_prices(raw,actual)
        columns['adj_'+f]=decimal_prices(adj[f],actual)
    columns.update(raw_volume=pa.array(volume,mask=~actual,type=pa.float64()).cast(pa.int64()),
        raw_amount=pa.array(amount,mask=~actual),qfq_mul=pa.array(mul,type=pa.string()),qfq_add=pa.array(add,type=pa.string()),
        price_basis=pa.array(['TDX_NATIVE_QFQ']*n),project_price_basis=pa.array(['FORWARD_ADJUSTED']*n),
        adjustment_status=pa.array(['VERIFIED_REPRODUCIBLE_TDX_NATIVE']*n),
        adjustment_version=pa.array(['tdx-affine-qfq-v0.2']*n),
        # ``tradable`` is retained as a Phase4 compatibility field and means
        # only "an actual local bar exists".  It is not proof of exchange
        # trade status.  R1's explicit fields carry the precise semantics.
        tradable=pa.array(actual),has_actual_bar=pa.array(actual),data_observed=pa.array(actual),
        has_positive_amount=pa.array(actual & (amount>0)),
        trade_status_known=pa.array(state=='CONFIRMED_SUSPENSION'),
        is_synthetic_fill=pa.array(synthetic),
        is_master_session=pa.array(master),
        security_type=pa.array(['A_STOCK']*n),universe_status=pa.array([ua]*n),
        universe_asof_date=pa.array([cutoff]*n,type=pa.int32()),
        data_quality_flag=pa.array(flags),missing_state=pa.array(state),
        aligned_close=pa.array(aligned,from_pandas=True),
        aligned_volume=pa.array(aligned_volume,from_pandas=True),aligned_amount=pa.array(aligned_amount,from_pandas=True))
    context=pd.DataFrame({'date':dates,'close':aligned,'high':np.where(actual,adj['high']/100,np.nan),
        'low':np.where(actual,adj['low']/100,np.nan),'amount':aligned_amount,'synthetic':synthetic,'state':state})
    stats={'security_id':sid,'input_bar_count':len(rows),'aligned_rows':n,'normal':normal,
           'synthetic':int(synthetic.sum()),'inferred_gap':int((state=='INFERRED_GAP').sum()),
           'confirmed_suspension':int((state=='CONFIRMED_SUSPENSION').sum()),
           'missing':int((state=='MISSING_DATA').sum()),
           'nonpositive':int(nonpositive.sum()),'qfq_null_count':int((~actual).sum()),
           'off_master_calendar_count':int((~master).sum()),
           'anchor':int(rows['date'][-1]) if len(rows) else None,
           'recent_valid_bar_count':int(counts),'states':pd.Series(state).value_counts().to_dict()}
    return pa.table(columns),context.loc[master].tail(251).reset_index(drop=True),stats
