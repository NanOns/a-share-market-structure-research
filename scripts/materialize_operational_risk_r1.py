"""Materialize current accepted risk facts into an additive immutable PG Owner."""
import hashlib,json,os,psutil,sys
from pathlib import Path
ROOT=Path(r'G:\codex work\v4-production-20261012');SOURCE=Path(__file__).resolve().parents[1]
def live_env():
    for process in psutil.process_iter(['pid','name','cmdline']):
        try:
            argv=process.info.get('cmdline') or []
            if (process.info.get('name') or '').lower()=='daav4.exe' and '--port' in argv and argv[argv.index('--port')+1]=='28765':
                env=process.environ()
                for key in ('V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN'):
                    os.environ[key]=env[key]
                return process.info['pid']
        except (psutil.Error,ValueError,IndexError,KeyError):pass
    raise RuntimeError('LIVE_28765_CONTROLLED_PG_ENVIRONMENT_UNAVAILABLE')
def main():
    pid=live_env();head_path=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head_bytes=head_path.read_bytes();head=json.loads(head_bytes)
    sys.path[:0]=[str(SOURCE/'src'),str(SOURCE)]
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    from workbench_db.v4_operational_risk_pg_r1 import prepare,load,prepare_priority,load_priority
    from workbench_service.research_priority_r1 import build_priority
    class NoLegacy:
        def __getattr__(self,name):raise ValueError('RISK_MATERIALIZER_LEGACY_READ_FORBIDDEN:'+name)
    api=OperationalSuccessorReaderV1(ROOT,head);bff=CoreProductBFFR1(api,NoLegacy());day=head['accepted_trade_date']
    bff.building_read_index=True
    code,payload=bff.get('/api/v4/home',{'trade_date':day,'context_token':api.token})
    if code!=200 or payload.get('status')!='READY':raise ValueError('RISK_MATERIALIZER_HOME_NOT_READY')
    families=payload.get('risk_families',{})
    material=dict(contract_id='V4_OPERATIONAL_RISK_CHANGE_R1',T0=day,context_token=api.token,
        families=families,focus_risk_scope=payload.get('focus_risk_scope'),
        source_bindings={name:head['owners'][day].get(domain) for name,domain in
            (('stock','core'),('sector','sector'),('market','market'))},
        denominator_policy='Accepted stock and sector Owner domains; market axes are one dated fact bundle; never Focus count',
        AS_RECORDED=False,PIT_ELIGIBLE=False,probability_claims=False,trading=False)
    binding,readback=prepare(ROOT,api.token,day,material)
    loaded_binding,loaded=load(ROOT,api.token,day)
    if loaded!=material or loaded_binding!=binding:raise ValueError('RISK_MATERIALIZER_POSTCOMMIT_READBACK_MISMATCH')
    parameter_bytes=(SOURCE/'config/v4_daily_research_priority_r1.json').read_bytes()
    parameter_digest=hashlib.sha256(parameter_bytes).hexdigest()
    priority=build_priority(day,api.token,bff.project('stocks',day),bff.project('sectors',day),
        payload.get('market'),head['owners'][day].get('core'),head['owners'][day].get('sector'),parameter_digest)
    priority['producer_sha256']=hashlib.sha256((SOURCE/'src/workbench_service/research_priority_r1.py').read_bytes()).hexdigest()
    priority_binding,priority_readback=prepare_priority(ROOT,api.token,day,priority)
    priority_loaded_binding,priority_loaded=load_priority(ROOT,api.token,day)
    if priority_loaded!=priority or priority_loaded_binding!=priority_binding:raise ValueError('RESEARCH_PRIORITY_POSTCOMMIT_READBACK_MISMATCH')
    if head_path.read_bytes()!=head_bytes:raise ValueError('RISK_MATERIALIZER_HEAD_MUTATION')
    result=dict(contract_id='V4_OPERATIONAL_RISK_PG_MATERIALIZATION_R1',acceptance='PASS_PG_READBACK',T0=day,
        context_token_sha256=hashlib.sha256(api.token.encode()).hexdigest(),head_sha256=hashlib.sha256(head_bytes).hexdigest(),
        production_service_pid_used_for_environment=pid,binding=binding,priority_binding=priority_binding,
        families={name:{'status':value.get('status'),'numerator':value.get('numerator'),'denominator':value.get('denominator'),
            'coverage':value.get('coverage'),'change_total':value.get('change_total')} for name,value in families.items()},
        priority={'contract_id':priority['contract_id'],'sectors':{'total':priority['sectors']['total'],'rankable':priority['sectors']['rankable'],'not_rankable':priority['sectors']['not_rankable']},
            'stocks':{'total':priority['stocks']['total'],'rankable':priority['stocks']['rankable'],'not_rankable':priority['stocks']['not_rankable']},
            'market_permission':priority['market_permission']},
        head_unchanged=True,auto_daily_changed=False,readback_digest=hashlib.sha256(json.dumps(loaded,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        priority_readback_digest=hashlib.sha256(json.dumps(priority_loaded,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest())
    out=SOURCE/'reports/audits/v4_r6_closeout_20261014/OPERATIONAL_RISK_PG_READBACK.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'acceptance':result['acceptance'],'binding':binding,'families':result['families']},ensure_ascii=False))
if __name__=='__main__':main()
