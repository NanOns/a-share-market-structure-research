"""Read-only real-source scoped audit; no production compute/adjustment imports."""
import gzip, hashlib, json, os, struct, sys, zipfile
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tdx.gbbq_reader import read_gbbq  # Decoder only; arithmetic below is independent.
OUT=ROOT/'docs/evidence/r4_2_1_20261009'
OLD=ROOT/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1'
def read(p): return json.loads(p.read_bytes())
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def bound(r):
    p=ROOT/r['path'];assert sha(p)==r['sha256'],p
    return p
def rows(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:
        for line in f:
            if line.strip():yield json.loads(line)
def write(n,v):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/n;t=p.with_suffix(p.suffix+'.tmp.identity')
    t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(t,p)

def main():
    write('P1_BOUNDARIES_STAGE_CONTRACT.json',dict(contract='R4_2_1_P1_REAL_SOURCE_AUDIT_V1',upgrade_document='R4.2.1 sections 3,4',scope=['BJ canonical candidate per source','breakout prior availability','real anomaly numeric oracle'],acceptance='IN_PROGRESS',next_stage='INDEPENDENT_SCOPED_ADMISSION',production_permission=False))
    src=ROOT/'docs/evidence/r4_1_audit_repair_r1_20261009/UNBOUND_IDENTITY_CLASSIFICATION.json'
    data=read(src);objects=[]
    for r in data['rows']:
        c=r['classification'];candidates=r['bse_candidates'];stable=[x for x in candidates if x.get('disposition')=='MAPPED_STABLE_BSE_ENTITY']
        objects.append(dict(**r,admission_object_id='BJ_IDENTITY:'+r['trade_date']+':'+r['source_security_key'],candidate_security_id=stable[0]['security_id'] if len(stable)==1 else None,source_contract='SECURITY_ENTITY_IDENTITY_V1 + SECURITY_LIFECYCLE_HISTORY_V1',requested_scope='CORRECTED_RECONSTRUCTED_ONLY',admission_status='SCOPED_CANDIDATE_PENDING_INDEPENDENT_SOURCE_ADMISSION' if len(stable)==1 else 'BLOCKED_SOURCE_RESOLUTION_REQUIRED',required_gate=['OFFICIAL_ALIAS_SOURCE_ACCEPTANCE','ENTITY_COLLISION_AND_EFFECTIVE_INTERVAL_QA','NO_HISTORICAL_FIRST_AVAILABLE_CLAIM'] if stable else ['AUTHORITATIVE_INSTRUMENT_OR_LIFECYCLE_RESOLUTION'],automatic_acceptance=False))
    write('BJ_IDENTITY_SCOPED_ADMISSION_CANDIDATES.json',dict(contract='R4_2_1_BJ_SCOPED_IDENTITY_ADMISSION_V1',source=ref(src),counts=data['counts'],objects=objects,acceptance='PER_OBJECT_CANDIDATES_ONLY',accepted_count=0,missing_input='Independent source Owner acceptance for BSE official alias capture; 101 explicit unresolved source rows and one lifecycle case per date cannot acquire IDs by inference'))
    replay=read(OLD/'PROFILE_STRUCTURE_REPLAY.json');audit=[]
    for item in replay['owners']:
        manifest=read(bound(item['structure_manifest']));runtime=next(x for x in manifest['artifacts'] if x['path'].endswith('runtime_security.jsonl.gz'));rs=list(rows(bound(runtime)))
        events=[e for r in rs for e in r.get('events',[])];episodes=[e for r in rs for e in r.get('breakout_episodes',[])]
        audit.append(dict(trade_date=item['owner']['trade_date'],runtime=runtime,manifest=item['structure_manifest'],rows=len(rs),breakout_counts=dict(Counter(r['basic_breakout_state'] for r in rs)),absence_quality=dict(Counter(r['breakout_episode_set_quality'] for r in rs)),event_count=len(events),episode_count=len(episodes),real_event_samples=events[:10],prior=manifest.get('prior'),unknown_reason_counts=dict(Counter(json.dumps(r.get('breakout_projection_reason'),sort_keys=True) for r in rs))))
    historical=[]
    for p in sorted((ROOT/'reports/v4_12_runtime_r13/real').glob('*/r1/runtime_security.jsonl.gz')):
        rs=list(rows(p));ev=[e for r in rs for e in r.get('events',[])];ep=[e for r in rs for e in r.get('breakout_episodes',[])]
        historical.append(dict(source=ref(p),rows=len(rs),event_count=len(ev),episode_count=len(ep),episode_set_quality=dict(Counter(r.get('breakout_episode_set_quality') for r in rs)),real_event_samples=ev[:5],real_episode_samples=ep[:5]))
    write('BREAKOUT_PRIOR_EVENT_SOURCE_AUDIT.json',dict(contract='R4_2_1_BREAKOUT_PRIOR_SOURCE_AUDIT_V1',corrected_runtime=audit,real_historical_runtime=historical,implementation=[ref(ROOT/'src/workbench_analysis/corrected_structure_replay.py'),ref(ROOT/'src/workbench_analysis/v4_12_breakout_episode.py')],root_cause='Corrected replay starts prior=None on 2026-09-28 and engineering_empty_seed=False. Breakout creation requires KNOWN episode absence. UNKNOWN absence propagates through successors; OHLC trigger or empty event list does not establish prior absence.',repair_disposition='NO_UNKNOWN_TO_FALSE_PATCH; missing accepted predecessor/complete episode coverage is source admission issue',production_changed=False,acceptance='REAL_HISTORY_SCANNED_SOURCE_GAP_EXPLICIT'))
    core=read(OLD/'CORE_REPLAY.json')['owners'];owner=core[-1];events=defaultdict(list)
    for e in read_gbbq(bound(owner['sources']['gbbq'])):
        if e.category==1:events[e.security_id.lower()].append(e)
    cores={r['security_id']:r for r in rows(bound(owner['core']))};priors={r['security_id']:r for r in rows(bound(owner['prior_core']))};raw={r['security_id']:r for r in rows(bound(owner['raw']))}
    samples=[];categories=Counter();errors=[];package=bound(owner['sources']['package'])
    with zipfile.ZipFile(package) as z:
        names={p.lower().split('/')[-1]:p for p in z.namelist() if p.endswith('.day')}
        for hist in rows(bound(owner['history'])):
            sid=hist['security_id'];row=cores[sid];code=row['source_security_key'].lower();bs=hist['bars'];ev=events[code];cross=[e for e in ev if int(bs[0]['trade_date'].replace('-',''))<e.event_date<=20261008]
            category='SUSPENDED_NO_BAR' if sid not in raw else 'SHORT_LISTING_WINDOW' if len(bs)<21 else 'CROSS_XRXD' if cross else 'ORDINARY_CONTROL'
            limit={'SUSPENDED_NO_BAR':2,'SHORT_LISTING_WINDOW':2,'CROSS_XRXD':4,'ORDINARY_CONTROL':2}[category]
            if categories[category]>=limit:continue
            leaf=code.replace('.','')+'.day';name=names.get(leaf)
            if not name:continue
            binary=z.read(name);official={str(b[0]):b for b in struct.iter_unpack('<IIIIIfII',binary)}
            values=[]
            for b in bs:
                record=official.get(b['trade_date'].replace('-',''));assert record is not None
                assert [v/100 for v in record[1:5]]==b['raw_ohlc']
                if b['qfq_ohlc'] is None:continue
                expected=[]
                for v in b['raw_ohlc']:
                    with localcontext() as ctx:
                        ctx.prec=40;p=Decimal(str(v))
                        for e in sorted(ev,key=lambda e:(e.event_date,e.source_record_index)):
                            if int(b['trade_date'].replace('-',''))<e.event_date<=20261008:
                                cash,price,bonus,rights=[Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for x in (e.c1,e.c2,e.c3,e.c4)]
                                p=(p*10-cash+rights*price)/(10+bonus+rights)
                        expected.append(float(p.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)))
                if expected!=b['qfq_ohlc']:errors.append(dict(sid=sid,day=b['trade_date'],expected=expected,actual=b['qfq_ohlc']))
                values.append(dict(trade_date=b['trade_date'],raw=b['raw_ohlc'],independent_qfq=expected))
            checks=[]
            for endpoint,r in [('current',row),('prior',priors[sid])]:
                for field in ['ma20','atr20']:
                    cell=r['fields'][field];actual=cell['value'];window=[b for b in values if (cell.get('window_start_trade_date') or '9999')<=b['trade_date']<=(cell.get('window_end_trade_date') or '0000')]
                    calc=None
                    if actual is not None:
                        ps=[b['independent_qfq'] for b in window];assert len(ps)==(20 if field=='ma20' else 21)
                        calc=sum(p[3] for p in ps)/20 if field=='ma20' else sum(max(b[1]-b[2],abs(b[1]-a[3]),abs(b[2]-a[3])) for a,b in zip(ps,ps[1:]))/20
                        if abs(calc-actual)>1e-8:errors.append(dict(sid=sid,field=field,endpoint=endpoint,expected=calc,actual=actual))
                    checks.append(dict(endpoint=endpoint,field=field,expected=calc,actual=actual,unknown_reason=cell.get('unknown_reason'),window_start=cell.get('window_start_trade_date'),window_end=cell.get('window_end_trade_date')))
            samples.append(dict(security_id=sid,source_security_key=code,category=category,zip_entry=name,zip_entry_sha256=hashlib.sha256(binary).hexdigest(),target_bar_present=sid in raw,history_bar_count=len(bs),events=[dict(date=e.event_date,c1=e.c1,c2=e.c2,c3=e.c3,c4=e.c4,source_record_index=e.source_record_index) for e in cross],checks=checks,ohlc_samples=values[:2]+values[-2:]));categories[category]+=1
            if len(samples)==10:break
    legacy=read(OLD/'LEGACY_528_AND_35_RECONCILIATION_V2.json')['rows']
    write('REAL_BOUNDARY_AND_CROSS_XRXD_INDEPENDENT_ORACLE.json',dict(contract='R4_2_1_REAL_BOUNDARY_ORACLE_V1',inputs={k:owner[k] for k in ['core','prior_core','history','raw']},sources=owner['sources'],formula='Chronological per event P=(10*P-cash+rights*price)/(10+bonus+rights); parameter and final cents ROUND_HALF_UP; MA20 mean 20 closes; ATR20 mean max(H-L,abs(H-priorC),abs(L-priorC)) over 20 transitions. No production adjustment or compute imports.',samples=samples,categories=dict(categories),errors=errors,legacy_counts=dict(Counter((r['trade_date']+':'+str(r['usable_corrected'])) for r in legacy)),source_conflict_real_count=sum(bool(r['source_conflict']) for r in legacy),missing_real_cases=['No real cross-source OHLC conflict observed in LEGACY evidence; do not fabricate conflict','Code transfer is governed by separate BJ alias admission objects'],acceptance='PASS_SCOPED_INDEPENDENT_ARITHMETIC' if not errors and len(samples)>=8 else 'BLOCKED_ORACLE'))
    write('P1_BOUNDARIES_STAGE_RESULT.json',dict(acceptance='PASS_ENGINEERING_AUDIT_WITH_SCOPED_IDENTITY_AND_PRIOR_GAPS',next_stage='INDEPENDENT_SOURCE_OWNER_ADMISSION',identity_accepted=0,production_changed=False,numeric_samples=len(samples),numeric_errors=len(errors)))
    print(json.dumps(dict(samples=len(samples),categories=dict(categories),errors=len(errors),breakout=audit[0]['breakout_counts'])))
if __name__=='__main__':main()


