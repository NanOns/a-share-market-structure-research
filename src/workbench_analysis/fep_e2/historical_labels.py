"""Historical source transport; all forward arithmetic belongs to V4-15."""
from pathlib import Path
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.v4_15_settlement import VectorPriceSource,SettlementRuntime
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from .historical_dataset import slots_for,read_gzip,write_gzip,LINEAGE,admissible,verify_label
from .historical_owners import RecordStore,frozen_authority


class HistoricalPriceSource(VectorPriceSource):
    evidence_class='ENGINEERING_HISTORICAL_REPLAY'
    def __init__(self,sid,slots,t0,binding,knowledge_at):
        self.sid=sid;self.slots={r['date']:r for r in slots};self.t0=t0
        self.binding=binding;self.knowledge_at=knowledge_at;self.read_log=[]
    def read(self,security_id,date,basis_date,cutoff):
        if security_id!=self.sid or date>cutoff:raise ValueError('E2_HISTORICAL_PRICE_SCOPE_OR_FUTURE')
        row=self.slots.get(date,{})
        source=self.slots[self.t0]
        common=(row.get('price_basis')==source.get('price_basis') and
            row.get('adjustment_source_revision')==source.get('adjustment_source_revision') and source.get('has_actual_bar') is True)
        result=dict(trade_date=date,evaluation_basis_date=basis_date,
            **{k:row.get(k) for k in ('close','high','low')},
            status='ACTUAL' if row.get('has_actual_bar') else row.get('accepted_trading_status','UNKNOWN'),
            verified_identity=row.get('identity_verified') is True,verified_adjustment=row.get('has_actual_bar') is True and common,
            T0_basis_verified=common,transform_coefficients=dict(alpha=1,beta=0),T0_transform_coefficients=dict(alpha=1,beta=0),
            adjustment_identity=row.get('adjustment_source_revision'),source_asof=date,available_at=self.knowledge_at,
            first_available_at_target_proven=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',
            source_row_digest=row.get('accepted_source_digest'),source_affine_coefficients=dict(mul=row.get('mul'),add=row.get('add')))
        self.read_log.append(dict(security_id=security_id,date=date,basis_date=basis_date,cutoff=cutoff,read_digest=digest(result)))
        return result


def label_worker(job):
    sid,raw,sessions,members,statuses,report,source_binding,knowledge_at=job
    report=Path(report);root=report.parents[1];store=RecordStore()
    for r in read_gzip(report/'owner_records'/(sid+'.jsonl.gz')):
        kind,key=r['record_id'].split(':',1)
        if digest(r['payload'])!=r['sha256']:raise ValueError('E2_OWNER_BUNDLE_DIGEST')
        store.append(kind,key,r['payload'])
    slots=slots_for(sid,raw,sessions,set(members),statuses)
    authority=frozen_authority(root);runtime=SettlementRuntime(authority,store);outputs=[]
    for row in read_gzip(report/'population'/(sid+'.jsonl.gz')):
        admissible(row);date=row['trade_date'];slot=slots[row['date_ordinal']]
        snapshot=dict(trade_date=date,source_asof=date,available_at=knowledge_at,evidence_class='RECONSTRUCTED_ASOF',
            universe=[dict(security_id=sid,close=slot['close'],research_eligible=None,hard_safety=None,
                adjustment_identity=slot['adjustment_source_revision'])],benchmark_control_status='UNAVAILABLE_NOT_ADMITTED')
        snapref=store.append('t0_snapshots',row['observation_id'],snapshot)
        frozen=runtime.freeze_t0(row['enrollment_ref'],snapref,event_count=0)
        source=HistoricalPriceSource(sid,slots,date,source_binding,knowledge_at)
        outcome_ref=runtime.settle(frozen,source,sessions[-1],horizons=(1,))[0]
        outcome=store.read(outcome_ref)
        eligible=outcome['outcome_status']=='OBSERVED' and outcome.get('path_quality')=='OBSERVED' and outcome['R_N'] is not None
        result=dict(row,outcome_status=outcome['outcome_status'],outcome_ref=outcome_ref,
            outcome_revision_id=outcome['outcome_revision_id'],source_fact_available_at=knowledge_at,
            label_revision_available_at=knowledge_at,label_training_mature_at=knowledge_at,
            training_allowed_engineering_only=eligible,real_training_allowed=False,
            selected_label_revision=outcome['revision_sequence'],selected_label_digest=digest(outcome['R_N']),
            source_read_log_digest=digest(source.read_log),path_quality=outcome.get('path_quality'),
            three_time_semantics='Actual historical engineering reconstruction receipt; NOT historical first availability')
        if eligible:result.update(outcome=outcome['R_N'],support_class='POS' if outcome['R_N']>0 else 'NEG' if outcome['R_N']<0 else 'ZERO')
        else:result['support_class']='NOT_EVALUABLE'
        verify_label(result,outcome);outputs.append(result)
    sha=write_gzip(report/'labels'/(sid+'.jsonl.gz'),outputs)
    bundle_sha=write_gzip(report/'settlement_records'/(sid+'.jsonl.gz'),store.rows())
    return dict(entity_id=sid,rows=len(outputs),eligible=sum(r['training_allowed_engineering_only'] for r in outputs),
        label_sha256=sha,settlement_bundle_sha256=bundle_sha)
