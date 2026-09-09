from __future__ import annotations
import json, mimetypes, os, secrets, subprocess, sys, threading, time, uuid
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import duckdb
from workbench_publish.orchestrator import submit_one_click, ControlledProduction
from workbench_publish import OneClickPublisher
from workbench_ops import OperationsConfig, ConfigConflict, ConfigValidationError
from workbench_ops import StorageGovernance, BackupService, MaintenanceService
from workbench_service.strength_association import choose_association
from workbench_service.universe import A_SHARE_SQL, summarize_universe
from workbench_service.quotes import QuoteService

MAX_PAGE_SIZE=100

def resolve_workbench_path(root,trade_date,publication_id):
 base=Path(root)/'reports/workbench'/str(trade_date).replace('-','')/publication_id
 matches=[]
 for path in base.glob('*/market_structure_workbench.html'):
  # Legacy reports embedded the whole dataset and can freeze the browser.
  # They remain audit artifacts, but are never eligible to be served.
  if path.stat().st_size >= 1_000_000: continue
  with path.open('r',encoding='utf-8',errors='ignore') as handle:
   prefix=handle.read(256_000)
  if 'const 数据=' in prefix or '/api/queues' not in prefix: continue
  matches.append(path)
 matches=sorted(matches,key=lambda p:p.stat().st_mtime_ns,reverse=True)
 if not matches: raise ValueError('WORKBENCH_NOT_FOUND')
 return matches[0]

class Api:
 def __init__(self,db): self.db=str(Path(db).resolve());self._quote_cache={};self._quote_lock=threading.Lock();self._quote_service=QuoteService(Path(self.db).parents[1]/'normalized/adjusted_daily.parquet');self._association_cache={};self._association_lock=threading.Lock()
 def _con(self):
  # DuckDB refuses a read_only connection while the publisher owns a normal
  # writer connection.  A normal read connection participates in DuckDB MVCC:
  # it sees the last committed publication while the writer's transaction is
  # in flight, so the workbench remains readable throughout publication.
  return duckdb.connect(self.db)
 def publications(self):
  with self._con() as c:
   rows=c.execute("select cast(h.trade_date as varchar),h.publication_id from publication_heads h join publications p using(publication_id) where p.status='SUCCESS' order by h.trade_date desc").fetchall()
  return {'items':[{'trade_date':d,'publication_id':p} for d,p in rows],'latest_publication_id':rows[0][1] if rows else None}
 def latest_bundle(self):
  with self._con() as c: rows=c.execute("select source_bundle_id,payload_json from source_bundles").fetchall()
  values=[]
  for bundle_id,payload in rows:
   value=json.loads(payload);receipt=Path(self.db).parents[2]/'data/source_bundles'/bundle_id/'source_bundle.json'
   # Test/import databases may contain an identity before its local receipt is
   # materialised.  Production computation still verifies that receipt.
   values.append((value,receipt.stat().st_mtime_ns if receipt.is_file() else 0))
  values.sort(key=lambda x:(x[0].get('target_trade_date',''),x[1]),reverse=True)
  if not values:raise ValueError('SOURCE_BUNDLE_NOT_FOUND')
  return values[0][0]
 def _pub(self,p):
  with self._con() as c: row=c.execute("select cast(trade_date as varchar),source_revision_id from publications where publication_id=? and status='SUCCESS'",[p]).fetchone()
  if not row: raise ValueError('PUBLICATION_NOT_FOUND')
  return row
 def _quotes(self,p):
  if p in self._quote_cache:return self._quote_cache[p]
  with self._quote_lock:
   if p not in self._quote_cache:self._quote_cache[p]=self._load_quotes(p)
  return self._quote_cache[p]
 def _load_quotes(self,p):
  trade_date,_=self._pub(p); current=date.fromisoformat(trade_date)
  identity=self.identity(p)
  return self._quote_service.load(trade_date=current,publication_id=p,source_identity_sha256=identity.get('source_identity_sha256'))
 def _add_quotes(self,p,result):
  quotes=self._quotes(p)
  for item in result['items']: item.update(quotes.get(item.get('security_id'),{}))
  return result
 def _add_strength_associations(self,p,result):
  security_ids=[item.get('security_id') for item in result['items'] if item.get('security_id')]
  missing=[sid for sid in security_ids if (p,sid) not in self._association_cache]
  if missing:
   with self._association_lock:
    missing=[sid for sid in missing if (p,sid) not in self._association_cache]
    if missing:
     with self._con() as c:
      snap=c.execute('select membership_snapshot_id from publication_memberships where publication_id=?',[p]).fetchone()
      if snap:
       placeholders=','.join('?' for _ in missing)
       rows=c.execute(f'''select m.security_id,m.sector_id,d.payload_json
          from membership_entries m join sector_daily d on d.publication_id=? and d.sector_id=m.sector_id
         where m.membership_snapshot_id=? and m.security_id in ({placeholders})''',[p,snap[0],*missing]).fetchall()
       sector_payloads={sector_id:json.loads(payload) for _,sector_id,payload in rows}
       sector_ids=sorted(sector_payloads)
       grouped={sector_id:[] for sector_id in sector_ids}
       if sector_ids:
        sector_placeholders=','.join('?' for _ in sector_ids)
        member_rows=c.execute(f'''select m.sector_id,m.security_id,s.payload_json
           from membership_entries m join stock_daily s on s.publication_id=? and s.security_id=m.security_id
          where m.membership_snapshot_id=? and m.sector_id in ({sector_placeholders})
            and {A_SHARE_SQL.format(id='m.security_id')}''',[p,snap[0],*sector_ids]).fetchall()
        for sector_id,security_id,payload in member_rows:
         member=json.loads(payload);member['security_id']=security_id;grouped[sector_id].append(member)
       memberships={sid:[] for sid in missing}
       for sid,sector_id,_ in rows:
        memberships[sid].append((sector_payloads[sector_id],grouped.get(sector_id,[])))
       for sid in missing:self._association_cache[p,sid]=choose_association(sid,memberships[sid])
      else:
       for sid in missing:self._association_cache[p,sid]=choose_association(sid,[])
  for item in result['items']:item.update(self._association_cache.get((p,item.get('security_id')),choose_association(item.get('security_id'),[])))
  return result
 def _rows(self,table,p,where='',args=(),order='',page=1,size=50):
  size=max(1,min(MAX_PAGE_SIZE,int(size))); page=max(1,int(page)); self._pub(p)
  q=f" from {table} where publication_id=? {where}"; params=[p,*args]
  with self._con() as c:
   total=c.execute('select count(*)'+q,params).fetchone()[0]
   vals=c.execute('select payload_json'+q+(' order by '+order if order else '')+' limit ? offset ?',params+[size,(page-1)*size]).fetchall()
  return {'publication_id':p,'page':page,'page_size':size,'total':total,'items':[json.loads(x[0]) for x in vals]}
 def dashboard(self,p):
  d,rev=self._pub(p)
  with self._con() as c:
   market=c.execute('select payload_json from market_daily where publication_id=?',[p]).fetchone()
   counts={t:c.execute(f'select count(*) from {t} where publication_id=?',[p]).fetchone()[0] for t in ('sector_daily','stock_daily','candidate_daily','queue_memberships')}
  return {'publication_id':p,'selected_date':d,'actual_input_date':d,'latest_success_date':self.publications()['items'][0]['trade_date'],'source_revision_id':rev,'market':json.loads(market[0]) if market else None,'counts':counts}
 def sectors(self,p,q,page,size,sector_type=''):
  extra='and (sector_name ilike ? or sector_id ilike ?)'; args=(f'%{q}%',f'%{q}%')
  if sector_type: extra+=' and sector_type=?'; args += (sector_type,)
  result=self._rows('sector_daily',p,extra,args,'display_rank nulls last, sector_id',page,size)
  ids={item['sector_id'] for item in result['items']};quotes=self._quotes(p)
  if ids:
   snap=self.identity(p).get('membership_snapshot_id')
   with self._con() as c: members=c.execute('select sector_id,security_id from membership_entries where membership_snapshot_id=? and sector_id in ('+','.join('?' for _ in ids)+')',[snap,*ids]).fetchall()
   grouped={sid:[] for sid in ids}
   for sid,security_id in members:
    if security_id in quotes: grouped[sid].append(quotes[security_id])
   for item in result['items']:
    values=grouped[item['sector_id']];returns=sorted(x['RET1'] for x in values if x.get('RET1') is not None)
    item['sector_ret1_median']=returns[len(returns)//2] if len(returns)%2 else (returns[len(returns)//2-1]+returns[len(returns)//2])/2 if returns else None
    item['sector_turnover_amount']=sum(x['turnover_amount'] for x in values if x.get('turnover_amount') is not None)
    item['total_member_count']=len(values)
  return result
 def stocks(self,p,q,page,size): return self._add_quotes(p,self._rows('stock_daily',p,'and '+A_SHARE_SQL.format(id='security_id')+' and (security_name ilike ? or security_id ilike ?)',(f'%{q}%',f'%{q}%'),'security_id',page,size))
 def universe_summary(self,p):
  trade_date,source_revision=self._pub(p)
  with self._con() as c:
   rows=c.execute('select security_id,payload_json from stock_daily where publication_id=? order by security_id',[p]).fetchall()
  records=[]
  for security_id,payload in rows:
   record=json.loads(payload);record['security_id']=security_id
   records.append(record)
  summary=summarize_universe(records,quote_valid_ids=set(self._quotes(p)))
  summary.pop('items',None)
  identity=self.identity(p)
  summary.update({
   'publication_id':p,
   'trade_date':trade_date,
   'source_revision_id':source_revision,
   'source_identity_sha256':identity.get('source_identity_sha256'),
   'source_manifest_sha256':identity.get('source_manifest_sha256'),
  })
  return {'publication_id':p,'item':summary}
 def candidates(self,p,q,page,size,grade='',pattern=''):
  extra='and (security_name ilike ? or security_id ilike ?)'; args=(f'%{q}%',f'%{q}%')
  if grade: extra+=' and research_priority=?'; args += (grade,)
  if pattern: extra+=' and primary_pattern=?'; args += (pattern,)
  extra='and '+A_SHARE_SQL.format(id='security_id')+' '+extra
  result=self._rows('candidate_daily',p,extra,args,"case research_priority when 'A+' then 0 when 'A' then 1 when 'B' then 2 when 'C' then 3 else 9 end, cast(json_extract_string(payload_json,'$.priority_score') as double) desc, security_id",page,size)
  return self._add_quotes(p,self._add_strength_associations(p,result))
 def queues(self,p,name,page,size,q='',band=''):
  canonical=str(name).removesuffix('_QUEUE').upper()+'_QUEUE'
  size=max(1,min(MAX_PAGE_SIZE,int(size))); page=max(1,int(page)); self._pub(p)
  filters=['q.publication_id=?','q.queue_name=?',A_SHARE_SQL.format(id='q.security_id')]; args=[p,canonical]
  if q: filters+=['(s.security_name ilike ? or q.security_id ilike ?)']; args += [f'%{q}%',f'%{q}%']
  if band:
   bands=[x for x in str(band).split(',') if x]
   if bands == ['__NONE__']: filters.append('1=0')
   elif len(bands)==1: filters.append('json_extract_string(u.payload_json,\'$.shadow_research_band\')=?'); args += bands
   else: filters.append('json_extract_string(u.payload_json,\'$.shadow_research_band\') in ('+','.join('?' for _ in bands)+')'); args += bands
  where=' and '.join(filters)
  with self._con() as c:
   total=c.execute(f'select count(*) from queue_memberships q left join stock_daily s using(publication_id,security_id) left join unified_board u using(publication_id,security_id) where {where}',args).fetchone()[0]
   rank_key=canonical.removesuffix('_QUEUE').lower()+'_queue_rank'
   vals=c.execute(f"select q.payload_json,s.payload_json,u.payload_json,c.payload_json,d.payload_json,r.payload_json from queue_memberships q left join stock_daily s using(publication_id,security_id) left join unified_board u using(publication_id,security_id) left join candidate_daily c using(publication_id,security_id) left join queue_rankings r using(publication_id,security_id) left join structure_details d on d.publication_id=q.publication_id and d.security_id=q.security_id and d.queue_name=replace(q.queue_name,'_QUEUE','') where {where} order by try_cast(json_extract_string(r.payload_json,'$.{rank_key}') as integer) nulls last,q.security_id limit ? offset ?",args+[size,(page-1)*size]).fetchall()
  items=[]
  for index,parts in enumerate(vals):
   merged={}
   for value in parts:
    if value: merged.update(json.loads(value))
   if parts[4]: merged['_evidence']=json.loads(parts[4])
   merged['a_share_queue_rank']=(page-1)*size+index+1
   items.append(merged)
  result={'publication_id':p,'page':page,'page_size':size,'total':total,'items':items}
  return self._add_quotes(p,self._add_strength_associations(p,result))
 def evidence(self,p,queue,security):
  # The UI uses stable lowercase route keys while the publication contract
  # stores queue names in uppercase.  Normalize both forms before lookup.
  detail=str(queue).removesuffix('_QUEUE').upper(); canonical=detail+'_QUEUE'
  with self._con() as c: row=c.execute('select payload_json from structure_details where publication_id=? and queue_name=? and security_id=?',[p,detail,security]).fetchone()
  return {'publication_id':p,'item':json.loads(row[0]) if row else None}
 def identity(self,p):
  d,rev=self._pub(p)
  with self._con() as c:
   x=c.execute('select source_manifest_sha256,source_identity_sha256,computation_identity_sha256,render_identity_sha256 from publications where publication_id=?',[p]).fetchone()
   membership=c.execute('select membership_snapshot_id from publication_memberships where publication_id=?',[p]).fetchone()
  return {'publication_id':p,'trade_date':d,'source_revision_id':rev,'source_manifest_sha256':x[0],'source_identity_sha256':x[1],'computation_identity_sha256':x[2],'render_identity_sha256':x[3],'membership_snapshot_id':membership[0] if membership else None,'api_contract':'m2-read-only-api-v1.2'}
 def linkage(self,p,sector,security,page=1,size=100,q=''):
  size=max(1,min(MAX_PAGE_SIZE,int(size))); page=max(1,int(page))
  self._pub(p)
  with self._con() as c:
   snap=c.execute('select membership_snapshot_id from publication_memberships where publication_id=?',[p]).fetchone()
   if not snap:return {'publication_id':p,'page':page,'page_size':size,'total':0,'items':[]}
   if not sector and not security: raise ValueError('LINKAGE_KEY_REQUIRED')
   # Rank every member before applying the stock/search filter.  This keeps a
   # stock's sector rank stable in both directions and across pagination.
   scope=' and m.sector_id=?' if sector else ''
   scope_args=[sector] if sector else []
   cte=f'''with ranked as (
    select m.payload_json membership_payload,s.payload_json stock_payload,u.payload_json board_payload,
           m.sector_id,m.security_id,
           row_number() over(partition by m.sector_id order by
             try_cast(json_extract_string(u.payload_json,'$.stock_rs20_pct') as double) desc nulls last,
             try_cast(json_extract_string(s.payload_json,'$.RET20') as double) desc nulls last,
             m.security_id) sector_member_rank,
           count(*) over(partition by m.sector_id) sector_member_count
      from membership_entries m
      left join stock_daily s on s.publication_id=? and s.security_id=m.security_id
      left join unified_board u on u.publication_id=? and u.security_id=m.security_id
     where m.membership_snapshot_id=?{scope} and {A_SHARE_SQL.format(id='m.security_id')})'''
   params=[p,p,snap[0],*scope_args]
   filters=[]; filter_args=[]
   if security: filters.append('security_id=?'); filter_args.append(security)
   if q:
    filters.append("(json_extract_string(stock_payload,'$.security_name') ilike ? or security_id ilike ?)")
    filter_args += [f'%{q}%',f'%{q}%']
   where=(' where '+' and '.join(filters)) if filters else ''
   total=c.execute(cte+' select count(*) from ranked'+where,params+filter_args).fetchone()[0]
   vals=c.execute(cte+' select membership_payload,stock_payload,board_payload,sector_member_rank,sector_member_count from ranked'+where+' order by sector_id,sector_member_rank limit ? offset ?',params+filter_args+[size,(page-1)*size]).fetchall()
  items=[]
  for parts in vals:
   merged={}
   for value in parts[:3]:
    if value: merged.update(json.loads(value))
   merged['sector_member_rank']=int(parts[3])
   merged['sector_member_count']=int(parts[4])
   merged.update(self._quotes(p).get(merged.get('security_id'),{}))
   items.append(merged)
  sector_member_count=(items[0]['sector_member_count'] if sector and items else total if sector and not q else None)
  return {'publication_id':p,'page':page,'page_size':size,'total':total,'sector_member_count':sector_member_count,'sector_member_rank_basis':'stock_rs20_pct_desc_then_ret20_desc_then_security_id','items':items}

def make_handler(root,db):
 api=Api(db); operations=OperationsConfig(root,db); storage=StorageGovernance(root,db); backups=BackupService(root,db); maintenance=MaintenanceService(root,db); static=Path(root)/'src/workbench_service/static';csrf=secrets.token_urlsafe(24);publishers={};daily_jobs={}
 def today_status(job_id):
  task=daily_jobs.get(job_id)
  if not task: return None
  publisher=task.get('publisher')
  if publisher:
   child=publisher.status(task['publication_job_id'])
   task.update(status=child['status'],progress=child.get('progress',{}),updated_at_utc=child.get('updated_at_utc'))
  return {'job_id':job_id,'status':task['status'],'details':{'trade_date':task.get('trade_date'),'source_bundle_id':task.get('source_bundle_id')},'progress':task.get('progress',{}),'updated_at_utc':task.get('updated_at_utc')}
 def run_today(job_id,body):
  task=daily_jobs[job_id];task.update(status='RUNNING',progress={'status':'INPUT_DOWNLOADING'})
  result=subprocess.run([sys.executable,str(Path(root)/'run_upgrade_m3.py')],cwd=root,capture_output=True,text=True)
  receipt_path=Path(root)/'reports/upgrade_m3/M3_AUTOMATIC_INPUT_RECEIPT.json'
  receipt=json.loads(receipt_path.read_text('utf-8')) if receipt_path.is_file() else {}
  if result.returncode or receipt.get('final_status')!='FULL_PASS':
   task.update(status='FAILED',progress={'status':'INPUT_FAILED','error':receipt.get('blockers') or result.stderr[-500:]});return
  bundle=receipt['source_bundle_id'];day=receipt['day_validation']['target_trade_date'];trade_date=date(int(str(day)[:4]),int(str(day)[4:6]),int(str(day)[6:]))
  task.update(source_bundle_id=bundle,trade_date=trade_date.isoformat(),progress={'status':'PUBLISHING'})
  publisher,publication_job_id=submit_one_click(Path(root),bundle,trade_date,body.get('economic_model_id','current-economic-model'),body.get('computation_contract_id','current-computation-contract'),db)
  task.update(publisher=publisher,publication_job_id=publication_job_id,status='RUNNING')
 def legacy_workbench(publication_id):
  trade_date,_=api._pub(publication_id)
  return resolve_workbench_path(root,trade_date,publication_id).read_bytes()
 class Handler(BaseHTTPRequestHandler):
  def _send(self,status,body,ctype='application/json; charset=utf-8'):
   raw=(json.dumps(body,ensure_ascii=False) if not isinstance(body,bytes) else body); raw=raw.encode() if isinstance(raw,str) else raw
   self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(raw)
  def do_GET(self):
   u=urlparse(self.path); x={k:v[0] for k,v in parse_qs(u.query).items()}
   try:
    if u.path=='/api/publications': out=api.publications()
    elif u.path=='/api/dashboard': out=api.dashboard(x['publication_id'])
    elif u.path=='/api/sectors': out=api.sectors(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50),x.get('type',''))
    elif u.path=='/api/stocks': out=api.stocks(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50))
    elif u.path=='/api/candidates': out=api.candidates(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50),x.get('grade',''),x.get('pattern',''))
    elif u.path=='/api/queues': out=api.queues(x['publication_id'],x.get('queue','STEADY'),x.get('page',1),x.get('page_size',50),x.get('q',''),x.get('band',''))
    elif u.path=='/api/evidence': out=api.evidence(x['publication_id'],x['queue'],x['security_id'])
    elif u.path=='/api/identity': out=api.identity(x['publication_id'])
    elif u.path=='/api/universe/summary': out=api.universe_summary(x['publication_id'])
    elif u.path=='/api/linkage': out=api.linkage(x['publication_id'],x.get('sector_id'),x.get('security_id'),x.get('page',1),x.get('page_size',100),x.get('q',''))
    elif u.path=='/api/input/latest': out=api.latest_bundle()
    elif u.path=='/api/operations/config': out=operations.current()
    elif u.path=='/api/operations/config/history':
     with duckdb.connect(str(db)) as c: out={'items':[json.loads(x[0]) for x in c.execute('select payload_json from config_versions').fetchall()]}
    elif u.path=='/api/operations/status': out=maintenance.status()
    elif u.path=='/api/operations/restart-status':
     status_path=Path(root)/'runtime/controlled_restart_status.json';out=json.loads(status_path.read_text('utf-8')) if status_path.is_file() else {'state':'尚未执行'}
    elif u.path=='/api/operations/storage':
     with duckdb.connect(str(db)) as c: out={'items':[json.loads(x[0]) for x in c.execute('select payload_json from storage_objects').fetchall()]}
    elif u.path=='/api/operations/backups':
     with duckdb.connect(str(db)) as c: out={'items':[json.loads(x[0]) for x in c.execute('select payload_json from backup_catalog').fetchall()]}
    elif u.path=='/api/operations/cleanup-plans':
     with duckdb.connect(str(db)) as c: out={'items':[json.loads(x[0]) for x in c.execute('select payload_json from cleanup_jobs').fetchall()]}
    elif u.path=='/api/jobs' and x.get('active')=='1':
     active=[]
     for job_id in list(daily_jobs):
      status=today_status(job_id)
      if status and status['status'] in ('QUEUED','RUNNING'):active.append(status)
     for job_id,publisher in publishers.items():
      if not isinstance(publisher,OneClickPublisher):continue
      status=publisher.status(job_id)
      if status['status'] in ('QUEUED','RUNNING'):active.append(status)
     out={'items':active}
    elif u.path=='/api/jobs' and x['job_id'] in daily_jobs: out=today_status(x['job_id'])
    elif u.path=='/api/jobs':
     publisher=publishers.get(x['job_id'])
     out=(publisher if isinstance(publisher,OneClickPublisher) else OneClickPublisher(root,db)).status(x['job_id'])
    elif u.path in ('/v2','/v2/','/v2/index.html'):
     return self._send(200,(static/'v2/index.html').read_bytes(),'text/html; charset=utf-8')
    elif u.path.startswith('/v2/'):
     relative=unquote(u.path[len('/v2/'):])
     candidate=(static/'v2'/relative).resolve()
     v2_root=(static/'v2').resolve()
     if v2_root not in candidate.parents or not candidate.is_file():
      return self._send(404,{'code':'NOT_FOUND','message':'v2资源不存在','retryable':False,'next_action':'检查地址'})
     content_type=mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
     return self._send(200,candidate.read_bytes(),content_type+'; charset=utf-8' if content_type.startswith(('text/','application/javascript')) else content_type)
    elif u.path=='/view': return self._send(200,legacy_workbench(x['publication_id']),'text/html; charset=utf-8')
    elif u.path=='/operations': return self._send(200,(static/'operations.html').read_text('utf-8').replace('__CSRF_TOKEN__',csrf).replace('</body>','<script src="/operations-i18n.js"></script></body>').encode(),'text/html; charset=utf-8')
    elif u.path=='/operations-i18n.js': return self._send(200,(static/'operations-i18n.js').read_bytes(),'application/javascript; charset=utf-8')
    elif u.path in ('/','/index.html'): return self._send(200,(static/'index.html').read_text('utf-8').replace('__CSRF_TOKEN__',csrf).encode(),'text/html; charset=utf-8')
    elif u.path=='/fixes.js': return self._send(200,(static/'fixes.js').read_bytes(),'application/javascript; charset=utf-8')
    else:return self._send(404,{'code':'NOT_FOUND','message':'页面不存在','retryable':False,'next_action':'检查地址'})
    self._send(200,out)
   except (KeyError,ValueError) as e:self._send(400,{'code':str(e).strip("'"),'message':'请求参数或发布版本无效','retryable':False,'next_action':'重新选择日期'})
   except Exception:self._send(500,{'code':'INTERNAL_ERROR','message':'读取失败','retryable':True,'next_action':'稍后重试'})
  def do_POST(self):
   try:
    if self.headers.get('X-CSRF-Token')!=csrf: return self._send(403,{'code':'CSRF_REJECTED','message':'会话校验失败，请刷新页面','retryable':True})
    origin=self.headers.get('Origin');expected='http://'+self.headers.get('Host','')
    if origin and origin!=expected:return self._send(403,{'code':'ORIGIN_REJECTED','message':'拒绝跨站请求','retryable':False})
    length=int(self.headers.get('Content-Length','0'));body=json.loads(self.rfile.read(length) or b'{}')
    if self.path=='/api/operations/config/validate':
     return self._send(200,operations.validate(body.get('config',{})))
    if self.path=='/api/operations/config/apply':
     return self._send(200,operations.apply(body.get('config',{}),expected_revision=body.get('expected_revision')))
    if self.path=='/api/operations/storage/preview':
     return self._send(200,storage.preview_cleanup(as_of=date.fromisoformat(body['as_of'])))
    if self.path=='/api/operations/storage/quarantine':
     maintenance._guard(body.get('confirmation'))
     try:return self._send(200,storage.quarantine(body['cleanup_job_id']))
     finally:maintenance.lock.release()
    if self.path=='/api/operations/storage/restore':
     maintenance._guard(body.get('confirmation'))
     try:return self._send(200,storage.restore_quarantine(body['cleanup_job_id']))
     finally:maintenance.lock.release()
    if self.path=='/api/operations/storage/delete':
     maintenance._guard(body.get('confirmation'))
     try:return self._send(200,storage.delete_quarantine(body['cleanup_job_id']))
     finally:maintenance.lock.release()
    if self.path=='/api/operations/backup/create':
     return self._send(200,maintenance.create_backup(body.get('confirmation')))
    if self.path=='/api/operations/backup/restore-drill':
     return self._send(200,maintenance.restore_drill(body['backup_id'],body.get('confirmation')))
    if self.path=='/api/operations/migration/prepare':
     return self._send(200,maintenance.prepare_migration(body['target_path'],body.get('confirmation')))
    if self.path=='/api/operations/restart':
     maintenance._guard(body.get('confirmation'));maintenance.lock.release()
     host,port=self.server.server_address;status_path=Path(root)/'runtime/controlled_restart_status.json'
     command=[sys.executable,str(Path(root)/'scripts/m5_restart_helper.py'),'--pid',str(os.getpid()),'--root',str(root),'--host',str(host),'--port',str(port),'--status',str(status_path)]
     flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0;subprocess.Popen(command,cwd=root,creationflags=flags)
     self._send(202,{'state':'DRAINING','message':'受控重启已启动，页面将自动重连'})
     threading.Thread(target=lambda:(time.sleep(.4),self.server.shutdown()),daemon=True).start();return
    if self.path!='/api/jobs':return self._send(404,{'code':'NOT_FOUND','message':'接口不存在','retryable':False})
    job_id='daily-'+uuid.uuid4().hex;daily_jobs[job_id]={'status':'QUEUED','progress':{'status':'INPUT_QUEUED'}}
    thread=threading.Thread(target=run_today,args=(job_id,body),daemon=True,name=job_id);thread.start()
    self._send(202,{'job_id':job_id,'status':'QUEUED','message':'已提交当日输入更新与发布任务'})
   except ConfigConflict as e:self._send(409,{'code':str(e),'message':'配置已被其他操作更新，请先重新读取','retryable':True})
   except ConfigValidationError as e:self._send(400,{'code':str(e),'message':'配置校验未通过，未应用任何变更','retryable':False})
   except (ValueError,KeyError) as e:self._send(400,{'code':str(e).strip("'"),'message':'无法提交生成任务','retryable':False})
   except Exception as e:self._send(500,{'code':'JOB_SUBMIT_FAILED','message':'任务提交失败','retryable':True,'detail':str(e)})
  def log_message(self,*_): pass
 return Handler

def serve(root,host='127.0.0.1',port=8765,database_path=None):
 db=Path(database_path).resolve() if database_path else Path(root)/'data/database/market_research.duckdb'
 # Persisted jobs are resumed before accepting new commands.  The controlled
 # worker is supplied explicitly so an interrupted production request cannot
 # be mistakenly published as an empty request.
 OneClickPublisher(root,db).recover_interrupted(ControlledProduction(Path(root)),background=True)
 ThreadingHTTPServer((host,port),make_handler(root,db)).serve_forever()
