"""Read-only fixture inventory and actual baseline defect reproductions."""
import json
import psycopg
from scripts.full_chain_repair_io import write,PREFIX,ROOT
from workbench_analysis.fep_e5.metadata_binding import authority
from workbench_analysis.v4_15_settlement import price_path

def probe():
    a=authority();records={}
    for kind,port in [('fresh',55492),('upgrade',55493)]:
        try:
            with psycopg.connect(f'host=127.0.0.1 port={port} user=fep_e5_admin dbname=fep_e5b_{kind} connect_timeout=3') as pg:
                records[kind]=dict(contracts=pg.execute('select contract_id,family,version,digest,body from fep.contracts where contract_id in (select distinct core_signal_contract_id from fep.observations)').fetchall(),
                    observations=pg.execute('select distinct scope_id,split_part(signal_key,\':\',1),core_signal_contract_id from fep.observations').fetchall(),
                    scopes=pg.execute('select scope_id,signal_type from fep.scopes').fetchall())
        except psycopg.Error as error:records[kind]=dict(error=str(error))
    records['predicate_digest']=a['predicate_digest']
    write(PREFIX+'BASELINE_FEP_SIGNAL_READBACK.json',records)
    print(json.dumps(records,default=str,ensure_ascii=True)[:7000])

if __name__=='__main__':probe()
