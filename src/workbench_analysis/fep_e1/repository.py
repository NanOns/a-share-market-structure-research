"""FEP_E1_DATASET_WRITER_V1: one FEP-only transaction, no Core writes."""
from psycopg.types.json import Jsonb
from .contracts import digest


def persist_dataset(pg, dataset_id, scope_id, feature_contract_id, policy_contract_id,
                    dataset_cutoff, created_at, assembled):
    semantic = {k: assembled[k] for k in ('denominator', 'folds', 'selections', 'rows')}
    if digest(semantic) != assembled['digest']:
        raise ValueError('FEP_DATASET_DIGEST_MISMATCH')
    manifest = dict(semantic, expected_targets=[dict(observation_id=e['observation_id'],
                    target_id=e['target_id']) for e in assembled['denominator']],
                    dataset_content_digest=assembled['digest'])
    with pg.transaction():
        pg.execute('insert into fep.datasets values (%s,%s,%s,%s,%s,%s,%s,%s)',
                   (dataset_id,scope_id,feature_contract_id,policy_contract_id,dataset_cutoff,
                    Jsonb(manifest),assembled['digest'],created_at))
        for e in assembled['denominator']:
            pg.execute('insert into fep.dataset_eligibility_ledger values (%s,%s,%s,%s,%s,%s,%s)',
                       (dataset_id,e['observation_id'],e['scope_id'],e['target_id'],e['horizon'],e['status'],e.get('reason')))
        for f in assembled['folds']:
            pg.execute('insert into fep.dataset_fold_cutoffs values (%s,%s,%s,%s,%s,%s,%s)',
                       (dataset_id,f['fold_id'],f['partition_name'],f['fold_dataset_cutoff'],f['phase_started_at'],policy_contract_id,digest(f)))
        for s in assembled['selections']:
            pg.execute('insert into fep.dataset_fold_label_selection values (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                       (dataset_id,s['fold_id'],s['partition_name'],s['observation_id'],s['target_id'],s['selected_label_revision'],
                        s['selected_label_digest'],s['selection_reason'],s['eligibility']))
        for row in assembled['rows']:
            pg.execute('insert into fep.dataset_rows values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,null)',
                       (dataset_id,scope_id,feature_contract_id,row['observation_id'],row['snapshot_id'],row['target_id'],
                        row['selected_label_revision'],row['selected_label_digest'],row['weight'],row['partition_name'],row['fold_id']))
        pg.execute('set constraints all immediate')
    return dict(dataset_id=dataset_id,digest=assembled['digest'],denominator=len(assembled['denominator']),
                rows=len(assembled['rows']),training_started=False)
