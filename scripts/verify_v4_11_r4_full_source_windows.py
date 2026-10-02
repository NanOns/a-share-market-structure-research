"""Reopen every 129/130-slot source window without any tested adapter helper."""
from scripts.next_round_execution_r4 import *
from scripts.verify_v4_11_target_facts_r4a import source_windows
from scripts.verify_v4_11_r4_capability_closure import gz

def main():
    sealed=read('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json');reports=[]
    fields=['source_security_key','quality','mul','add','price_basis','adjustment_source_revision','has_actual_bar','raw_actual_bar','session_index','open','high','low','close','raw_open','raw_high','raw_low','raw_close','amount','volume']
    for day in ('2026-09-29','2026-09-30'):
        windows,_,sources,_=source_windows(day);calculations=gz(sealed['calculations'][day]);count=0
        for calc in calculations:
            expected=windows[calc['security_id']]
            if len(expected)!=len(calc['window']):raise ValueError('MASTER_WINDOW_SCOPE_MISMATCH')
            for source,slot in zip(expected,calc['window']):
                if source['date']!=slot['date'] or any(source.get(f)!=slot.get(f) for f in fields):raise ValueError('FULL_SOURCE_WINDOW_MISMATCH:'+calc['security_id']+':'+slot['date'])
                count+=1
        reports.append(dict(day=day,status='PASS',row_scope=len(calculations),source_slots=count,calculations=sealed['calculations'][day],source_bindings=sources,compared_fields=fields,independent_basis_gate='Nonmissing (price_basis, adjustment_source_revision) pair equality and accepted quality, no coefficient gate'))
        print(day,count,'PASS',flush=True)
        del windows,calculations
    write('reports/v4_11_r4/FULL_SOURCE_WINDOW_ORACLE.json',dict(status='PASS',dates=reports,adapter_helpers_invoked=False,accepted=False,permissions=PERMISSIONS))

if __name__=='__main__':main()
