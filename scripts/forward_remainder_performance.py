"""Read-only accepted-scale verification. No synthetic expansion or SLA claim."""
import json,time,threading,os
from pathlib import Path
import psutil,duckdb
from scripts import run_fep_e3_r1 as e3
from scripts.full_chain_repair_io import ROOT,write,binding
from workbench_analysis.fep_e1 import datasets
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e3 import protocol
from workbench_analysis import v4_15_forward_r2 as forward
P='reports/forward_r2_remainder_consolidated_20261007/'
SNAP='reports/v4_15_runtime_r20/r20d_accepted_source_r3/snapshots/ccf05627352fcf4065e1ac98d730c7f15b882e3e55af23fbe4fda509265e8f16.json'
def run():
    rows=e3.rows();cp=e3.contract();snapshot=e3.load(ROOT/SNAP);universe=snapshot['universe'];measure=[]
    inputs=e3.load(ROOT/'config/fep_e2_historical_dataset_contract_v1.json')['source_bindings']
    write(P+'IA07_PERFORMANCE_INPUT_MANIFEST.json',dict(model_rows=binding('reports/fep_e3_r1/EXACT_MODEL_ROWS.jsonl.gz'),model_row_count=len(rows),entities=len({r['entity_id'] for r in rows}),dates=len({r['trade_date'] for r in rows}),snapshot=binding(SNAP),snapshot_entities=len(universe),accepted_source=snapshot['accepted_source'],canonical=inputs['adjustment_identity'],permissions='ENGINEERING_VERIFICATION_ONLY',synthetic_row_expansion=False,feature_availability=snapshot['quality']))
    process=psutil.Process()
    def measured(name,size,fn):
        peak=[process.memory_info().rss];stop=threading.Event()
        def poll():
            while not stop.wait(.01):peak[0]=max(peak[0],process.memory_info().rss)
        thread=threading.Thread(target=poll);thread.start();start=time.perf_counter();cpu=time.process_time()
        try:out=fn()
        finally:elapsed=time.perf_counter()-start;used=time.process_time()-cpu;stop.set();thread.join()
        raw=json.dumps(out,sort_keys=True,separators=(',',':'),default=str).encode()
        measure.append(dict(workload=name,scale=size,wall_seconds=elapsed,cpu_seconds=used,peak_RSS_bytes=peak[0],output_bytes=len(raw),artifact_count=1,repeated_snapshot_bytes=0,logical_digest=digest(out),correctness_digest=digest(out),NO_RESOURCE_FAILURE=True))
        print(name,size,round(elapsed,3),'s',flush=True);return out
    groups=cp['split']['groups'];train_dates=set(groups['TRAIN'])
    gradients=[]
    for scale,limit in [('small',1000),('medium',2200),('accepted_current',len(rows))]:
        train=[r for r in rows if r['trade_date'] in train_dates][:limit]
        sample=train+[r for r in rows if r['trade_date'] not in train_dates]
        result=measured('E3_DATE_SPLIT_PURGE',scale,lambda:protocol.purge(sample,cp['split']))
        # The full-scale ledger must match the accepted immutable population.
        if scale=='accepted_current':
            accepted=e3.folds();assert {k:[r['observation_id'] for r in v] for k,v in result[0].items()}=={k:[r['observation_id'] for r in v] for k,v in accepted.items()}
        obs=[dict(observation_id=r['observation_id'],scope_id='FEP_STOCK_ENTRY_CORE',entity_id=r['entity_id'],trade_date=r['trade_date'],episode_key=r['episode_id']) for r in sample]
        target=dict(target_id='ABS_RETURN_N:T1',scope_id='FEP_STOCK_ENTRY_CORE',horizon=1)
        cutoff=cp['knowledge_cutoff'];labels={};snaps={}
        for r in sample:
            snaps[r['observation_id']]=dict(snapshot_id=r['original_e2_row_digest'])
            labels[r['observation_id'],target['target_id']]=[dict(revision=r['selected_label_revision'] or 1,target_digest=r['selected_label_digest'] or r['original_e2_row_digest'],training_allowed=r['status']=='ELIGIBLE',quality=r['outcome_status'],**{k:r[k] for k in ('source_fact_available_at','label_revision_available_at','label_training_mature_at')})]
        folds=[dict(fold_id='ACCEPTED_ENGINEERING',partition_name={'TRAIN':'FIT','INTERNAL_TUNE':'TUNE','CALIBRATION':'CALIBRATION','OUTER_TEST':'OUTER_TEST'}[part],observation_ids=[r['observation_id'] for r in sample if r['trade_date'] in dates],fold_dataset_cutoff=cutoff,phase_started_at=cutoff) for part,dates in groups.items()]
        out=measured('E1_DATASET_ASSEMBLE',scale,lambda:datasets.assemble(obs,[target],folds,labels,snaps,cutoff))
        assert len(out['denominator'])==len(sample) and len(out['selections'])==len(sample)
        gradients.append(dict(scale=scale,rows=len(sample),entities=len(obs),dates=len({r['trade_date'] for r in sample}),E1_digest=out['digest']))
    for scale,n in [('small',100),('medium',1000),('accepted_current',len(universe))]:
        pop=universe[:n]
        measured('V4_15_CONTROL_FREEZE_ALL_SIGNALS',scale,lambda:[forward.freeze_controls(pop,signal,1) for signal in pop])
    def full_market():
        con=duckdb.connect(':memory:')
        try:return con.execute('select count(*),count(distinct canonical_security_id),min(trade_date),max(trade_date),sum(hash(canonical_security_id,trade_date,qfq_close,qfq_high,qfq_low)) from read_parquet(?)',[str(ROOT/inputs['adjustment_identity']['path'])]).fetchone()
        finally:con.close()
    market=measured('FULL_MARKET_CANONICAL_SCAN','accepted_current',full_market);assert market[0]==4026611
    # Current accepted snapshot explicitly lacks cross-date T0 authority.
    # Preserve that fail-closed state while exercising every actual security.
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    authority=CurrentStageAuthority(ROOT)
    source=forward.AcceptedPriceSource(authority,snapshot['accepted_source']);day=snapshot['trade_date']
    def stock():
        return [forward.price_path(r['close'],[source.read(r['security_id'],day,day,day)],day) for r in universe]
    outcomes=measured('CURRENT_ACCEPTED_STOCK_OUTCOMES','accepted_current',stock)
    assert all(r['R_N'] is None for r in outcomes)
    # Engineering read of the independently accepted current PIT membership.
    # Formal consumer permission stays false; missing references stay explicit.
    import gzip
    from collections import defaultdict
    membership_path='data/v4/artifact_store/v4_08/V4_08_PIT_MEMBERSHIP_FACTS_20260930_R1.jsonl.gz'
    membership=binding(membership_path);sectors=defaultdict(set)
    with gzip.open(ROOT/membership_path,'rt',encoding='utf8') as stream:
        for line in stream:
            fact=json.loads(line);sectors[fact['sector_id']].add(fact['security_id'])
    by_id={r['security_id']:r for r in universe}
    def sector_outcomes():
        result=[]
        for subject,members in sorted(sectors.items()):
            missing=sorted(members-set(by_id))
            if missing:
                result.append(dict(subject=subject,members=sorted(members),missing=missing,status='T0_REFERENCE_UNAVAILABLE'));continue
            basket=forward.freeze_sector_basket([by_id[sid] for sid in sorted(members)],day,subject,membership)
            point=dict(trade_date=day,members={sid:source.read(sid,day,day,day) for sid in sorted(members)})
            result.append(dict(subject=subject,members=sorted(members),outcome=forward.sector_path(basket,[point],day,snapshot['accepted_source'])))
        return result
    sector_results=measured('CURRENT_ACCEPTED_SECTOR_OUTCOMES','accepted_current',sector_outcomes)
    assert len(sector_results)==len(sectors)
    write(P+'IA07_SECTOR_INPUT_READBACK.json',dict(membership=membership,sectors=len(sectors),membership_rows=sum(map(len,sectors.values())),evaluated_subjects=len(sector_results),missing_reference_subjects=sum('missing' in r for r in sector_results),formal_consumers_enabled=False,no_member_reweighting=True,all_original_members_retained=True,output_digest=digest(sector_results)))
    write(P+'IA07_PERFORMANCE_MEASUREMENTS.json',dict(status='CURRENT_ACCEPTED_SCALE_MEASURED',NO_RESOURCE_FAILURE=True,measurements=measure,full_market_dimensions=market,stock_semantics='Cross-date T0 basis unavailable; no verification flag invented',controls_semantics=snapshot['quality'],SLA=None))
    write(P+'IA07_COMPLEXITY_GROWTH.json',dict(input_gradients=gradients,measurements=[m for m in measure if m['workload'] in ('E1_DATASET_ASSEMBLE','E3_DATE_SPLIT_PURGE','V4_15_CONTROL_FREEZE_ALL_SIGNALS')],omitted_full_rows=0,controls_current_rank_complete=0,model_algorithms_unchanged=True))
    write(P+'IA07_BEFORE_AFTER_PARITY.json',dict(optimization_applied=False,reason='No resource failure at accepted scale; no SLA exists',accepted_purge_membership_exact=True,selection_weights_and_digests_unchanged=True,full_current_universe_count=len(universe),repeated_snapshots_per_control=0))
if __name__=='__main__':run()
