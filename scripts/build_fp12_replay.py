"""Freeze date-local corrected views; never grant missing first-availability proof."""
import gzip,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.build_fp05_market import verified
from workbench_service.current_v4_context import canonical,digest
from workbench_service.production_v4 import ProductionV4ResearchReader,frozen_current_reader

def main():
    reader=ProductionV4ResearchReader(ROOT);legacy,_=frozen_current_reader(ROOT);contract,_=legacy._contract();headref=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json');head=json.loads(verified(headref).read_bytes());chain=json.loads(verified(head['accepted_chain']).read_bytes());catalog=[]
    pointer=ROOT/'config/v4_replay_compare_authority_v1.json';existing=json.loads(pointer.read_bytes()) if pointer.exists() else {};frozen={r['as_of']:r for r in existing.get('catalog',[])}
    current=legacy._source(contract,'states');prior=json.load(gzip.open(verified(current['prior_binding']),'rt',encoding='utf8'));states={x['rows'][0]['trade_date']:{r['entity_id']:r for r in x['rows']} for x in (prior,current)}
    state_sources={current['rows'][0]['trade_date']:contract['sources']['states'],prior['rows'][0]['trade_date']:current['prior_binding']}
    for node in chain['nodes']:
        day=node['trade_date']
        if day>reader.context['trade_date']:continue
        if day in frozen:
            saved=json.loads(verified(frozen[day]['snapshot']).read_bytes())
            for kind in ('RAW_DAILY','ADJUSTED_DAILY','TRADING_STATUS','IDENTITY_UNIVERSE'):
                if saved['sources'][kind]['sha256']!=node['components'][kind]['artifact_sha256']:raise ValueError('HISTORICAL_DATE_REVISION_REQUIRES_EXPLICIT_PUBLICATION')
            catalog.append(frozen[day]);continue
        sources={};data={}
        for kind in ('RAW_DAILY','ADJUSTED_DAILY','TRADING_STATUS','IDENTITY_UNIVERSE'):
            c=node['components'][kind];sources[kind]=dict(path=c['artifact_path'],sha256=c['artifact_sha256']);data[kind]=json.loads(verified(sources[kind]).read_bytes())['rows']
        by={kind:{r['security_id']:r for r in rows} for kind,rows in data.items()};items=[]
        if day in state_sources:sources['states']=state_sources[day]
        for row in data['RAW_DAILY']:
            sid=row['security_id'];fields={k:dict(value=row.get(k),effective_date=day,known_at=None,publication_date=head['promoted_at_utc'],model_namespace='FP12_RECONSTRUCTED_CORRECTED_V1',source=sources['RAW_DAILY'],quality='KNOWN',unit='CNY' if k=='amount' else 'SHARES' if k=='volume' else 'CNY_PER_SHARE') for k in ('open','high','low','close','amount','volume')}
            s=states.get(day,{}).get(sid)
            if s:
                for k in ('maturity','health','validity','scenario','tracking'):
                    fields[k]=dict(value=s.get(k),effective_date=day,known_at=s.get('cutoff'),publication_date=s.get('cutoff'),model_namespace=s.get('model_contract_id'),source=sources['states'],quality='UNKNOWN' if s.get(k) in (None,'UNKNOWN') else 'KNOWN',unit='ENUM')
            status=by['TRADING_STATUS'].get(sid,{});items.append(dict(entity_id=sid,symbol=row['source_security_key'],fields=fields,trading_status=status.get('trading_status'),price_basis='RAW',AS_RECORDED=False))
        snapshot=dict(contract_id='FP12_DATE_FROZEN_RECONSTRUCTION_V1',as_of=day,items=items,sources=sources,model_namespace='FP12_RECONSTRUCTED_CORRECTED_V1',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,pit_status='PIT_NOT_AVAILABLE',reason='NO_FIRST_AVAILABLE_AT_T0_PROOF_SOURCE_ACCEPTED_AFTER_T0',sector_history='NO_DATED_PRIOR_MEMBERSHIP_STATE_PUBLICATION',first_available_proven=False)
        path=ROOT/'data/v4/fp12_replay'/day/digest(canonical(snapshot))/'snapshot.json';write(path,snapshot);catalog.append(dict(as_of=day,snapshot=ref(path),pit_status=snapshot['pit_status'],corrected_status='READY',stock_count=len(items),first_available_proven=False,known_at=None,publication_date=head['promoted_at_utc'],model_namespace=snapshot['model_namespace']))
    sources=dict(data_head=headref,chain=head['accepted_chain'],calendar=head['calendar'],series=reader.manifest['domain_features']['stocks']['series'],series_authority=ref('config/v4_stock_operational_authority_v1.json'),membership=reader.manifest['sources']['membership'],sector=reader.manifest['sources']['sector_operational'],market=reader.manifest['sources']['market_operational'],market_reference_factors=reader.manifest['sources']['stock_factors'])
    authority=dict(contract_id='FP12_REPLAY_COMPARE_AUTHORITY_V1',catalog=catalog,sources=sources,session_dates=json.loads(verified(head['calendar']).read_bytes())['session_dates'],trade_date=reader.context['trade_date'],input_data_head=headref,contract=ref('config/v4_replay_compare_contract_v1.json'))
    write(ROOT/'config/v4_replay_compare_authority_v1.json',authority);write(ROOT/'docs/evidence/fp12_20261008/REAL_SOURCE_CATALOG.json',authority);print(json.dumps(dict(dates=[x['as_of'] for x in catalog],strict_pit_dates=0,corrected_dates=len(catalog))))
if __name__=='__main__':main()
