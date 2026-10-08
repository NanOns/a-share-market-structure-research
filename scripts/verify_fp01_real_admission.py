"""Independent, direct-file oracle for existing real outputs; never calls admit().

This is local independent QA code, not an external independent acceptance audit.
"""
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from fp01_evidence import ROOT, OUT, ref, write


def checked(binding):
    path = (ROOT / binding['path']).resolve()
    assert path.is_relative_to(ROOT)
    raw = path.read_bytes()
    assert len(raw) == binding['bytes'] and hashlib.sha256(raw).hexdigest() == binding['sha256']
    return raw


def verify(request, policy):
    approved = json.loads(checked(policy))['independent_verifier']
    assert ref(__file__)['sha256'] == approved['sha256']
    checked(approved)
    meta = request['metadata']
    raw = {key:checked(request[key]) for key in ['input','output','code','contract']}
    data = json.loads(raw['input'])
    assert data['accepted_trade_date'] == meta['trading_date'] == '2026-09-30'
    assert data['external_acceptance'].startswith('EXTERNALLY_ACCEPTED')
    runtime = json.loads((ROOT / 'config/v4_production_runtime_authority_v1.json').read_bytes())
    current = json.loads(checked(runtime['read_authority']))
    assert current['anchors']['data_head']['sha256'] == request['input']['sha256']
    samples, counts = [], Counter()
    reason_gaps = Counter()
    feature = request['feature_id']
    if feature == 'V4_13_PROFILE_ADVANCED':
        owner = json.loads((ROOT / 'data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json').read_bytes())
        assert any(r['sha256'] == request['output']['sha256'] and r['path'] == request['output']['path'] for r in owner['artifact_refs'])
        assert any(r['sha256'] == request['code']['sha256'] and r['path'] == request['code']['path'] for r in owner['runtime_source_bindings'])
        assert owner['active_family_closure']['sha256'] == request['contract']['sha256']
        assert owner['contract_digest'] == meta['contract_version']
        assert owner['protected_head_bindings']['data/v4/V4_DATA_ACCEPTED_HEAD.json']['sha256'] == request['input']['sha256']
        assert owner['capabilities']['V4_13_PROFILE_ADVANCED_PROJECTION'] == 'ENGINEERING_ACCEPTED'
        count = 0
        with gzip.open(ROOT / request['output']['path'], 'rt', encoding='utf8') as stream:
            for line in stream:
                row = json.loads(line)
                assert row['trade_date'] == meta['trading_date'] and row['knowledge_lineage'] == meta['knowledge_lineage']
                assert datetime.fromisoformat(row['cutoff']) <= datetime.fromisoformat(meta['source_as_of'])
                assert row['security_id'] and isinstance(row['fields'], dict) and row['source_refs']
                count += 1
                for name, cell in row['fields'].items():
                    assert 'quality' in cell and 'value' in cell and cell.get('producer_contract_id')
                    counts[cell['quality']] += 1
                    # Preserve original unknown/degraded and legitimate known-null (no anchor).
                    # A known quality label whose value is UNKNOWN describes source quality.
                    if cell['quality'] == 'UNKNOWN':
                        assert cell.get('reason') or cell.get('producer_identity') or cell.get('source_identity')
                        if not cell.get('reason'):
                            reason_gaps[name] += 1
                if len(samples) < 3:
                    samples.append(dict(security_id=row['security_id'], trade_date=row['trade_date'],
                                        fields={k:{x:v.get(x) for x in ['value','quality','reason','producer_contract_id']} for k,v in row['fields'].items() if k in ['primary_industry','active_anchor_id','algorithmic_support_sector']}))
        assert count > 5000
        sample_count = count
        owner_ref = ref('data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json')
    elif feature == 'V4_11_STATE_EVENTS':
        assert current['sources']['events']['sha256'] == request['output']['sha256']
        rows = json.loads(gzip.decompress(raw['output']))
        assert len(rows) > 5000
        for row in rows:
            assert row['trade_date'] == meta['trading_date'] and row['entity_id'] and row['contract_id'] == 'STATE_EVENT_V1'
            assert row['event_quality'] in ('KNOWN','UNKNOWN','DEGRADED')
            assert row['knowledge_lineage'] == meta['knowledge_lineage']
            counts[row['event_quality']] += 1
        samples = [{k:r[k] for k in ['entity_id','trade_date','effective_event','event_quality','accepted','knowledge_lineage']} for r in rows[:3]]
        sample_count = len(rows)
        owner_ref = ref('data/v4/V4_11_ACCEPTED_HEAD.json')
    else:
        raise ValueError('FEATURE_NOT_IMPLEMENTED_IN_ORACLE')
    assert meta['evidence_origin'] == 'REAL_ACCEPTED_SOURCE'
    assert meta['input_digest'] == request['input']['sha256']
    assert meta['source_snapshot'] == request['input']['sha256']
    assert datetime.fromisoformat(meta['source_as_of']) <= datetime.fromisoformat(meta['published_at'])
    # The v1 pointer is still readable and is the retained service rollback baseline.
    assert runtime['activation_status'] == 'ACTIVE' and runtime['tdx_write_authorized'] is False
    receipt = dict(contract_id='V4_OPERATIONAL_INDEPENDENT_QA_V1', feature_id=feature, status='PASS',
        checked_by='FP01_DIRECT_FILE_ORACLE', verifier=json.loads(checked(policy))['independent_verifier'],
        policy=policy, metadata=meta, **{k:request[k] for k in ['input','output','code','contract']},
        owner=owner_ref, row_count=sample_count, field_quality_counts=dict(counts), samples=samples,
        original_reason_gaps=dict(reason_gaps),
        reason_gap_action='AUD-FP01-FIELD-REASON-GAPS; preserve UNKNOWN and source identity; FP02/03 explicit reason adapter required, no new KNOWN values.',
        checks={k:'PASS' for k in ['REAL_LINEAGE','SCHEMA','FIELD_QUALITY','NO_FUTURE','SOURCE_READBACK','ROLLBACK_COMPATIBLE']},
        evidence_limit='Real retained output and full schema/quality scan; not a fresh algorithm rerun, not historical AS_RECORDED, not maturity/profit evidence or external acceptance.')
    return receipt


if __name__ == '__main__':
    requests = json.loads((OUT / 'admission_requests.json').read_bytes())
    for request in requests['requests']:
        receipt = verify(request, requests['policy'])
        raw = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf8')
        immutable = OUT / ('QA_' + request['feature_id'] + '_' + hashlib.sha256(raw).hexdigest() + '.json')
        if immutable.exists():
            assert immutable.read_bytes() == raw
        else:
            write(immutable, raw)
        request['qa'] = ref(immutable)
        write(OUT / ('QA_' + request['feature_id'] + '.json'), receipt)
        print(request['feature_id'], receipt['row_count'], receipt['field_quality_counts'])
    write(OUT / 'admission_requests.json', requests)
