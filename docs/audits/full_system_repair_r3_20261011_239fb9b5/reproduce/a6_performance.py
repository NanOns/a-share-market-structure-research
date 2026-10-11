from pathlib import Path
import sys,json,hashlib,time,threading,urllib.request,urllib.parse,concurrent.futures,os,platform
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import psutil
from http.server import ThreadingHTTPServer
from workbench_service.core_product_server_r1 import make_product_handler
token=hashlib.sha256((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()).hexdigest()
protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/v4').glob('*HEAD.json')}
base=make_product_handler(ROOT,None)
class ReadOnly(base):
    def do_POST(self):self.send(405,{'code':'AUDIT_GET_ONLY'})
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),ReadOnly);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
process=psutil.Process();memory=[];stop=threading.Event()
def monitor():
    while not stop.wait(.05):memory.append(process.memory_info().rss)
threading.Thread(target=monitor,daemon=True).start()
baseline={};records=[];waves=[]
def call(route,day,kind):
    q=urllib.parse.urlencode(dict(trade_date=day,context_token=token,limit=30))
    start=time.perf_counter()
    with urllib.request.urlopen(url+'/api/v4/'+route+'?'+q,timeout=120) as response:raw=response.read();status=response.status
    elapsed=time.perf_counter()-start;data=json.loads(raw)
    assert data['context_token']==token and data['context']['trade_date']==day
    digest=hashlib.sha256(raw).hexdigest();key=(route,day)
    if key in baseline:assert baseline[key]==digest,(key,baseline[key],digest)
    else:baseline[key]=digest
    return dict(route=route,day=day,seconds=elapsed,bytes=len(raw),status=status,capability=data.get('status'),sha256=digest,kind=kind)
try:
    days=('2026-10-09','2026-09-28');routes=('home','market','stocks','sectors','focus','forward')
    for day in days:
        for route in routes:records.append(call(route,day,'cold_or_first_route'))
    for workers in (1,4,8):
        jobs=[(routes[i%6],days[(i//6)%2]) for i in range(24)];start=time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:values=list(pool.map(lambda pair:call(*pair,'warm_concurrent'),jobs))
        elapsed=time.perf_counter()-start;latencies=sorted(v['seconds'] for v in values)
        records+=values;waves.append(dict(workers=workers,requests=len(values),wall_seconds=elapsed,throughput_rps=len(values)/elapsed,p50_seconds=latencies[(len(latencies)-1)//2],p95_seconds=latencies[int(.95*(len(latencies)-1))],maximum_seconds=max(latencies)))
    try:
        urllib.request.urlopen(urllib.request.Request(url+'/api/v4/operations/daily-update',data=b'{}'),timeout=10)
        raise AssertionError('POST was not denied')
    except urllib.error.HTTPError as error:assert error.code==405
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==value for p,value in protected.items())
    receipt=dict(contract_id='SAME_HEAD_PRODUCT_CAPACITY_MEASUREMENT_R3',head_token=token,port=server.server_port,hardware=dict(platform=platform.platform(),logical_cpu=os.cpu_count(),physical_ram_bytes=psutil.virtual_memory().total),memory=dict(peak_sampled_rss_bytes=max(memory),sampling_seconds=.05),cold_and_warm_records=records,waves=waves,read_write_isolation='GET-only audit server; POST405; all protected Heads unchanged; current global lock retained',numerical_same_route_date_byte_parity=True,governing_contract=dict(path='config/v4_performance_measurement_contract_v1.json',sha256=hashlib.sha256((ROOT/'config/v4_performance_measurement_contract_v1.json').read_bytes()).hexdigest()),threshold_status='NUMERIC_CAPACITY_THRESHOLD_NOT_REGISTERED_IN_APPLICABLE_CONTRACTS',acceptance='MEASURED_WITH_BYTE_PARITY; FA-004_OPEN_CAPACITY_AND_PAYLOAD_GATE',production_restart=False,next='Register justified workload/latency/payload thresholds, then consider snapshot-safe concurrency or payload changes without cross-date mutation')
    p=OUT/'A6_PERFORMANCE_READBACK.json';t=p.with_suffix('.tmp');t.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode());os.replace(t,p)
    print(json.dumps(dict(waves=waves,peak_ram_bytes=max(memory),acceptance=receipt['acceptance'])),flush=True)
finally:
    stop.set();server.shutdown();server.server_close()
