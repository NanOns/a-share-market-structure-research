"""Final scoped verification and protected governance readback."""
import json,os,subprocess,sys
from pathlib import Path
from scripts.build_fep_e2_r1r1_history import ROOT,REPORT,binding,now
from workbench_analysis.fep_e1.contracts import atomic_json
from scripts import run_fep_e2_r1 as historical


def tests():
    historical.REPORT=REPORT;historical.BASE='6aaff0b4a2126dc2823496fb07b7929880b5d94a'
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'src')
    env['TEMP']=env['TMP']='E:/codex_tmp/test_temp'
    env['WORKBENCH_PG_DSN']=env['FEP_E1_TEST_DSN']='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh'
    command=[sys.executable,'-B','-m','pytest','tests/fep_e2','tests/fep','-q',
        '--basetemp=E:/codex_tmp/test_temp/e2-r1r1-targeted','--junitxml='+str(REPORT/'targeted.xml')]
    historical.execute(command,env,'targeted')
    prior=json.loads((ROOT/'reports/fep_e2_r1/SCOPED_REGRESSION_SUMMARY.json').read_bytes())
    command=[s for s in prior['command'] if not s.startswith(('--basetemp=','--junitxml='))]
    command[0]=sys.executable
    command+=['--basetemp=E:/codex_tmp/test_temp/e2-r1r1-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    historical.execute(command,env,'scoped',prior['failed_nodes'])


if __name__=='__main__':tests()
