"""Project a single E1-selected population without resolving any newer revision."""
from workbench_analysis.fep_e1.contracts import digest


def bind(e1, metadata, envelopes):
    if digest({k:v for k,v in e1.items() if k != 'digest'}) != e1['digest']:
        raise ValueError('E2_E1_DIGEST')
    fold, partition, target = (metadata[k] for k in ('fold_id','partition_name','target'))
    selections = [s for s in e1['selections'] if
                  (s['fold_id'],s['partition_name'],s['target_id']) == (fold,partition,target)]
    if not selections:
        raise ValueError('E2_E1_POPULATION_ABSENT')
    rows = {r['observation_id']:r for r in e1['rows'] if
            (r['fold_id'],r['partition_name'],r['target_id']) == (fold,partition,target)}
    expected = []
    for selected in selections:
        key = selected['observation_id']
        envelope = dict(envelopes[key])
        if envelope['observation_id'] != key:
            raise ValueError('E2_ENVELOPE_ID')
        eligible = selected['eligibility'] == 'ELIGIBLE'
        if eligible:
            if key not in rows or any(envelope[k] != selected[k] for k in
                                     ('selected_label_revision','selected_label_digest')):
                raise ValueError('E2_E1_SELECTED_LABEL')
            if digest(envelope['outcome']) != selected['selected_label_digest']:
                raise ValueError('E2_OUTCOME_DIGEST')
            if metadata['target_kind'] == 'CONTINUOUS':
                value=envelope['outcome']
                category='POS' if value > 0 else 'NEG' if value < 0 else 'ZERO'
                if envelope['support_class'] != category:
                    raise ValueError('E2_SUPPORT_CLASS')
            if envelope['trade_date'] != rows[key]['trade_date']:
                raise ValueError('E2_E1_DATE')
        elif 'outcome' in envelope:
            raise ValueError('E2_PENDING_HAS_OUTCOME')
        envelope['status'] = selected['eligibility']
        expected.append(envelope)
    result = dict(metadata, e1_dataset_digest=e1['digest'], e1_frozen_payload=e1,
                  selections=selections, denominator=expected,
                  rows=[r for r in expected if r['status'] == 'ELIGIBLE'])
    result['digest'] = digest(result)
    return result
