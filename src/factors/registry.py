import hashlib
import json

VERSION='factor-contract-v1.0'
REGISTRY=[]


def add(name,n,formula,inputs,*,kind,min_samples=None,positive=False,unit='ratio'):
    entry=dict(name=name,version=VERSION,formula=formula,window=n,
        min_samples=min_samples or n,include_t=True,input_columns=inputs,
        price_basis='RAW_AMOUNT' if kind.startswith('amount') else 'TDX_NATIVE_QFQ',
        universe='CURRENT_NORMAL_UNIVERSE_AT_OUTPUT_DATE',calendar_basis='MASTER_TRADING_CALENDAR',
        null_rule='NULL if any required observation missing or denominator zero; never fill NULL with zero',
        nonpositive_rule='NULL; NONPOSITIVE_QFQ and NONPOSITIVE_PRICE_WINDOW' if positive else 'No log/price ratio; negative prices retained',
        suspension_rule='Use aligned_close/amount for proven suspension; high/low stay NULL and extrema require all N highs/lows',
        output_unit=unit,kind=kind,positive=positive,
        extreme_rule='FLAG only: absolute value > 10 for dimensionless output; no winsorization',
        epsilon=1e-12,rs_min_universe=100)
    entry['formula_hash']=hashlib.sha256(json.dumps(entry,sort_keys=True).encode()).hexdigest()
    REGISTRY.append(entry)


for n in (5,10,20,60): add(f'RET{n}',n,f'C[t]/C[t-{n}]-1',['aligned_close'],kind='ret',min_samples=n+1,positive=True)
for n in (5,10,20,60): add(f'MA{n}',n,f'mean(C[t-{n-1}:t])',['aligned_close'],kind='ma',unit='CNY')
for n in (20,60):
    add(f'TREND_SLOPE_{n}',n,'OLS slope of ln(C) on x=0..N-1',['aligned_close'],kind='slope',positive=True,unit='log_price/session')
    add(f'TREND_R2_{n}',n,'1-SSE/SST of OLS ln(C); constant series SST=0 -> NULL',['aligned_close'],kind='r2',positive=True)
for n in (20,60,120): add(f'POS{n}',n,'(C[t]-min(L))/(max(H)-min(L)); zero range -> NULL; epsilon=1e-12',['aligned_close','adj_high','adj_low'],kind='pos',positive=True)
for n in (20,60): add(f'DIST_HIGH{n}',n,'C[t]/max(H)-1; max(H)<=0 -> NULL',['aligned_close','adj_high'],kind='dist',positive=True)
for n in (20,60): add(f'MDD{n}',n,'min_j(C[j]/running_max(C)[j]-1) within N sessions',['aligned_close'],kind='mdd',positive=True)
add('VOLATILITY20',20,'sample_std(ln(C[j]/C[j-1])), 20 returns, ddof=1, not annualized',['aligned_close'],kind='vol',min_samples=21,positive=True)
for n in (5,10,20,60): add(f'RS{n}',n,'RET_N - same-date valid NORMAL_UNIVERSE median(RET_N); count<100 -> NULL',[f'RET{n}','universe_status'],kind='rs',min_samples=n+1,positive=True)
for n in (5,10,20): add(f'AMOUNT_MA{n}',n,'mean(raw/aligned amount over N sessions)',['aligned_amount'],kind='amount_ma',unit='CNY')
add('AMOUNT_RATIO20',20,'Amount[t]/AMOUNT_MA20[t]; denominator<=0 -> NULL',['aligned_amount'],kind='amount_ratio')
add('RETURN_CONCENTRATION_20',20,'max(max(simple_ret_1d,0))/sum(max(simple_ret_1d,0)); 20 returns; top_k=1; zero denominator -> NULL',['aligned_close'],kind='concentration',min_samples=21,positive=True)

NAMES=[r['name'] for r in REGISTRY]
