"""Multi-anchor fresh-process E2E and real reconstructed wiring."""
import argparse,subprocess,sys
from scripts.v4_11_promotion_contract_r1 import ROOT
OUT='reports/v4_12_runtime_r12/'
def run():
    for scope,dates in [('synthetic',['2026-09-23','2026-09-24','2026-09-28','2026-09-29','2026-09-30']),('real',['2026-09-29','2026-09-30'])]:
        previous=None
        for date in dates:
            revisions=['r1','r2','r3'] if scope=='synthetic' and date=='2026-09-29' else ['r1']
            for revision in revisions:
                directory=OUT+'final_'+scope+'/'+date+'/'+revision
                command=[sys.executable,'-m','scripts.run_v4_12_r12_day','--date',date,'--revision',revision,'--directory',directory]
                if scope=='synthetic':command+=['--fixture',OUT+'fixtures/closure/'+date+'.json']
                if previous:command+=['--prior',previous]
                subprocess.run(command,cwd=ROOT,check=True)
            previous=OUT+'final_'+scope+'/'+date+'/r1/snapshot_ref.json'
if __name__=='__main__':run()
