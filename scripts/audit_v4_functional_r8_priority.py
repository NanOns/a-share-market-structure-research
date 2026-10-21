"""Independent arithmetic and 28766 readback for FA8-PRIORITY-07.

The input projection is the active candidate's normal read-only BFF projection;
this audit deliberately does not call research_priority_r1.build_priority.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


GOOD_QUALITY = {'KNOWN', 'OBSERVED', 'RECONSTRUCTED', 'PROXY_RECONSTRUCTED'}
ROTATION_ACTIVE = {'ROTATION_IN', 'ROTATION_ACCEPTED', 'ROTATION_EXPANDING', 'ROTATION_REACCELERATING'}
ROTATION_WEIGHT = {**{key: 4 for key in ROTATION_ACTIVE}, 'ROTATION_PULSE': 2}
MATURITY_WEIGHT = {'MATURE': 4, 'DEVELOPING': 3, 'EARLY': 1, 'NONE': 0}
HEALTH_WEIGHT = {'NONE': 2, 'WATCH': 1, 'WEAKENING': 0, 'DAMAGED': -3}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _number(row, field, day, *, positive=False, low=None, high=None, low_exclusive=False):
    fields = row.get('fields') or {}
    if field not in fields:
        return None, 'MISSING'
    cell = fields[field]
    if not isinstance(cell, dict):
        return None, 'INVALID_TYPE'
    value = cell.get('value')
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return None, 'INVALID_NUMERIC'
    if cell.get('quality') not in GOOD_QUALITY:
        return None, 'INVALID_QUALITY'
    if cell.get('as_of') not in (None, day) or row.get('trade_date') not in (None, day):
        return None, 'INVALID_DATE'
    if positive and value <= 0:
        return None, 'OUT_OF_RANGE'
    if ((low is not None and (value <= low if low_exclusive else value < low))
            or (high is not None and value > high)):
        return None, 'OUT_OF_RANGE'
    return float(value), None


def stock_reference(rows, day):
    ranked, excluded = [], []
    for row in rows:
        fields = row.get('fields') or {}
        raw_damage = fields.get('core_price_damage')
        damage = raw_damage.get('value') if isinstance(raw_damage, dict) else None
        invalid = []
        if not isinstance(raw_damage, dict) or raw_damage.get('quality') not in GOOD_QUALITY or not isinstance(damage, bool):
            invalid.append('core_price_damage')
        values = {}
        bounds = {
            'close': dict(positive=True), 'prior_low20': dict(positive=True),
            'rps20': dict(low=0, high=100), 'rps20_delta3': dict(low=-100, high=100),
            'ret5': dict(low=-1, low_exclusive=True), 'pos60': dict(low=0, high=1),
        }
        for name, rule in bounds.items():
            values[name], issue = _number(row, name, day, **rule)
            if issue and issue != 'MISSING':
                invalid.append(name)
        missing = [name for name in bounds if name not in fields]
        reason_codes = []
        close_basis=(fields.get('close') or {}).get('adjustment_basis')
        low_basis=(fields.get('prior_low20') or {}).get('adjustment_basis')
        if not close_basis or not low_basis or close_basis!=low_basis:
            invalid.append('price_coordinate:close,prior_low20')
        if invalid:
            reason_codes.append('INVALID_INPUT_' + ','.join(sorted(set(invalid))))
        if missing:
            reason_codes.append('MISSING_INPUT_' + ','.join(missing))
        if damage is True:
            reason_codes.append('STRUCTURE_DAMAGED')
        if values['rps20_delta3'] is not None and values['rps20_delta3'] <= 0:
            reason_codes.append('RELATIVE_STRENGTH_NOT_IMPROVING')
        if values['ret5'] is not None and values['ret5'] <= 0:
            reason_codes.append('FIVE_SESSION_RETURN_NOT_POSITIVE')
        if values['pos60'] is not None and values['pos60'] >= .95:
            reason_codes.append('EXTENDED_POSITION')
        if damage is not False or invalid or missing or reason_codes:
            primary = ('MISSING_INPUT' if missing else 'INVALID_INPUT' if invalid else
                'STRUCTURE_DAMAGED' if damage is True else
                'RELATIVE_STRENGTH_NOT_IMPROVING' if values['rps20_delta3'] is not None and values['rps20_delta3'] <= 0 else
                'FIVE_SESSION_RETURN_NOT_POSITIVE' if values['ret5'] is not None and values['ret5'] <= 0 else
                'EXTENDED_POSITION' if values['pos60'] is not None and values['pos60'] >= .95 else 'INVALID_INPUT')
            excluded.append(dict(entity_id=row['entity_id'], rank=None, score=None,
                unknown_inputs=missing, invalid_inputs=sorted(set(invalid)),
                exclusion_reason=primary, exclusion_reasons=reason_codes))
            continue
        distance = max(0.0, min(1.0, (values['close'] - values['prior_low20']) / values['prior_low20']))
        score = round(4 + min(4, values['rps20_delta3'] * 100)
            + min(2, values['ret5'] * 100) + max(0, 2 - distance * 10), 6)
        facts = dict(core_price_damage=damage, rps20=values['rps20'],
            rps20_delta3=values['rps20_delta3'], ret5=values['ret5'], pos60=values['pos60'],
            prior_low20=values['prior_low20'], distance_from_prior_low20=distance)
        ranked.append(dict(entity_id=row['entity_id'], rank=None, score=score,
            tie_break=(score, values['rps20_delta3'], values['ret5'], row['entity_id']), facts=facts))
    ranked.sort(key=lambda item: (-item['tie_break'][0], -item['tie_break'][1], -item['tie_break'][2], item['entity_id']))
    for index, row in enumerate(ranked, 1):
        row['rank'] = index
        row.pop('tie_break')
    return ranked, excluded


def sector_reference(rows):
    ranked, excluded = [], []
    for row in rows:
        fields = row.get('fields') or {}
        rotation_cell = fields.get('output_state') or {}
        rotation = rotation_cell.get('value') if isinstance(rotation_cell, dict) else None
        maturity_cell = fields.get('maturity') or {}
        health_cell = fields.get('health') or {}
        maturity = maturity_cell.get('value') if isinstance(maturity_cell, dict) else None
        health = health_cell.get('value') if isinstance(health_cell, dict) else None
        rs = {}
        invalid = []
        for name in ('sector_rs5', 'sector_rs20'):
            rs[name], issue = _number(row, name, row.get('trade_date'))
        unknown = []
        for name, value, cell in (('maturity', maturity, maturity_cell), ('health', health, health_cell),
                                  ('rotation', rotation, rotation_cell)):
            if value is None or value == 'UNKNOWN' or not isinstance(cell, dict) or cell.get('quality') not in GOOD_QUALITY:
                unknown.append(name)
        unknown += [name for name in ('sector_rs5', 'sector_rs20') if rs[name] is None]
        if invalid or unknown:
            excluded.append(dict(entity_id=row['entity_id'], rank=None, score=None,
                unknown_inputs=sorted(set(unknown))))
            continue
        score = (ROTATION_WEIGHT.get(rotation, 0) + MATURITY_WEIGHT.get(maturity, 0)
            + HEALTH_WEIGHT.get(health, -3) + int(rs['sector_rs5'] > 0) + int(rs['sector_rs20'] > 0))
        ranked.append(dict(entity_id=row['entity_id'], rank=None, score=score,
            tie_break=(score, rs['sector_rs5'], rs['sector_rs20'], row['entity_id'])))
    ranked.sort(key=lambda item: (-item['tie_break'][0], -item['tie_break'][1], -item['tie_break'][2], item['entity_id']))
    for index, row in enumerate(ranked, 1):
        row['rank'] = index
        row.pop('tie_break')
    return ranked, excluded


def get_json(base, path, query=None):
    url = base + path
    if query:
        url += '?' + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read())


def paged(base, path, query, total):
    rows = []
    for offset in range(0, total, 200):
        payload = get_json(base, path, {**query, 'offset': offset, 'limit': 200})
        if payload.get('status') not in ('READY', 'EMPTY_VALID'):
            raise RuntimeError(f'API_STATUS:{path}:{payload.get("status")}')
        rows.extend(payload.get('items') or [])
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate-root', required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--port', type=int, default=28766)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root, repo = Path(args.candidate_root), Path(args.repo)
    candidate = json.loads((root/'data/v4/dynamic_daily_owners/2026-10-14/727b8c2e04b1b84d190da7da1bdae5338c3b575f94ebac4ab4f8314e624c1157/SUCCESSOR_CANDIDATE.json').read_text(encoding='utf-8'))
    manifest = json.loads((root/'runtime/candidate_chain_20261020/CANDIDATE_METADATA_REBIND_R1.json').read_text(encoding='utf-8'))
    for line in (repo/'config/.env').read_text(encoding='utf-8').splitlines():
        item=line.strip()
        if not item or item.startswith('#') or '=' not in item: continue
        key,value=item.split('=',1); key=key.strip(); value=value.strip().strip('"').strip("'")
        if key in ('WORKBENCH_PG_DSN','V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN') and value:
            os.environ.setdefault(key,value)
    if not os.environ.get('V4_NATIVE_PG_DSN') and os.environ.get('WORKBENCH_PG_DSN'):
        os.environ['V4_NATIVE_PG_DSN']=os.environ['WORKBENCH_PG_DSN']
    if not os.environ.get('V4_NATIVE_PG_READER_DSN'):
        os.environ['V4_NATIVE_PG_READER_DSN']=os.environ.get('V4_NATIVE_PG_DSN','')
    sys.path[:0]=[str(repo/'src'),str(repo),str(root/'src'),str(root)]
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1, validate
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    from workbench_service.research_bff import ResearchBFF
    validate(root, candidate)
    reader=OperationalSuccessorReaderV1(root,candidate)
    bff=CoreProductBFFR1(copy.copy(reader),ResearchBFF(root))
    day=candidate['accepted_trade_date']; base=f'http://127.0.0.1:{args.port}'
    context=get_json(base,'/api/v4/context')
    if context.get('context_token') != reader.token or context.get('context',{}).get('trade_date') != day:
        raise RuntimeError('LIVE_CONTEXT_TOKEN_OR_T0_MISMATCH')
    token=reader.token
    phase=time.perf_counter(); stocks=bff.project('stocks',day); stock_project_seconds=time.perf_counter()-phase
    phase=time.perf_counter(); raw_sectors=bff.project('sectors',day); sector_project_seconds=time.perf_counter()-phase
    phase=time.perf_counter(); lifecycle=bff._candidate_lifecycle(); lifecycle_seconds=time.perf_counter()-phase
    sectors=bff._attach_candidate_lifecycle(raw_sectors,lifecycle)
    phase=time.perf_counter(); stock_expected,stock_excluded=stock_reference(stocks,day); stock_oracle_seconds=time.perf_counter()-phase
    phase=time.perf_counter(); sector_expected,sector_excluded=sector_reference(sectors); sector_oracle_seconds=time.perf_counter()-phase
    stock_query={'view':'candidate','context_token':token,'scope':'stocks'}
    phase=time.perf_counter()
    stock_first_cold=get_json(base,'/api/v4/radar/priority',{**stock_query,'offset':0,'limit':1})
    stock_cold_seconds=time.perf_counter()-phase
    phase=time.perf_counter()
    stock_first_hot=get_json(base,'/api/v4/radar/priority',{**stock_query,'offset':0,'limit':1})
    stock_hot_seconds=time.perf_counter()-phase
    phase=time.perf_counter()
    stock_live_ranked=paged(base,'/api/v4/radar/priority',stock_query,len(stock_expected))
    stock_ranked_read_seconds=time.perf_counter()-phase
    phase=time.perf_counter()
    stock_live_excluded=paged(base,'/api/v4/radar/priority',{**stock_query,'rankability':'NOT_RANKABLE'},len(stock_excluded))
    stock_excluded_read_seconds=time.perf_counter()-phase
    sector_query={'view':'candidate','context_token':token,'scope':'sectors'}
    phase=time.perf_counter()
    sector_live_ranked=paged(base,'/api/v4/radar/priority',sector_query,len(sector_expected))
    sector_ranked_read_seconds=time.perf_counter()-phase
    phase=time.perf_counter()
    sector_live_excluded=paged(base,'/api/v4/radar/priority',{**sector_query,'rankability':'NOT_RANKABLE'},len(sector_excluded))
    sector_excluded_read_seconds=time.perf_counter()-phase
    sector_context=get_json(base,'/api/v4/sectors',{'context_token':token,'trade_date':day,'offset':0,'limit':1})
    sector_count=sector_context.get('total')
    stocks_context=get_json(base,'/api/v4/stocks',{'context_token':token,'trade_date':day,'offset':0,'limit':1})
    stock_count=stocks_context.get('total')
    def compare(expected_ranked, actual_ranked, expected_excluded, actual_excluded, *, stock):
        differences=[]
        actual_by_id={row.get('entity_id'):row for row in actual_ranked}
        expected_ids={row.get('entity_id') for row in expected_ranked}
        for expected in expected_ranked:
            actual=actual_by_id.get(expected.get('entity_id'))
            if actual is None:
                differences.append(dict(entity_id=expected['entity_id'],kind='MISSING_RANKED_ENTITY'))
                continue
            fields=['entity_id','rank','score']
            if stock: fields += ['facts']
            if any(expected.get(k)!=actual.get(k) for k in fields):
                differences.append(dict(entity_id=expected['entity_id'],expected=expected,actual={k:actual.get(k) for k in fields}))
        for extra_id in sorted(set(actual_by_id)-expected_ids):
            differences.append(dict(entity_id=extra_id,kind='UNEXPECTED_RANKED_ENTITY'))
        actual_by_id={row.get('entity_id'):row for row in actual_excluded}
        expected_ids={row.get('entity_id') for row in expected_excluded}
        for expected in expected_excluded:
            actual=actual_by_id.get(expected.get('entity_id'))
            if actual is None:
                differences.append(dict(entity_id=expected['entity_id'],kind='MISSING_EXCLUDED_ENTITY'))
                continue
            fields=['entity_id','unknown_inputs']
            if stock: fields += ['invalid_inputs','exclusion_reason','exclusion_reasons']
            if any((sorted(expected.get(k) or [])!=sorted(actual.get(k) or [])
                    if k in ('unknown_inputs','invalid_inputs') else expected.get(k)!=actual.get(k))
                   for k in fields):
                differences.append(dict(entity_id=expected['entity_id'],expected=expected,actual={k:actual.get(k) for k in fields}))
        for extra_id in sorted(set(actual_by_id)-expected_ids):
            differences.append(dict(entity_id=extra_id,kind='UNEXPECTED_EXCLUDED_ENTITY'))
        if len(expected_ranked)!=len(actual_ranked) or len(expected_excluded)!=len(actual_excluded):
            differences.append(dict(kind='COUNT_MISMATCH',expected=[len(expected_ranked),len(expected_excluded)],actual=[len(actual_ranked),len(actual_excluded)]))
        return differences
    stock_diff=compare(stock_expected,stock_live_ranked,stock_excluded,stock_live_excluded,stock=True)
    sector_diff=compare(sector_expected,sector_live_ranked,sector_excluded,sector_live_excluded,stock=False)
    price_basis=Counter()
    for row in stocks:
        fields=row.get('fields') or {}
        close=(fields.get('close') or {}).get('adjustment_basis')
        low=(fields.get('prior_low20') or {}).get('adjustment_basis')
        price_basis[f'{close or "MISSING"}|{low or "MISSING"}']+=1
    report={
        'contract_id':'V4-FUNCTIONAL-R8-REPAIR-20261021/R2',
        'task':'S03 independent numerical and real API readback',
        'candidate':{'T0':day,'token':token,'evidence_class':'NON_PIT','production_accepted':False,
            'candidate_digest':digest(candidate),'metadata_rebind_sha256':hashlib.sha256((root/'runtime/candidate_chain_20261020/CANDIDATE_METADATA_REBIND_R1.json').read_bytes()).hexdigest()},
        'API':{'base':base,'stock_total':stock_count,'sector_total':sector_count,
            'stock_rankable_pages':math.ceil(len(stock_expected)/200),'sector_rankable_pages':math.ceil(len(sector_expected)/200),
            'stock_cold_cache_diagnostics':stock_first_cold.get('cache_diagnostics'),
            'stock_hot_cache_diagnostics':stock_first_hot.get('cache_diagnostics'),
            'stock_payload_sha256_cold':stock_first_cold.get('candidate_payload_sha256'),
            'stock_payload_sha256_hot':stock_first_hot.get('candidate_payload_sha256'),
            'candidate_source_bindings':stock_first_hot.get('candidate_source_bindings')},
        'measured_hotspots_seconds':{'stock_project':stock_project_seconds,'sector_project':sector_project_seconds,
            'sector_lifecycle_build_or_cache':lifecycle_seconds,'stock_reference':stock_oracle_seconds,
            'sector_reference':sector_oracle_seconds,'priority_api_first_cold':stock_cold_seconds,
            'priority_api_first_hot':stock_hot_seconds,'priority_stock_rankable_pages':stock_ranked_read_seconds,
            'priority_stock_exclusion_pages':stock_excluded_read_seconds,
            'priority_sector_rankable_pages':sector_ranked_read_seconds,
            'priority_sector_exclusion_pages':sector_excluded_read_seconds},
        'denominators':{'stocks':{'total':len(stocks),'expected':5225,'rankable':len(stock_expected),'not_rankable':len(stock_excluded)},
            'sectors':{'total':len(sectors),'expected':400,'rankable':len(sector_expected),'not_rankable':len(sector_excluded),
                'maturity_unknown':sum(1 for r in sectors if (r.get('fields',{}).get('maturity') or {}).get('value') in (None,'UNKNOWN')),
                'health_unknown':sum(1 for r in sectors if (r.get('fields',{}).get('health') or {}).get('value') in (None,'UNKNOWN'))}},
        'stock_close_vs_prior_low_basis_counts':dict(sorted(price_basis.items())),
        'stock_exclusion_reasons':dict(Counter(x['exclusion_reason'] for x in stock_excluded)),
        'sector_unknown_inputs':dict(Counter(name for x in sector_excluded for name in x['unknown_inputs'])),
        'comparison':{'stock_differences':len(stock_diff),'sector_differences':len(sector_diff),
            'stock_digest':digest(stock_expected+stock_excluded),'sector_digest':digest(sector_expected+sector_excluded),
            'differences_sample':(stock_diff+sector_diff)[:25]},
        'per_object':{'stocks_rankable':stock_expected,'stocks_not_rankable':stock_excluded,
            'sectors_rankable':sector_expected,'sectors_not_rankable':sector_excluded},
        'acceptance':{'numeric':'PASS' if not stock_diff and not sector_diff else 'FAIL',
            'API_context':'PASS' if stock_count==5225 and sector_count==400 else 'FAIL',
            'cache_cold_hot_sha':'PASS' if stock_first_cold.get('candidate_payload_sha256')==stock_first_hot.get('candidate_payload_sha256') else 'FAIL',
            'NON_PIT_preserved':context.get('context',{}).get('PIT_ELIGIBLE') is False and context.get('production_accepted') is False},
    }
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(output.suffix+'.tmp')
    temporary.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(output)
    print(json.dumps({k:v for k,v in report.items() if k!='per_object'},ensure_ascii=False,sort_keys=True,indent=2))


if __name__=='__main__':
    main()
