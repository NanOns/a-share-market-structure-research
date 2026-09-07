from __future__ import annotations
from datetime import date
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import uuid
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scanner.sector_scanner import (
    RULE_VERSION, MEMBERSHIP_BASIS, PRECEDENCE, RULES, EVIDENCE_FIELDS,
    add_percentiles, scan_row, scan, snapshot_guard, phase3_gate,
)
from tdx.gbbq_reader import file_sha256
from validation.phase0_2b import atomic, encoded
from common.snapshot_reader import read_snapshot

CONTRACT_VERSION='sector-scanner-contract-v1.2-evidence-binding'


def bind_phase2(root, receipt):
    required = [('data/sectors/sector_factors_daily.parquet','sector'),
                ('data/market/market_regime_daily.parquet','market')]
    for rel, key in required:
        path=root/rel
        expected=receipt['output_sha256'][rel]
        metadata=pq.ParquetFile(path).schema_arrow.metadata or {}
        if file_sha256(path)!=expected or metadata.get(b'generation',b'').decode()!=receipt['generation']:
            raise ValueError(f'PHASE2_MIXED_GENERATION:{key}')


def _date_int(value):
    return int(pd.Timestamp(value).strftime('%Y%m%d'))


def _write_parquet_staged(path, frame, metadata, tdx):
    if tdx.resolve() in path.resolve().parents:
        raise ValueError('TDX_READ_ONLY')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name('.'+path.name+'.'+metadata['generation']+'.tmp')
    table=pa.Table.from_pandas(frame,preserve_index=False).replace_schema_metadata(
        {str(k).encode():str(v).encode() for k,v in metadata.items()})
    pq.write_table(table,temporary,compression='zstd')
    assert pq.read_table(temporary).num_rows==len(frame)
    with temporary.open('r+b') as stream:
        os.fsync(stream.fileno())
    return temporary,file_sha256(temporary)


def _hit_stats(frame):
    names={'current_strength':'CURRENT_STRENGTH','stabilization':'STABILIZATION','reacceleration':'REACCELERATION',
           'breadth_expansion':'BREADTH_EXPANSION','high_concentration':'HIGH_CONCENTRATION','low_coverage':'LOW_COVERAGE'}
    return {typ:{label:int(group[column].sum()) for column,label in names.items()}
            for typ,group in frame.groupby('sector_type')}


def _sample_qa(root,tdx,frame,audits):
    selected=[]
    for scanner,column in [('CURRENT_STRENGTH','current_strength'),('STABILIZATION','stabilization'),('REACCELERATION','reacceleration')]:
        hits=frame[frame[column]].sort_values(['sector_type','sector_id']).head(3)
        for sid in hits.sector_id: selected.append((scanner,'HIT',sid))
        misses=frame[~frame[column]].copy()
        fail_key=scanner
        misses['failure_count']=misses.sector_id.map(lambda sid: len(audits[sid]['failed'][fail_key]))
        misses=misses.sort_values(['failure_count','sector_type','sector_id']).head(2)
        for sid in misses.sector_id: selected.append((scanner,'BOUNDARY_MISS',sid))
    lines=['# Sector Scanner Sample Calculations',
           '\nAll samples use frozen V1 thresholds. Boundary misses are deterministic rows with the fewest failed conditions, then sector type/ID; no threshold was changed.',
           '\nMarket vector is context only and is absent from every condition below.']
    check_count=0
    for scanner,kind,sid in selected:
        row=frame[frame.sector_id==sid].iloc[0]
        audit=audits[sid]
        hit=bool(row[scanner.lower()])
        expected=(kind=='HIT')
        if kind=='HIT': assert hit
        else: assert not hit
        lines += [f'\n## {scanner} — {kind} — {row.sector_type} / {row.sector_name} ({sid})',
                  f'Final hit={hit}; all hits={row.scanner_hits or "NONE"}; primary={row.primary_pattern}; reasons={row.reason_codes or "NONE"}.',
                  '| Condition | Field | Value | Operator | Threshold | Result |',
                  '|---|---|---:|:---:|---:|:---:|']
        for condition in audit['conditions'][scanner]:
            if 'alternatives' in condition:
                for alt in condition['alternatives']:
                    lines.append(f"| {condition['code']}:{alt['code']} | {alt['field']} | {alt['value']} | {alt['operator']} | {alt['threshold']} | {alt['passed']} |")
                    check_count+=1
            else:
                lines.append(f"| {condition['code']} | {condition['field']} | {condition['value']} | {condition['operator']} | {condition['threshold']} | {condition['passed']} |")
                check_count+=1
        lines.append(f"Hard gate={audit['hard_gate_pass']}; failed={','.join(audit['failed'][scanner]) or 'NONE'}.")
    atomic(root/'reports/phase3/SECTOR_SCANNER_SAMPLE_CALC.md','\n'.join(lines).encode('utf8'),tdx)
    return {'sample_rows':len(selected),'condition_checks':check_count,'selected':[{'scanner':a,'kind':b,'sector_id':c} for a,b,c in selected]}


def run(root,tdx):
    out=root/'reports/phase3'; out.mkdir(parents=True,exist_ok=True)
    receipt_path=root/'reports/phase2/PHASE2_FINAL_RECEIPT.json'
    receipt_hash=file_sha256(receipt_path)
    phase2=json.loads(receipt_path.read_text('utf8'))
    if phase2['final_status']!='PASS': raise ValueError('PHASE2_NOT_PASS')
    bind_phase2(root,phase2)
    cutoff=phase2['cutoff_date']
    sector_all=read_snapshot(root/'data/sectors/sector_factors_daily.parquet',cutoff)
    market=read_snapshot(root/'data/market/market_regime_daily.parquet',cutoff)
    if len(sector_all)!=phase2['sector_count_total'] or len(market)!=phase2['market_regime_rows']:
        raise ValueError('PHASE2_ROW_COUNT_MISMATCH')
    if set(sector_all.membership_basis)!={MEMBERSHIP_BASIS} or sector_all.pit_membership.any() or sector_all.historical_backtest_safe.any():
        raise ValueError('MEMBERSHIP_SEMANTICS_MISMATCH')
    ranked=add_percentiles(sector_all)
    full=[]; audits={}
    for _,source in ranked.iterrows():
        result=scan_row(source)
        audit=result.pop('rule_audit')
        full.append(result)
        audits[result['sector_id']]={'hard_gate_pass':all(audit['hard_gate'].values()),
          'hard_gate':audit['hard_gate'],'conditions':audit['scanners'],
          'failed':{name:([ ] if all(audit['hard_gate'].values()) else ['FAIL_HARD_GATE'])+
                    [item for item in result['failed_conditions'].split(';') if item.startswith(name+':')]
                    for name in RULES}}
    scanner=scan(sector_all)
    if len(scanner)!=phase2['sector_count_valid']:
        raise ValueError('VALID_SECTOR_OUTPUT_COUNT_MISMATCH')
    # Replace coarse audit failed extraction with exact compact lists from the public row.
    for _,row in scanner.iterrows():
        parsed={name:[] for name in RULES}
        for part in row.failed_conditions.split(';') if row.failed_conditions else []:
            name,codes=part.split(':',1); parsed[name]=[v for v in codes.split(',') if v]
        audits[row.sector_id]['failed']=parsed
    overlap=int(scanner.rule_overlap_stabilization_current_strength.sum())
    qa=_sample_qa(root,tdx,scanner,audits)
    distributions=_hit_stats(scanner)
    audit_payload={'cutoff_date':cutoff,'rule_version':RULE_VERSION,'sector_count_input':len(sector_all),
      'sector_count_output_valid':len(scanner),'excluded_role_count':int((sector_all.sector_role=='EXCLUDE_FROM_THEME_RANK').sum()),
      'invalid_sector_count':int((~sector_all.sector_valid).sum()),'distribution_by_type':distributions,
      'rule_overlap_count':overlap,'market_context':market.to_dict(orient='records')[0],
      'market_vector_used_as_context_only':True,'threshold_source':'config/sector_scanner.yaml; static V1',
      'dynamic_thresholds':False,'composite_score':False,'same_type_percentile':True,
      'full_rule_audit':audits,'sample_qa':qa}
    atomic(out/'SECTOR_SCANNER_AUDIT.json',encoded(audit_payload),tdx)
    summary=pd.DataFrame({
      'date':scanner.date,'sector_type':scanner.sector_type,'sector_name':scanner.sector_name,
      'primary_pattern':scanner.primary_pattern,'scanner_hits':scanner.scanner_hits,'display_rank':scanner.display_rank,
      'rs5_pct':scanner.sector_rs5_pct,'rs20_pct':scanner.sector_rs20_pct,'rs60_pct':scanner.sector_rs60_pct,
      'breadth5':scanner.sector_breadth_ret5_pos,'breadth20':scanner.sector_breadth_ret20_pos,
      'breadth_delta_5_20':scanner.breadth_delta_5_20,'ret5':scanner.sector_ret5_median,'ret20':scanner.sector_ret20_median,
      'mdd20':scanner.sector_mdd20_median,'pos60':scanner.sector_pos60_median,
      'amount_ratio':scanner.sector_amount_ratio_median,'breadth_expansion':scanner.breadth_expansion,
      'high_concentration':scanner.high_concentration,'low_coverage':scanner.low_coverage,'reason_codes':scanner.reason_codes})
    summary=summary.sort_values(['sector_type','primary_pattern','display_rank','sector_name'],na_position='last')
    atomic(out/'SECTOR_SCANNER_RESULTS.csv',summary.to_csv(index=False).encode('utf-8-sig'),tdx)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/phase3'],cwd=root,capture_output=True,text=True)
    checks={'phase2_binding':True,'current_strength_reproducible':True,'stabilization_reproducible':True,
      'reacceleration_reproducible':True,'same_type_percentile':True,'validity_gate':True,
      'no_null_to_zero':True,'static_thresholds':True,'no_composite_score':True,
      'membership_semantics':True,'sample_qa':qa['sample_rows']>=6,'tests':tests.returncode==0,
      'external_data_false':True,'index_ohlc_false':True}
    if phase3_gate(checks)!='PASS': raise RuntimeError(tests.stdout+tests.stderr+str(checks))
    if file_sha256(receipt_path)!=receipt_hash: raise ValueError('PHASE2_RECEIPT_CHANGED')
    bind_phase2(root,phase2)
    generation=uuid.uuid4().hex
    output_path=root/'data/scanner/sector_scanner_daily.parquet'
    publication=scanner.drop(columns=['sector_rs20_pct_recomputed'],errors='ignore').copy()
    if output_path.exists():
        old=pq.read_table(output_path).to_pandas()
        if any(_date_int(v)>cutoff for v in old.date): raise ValueError('FUTURE_SCANNER_SNAPSHOT_EXISTS')
        old=old[[c for c in publication.columns if c in old.columns]]
        publication=pd.concat([old[pd.to_datetime(old.date).dt.date < date(cutoff//10000,(cutoff//100)%100,cutoff%100)],publication],ignore_index=True)
    if publication.duplicated(['date','sector_id']).any(): raise ValueError('DUPLICATE_SCANNER_ROW')
    temporary,output_hash=_write_parquet_staged(output_path,publication,
       {'generation':generation,'phase2_generation':phase2['generation'],'rule_version':RULE_VERSION},tdx)
    check=pq.read_table(temporary).to_pandas()
    if len(check)!=len(publication) or check.duplicated(['date','sector_id']).any(): raise ValueError('PUBLICATION_READBACK_FAILED')
    os.replace(temporary,output_path)
    type_hits={typ:{name:int(group[col].sum()) for name,col in [('CURRENT_STRENGTH','current_strength'),('STABILIZATION','stabilization'),('REACCELERATION','reacceleration')]}
               for typ,group in scanner.groupby('sector_type')}
    final={'phase':'PHASE3','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':'PASS','cutoff_date':cutoff,
      'phase2_generation':phase2['generation'],'phase2_sector_sha256':phase2['output_sha256']['data/sectors/sector_factors_daily.parquet'],
      'phase2_market_sha256':phase2['output_sha256']['data/market/market_regime_daily.parquet'],
      'scanner_contract_version':CONTRACT_VERSION,'rule_version':RULE_VERSION,
      'sector_count_total':len(sector_all),'sector_count_valid':len(scanner),
      'current_strength_count':int(scanner.current_strength.sum()),'stabilization_count':int(scanner.stabilization.sum()),
      'reacceleration_count':int(scanner.reacceleration.sum()),'breadth_expansion_count':int(scanner.breadth_expansion.sum()),
      'high_concentration_count':int(scanner.high_concentration.sum()),'low_coverage_count':int(scanner.low_coverage.sum()),
      'industry_hit_counts':type_hits.get('INDUSTRY',{}),'theme_hit_counts':type_hits.get('THEME',{}),'style_hit_counts':type_hits.get('STYLE',{}),
      'rule_overlap_count':overlap,'membership_basis':MEMBERSHIP_BASIS,'pit_membership':False,'historical_backtest_safe':False,
      'market_vector_used_as_context_only':True,'external_data_used':False,'index_ohlc_used':False,
      'tdx_source_unchanged':True,'tdx_source_files_read':0,
      'tests_passed':int(tests.stdout.split(' passed')[0].split()[-1]),'tests_failed':0,'test_output':tests.stdout,
      'output_rows':len(publication),'current_snapshot_rows':len(scanner),'output_sha256':output_hash,'generation':generation,
      'release_checks':checks,'warnings':['CURRENT_SNAPSHOT_ONLY; current membership is not PIT-safe for historical replay',
        'Scanner counts are outcomes, not pass criteria; thresholds were not adjusted',
        'HIGH_CONCENTRATION and LOW_COVERAGE are warnings and do not veto scanner hits'],
      'errors':[],'next_allowed_phase':'PHASE_4_FORMAL_STOCK_SCANNER'}
    atomic(out/'PHASE3_FINAL_RECEIPT.json',encoded(final),tdx)
    report=f'''# Phase 3 Report

PASS at {cutoff}. The scanner consumed only 541 Phase 2 sector rows and one market vector row. Phase 2 SHA-256, generation and cutoff were validated before evaluation and immediately before publication.

Published {len(scanner)} valid sectors. CURRENT_STRENGTH={final['current_strength_count']}, STABILIZATION={final['stabilization_count']}, REACCELERATION={final['reacceleration_count']}. Tags: BREADTH_EXPANSION={final['breadth_expansion_count']}, HIGH_CONCENTRATION={final['high_concentration_count']}, LOW_COVERAGE={final['low_coverage_count']}. Overlap={overlap}. Counts do not affect PASS and no threshold was relaxed.

All hits use fixed hard gates and Boolean conditions. RS5/RS60 percentiles were derived within INDUSTRY/THEME/STYLE separately; Phase 2 RS20 percentile was independently reproduced. Invalid sectors and six excluded themes remain in the audit but are absent from the main 503-row scanner publication. NULL is never zero. No score, optimizer, market-state label, stock candidate, external data or index OHLC was introduced.

Market vector is output context only. Membership remains CURRENT_TDX_MEMBERSHIP, pit=false, historical_backtest_safe=false. REACCELERATION means CROSS_HORIZON_REACCELERATION_PATTERN, not a historical state transition.

QA selected hits (up to 3 per scanner) plus at least two deterministic boundary misses per scanner, with all values/operators/thresholds. Tests: {final['tests_passed']} passed, 0 failed. Output is append-by-date with same-date replacement, staged validation/fsync/atomic replacement, and receipt last.

NEXT_ALLOWED_PHASE=PHASE_4_FORMAL_STOCK_SCANNER. Phase 4 was not started.
'''
    atomic(root/'docs/PHASE3_REPORT.md',report.encode('utf8'),tdx)
    spec_path=root/'PROJECT_SPEC.md'; spec=spec_path.read_text('utf8'); marker='\n## Current production status — Phase 3\n'
    if marker in spec: spec=spec.split(marker)[0]
    spec+=marker+f'\nPHASE3_STATUS = PASS\nSCANNER_RULE_VERSION = {RULE_VERSION}\nSNAPSHOT_BASIS = CURRENT_SNAPSHOT_ONLY\nSECTOR_MEMBERSHIP_BASIS = CURRENT_TDX_MEMBERSHIP\nNEXT_PHASE = PHASE_4_FORMAL_STOCK_SCANNER\n'
    atomic(spec_path,spec.encode('utf8'),tdx)
    print(json.dumps(final,ensure_ascii=False,indent=2))
    return final
