"""FEP_DATASET_V1: full denominator and independent per-partition as-of selection."""
from collections import Counter
from .contracts import digest, instant


def select(revisions, cutoff):
    cutoff = instant(cutoff)
    visible = [r for r in revisions if all(instant(r[t]) <= cutoff for t in
               ('source_fact_available_at', 'label_revision_available_at'))]
    if not visible:
        return dict(eligibility='MISSING_LABEL', selected_label_revision=None,
                    selected_label_digest=None, selection_reason='NO_ASOF_REVISION')
    r = max(visible, key=lambda r: r['revision'])
    eligible = r['training_allowed'] and instant(r['label_training_mature_at']) <= cutoff
    return dict(eligibility='ELIGIBLE' if eligible else 'PENDING',
                selected_label_revision=r['revision'], selected_label_digest=r['target_digest'],
                selection_reason='LATEST_VISIBLE_TRAINABLE' if eligible else r.get('quality', 'NOT_MATURE'))


def assemble(observations, targets, folds, labels, snapshots, cutoff):
    observations = sorted(observations, key=lambda o: o['observation_id'])
    targets = sorted(targets, key=lambda t: t['target_id'])
    folds = sorted([dict(f, observation_ids=sorted(f['observation_ids'])) for f in folds],
                   key=lambda f: (f['fold_id'], f['partition_name']))
    if len({o['observation_id'] for o in observations}) != len(observations):
        raise ValueError('FEP_DUPLICATE_OBSERVATION')
    denominator = [dict(observation_id=o['observation_id'], target_id=t['target_id'],
                        scope_id=o['scope_id'], horizon=t['horizon'], status='EXPECTED')
                   for o in observations for t in targets if t['scope_id'] == o['scope_id']]
    selections, rows, seen = [], [], {}
    for f in sorted(folds, key=lambda f: (f['fold_id'], f['partition_name'])):
        if f['partition_name'] not in ('FIT', 'TUNE', 'CALIBRATION', 'OUTER_TEST'):
            raise ValueError('FEP_PARTITION_INVALID')
        if instant(f['fold_dataset_cutoff']) > min(instant(cutoff), instant(f['phase_started_at'])):
            raise ValueError('FEP_FOLD_CUTOFF_INVALID')
        for o in observations:
            if o['observation_id'] not in f['observation_ids']:
                continue
            group = ('observation', f['fold_id'], o['observation_id'])
            date = ('trade_date', f['fold_id'], o['trade_date'])
            episode = ('episode', f['fold_id'], o['scope_id'], o['entity_id'], o['episode_key'])
            for key in [group, date] + ([episode] if o['episode_key'] is not None else []):
                if key in seen and seen[key] != f['partition_name']:
                    raise ValueError('FEP_FOLD_PHASE_OVERLAP')
                seen[key] = f['partition_name']
            for t in targets:
                if t['scope_id'] != o['scope_id']:
                    continue
                s = dict(fold_id=f['fold_id'], partition_name=f['partition_name'],
                         observation_id=o['observation_id'], target_id=t['target_id'],
                         **select(labels.get((o['observation_id'], t['target_id']), []), f['fold_dataset_cutoff']))
                selections.append(s)
                if s['eligibility'] == 'ELIGIBLE':
                    snapshot = snapshots[o['observation_id']]
                    rows.append(dict(s, snapshot_id=snapshot['snapshot_id'], trade_date=o['trade_date']))
    # Date weights are frozen separately for each fold, partition and target population.
    for r in rows:
        population = [x for x in rows if (x['fold_id'], x['partition_name'], x['target_id']) ==
                      (r['fold_id'], r['partition_name'], r['target_id'])]
        counts = Counter(x['trade_date'] for x in population)
        r['weight'] = 1 / (len(counts) * counts[r['trade_date']])
    result = dict(denominator=denominator, folds=folds, selections=selections, rows=rows)
    result['digest'] = digest(result)
    return result
