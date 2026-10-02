"""Sequential process boundaries, exact snapshot refs; never SessionLedger history."""
import argparse,json,subprocess,sys
from scripts.v4_11_promotion_contract_r1 import ROOT

DATES=['2026-09-23','2026-09-24','2026-09-28','2026-09-29','2026-09-30']
def run(phase):
    out='reports/v4_12_runtime_r11/'
    for scope,dates in [('synthetic',DATES),('real',['2026-09-29','2026-09-30'])]:
        previous=None
        for date in dates:
            revisions=['r1','r2','r3'] if scope=='synthetic' and date=='2026-09-29' else ['r1']
            next_prior=None
            for revision in revisions:
                directory=out+phase+('_closure_chain_' if phase=='b' else '_persisted_chain_')+scope+'/'+date+'/'+revision
                cmd=[sys.executable,'-m','scripts.run_v4_12_r11_day','--date',date,'--revision',revision,'--directory',directory]
                if scope=='synthetic':cmd+=['--fixture',out+'fixtures/'+('b/' if phase=='b' else '')+date+'.json']
                if previous:cmd+=['--prior',previous]
                subprocess.run(cmd,cwd=ROOT,check=True)
                if revision=='r1':next_prior=directory+'/snapshot_ref.json'
            previous=next_prior
    # Fresh process again, same revision must reproduce runtime and frozen bytes.
    directory=out+phase+('_closure_chain_synthetic/' if phase=='b' else '_persisted_chain_synthetic/')+'2026-09-30/r1'
    subprocess.run([sys.executable,'-m','scripts.run_v4_12_r11_day','--date','2026-09-30','--directory',directory,'--fixture',out+'fixtures/'+('b/' if phase=='b' else '')+'2026-09-30.json','--prior',out+phase+('_closure_chain_synthetic/' if phase=='b' else '_persisted_chain_synthetic/')+'2026-09-29/r1/snapshot_ref.json'],cwd=ROOT,check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['a','b'],required=True);run(p.parse_args().phase)
