"""Production-shaped isolated batch promotion fixture; never real authority."""
import copy,json,os,tempfile
from pathlib import Path
from datetime import date,timedelta
from decimal import Decimal,ROUND_HALF_UP
from scripts.r20r1r2_io import ROOT,ref,exact,digest,require
from scripts.r20r1r2_forward_projection import persist

def put(root,path,value=None,raw=None):
    root=Path(root).resolve();p=(root/path).resolve()
    require(root!=ROOT.resolve() and (root.is_relative_to(Path(tempfile.gettempdir()).resolve()) or root.is_relative_to(ROOT/'reports/r20r1r2/engineering_fixtures')) and p.is_relative_to(root),'ISOLATED_FIXTURE_NAMESPACE_ONLY')
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_bytes(raw if raw is not None else (json.dumps(value,sort_keys=True,indent=2)+'\n').encode());os.replace(t,p);return ref(path,root)

def build(root,horizons=(1,3,5,10,20),revision=1,prior_accepted_revision=None):
    root=Path(root);reg=json.loads((ROOT/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes());head=exact(reg['accepted_head']);base=exact(reg['T0_data_archive']);freeze=exact(reg['freeze'])
    chain=exact(base['accepted_chain']);ctx=exact(chain['source_context']);gbbq=ctx['inputs']['2026-09-30']['inputs']['GBBQ'];disp_ref=ctx['inputs']['2026-09-30']['inputs']['GBBQ_DISPOSITIONS'];builder=json.loads((ROOT/'config/dm01_incremental_builders_contract_r3_3.json').read_bytes())
    refs=[reg[k] for k in ['accepted_head','owner_publication','enrollment','freeze','producer_receipt','T0_data_archive']]+[head['bindings']['runtime_seal'],head['bindings']['calendar'],base['component_artifacts']['ADJUSTED_DAILY'],base['component_permissions']['ADJUSTED_DAILY']['receipt'],gbbq,disp_ref,builder['gbbq_classification_binding']]
    for b in refs:put(root,b['path'],raw=(ROOT/b['path']).read_bytes())
    for path in ['data/v4/V4_STAGE_ACCEPTED_HEAD.json','config/v4_data_accepted_head_v2.json','config/v4_15_maturity_t0_lineage_r20r1r1_v2.json','config/v4_15_forward_projection_r20r1r2_v1.json','config/dm01_incremental_builders_contract_r3_3.json']:
        put(root,path,raw=(ROOT/path).read_bytes())
    native=copy.deepcopy(next(r for r in exact(base['component_artifacts']['ADJUSTED_DAILY'])['rows'] if r['security_id']==freeze['signal_id']))
    if revision>1:native['source_snapshot_id']='sha256-'+digest([native['source_snapshot_id'],revision])
    past=exact(base['calendar'])['session_dates'];future=[];day=date(2026,10,8)
    while len(future)<20:
        if day.weekday()<5:future.append(day.isoformat())
        day+=timedelta(days=1)
    calendar=put(root,'fixtures/calendar.json',dict(session_dates=past+future))
    # Exact original parent bindings remain immutable, without copying irrelevant large components.
    parent_head=reg['T0_data_archive'];parent_components=base['component_artifacts'];packets=[];previous_n=0
    producer=exact(reg['producer_receipt']);en=exact(reg['enrollment'])
    for n in sorted(horizons):
        parent=parent_head;nodes=[];context_inputs={}
        for j in range(previous_n+1,n+1):
            day=future[j-1];row=copy.deepcopy(native);row.update(trade_date=day)
            cents=lambda x:x.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            close=cents(Decimal(native['close'])*(Decimal(1)+Decimal(j)/100-Decimal(j%3)/200))
            row.update(close=str(close),open=str(close),high=str(cents(close*Decimal('1.02'))),low=str(cents(close*Decimal('.97'))))
            bar=dict(security_id=row['source_security_key'],source_security_key=row['source_security_key'],trade_date=int(day.replace('-','')),**{k:float(row[k]) for k in ['open','high','low','close']},volume=row['volume'],amount=row['amount'])
            delta=put(root,f'fixtures/r{revision}/durable/{day}/tdx_delta.json',dict(contract_id='TDX_PACKAGE_DELTA_V1',current_snapshot_id=native['source_snapshot_id'],future_rows_consumed=0,future_rows_discarded=0,target_date=day,target_bars=[bar],status='READY',revision_events=[],out_of_scope_files_excluded=0))
            row['source_digest']=delta['sha256']
            rawrow={k:v for k,v in row.items() if k not in ['price_basis','adjustment_readiness','adjustment_source_revision','qfq_mul','qfq_add','raw_daily_digest']}
            row['raw_daily_digest']=digest([rawrow])
            rawa=put(root,f'fixtures/r{revision}/durable/{day}/RAW_DAILY/artifact.json',dict(contract_id='DM01_RAW_DAILY_ARTIFACT_R3_3',trade_date=day,rows=[rawrow]))
            receipts={};artifacts={}
            for cap in base['component_artifacts']:
                payload=dict(contract_id='DM01_'+cap+'_ARTIFACT_R3_3',trade_date=day,rows=[row] if cap=='ADJUSTED_DAILY' else [rawrow] if cap=='RAW_DAILY' else [])
                if cap=='ADJUSTED_DAILY':payload['raw_daily_artifact_sha256']=rawa['sha256']
                a=put(root,f'fixtures/r{revision}/durable/{day}/{cap}/artifact.json',payload)
                template=copy.deepcopy(exact(base['component_permissions']['ADJUSTED_DAILY']['receipt']))
                template.update(component_id=cap,contract_id='DM01_'+cap+'_INCREMENT_R3_3',trade_date=day,target_trade_date=day,parent_data_head_digest=parent['sha256'],parent_component_bindings=parent_components,artifact_path=a['path'],artifact_sha256=a['sha256'],artifact_bytes=a['bytes'],row_count=len(payload['rows']),logical_digest=digest(payload['rows']),calendar_publication_id=calendar['sha256'],source_revision=digest([day,gbbq]),input_publication_ids=sorted({parent['sha256'],calendar['sha256'],base['identity']['sha256'],gbbq['sha256'],disp_ref['sha256'],delta['sha256']}),fixture_scope='ISOLATED_ENGINEERING_REACHABILITY_ONLY',status='FULL_PASS',unknown_reason_counts={})
                put(root,f'fixtures/r{revision}/durable/{day}/{cap}/receipt.json',template);receipts[cap]=template;artifacts[cap]=a
            manifest=put(root,f'fixtures/r{revision}/durable/{day}/parent_manifest.json',dict(parent_data_head_digest=parent['sha256'],components=parent_components))
            pc=put(root,f'fixtures/r{revision}/durable/{day}/parent_context.json',dict(binding=parent,components=parent_components,component_manifest_binding=manifest,kind='ACCEPTED_PARENT' if not nodes else 'CANDIDATE_PARENT',external_acceptance='PENDING'))
            marker=dict(contract_id='DM01_ATOMIC_CONTINUOUS_CANDIDATE_R3_3',target_trade_date=day,parent_data_head_digest=parent['sha256'],parent_context_binding=pc,components=receipts,calendar_binding=calendar,identity_binding=base['identity'],status='READY_FOR_EXTERNAL_REAUDIT',source_freeze_digest=digest([day,gbbq]),logical_digest=digest(receipts),accepted_anchor=parent_head,source_instance_digests={})
            candidate=put(root,f'fixtures/r{revision}/durable/{day}/PROMOTION_CANDIDATE.json',marker)
            nodes.append(dict(trade_date=day,parent=parent,candidate=candidate,components=receipts,source_instances={}))
            context_inputs[day]=dict(inputs=dict(GBBQ=gbbq,GBBQ_DISPOSITIONS=disp_ref,TDX_PACKAGE_DELTA=delta));parent=candidate;parent_components=artifacts
        context=put(root,f'fixtures/r{revision}/batch_{n}/context.json',dict(calendar=dict(binding=calendar),identity=dict(binding=base['identity']),inputs=context_inputs))
        authority_doc=put(root,f'fixtures/r{revision}/batch_{n}/engineering_authority.md',raw=b'ISOLATED_ENGINEERING_REACHABILITY_ONLY; NO_REAL_EXTERNAL_ACCEPTANCE\n')
        authority=dict(authority_kind='ISOLATED_ENGINEERING_REACHABILITY_ONLY',audited_head='ISOLATED_ENGINEERING_ONLY',document=authority_doc)
        record_body=copy.deepcopy(exact(base['external_acceptance_record']));record_body.update(accepted_through=day,candidate_bindings=[x['candidate'] for x in nodes],external_authority=authority,audited_head=authority['audited_head'],fixture_scope='ISOLATED_ENGINEERING_REACHABILITY_ONLY',evidence_bindings=[prior_accepted_revision] if prior_accepted_revision else [])
        record_body['accepted_scope'].update(anchor=base['accepted_trade_date'] if previous_n==0 else future[previous_n-1],sessions=[x['trade_date'] for x in nodes])
        record=put(root,f'fixtures/r{revision}/batch_{n}/acceptance.json',record_body)
        batch_contract=copy.deepcopy(builder);batch_contract['execution_context']=context
        builder_ref=put(root,f'fixtures/r{revision}/batch_{n}/builder_contract.json',batch_contract)
        chain_body=copy.deepcopy(chain);chain_body.update(anchor=dict(archive=parent_head,original_namespace=parent_head,trade_date=base['accepted_trade_date'] if previous_n==0 else future[previous_n-1]),nodes=nodes,accepted_through=day,external_acceptance_record=record,source_context=context,builder_contract=builder_ref,external_authority=authority,fixture_scope='ISOLATED_ENGINEERING_REACHABILITY_ONLY')
        chain_ref=put(root,f'fixtures/r{revision}/batch_{n}/accepted_chain.json',chain_body)
        h=copy.deepcopy(base);h.update(accepted_trade_date=day,calendar=calendar,parent_archive=parent_head,parent_head_sha256=parent_head['sha256'],accepted_chain=chain_ref,external_acceptance_record=record,final_candidate=parent,component_artifacts=artifacts,manifest_path=chain_ref['path'],manifest_sha256=chain_ref['sha256'],canonical_data_revision=marker['logical_digest'],source_revision=marker['source_freeze_digest'])
        for cap in artifacts:
            rr=receipts[cap];h['component_permissions'][cap].update(artifact=artifacts[cap],receipt=ref(f'fixtures/r{revision}/durable/{day}/{cap}/receipt.json',root),cutoff=day,status=rr['status'],logical_digest=rr['logical_digest'],row_count=rr['row_count'])
        put(root,'data/v4/V4_DATA_ACCEPTED_HEAD.json',h)
        projection=persist(reg['freeze'],day,root);value=exact(projection,root);rows=value['rows'];t=value['T0_transform_coefficients'];d=lambda x:Decimal(str(x));reference=d(t['alpha'])*d(freeze['comparison_reference'])+d(t['beta']);val=lambda r,k:d(r['transform_coefficients']['alpha'])*d(r[k])+d(r['transform_coefficients']['beta'])
        peak=reference;dd=Decimal(0)
        for r in rows:c=val(r,'close');peak=max(peak,c);dd=min(dd,c/peak-1)
        metrics=dict(R_N=float(val(rows[-1],'close')/reference-1),MFE_N=float(max([reference]+[val(r,'high') for r in rows])/reference-1),MAE_N=float(min([reference]+[val(r,'low') for r in rows])/reference-1),PATH_MDD_CLOSE_N=float(dd))
        outcome=put(root,f'fixtures/r{revision}/outcome_n{n}_r1.json',dict(frozen_t0=reg['freeze'],enrollment_id=en['enrollment_id'],horizon=n,due_date=day,outcome_status='OBSERVED',projection=projection,price_path=rows,evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',revision_sequence=1,supersedes=None,**metrics))
        endpoints=[r['source_adjusted_daily_artifact'] for r in rows];opened=day+'T16:30:00+00:00'
        log=put(root,f'fixtures/r{revision}/read_n{n}.json',dict(freeze=reg['freeze'],projection=projection,accepted_endpoints=endpoints,first_future_endpoint_open_at=opened,raw_provider_fallback=False))
        packet=dict(accepted_head=reg['accepted_head'],owner_publication=reg['owner_publication'],enrollment=reg['enrollment'],freeze=reg['freeze'],freeze_completed_at=producer['end'],first_future_endpoint_open_at=opened,endpoint_read_receipt=log,data_head=value['resolution']['source_data_head'],accepted_endpoints=endpoints,projection=projection,outcome=outcome,horizon=n,raw_provider_fallback=False,historical_prices_only=False,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED')
        packets.append(packet);parent_head=packet['data_head'];previous_n=n
    put(root,'fixtures/packets.json',packets);return packets
