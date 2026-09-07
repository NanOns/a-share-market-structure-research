from collections import defaultdict, Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from adjustment.tdx_adjustment import xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq, file_sha256
from tdx.security_master import read_industry_assignments, current_a_stock_ids, classify_security
from normalize.phase1 import normalize, DAY_DTYPE
from common.snapshot_reader import assert_no_future_rows
from factors.registry import REGISTRY, NAMES, VERSION
from factors.engine import calculate, add_rs
from validation.phase0_2b import atomic, encoded

SAMPLES=('SH.600519','SZ.000001','SZ.000651','SZ.300750','SH.688001')


def write_parquet(path,table,tdx):
    if tdx.resolve() in path.resolve().parents: raise ValueError('TDX_READ_ONLY')
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,suffix='.tmp'); os.close(fd)
    try:
        pq.write_table(table,tmp,compression='zstd')
        assert pq.ParquetFile(tmp).metadata.num_rows==table.num_rows
        with open(tmp,'r+b') as stream: os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def phase1_gate(checks,pending=0):
    if not all(checks.values()): return 'BLOCKED'
    return 'PARTIAL_PASS' if pending else 'PASS'


def validate_canonical_dates_before_write(normalized,factors,cutoff):
    """Reject future canonical rows before any staged output is created."""
    for path in (Path(normalized),Path(factors)):
        if path.exists(): assert_no_future_rows(path,cutoff)
    return True


def registry_documents(root,tdx):
    # JSON is a valid YAML subset, avoiding ambiguity in formula strings.
    atomic(root/'config/factors.yaml',encoded({'version':VERSION,'factors':REGISTRY}),tdx)
    header='''# Formal Factor Contract V1

Version: factor-contract-v1.0. Authority: V0.3 baseline sections 18–29 plus Phase1 task card.
29 implemented atomic factors; no scores, rankings, scanner, or index OHLC.

Every record below fixes name/version/formula/window/min_samples/include_t/input_columns/price_basis/universe/calendar_basis/null_rule/nonpositive_rule/suspension_rule/output_unit and formula_hash. config/factors.yaml contains the identical machine-readable registry (JSON-compatible YAML).

First production factor output is the latest cutoff snapshot only. Earlier normalized QFQ rows are a cutoff-anchored analytical history, not PIT factor rows. No historical NORMAL_UNIVERSE is reconstructed from today's membership. Daily runs may append a new independently anchored snapshot. Historical --date is rejected until historical membership/adjustment governance exists.

The original V0.3 fixes AMOUNT_RATIO20 = Amount(t)/AMOUNT_MA20, and RETURN_CONCENTRATION_20 = max positive simple daily return / sum positive daily returns, N=20, top_k=1. These names supersede the task's illustrative aliases. Do not add duplicate AMOUNT_RATIO_5_20 or uncontracted RS percentiles.

N sessions includes t; RET_N requires N+1 complete aligned closes. Volatility/concentration need 21 closes for 20 returns. All ratio/log-price factors reject any nonpositive close in their own required window. MA uses finite prices even when nonpositive. NULL is never zero. POS uses epsilon=1e-12 with exactly zero range -> NULL. Constant log-price R2 is NULL. Volatility is daily sample standard deviation, ddof=1, not annualized.

Legal suspension alignment carries close and uses zero amount/volume. Actual high/low stay NULL on synthetic rows; therefore POS and DIST_HIGH require N actual finite highs/lows and can be NULL in suspension windows. This conservative rule does not lower min_samples. SUSPENSION_HEAVY_WINDOW means >25% synthetic rows. EXTREME_VALUE means abs(dimensionless value)>10; flag only. ZERO_AMOUNT/zero positive-return sum are explicit null reasons.

RS uses same-date finite RET_N of IN_NORMAL_UNIVERSE securities only, minimum100, arithmetic subtraction from median. rs_valid_universe_count_N records each horizon's count. OUTSIDE_NORMAL_UNIVERSE calculations remain separately labeled and never enter the benchmark. Every factor has __valid_sample_count and __quality_flag columns; aggregate factor_quality_flag is their union.

'''
    atomic(root/'docs/FACTOR_CONTRACT_V1.md',(header+'```json\n'+json.dumps(REGISTRY,ensure_ascii=False,indent=2)+'\n```\n').encode('utf8'),tdx)


def run(root,tdx,requested='latest',resolved_cutoff_date=None):
    if requested!='latest': raise ValueError('Historical factors prohibited without PIT membership governance; use --date latest')
    seal=json.loads((root/'reports/phase0_2c/PHASE0_2C_RELEASE_SEAL.json').read_text('utf8'))
    assert seal['final_status']=='FULL_PASS_TDX_NATIVE' and seal['adjusted_dataset_allowed']
    cfg=tdx/'T0002/hq_cache/tdxhy.cfg'; gbbq=tdx/'T0002/hq_cache/gbbq'; mapping=tdx/'T0002/hq_cache/gbbq.map'
    current=current_a_stock_ids(read_industry_assignments(cfg))
    sources={str(p):file_sha256(p) for p in (cfg,gbbq,mapping)}
    paths={}
    for market in ('sh','sz','bj'):
        for p in sorted((tdx/'vipdoc'/market/'lday').glob('*.day')):
            code=p.stem[-6:]; sid=market.upper()+'.'+code
            if classify_security(market,code,current)=='A_STOCK': paths[sid]=p
    for sid in current: paths.setdefault(sid,None)
    last_dates=[]
    for sid in current:
        p=paths[sid]
        if p and p.stat().st_size>=32:
            with p.open('rb') as f: f.seek(-32,2); last_dates.append(int(np.frombuffer(f.read(4),dtype='<u4')[0]))
    counts=Counter(last_dates)
    qualified=[d for d,n in counts.items() if n>=len(current)*.5]
    if resolved_cutoff_date is None:
        cutoff=max(qualified) if qualified else counts.most_common(1)[0][0]
        if not qualified: raise ValueError('LATEST_DATE_COVERAGE_FAILURE')
    else:
        # Production precheck is the only cutoff authority.  Phase 1 may
        # validate the supplied date against local coverage, but must not
        # replace it with a date inferred independently from the source.
        cutoff=int(str(resolved_cutoff_date).replace('-',''))
        if counts.get(cutoff,0)<len(current)*.5: raise ValueError('RESOLVED_CUTOFF_COVERAGE_FAILURE')
        if any(d>cutoff for d in counts): raise ValueError('FUTURE_DATE_AFTER_RESOLVED_CUTOFF')
    calendar_path=Path(os.environ.get('TDX_RUN_CALENDAR',root/'reports/phase0_1/MASTER_TRADING_CALENDAR.csv'))
    cal=pd.read_csv(calendar_path)
    sessions=cal.loc[cal.is_market_open,'calendar_date'].to_numpy(dtype='int64')
    # Future daily extension uses local index DATES only, never index prices.
    if cutoff>sessions[-1] and resolved_cutoff_date is None:
        extra=set()
        for market,code in [('sh','000001'),('sz','399001')]:
            p=tdx/'vipdoc'/market/'lday'/f'{market}{code}.day'
            raw=p.read_bytes(); sources[str(p)]=hashlib.sha256(raw).hexdigest()
            ds=np.frombuffer(raw,dtype=DAY_DTYPE)['date']
            extra.update(int(d) for d in ds if sessions[-1]<d<=cutoff)
        if cutoff not in extra: raise ValueError('NEW_CALENDAR_DATE_UNCONFIRMED')
        sessions=np.concatenate([sessions,np.array(sorted(extra))])
    sessions=sessions[sessions<=cutoff]
    if int(sessions[-1])!=cutoff: raise ValueError('CUTOFF_NOT_IN_CALENDAR')
    future_limit=int(datetime.now().strftime('%Y%m%d'))
    if cutoff>future_limit: raise ValueError('FUTURE_CUTOFF')
    output=root/'reports/phase1'; output.mkdir(parents=True,exist_ok=True)
    cache=root/'data/.phase1_cache'; cache.mkdir(parents=True,exist_ok=True)
    pipeline_files=[root/'src/normalize/phase1.py',root/'src/factors/engine.py',root/'src/factors/registry.py',root/'src/adjustment/tdx_adjustment.py',root/'src/tdx/gbbq_reader.py']
    code_hashes={str(p.relative_to(root)):file_sha256(p) for p in pipeline_files}
    calendar_hash=hashlib.sha256(sessions.tobytes()).hexdigest()
    common=hashlib.sha256(encoded([sources,calendar_hash,code_hashes])).hexdigest()
    event_map=defaultdict(list)
    for record in read_gbbq(gbbq):
        if record.category==1: event_map[record.security_id].append(xrxd_from_gbbq(record))
    metadata=[]; latest=[]; contexts={}; reused=0
    generation=uuid.uuid4().hex
    normalized=root/'data/normalized/adjusted_daily.parquet'; normalized.parent.mkdir(parents=True,exist_ok=True)
    # Validate every existing canonical date before creating or replacing any
    # staged canonical output.  A future snapshot must leave canonical files
    # byte-for-byte untouched.
    factors=root/'data/factors/factors_daily.parquet'
    validate_canonical_dates_before_write(normalized,factors,cutoff)
    staged=normalized.with_name(f'.adjusted_daily.{generation}.tmp')
    writer=None
    for i,(sid,p) in enumerate(sorted(paths.items())):
        raw=p.read_bytes() if p else b''
        digest=hashlib.sha256(raw).hexdigest()
        if p: sources[str(p)]=digest
        if len(raw)%32: raise ValueError(f'INVALID_DAY_LENGTH:{sid}')
        key=hashlib.sha256(encoded([common,sid,digest,sid in current])).hexdigest()
        shard=cache/f'{sid}.parquet'; context_path=cache/f'{sid}.context.parquet'; meta=cache/f'{sid}.json'
        old=json.loads(meta.read_text('utf8')) if meta.exists() else {}
        if old.get('key')==key and shard.exists() and context_path.exists():
            if old.get('shard_sha256')!=file_sha256(shard) or old.get('context_sha256')!=file_sha256(context_path):
                raise ValueError('CACHE_INTEGRITY_FAILED')
            table=pq.read_table(shard); context=pq.read_table(context_path).to_pandas(); stats=old['stats']; reused+=1
        else:
            rows=np.frombuffer(raw,dtype=DAY_DTYPE)
            table,context,stats=normalize(sid,rows,sessions,event_map[sid],sid in current)
            write_parquet(shard,table,tdx)
            write_parquet(context_path,pa.Table.from_pandas(context,preserve_index=False),tdx)
            atomic(meta,encoded({'key':key,'stats':stats,'shard_sha256':file_sha256(shard),'context_sha256':file_sha256(context_path)}),tdx)
        if writer is None:
            writer=pq.ParquetWriter(staged,table.schema.with_metadata({b'generation':generation.encode(),b'cutoff_date':str(cutoff).encode(),b'contract':b'adjusted-daily-contract-v1'}),compression='zstd')
        writer.write_table(table)
        values,_=calculate(context,cutoff=cutoff)
        latest.append({'security_id':sid,'date':cutoff,'universe_status':'IN_NORMAL_UNIVERSE' if stats['normal'] else 'OUTSIDE_NORMAL_UNIVERSE',**values})
        metadata.append(stats)
        if sid in SAMPLES: contexts[sid]=context
        if (i+1)%250==0: print(f'Normalized {i+1}/{len(paths)}; cached={reused}',flush=True)
    writer.close()
    frame=add_rs(pd.DataFrame(latest))
    frame['price_basis']='TDX_NATIVE_QFQ'; frame['project_price_basis']='FORWARD_ADJUSTED'
    frame['adjustment_identity']='TDX_NATIVE_AFFINE_QFQ'
    frame['date']=pd.to_datetime(frame.date.astype(str),format='%Y%m%d').dt.date
    factors.parent.mkdir(parents=True,exist_ok=True)
    factor_staged=factors.with_name(f'.factors_daily.{generation}.tmp')
    # Preserve previously sealed daily snapshots, never synthesize historical membership.
    if factors.exists():
        prior=pq.read_table(factors).to_pandas()
        prior=prior[prior.date<frame.date.iloc[0]]
        if len(prior): frame=pd.concat([prior,frame],ignore_index=True)
    factor_table=pa.Table.from_pandas(frame,preserve_index=False).replace_schema_metadata({b'generation':generation.encode(),b'factor_contract':VERSION.encode()})
    pq.write_table(factor_table,factor_staged,compression='zstd')
    assert pq.ParquetFile(staged).metadata.num_rows==sum(m['aligned_rows'] for m in metadata)
    assert not frame.duplicated(['security_id','date']).any()
    after={p:file_sha256(Path(p)) for p in sources}
    unchanged=sources==after
    if not unchanged: raise ValueError('TDX_SOURCE_CHANGED_DURING_BUILD')
    if any(file_sha256(root/p)!=h for p,h in code_hashes.items()): raise ValueError('PIPELINE_CODE_CHANGED_DURING_BUILD')
    # Readback validates finite outputs and expected types before any publication.
    actual=pq.read_table(factor_staged).to_pandas()
    assert all(not np.isinf(actual[n].to_numpy(dtype=float)).any() for n in NAMES)
    assert actual[NAMES].equals(frame[NAMES])
    from phase1_qa import audit_outputs
    qa=audit_outputs(root,tdx,frame,contexts,cutoff,metadata)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/phase1'],cwd=root,capture_output=True,text=True)
    if tests.returncode: raise RuntimeError(tests.stdout+tests.stderr)
    for tmp in (staged,factor_staged):
        with tmp.open('r+b') as f: os.fsync(f.fileno())
    adjusted_hash=file_sha256(staged); factor_hash=file_sha256(factor_staged)
    normal=sum(m['normal'] for m in metadata)
    norm_audit={'cutoff_date':cutoff,'calendar_version':'master-trading-calendar-v0.1','calendar_hash':calendar_hash,
        'input_security_count':len(paths),'normal_universe_count':normal,'input_bar_count':sum(m['input_bar_count'] for m in metadata),
        'output_aligned_row_count':sum(m['aligned_rows'] for m in metadata),'qfq_status':'VERIFIED_REPRODUCIBLE_TDX_NATIVE',
        'qfq_null_count':sum(m['qfq_null_count'] for m in metadata),'qfq_null_semantics':'No raw/adjusted OHLC on non-actual rows; aligned values exist only for confirmed suspension',
        'off_master_calendar_count':sum(m.get('off_master_calendar_count',0) for m in metadata),
        'synthetic_fill_count':sum(m['synthetic'] for m in metadata),'confirmed_suspension_count':sum(m.get('confirmed_suspension',0) for m in metadata),
        'inferred_gap_count':sum(m.get('inferred_gap',0) for m in metadata),
        'missing_data_count':sum(m['missing'] for m in metadata),'nonpositive_qfq_row_count':sum(m['nonpositive'] for m in metadata),
        'adjusted_dataset_sha256':adjusted_hash,'source_sha256':sources,'source_unchanged':unchanged,
        'cached_security_count':reused,'security_anchors':[{'security_id':m['security_id'],'anchor':m['anchor']} for m in metadata]}
    checks={'dataset_valid':True,'calendar_used':True,'contract_complete':len(REGISTRY)==29,'samples_reproducible':qa['sample_pass'],
            'rs_validated':qa['rs_pass'],'source_unchanged':unchanged,'tests_pass':tests.returncode==0}
    status=phase1_gate(checks)
    if status=='BLOCKED': raise ValueError(str(checks))
    os.replace(staged,normalized); os.replace(factor_staged,factors)
    atomic(output/'NORMALIZATION_AUDIT.json',encoded(norm_audit),tdx)
    receipt={'phase':'PHASE1','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':status,'phase1_status':status,
        'cutoff_date':cutoff,'generation':generation,'project_price_basis':'FORWARD_ADJUSTED','adjustment_identity':'TDX_NATIVE_AFFINE_QFQ',
        'normal_universe_count':normal,'adjusted_dataset_status':'GENERATED','adjusted_dataset_rows':norm_audit['output_aligned_row_count'],
        'adjusted_dataset_sha256':adjusted_hash,'factor_contract_version':VERSION,'implemented_factor_count':29,'pending_factor_count':0,
        'factor_dataset_status':'GENERATED','factor_dataset_rows':len(frame),'factor_dataset_sha256':factor_hash,
        'nonpositive_qfq_rows':norm_audit['nonpositive_qfq_row_count'],'synthetic_fill_rows':norm_audit['synthetic_fill_count'],
        'rs_benchmark':'NORMAL_UNIVERSE_MEDIAN','index_ohlc_used':False,'tests_passed':int(tests.stdout.split(' passed')[0].split()[-1]),'tests_failed':0,
        'test_output':tests.stdout,'tdx_source_unchanged':unchanged,'network_requests':0,'release_checks':checks,
        'warnings':['Initial factor dataset contains latest cutoff only; no historical PIT membership inferred',
                    'High/low factors are NULL in windows containing synthetic suspension rows',
                    'Single-file daily publication may rewrite Parquet bytes; cache avoids unchanged-symbol adjustment work at unchanged cutoff'],
        'errors':[],'next_allowed_phase':'PHASE_2_MARKET_REGIME_AND_SYNTHETIC_SECTOR_FACTOR',
        'code_sha256':code_hashes,'source_manifest':'NORMALIZATION_AUDIT.json','cache_reused':reused}
    atomic(output/'PHASE1_FINAL_RECEIPT.json',encoded(receipt),tdx)
    report=f'''# Phase 1 Report

Status: {status}. Cutoff: {cutoff}. TDX_NATIVE_QFQ / FORWARD_ADJUSTED.

Normalized {norm_audit['input_bar_count']} actual bars for {len(paths)} A-share identities into {norm_audit['output_aligned_row_count']} calendar-aligned rows. Latest NORMAL_UNIVERSE={normal}. Synthetic suspension rows={norm_audit['synthetic_fill_count']}; raw OHLC/volume/amount are NULL on derived rows and untouched on actual rows. Nonpositive actual QFQ closes={norm_audit['nonpositive_qfq_row_count']}; these only null relevant ratio/log windows, not the entire security.

Implemented all 29 contracted fields, including baseline AMOUNT_RATIO20 and RETURN_CONCENTRATION_20. Pending factors=0. RS uses each horizon's valid same-date NORMAL_UNIVERSE median (threshold100), never index prices. Every factor emits valid count and quality flags. Distribution CSV includes latest normal counts/null ratios/quantiles; sample calculations independently reproduce five required securities.

The first factors_daily build intentionally publishes only {cutoff}, with CALCULATED and IN/OUTSIDE_NORMAL_UNIVERSE separated. Normalized historical QFQ uses the cutoff snapshot; it is not historical point-in-time information. Current membership is used only at output t. Daily snapshots can append; historical --date is prohibited. This prevents retrospective membership or future-event leakage into historical factor rows.

Tests: {receipt['tests_passed']} passed, 0 failed, targeted tests/phase1 only. No external requests, no scanner/sector score/regime/backtest. Consumed source SHA256 verified before/after. Sealed affine engine and decoder reused without modification.

Files: data/normalized/adjusted_daily.parquet; data/factors/factors_daily.parquet. Match both hashes to PHASE1_FINAL_RECEIPT.json before consuming a published pair. Writers stage, validate, fsync and atomically replace each file; receipt published last. Mixed-generation files must be rejected by consumers.

Incremental design: per-security normalized/context cache keyed by input hash, calendar cutoff, event source and code. Same-cutoff unchanged securities reuse it; new cutoff/gbbq change conservatively invalidates affected cache. Latest-date append optimization of historical shards remains a documented next optimization; current correctness-first full build is supported. No-change daily runs can reuse cached normalization. A single canonical Parquet entails rewriting its bytes during compaction.

NEXT_ALLOWED_PHASE=PHASE_2_MARKET_REGIME_AND_SYNTHETIC_SECTOR_FACTOR. This run does not start Phase2.
'''
    atomic(output/'PHASE1_RUN_REPORT.md',report.encode('utf8'),tdx)
    print(json.dumps(receipt,ensure_ascii=False,indent=2),flush=True)
    return receipt
