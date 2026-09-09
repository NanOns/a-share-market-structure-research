from __future__ import annotations
import json, math, mimetypes, os, secrets, subprocess, sys, threading, time, uuid
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
from workbench_service.universe import A_SHARE_SQL, is_a_share_security_id, summarize_universe
from workbench_service.quotes import QuoteService
from workbench_service.catalog import API_CONTRACT, field_catalog
from workbench_service.window_planner import MAX_OUTPUT_DAYS, load_dependencies, plan_window
from workbench_service.history_jobs import HistoryJobError, HistoryJobService
from workbench_service.analysis_activation import AnalysisActivationError, AnalysisActivationService
from workbench_service.source_freezer import SourceFreezeError, validate_source_manifest
from workbench_analysis.chart import ChartCache, build_chart_points, chart_cache_key

MAX_PAGE_SIZE=100

def _sector_code(sector_id):
 return str(sector_id).split(':',1)[-1]

def _sector_rank_desc(values):
 finite=[value for value in values if isinstance(value,(int,float)) and math.isfinite(value)]
 if not finite:return [None for _ in values],[None for _ in values]
 ranks=[];percentiles=[]
 for value in values:
  if not isinstance(value,(int,float)) or not math.isfinite(value):
   ranks.append(None);percentiles.append(None);continue
  greater=sum(other>value for other in finite)
  tied=sum(other==value for other in finite)
  rank=greater+(tied+1)/2
  ranks.append(rank);percentiles.append((len(finite)-rank+1)/len(finite))
 return ranks,percentiles

def _annotate_sector_hierarchy(items,dates):
 # Industry parentage is derived only from the audited TDX code prefix.  Theme
 # and style sources do not expose an audited parent relation and stay flat.
 sector_names={(item['sector_type'],_sector_code(item['sector_id'])):item['sector_name'] for item in items}
 for item in items:
  item['sector_code']=_sector_code(item['sector_id'])
  item['parent_sector_id']=None;item['parent_sector_name']=None
  if item['sector_type']=='INDUSTRY':
   code=item['sector_code']
   parents=[parent for kind,parent in sector_names if kind=='INDUSTRY' and len(parent)>=5 and len(parent)<len(code) and code.startswith(parent)]
   if parents:
    parent=max(parents,key=len)
    item['parent_sector_id']='INDUSTRY:'+parent;item['parent_sector_name']=sector_names[('INDUSTRY',parent)]
  if item['sector_type']=='INDUSTRY':
   item['hierarchy_level_code']='LEAF' if item['parent_sector_id'] else 'ROOT'
   item['hierarchy_level']='细分行业' if item['parent_sector_id'] else '一级大板块'
  else:
   item['hierarchy_level_code']='FLAT';item['hierarchy_level']='平级板块'
  item['rank_scope']=f"{item['sector_type']}_{item['hierarchy_level_code']}"
 for date_index,_ in enumerate(dates):
  buckets={}
  for item_index,item in enumerate(items):
   cell=item['cells'][date_index]
   buckets.setdefault((item['sector_type'],item['hierarchy_level_code']),[]).append((item_index,cell.get('sector_rs20')))
  for members in buckets.values():
   ranks,percentiles=_sector_rank_desc([value for _,value in members])
   for (item_index,_),rank,percentile in zip(members,ranks,percentiles):
    items[item_index]['cells'][date_index]['hierarchy_rank']=rank
    items[item_index]['cells'][date_index]['hierarchy_sector_rs20_pct']=percentile
 return items

def _finite_or_none(value):
 if isinstance(value,float) and not math.isfinite(value):return None
 return value

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
 def __init__(self,db,root=None): self.db=str(Path(db).resolve());self._root=Path(root).resolve() if root else Path(__file__).resolve().parents[2];self._quote_cache={};self._quote_lock=threading.Lock();self._source_cache={};self._chart_cache=ChartCache();self._association_cache={};self._association_lock=threading.Lock();self._window_dependencies=load_dependencies(self._root);self._window_sessions_cache=None
 def _con(self):
  # DuckDB refuses a read_only connection while the publisher owns a normal
  # writer connection.  A normal read connection participates in DuckDB MVCC:
  # it sees the last committed publication while the writer's transaction is
  # in flight, so the workbench remains readable throughout publication.
  return duckdb.connect(self.db)
 def publications(self,include_analysis=False):
  with self._con() as c:
   rows=c.execute("select cast(h.trade_date as varchar),h.publication_id,p.revision,p.production_version from publication_heads h join publications p using(publication_id) where p.status='SUCCESS' and (p.production_version not like 'm4-%' or exists (select 1 from publication_analysis_snapshots a where a.publication_id=p.publication_id and a.domain='LOCAL_RECONSTRUCTED')) order by h.trade_date desc").fetchall()
  items=[]
  for d,p,revision,production_version in rows:
   item={'trade_date':d,'publication_id':p}
   if include_analysis:
    item.update({'revision':revision,'production_version':production_version,'analysis_capabilities':self._analysis_capabilities(p)})
   items.append(item)
  result={'items':items,'latest_publication_id':rows[0][1] if rows else None}
  if include_analysis: result['api_contract']=API_CONTRACT
  return result
 def sector_cycle(self,p,page=1,size=20,sector_type='',q='',days=10,metric='rank',hierarchy_level=''):
  if metric not in ('rank','sector_rs20_pct','breadth_ret1'): raise ValueError('SECTOR_CYCLE_METRIC_UNSUPPORTED')
  days=max(1,min(30,int(days)));size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p)
  bindings=self._analysis_bindings(p);selected=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected: raise ValueError('ANALYSIS_NOT_BUILT')
  filters=['e.snapshot_id=?',"e.domain='sector_cycle'"];args=[selected['snapshot_id']]
  if sector_type: filters.append('c.sector_type=?');args.append(sector_type)
  if q: filters.append('(c.sector_id ilike ? or c.sector_name ilike ?)');args.extend([f'%{q}%',f'%{q}%'])
  where=' and '.join(filters)
  query="with recent_dates as (select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='sector_cycle' order by trade_date desc limit ?) select c.sector_id,c.trade_date,c.sector_name,c.sector_type,c.board_quote_ret1,c.board_quote_source,c.member_ret1_median,c.member_ret5_median,c.member_ret20_median,c.member_amount_sum,c.amount_valid_count,c.total_member_count,c.quote_valid_count,c.factor_valid_count,c.coverage,c.breadth_ret1,c.breadth_ma20,c.sector_rs5,c.sector_rs20,c.sector_rs5_pct,c.sector_rs20_pct,c.amount_vs_prior20,c.rank,c.rank_change,c.window_stats from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='sector_cycle' and e.trade_date=d.trade_date join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where "+where+" order by c.trade_date,c.rank nulls last,c.sector_id"
  with self._con() as c: rows=c.execute(query,[selected['snapshot_id'],days,selected['snapshot_id'],*args]).fetchall()
  names=('sector_id','trade_date','sector_name','sector_type','board_quote_ret1','board_quote_source','member_ret1_median','member_ret5_median','member_ret20_median','member_amount_sum','amount_valid_count','total_member_count','quote_valid_count','factor_valid_count','coverage','breadth_ret1','breadth_ma20','sector_rs5','sector_rs20','sector_rs5_pct','sector_rs20_pct','amount_vs_prior20','rank','rank_change','window_stats')
  grouped={};date_values=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['window_stats']=json.loads(item['window_stats']) if item['window_stats'] else {};date_values.append(item['trade_date']);key=(item['sector_id'],item['sector_type']);grouped.setdefault(key,{'sector_id':item['sector_id'],'sector_name':item['sector_name'],'sector_type':item['sector_type'],'_rows':[]})['_rows'].append(item)
  dates=sorted(set(date_values));items=[]
  for item in grouped.values():
   cells={row['trade_date']:row for row in item.pop('_rows')};item['cells']=[{'trade_date':day,'rank':cells[day]['rank'] if day in cells else None,'hierarchy_rank':None,'hierarchy_sector_rs20_pct':None,'sector_rs20':cells[day]['sector_rs20'] if day in cells else None,'sector_rs20_pct':cells[day]['sector_rs20_pct'] if day in cells else None,'board_quote_ret1':cells[day]['board_quote_ret1'] if day in cells else None,'member_ret1_median':cells[day]['member_ret1_median'] if day in cells else None,'breadth_ret1':cells[day]['breadth_ret1'] if day in cells else None,'coverage':cells[day]['coverage'] if day in cells else None,'diffusion_state':None} for day in dates];items.append(item)
  _annotate_sector_hierarchy(items,dates)
  level_filter=str(hierarchy_level or '').upper()
  if level_filter not in ('','ALL','ROOT','LEAF','FLAT'): raise ValueError('SECTOR_HIERARCHY_LEVEL_UNSUPPORTED')
  if level_filter and level_filter!='ALL': items=[item for item in items if item['hierarchy_level_code']==level_filter]
  latest_index=len(dates)-1
  level_order={'ROOT':0,'LEAF':1,'FLAT':0}
  items.sort(key=lambda value: (level_order.get(value['hierarchy_level_code'],9),(value['cells'][latest_index]['hierarchy_rank'] if latest_index >= 0 and value['cells'][latest_index]['hierarchy_rank'] is not None else 10**9),value['sector_id']))
  total=len(items);start=(page-1)*size
  return {'publication_id':p,'snapshot_id':selected['snapshot_id'],'page':page,'page_size':size,'total':total,'days':days,'dates':dates,'metric':metric,'hierarchy_level_filter':level_filter or 'ALL','hierarchy_levels':sorted({item['hierarchy_level_code'] for item in items}),'as_of_trade_date':dates[-1] if dates else None,'items':items[start:start+size]}
 def sector_timeline(self,p,sector_id,days=30):
  days=max(1,min(250,int(days)));self._pub(p);bindings=self._analysis_bindings(p);selected=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected: raise ValueError('ANALYSIS_NOT_BUILT')
  with self._con() as c:
   rows=c.execute("with recent_dates as (select distinct e.trade_date from analysis_snapshot_entries e join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where e.snapshot_id=? and e.domain='sector_cycle' and c.sector_id=? order by e.trade_date desc limit ?) select c.trade_date,c.sector_id,c.sector_name,c.sector_type,c.board_quote_ret1,c.board_quote_source,c.member_ret1_median,c.member_ret5_median,c.member_ret20_median,c.member_amount_sum,c.amount_valid_count,c.total_member_count,c.quote_valid_count,c.factor_valid_count,c.coverage,c.breadth_ret1,c.breadth_ma20,c.sector_rs5,c.sector_rs20,c.sector_rs5_pct,c.sector_rs20_pct,c.amount_vs_prior20,c.rank,c.rank_change,c.window_stats from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='sector_cycle' and e.trade_date=d.trade_date join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where c.sector_id=? order by c.trade_date",[selected['snapshot_id'],sector_id,days,selected['snapshot_id'],sector_id]).fetchall()
  names=('trade_date','sector_id','sector_name','sector_type','board_quote_ret1','board_quote_source','member_ret1_median','member_ret5_median','member_ret20_median','member_amount_sum','amount_valid_count','total_member_count','quote_valid_count','factor_valid_count','coverage','breadth_ret1','breadth_ma20','sector_rs5','sector_rs20','sector_rs5_pct','sector_rs20_pct','amount_vs_prior20','rank','rank_change','window_stats');points=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['member_amount_sum']=float(item['member_amount_sum']) if item['member_amount_sum'] is not None else None;item['window_stats']=json.loads(item['window_stats']) if item['window_stats'] else {};points.append(item)
  if not points: return {'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'points':[],'status':'NOT_FOUND'}
  hierarchy_item=None;sector_type=points[-1]['sector_type'];page=1
  while hierarchy_item is None:
   matrix=self.sector_cycle(p,page=page,size=MAX_PAGE_SIZE,sector_type=sector_type,days=min(days,30),hierarchy_level='ALL')
   hierarchy_item=next((item for item in matrix['items'] if item['sector_id']==sector_id),None)
   if hierarchy_item is not None or page*MAX_PAGE_SIZE>=matrix['total']:break
   page+=1
  rank_by_date={cell['trade_date']:cell.get('hierarchy_rank') for cell in hierarchy_item['cells']} if hierarchy_item else {}
  pct_by_date={cell['trade_date']:cell.get('hierarchy_sector_rs20_pct') for cell in hierarchy_item['cells']} if hierarchy_item else {}
  for point in points:
   point['hierarchy_rank']=rank_by_date.get(point['trade_date']);point['hierarchy_sector_rs20_pct']=pct_by_date.get(point['trade_date'])
  result={'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'sector_name':points[-1]['sector_name'],'sector_type':points[-1]['sector_type'],'history_basis':selected['domain'].removeprefix('LOCAL_'),'points':points}
  if hierarchy_item:
   result.update({'hierarchy_level':hierarchy_item['hierarchy_level'],'hierarchy_level_code':hierarchy_item['hierarchy_level_code'],'parent_sector_id':hierarchy_item['parent_sector_id'],'parent_sector_name':hierarchy_item['parent_sector_name'],'rank_scope':hierarchy_item['rank_scope']})
  return result
 def sector_members_history(self,p,sector_id,days=10,page=1,size=50,state='',security_id=''):
  allowed={'ALL','ADDED','REMOVED','RETAINED','ENTERED','EXITED','UNKNOWN','UNCHANGED'};state=str(state or 'ALL').upper()
  if state not in allowed: raise ValueError('MEMBER_HISTORY_STATE_UNSUPPORTED')
  days=max(1,min(30,int(days)));size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p);bindings=self._analysis_bindings(p);selected=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected: raise ValueError('ANALYSIS_NOT_BUILT')
  filters=['e.snapshot_id=?',"e.domain='member_state'",'s.sector_id=?'];args=[selected['snapshot_id'],sector_id]
  if security_id: filters.append('s.security_id=?');args.append(security_id)
  if state!='ALL': filters.append('s.member_change_kind=?');args.append(state)
  where=' and '.join(filters)
  query="with recent_dates as (select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='member_state' order by trade_date desc limit ?) select s.sector_id,s.security_id,s.trade_date,s.member_present,s.member_rank,s.rank_valid_count,s.member_percentile,s.strong_state,s.strong_predicates,s.structure_hit,s.high_hit,s.member_change_kind,s.strength_change_kind,s.previous_rank,s.rank_delta,s.queue_refs,s.high_refs,s.history_basis,s.contract_id from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='member_state' and e.trade_date=d.trade_date join sector_member_state_daily s on s.slice_id=e.slice_id and s.trade_date=e.trade_date where "+where+" order by s.trade_date desc,s.member_rank nulls last,s.security_id"
  with self._con() as c: rows=c.execute(query,[selected['snapshot_id'],days,selected['snapshot_id'],*args]).fetchall()
  names=('sector_id','security_id','trade_date','member_present','member_rank','rank_valid_count','member_percentile','strong_state','strong_predicates','structure_hit','high_hit','member_change_kind','strength_change_kind','previous_rank','rank_delta','queue_refs','high_refs','history_basis','contract_id');items=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['member_rank']=_finite_or_none(item['member_rank']);item['rank_valid_count']=_finite_or_none(item['rank_valid_count']);item['member_percentile']=_finite_or_none(item['member_percentile']);item['previous_rank']=_finite_or_none(item['previous_rank']);item['rank_delta']=_finite_or_none(item['rank_delta']);item['strong_predicates']=json.loads(item['strong_predicates']) if item['strong_predicates'] else {};item['queue_refs']=json.loads(item['queue_refs']) if item['queue_refs'] else [];item['high_refs']=json.loads(item['high_refs']) if item['high_refs'] else [];items.append(item)
  security_names=self._security_names(p,{item['security_id'] for item in items if item.get('security_id')})
  for item in items:item['security_name']=security_names.get(item.get('security_id'))
  total=len(items);return {'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'page':page,'page_size':size,'days':days,'state':state,'total':total,'items':items[(page-1)*size:page*size]}
 def sector_leader_history(self,p,sector_id,days=30):
  days=max(1,min(250,int(days)));self._pub(p);bindings=self._analysis_bindings(p);selected=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected: raise ValueError('ANALYSIS_NOT_BUILT')
  with self._con() as c:
   rows=c.execute("with recent_dates as (select distinct e.trade_date from analysis_snapshot_entries e join representative_state_daily r on r.slice_id=e.slice_id and r.trade_date=e.trade_date where e.snapshot_id=? and e.domain='representative' and r.sector_id=? order by e.trade_date desc limit ?) select r.sector_id,r.trade_date,r.ranked_first_id,r.ranked_second_id,r.rank_gap,r.confirmed_id,r.candidate_id,r.candidate_since,r.candidate_streak,r.confirmed_since,r.confirmation_event,r.previous_confirmed_id,r.stale,r.representative_rank_basis,r.history_basis,r.contract_id from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='representative' and e.trade_date=d.trade_date join representative_state_daily r on r.slice_id=e.slice_id and r.trade_date=e.trade_date where r.sector_id=? order by r.trade_date",[selected['snapshot_id'],sector_id,days,selected['snapshot_id'],sector_id]).fetchall()
  names=('sector_id','trade_date','ranked_first_id','ranked_second_id','rank_gap','confirmed_id','candidate_id','candidate_since','candidate_streak','confirmed_since','confirmation_event','previous_confirmed_id','stale','representative_rank_basis','history_basis','contract_id');points=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['candidate_since']=str(item['candidate_since']) if item['candidate_since'] else None;item['confirmed_since']=str(item['confirmed_since']) if item['confirmed_since'] else None;points.append(item)
  security_ids={item.get(key) for item in points for key in ('ranked_first_id','ranked_second_id','confirmed_id','candidate_id','previous_confirmed_id') if item.get(key)};security_names=self._security_names(p,security_ids)
  for item in points:
   for key in ('ranked_first_id','ranked_second_id','confirmed_id','candidate_id','previous_confirmed_id'):item[key.replace('_id','_name')]=security_names.get(item.get(key))
  return {'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'days':days,'points':points,'status':'AVAILABLE' if points else 'NOT_FOUND'}
 def _analysis_capabilities(self,p):
  with self._con() as c:
   counts={table:c.execute(f'select count(*) from {table} where publication_id=?',[p]).fetchone()[0] for table in ('stock_daily','sector_daily','queue_memberships')}
  bindings=self._analysis_bindings(p)
  return {
   'overview':'AVAILABLE' if counts['stock_daily'] else 'UNAVAILABLE',
   'universe':'AVAILABLE' if counts['stock_daily'] else 'UNAVAILABLE',
   'sector':'AVAILABLE' if counts['sector_daily'] else 'UNAVAILABLE',
   'structure':'AVAILABLE' if counts['queue_memberships'] else 'UNAVAILABLE',
   'history_analysis':'AVAILABLE' if bindings else 'NOT_BUILT',
  }
 def _analysis_bindings(self,p):
  with self._con() as c:
   rows=c.execute('''select b.domain,b.snapshot_id,cast(s.cutoff_date as varchar),cast(s.query_start as varchar),s.manifest_hash
      from publication_analysis_snapshots b join analysis_snapshots s using(snapshot_id)
     where b.publication_id=? and s.status='SUCCESS' order by case b.domain when 'LOCAL_OBSERVED' then 0 else 1 end''',[p]).fetchall()
  return {row[0]:{'domain':row[0],'snapshot_id':row[1],'cutoff_date':row[2],'query_start':row[3],'manifest_hash':row[4]} for row in rows}
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
  manifests=[]
  for manifest_path in sorted((self._root/'reports/upgrade_m7').glob(f"source_manifest_{trade_date.replace('-','')}*.json")):
   try:
    candidate=json.loads(manifest_path.read_text('utf-8'));validate_source_manifest(candidate)
   except (OSError,json.JSONDecodeError,SourceFreezeError):continue
   if candidate.get('publication_id')==p and candidate.get('cutoff_date')==trade_date and (not identity.get('source_identity_sha256') or candidate.get('source_identity_sha256')==identity.get('source_identity_sha256')):manifests.append(candidate)
  if manifests:
   manifest=manifests[-1]
   source=next((item for item in manifest.get('inputs',[]) if item.get('role')=='normalized_raw_price' and item.get('kind')=='file'),None)
   if source:
    relative=Path(str(source.get('path','')))
    source_path=(self._root/relative).resolve()
    if not relative.is_absolute() and self._root in source_path.parents and source_path.is_file():
     self._source_cache[p]=(source_path,manifest)
     return QuoteService(source_path).load(trade_date=current,publication_id=p,source_identity_sha256=identity.get('source_identity_sha256'),expected_file_sha256=source['sha256'],source_path=relative.as_posix())
  # M4 publications are backed by a verified source bundle, but do not have
  # an M7 history manifest yet.  The controlled compute uses the same local
  # normalized parquet; bind it only when the publication explicitly points
  # at a source bundle whose cutoff matches the selected publication.  This
  # restores V1 quote fields without weakening the older manifest/hash path.
  with self._con() as c:
   row=c.execute("select production_version,source_manifest_sha256 from publications where publication_id=?",[p]).fetchone()
  if not row or not str(row[0] or '').startswith('m4-'):return {}
  bundle_id=str(row[1] or '')
  bundle_path=self._root/'data/source_bundles'/bundle_id/'source_bundle.json'
  if not bundle_path.is_file():return {}
  try: bundle=json.loads(bundle_path.read_text('utf-8'))
  except (OSError,json.JSONDecodeError):return {}
  if str(bundle.get('target_trade_date',''))!=trade_date:return {}
  source_path=self._root/'data/normalized/adjusted_daily.parquet'
  if not source_path.is_file():return {}
  source_path=source_path.resolve()
  try:
   with duckdb.connect() as parquet_con:
    normalized_latest=parquet_con.execute('select max(date) from read_parquet(?)',[str(source_path)]).fetchone()[0]
  except Exception:return {}
  if normalized_latest!=current:return {}
  manifest={'contract':'m4-normalized-quote-binding-v1','source_bundle_id':bundle_id,'source_path':'data/normalized/adjusted_daily.parquet','source_identity_sha256':identity.get('source_identity_sha256')}
  self._source_cache[p]=(source_path,manifest)
  return QuoteService(source_path).load(trade_date=current,publication_id=p,source_identity_sha256=identity.get('source_identity_sha256'),source_path='data/normalized/adjusted_daily.parquet')
 def _add_quotes(self,p,result):
  quotes=self._quotes(p)
  trade_date,_=self._pub(p)
  source_identity=self.identity(p).get('source_identity_sha256')
  for item in result['items']:
   security_id=item.get('security_id')
   item.update(quotes.get(security_id,{'quote_contract_id':'workbench-quote-v2.1','security_id':security_id,'quote_date':trade_date,'raw_close':None,'latest_price':None,'quote_prev_close':None,'quote_ret1':None,'RET1':None,'raw_amount':None,'turnover_amount':None,'quote_ret1_basis':'UNAVAILABLE','quote_state':'SOURCE_NOT_FROZEN','publication_id':p,'source_ref':None,'source_identity_sha256':source_identity}))
  return result
 def _security_names(self,p,security_ids):
  ids=sorted({str(value) for value in security_ids if value})
  if not ids:return {}
  placeholders=','.join('?' for _ in ids)
  with self._con() as c:rows=c.execute(f'select security_id,payload_json from stock_daily where publication_id=? and security_id in ({placeholders})',[p,*ids]).fetchall()
  result={}
  for security_id,payload in rows:
   try:data=json.loads(payload) if payload else {}
   except json.JSONDecodeError:data={}
   result[security_id]=data.get('security_name') or data.get('name') or security_id
  return result
 def _add_stock_payloads(self,p,result):
  security_ids=sorted({item.get('security_id') for item in result['items'] if item.get('security_id')})
  if not security_ids:return result
  placeholders=','.join('?' for _ in security_ids)
  with self._con() as c:rows=c.execute(f'select security_id,payload_json from stock_daily where publication_id=? and security_id in ({placeholders})',[p,*security_ids]).fetchall()
  payloads={security_id:json.loads(payload) for security_id,payload in rows if payload}
  for item in result['items']:
   merged={**payloads.get(item.get('security_id'),{}),**item};item.clear();item.update(merged)
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
   grouped={sid:{'members':[],'quotes':[]} for sid in ids}
   for sid,security_id in members:
    if is_a_share_security_id(security_id):
     grouped[sid]['members'].append(security_id)
     if security_id in quotes: grouped[sid]['quotes'].append(quotes[security_id])
   for item in result['items']:
    group=grouped[item['sector_id']];values=group['quotes'];returns=sorted(x['RET1'] for x in values if x.get('RET1') is not None)
    item['sector_ret1_median']=returns[len(returns)//2] if len(returns)%2 else (returns[len(returns)//2-1]+returns[len(returns)//2])/2 if returns else None
    item['sector_turnover_amount']=sum(x['turnover_amount'] for x in values if x.get('turnover_amount') is not None)
    item['total_member_count']=len(group['members'])
    item['quote_valid_count']=len(values)
  return result
 def stocks(self,p,q,page,size): return self._add_quotes(p,self._rows('stock_daily',p,'and '+A_SHARE_SQL.format(id='security_id')+' and (security_name ilike ? or security_id ilike ?)',(f'%{q}%',f'%{q}%'),'security_id',page,size))
 def technical(self,p,page=1,size=50,basis='AUTO',ma_state='',rps_window='',rps_min='',amount_class_filter='',turnover_min='',quality_filter='',research_band=''):
  if basis not in ('AUTO','OBSERVED','RECONSTRUCTED'): raise ValueError('BASIS_UNSUPPORTED')
  if quality_filter not in ('','INCLUDE_UNKNOWN'): raise ValueError('QUALITY_FILTER_UNSUPPORTED')
  research_band=str(research_band or '').strip().upper()
  if research_band not in ('','CORE_RESEARCH','SUPPORTED_RESEARCH','DIAGNOSTIC_ONLY'): raise ValueError('RESEARCH_BAND_UNSUPPORTED')
  bindings=self._analysis_bindings(p);requested={'OBSERVED':'LOCAL_OBSERVED','RECONSTRUCTED':'LOCAL_RECONSTRUCTED'}.get(basis)
  selected=bindings.get(requested) if requested else bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected: raise ValueError('ANALYSIS_NOT_BUILT')
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page))
  if turnover_min not in ('',None): raise ValueError('TURNOVER_NOT_BUILT')
  rps_window_value=str(rps_window or '').strip();rps_width=None
  if rps_window_value:
   try:rps_width=int(rps_window_value)
   except (TypeError,ValueError):raise ValueError('RPS_WINDOW_UNSUPPORTED')
   if rps_width not in (5,10,20,60):raise ValueError('RPS_WINDOW_UNSUPPORTED')
  elif rps_min not in ('',None):rps_width=20
  rps_value=None
  if rps_min not in ('',None):
   try:rps_value=float(rps_min)
   except (TypeError,ValueError):raise ValueError('RPS_THRESHOLD_UNSUPPORTED')
   if not math.isfinite(rps_value):raise ValueError('RPS_THRESHOLD_UNSUPPORTED')
  if rps_width is not None:
   with self._con() as check:
    if not check.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='strength'",[selected['snapshot_id']]).fetchone()[0]:raise ValueError('RPS_NOT_BUILT')
  joins=" left join analysis_snapshot_entries se on se.snapshot_id=e.snapshot_id and se.domain='strength' and se.trade_date=e.trade_date left join stock_strength_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=t.security_id left join analysis_snapshot_entries ue on ue.snapshot_id=e.snapshot_id and ue.domain='summary' and ue.trade_date=e.trade_date left join stock_structure_summary_daily ss on ss.slice_id=ue.slice_id and ss.trade_date=ue.trade_date and ss.security_id=t.security_id"
  include_unknown=quality_filter=='INCLUDE_UNKNOWN';filters=['e.snapshot_id=?',"e.trade_date=(select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='technical')"];params=[selected['snapshot_id'],selected['snapshot_id']]
  if ma_state:filters.append('(t.ma_alignment=?'+(' or t.ma_alignment is null)' if include_unknown else ')'));params.append(ma_state)
  if amount_class_filter:filters.append('(t.amount_class=?'+(' or t.amount_class is null)' if include_unknown else ')'));params.append(amount_class_filter)
  if rps_value is not None:filters.append(f'(st.rps{rps_width}>=?'+(f' or st.rps{rps_width} is null)' if include_unknown else ')'));params.append(rps_value)
  if research_band:filters.append("coalesce(ss.research_band,'DIAGNOSTIC_ONLY')=?");params.append(research_band)
  where=' and '.join(filters)
  select="t.security_id,t.trade_date,t.contract_id,t.price_basis,t.raw_close,t.adj_close,t.quote_ret1,t.raw_amount,t.raw_volume,t.ma5,t.ma10,t.ma20,t.ma60,t.ret5,t.ret10,t.ret20,t.ret60,t.rs5,t.rs10,t.rs20,t.rs60,t.amount_ma5,t.amount_ma10,t.amount_ma20,t.amount_ratio20,t.amount_vs_prior20,t.volume_vs_prior20,t.amount_class,t.ma_alignment,t.validity,t.quality_codes,t.basis_json,st.rps5,st.rps10,st.rps20,st.rps60,st.rps_valid_universe_count5,st.rps_valid_universe_count10,st.rps_valid_universe_count20,st.rps_valid_universe_count60,coalesce(ss.research_band,'DIAGNOSTIC_ONLY'),coalesce(ss.research_band_quality,'DATA_INSUFFICIENT')"
  with self._con() as c:
   total=c.execute("select count(*) from analysis_snapshot_entries e join stock_technical_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date"+joins+" where e.domain='technical' and "+where,params).fetchone()[0]
   rows=c.execute("select "+select+" from analysis_snapshot_entries e join stock_technical_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date"+joins+" where e.domain='technical' and "+where+" order by st.rps20 desc nulls last,t.ret20 desc nulls last,t.security_id limit ? offset ?",params+[size,(page-1)*size]).fetchall()
  names=('security_id','trade_date','contract_id','price_basis','raw_close','adj_close','quote_ret1','raw_amount','raw_volume','ma5','ma10','ma20','ma60','ret5','ret10','ret20','ret60','rs5','rs10','rs20','rs60','amount_ma5','amount_ma10','amount_ma20','amount_ratio20','amount_vs_prior20','volume_vs_prior20','amount_class','ma_alignment','validity','quality_codes','basis','rps5','rps10','rps20','rps60','rps_valid_universe_count5','rps_valid_universe_count10','rps_valid_universe_count20','rps_valid_universe_count60','research_band','research_band_quality')
  items=[]
  for row in rows:
   item=dict(zip(names,row));item['trade_date']=str(item['trade_date']);item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];item['basis']=json.loads(item['basis']) if item['basis'] else {};items.append(item)
  result={'publication_id':p,'page':page,'page_size':size,'total':total,'basis':basis,'rps_window':rps_width,'as_of_trade_date':str(max(item['trade_date'] for item in items)) if items else None,'snapshot_id':selected['snapshot_id'],'snapshot_capability':'AVAILABLE','items':items}
  security_names=self._security_names(p,{item['security_id'] for item in items if item.get('security_id')})
  for item in items:item['security_name']=security_names.get(item.get('security_id'))
  return self._add_quotes(p,result)
 def new_highs(self,p,page=1,size=50,basis='AUTO',window=20,streak_min='',include_ties=False,rps_min='',research_band=''):
  if basis not in ('AUTO','OBSERVED','RECONSTRUCTED'): raise ValueError('BASIS_UNSUPPORTED')
  research_band=str(research_band or '').strip().upper()
  if research_band not in ('','CORE_RESEARCH','SUPPORTED_RESEARCH','DIAGNOSTIC_ONLY'): raise ValueError('RESEARCH_BAND_UNSUPPORTED')
  try: window=int(window)
  except (TypeError,ValueError): raise ValueError('WINDOW_UNSUPPORTED')
  if window not in (20,30,60,100): raise ValueError('WINDOW_UNSUPPORTED')
  bindings=self._analysis_bindings(p);requested={'OBSERVED':'LOCAL_OBSERVED','RECONSTRUCTED':'LOCAL_RECONSTRUCTED'}.get(basis)
  selected=bindings.get(requested) if requested else bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected: raise ValueError('ANALYSIS_NOT_BUILT')
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));filters=["he.snapshot_id=?","he.domain='high'",'h."window"=?',"he.trade_date=(select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='high')"];params=[selected['snapshot_id'],window,selected['snapshot_id']]
  if not include_ties: filters.append('h.new_high=true')
  if streak_min not in ('',None): filters.append('h.streak>=?');params.append(int(streak_min))
  if rps_min not in ('',None):
   rps_value=float(rps_min)
   with self._con() as check:
    if not check.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='strength'",[selected['snapshot_id']]).fetchone()[0]: raise ValueError('RPS_NOT_BUILT')
   filters.append('st.rps20>=?');params.append(rps_value)
  if research_band:filters.append("coalesce(ss.research_band,'DIAGNOSTIC_ONLY')=?");params.append(research_band)
  where=' and '.join(filters)
  summary_joins=" left join analysis_snapshot_entries ue on ue.snapshot_id=he.snapshot_id and ue.domain='summary' and ue.trade_date=he.trade_date left join stock_structure_summary_daily ss on ss.slice_id=ue.slice_id and ss.trade_date=ue.trade_date and ss.security_id=h.security_id"
  with self._con() as c:
   available=c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='high'",[selected['snapshot_id']]).fetchone()[0]
   if not available: raise ValueError('ANALYSIS_NOT_BUILT')
   total=c.execute('select count(*) from analysis_snapshot_entries he join stock_high_daily h on h.slice_id=he.slice_id and h.trade_date=he.trade_date left join analysis_snapshot_entries se on se.snapshot_id=he.snapshot_id and se.domain=\'strength\' and se.trade_date=he.trade_date left join stock_strength_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=h.security_id'+summary_joins+' where '+where,params).fetchone()[0]
   rows=c.execute('select h.security_id,h.trade_date,h."window",h.contract_id,h.price_basis,h.prior_max_close,h.new_high,h.at_prior_high,h.streak,h.is_left_censored,h.dist_prior_high,h.valid_n,h.quality_codes,h.basis_json,st.rps5,st.rps10,st.rps20,st.rps60,st.rps_valid_universe_count5,st.rps_valid_universe_count10,st.rps_valid_universe_count20,st.rps_valid_universe_count60,st.quality_codes,st.basis_json,coalesce(ss.research_band,\'DIAGNOSTIC_ONLY\'),coalesce(ss.research_band_quality,\'DATA_INSUFFICIENT\') from analysis_snapshot_entries he join stock_high_daily h on h.slice_id=he.slice_id and h.trade_date=he.trade_date left join analysis_snapshot_entries se on se.snapshot_id=he.snapshot_id and se.domain=\'strength\' and se.trade_date=he.trade_date left join stock_strength_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=h.security_id'+summary_joins+' where '+where+' order by h.streak desc nulls last,st.rps20 desc nulls last,h.security_id limit ? offset ?',params+[size,(page-1)*size]).fetchall()
  names=('security_id','trade_date','window','contract_id','price_basis','prior_max_close','new_high','at_prior_high','streak','is_left_censored','dist_prior_high','valid_n','quality_codes','basis','rps5','rps10','rps20','rps60','rps_valid_universe_count5','rps_valid_universe_count10','rps_valid_universe_count20','rps_valid_universe_count60','strength_quality_codes','strength_basis','research_band','research_band_quality')
  items=[]
  for row in rows:
   item=dict(zip(names,row));item['trade_date']=str(item['trade_date']);item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];item['basis']=json.loads(item['basis']) if item['basis'] else {};item['strength_quality_codes']=json.loads(item['strength_quality_codes']) if item['strength_quality_codes'] else [];item['strength_basis']=json.loads(item['strength_basis']) if item['strength_basis'] else {};items.append(item)
  result={'publication_id':p,'page':page,'page_size':size,'total':total,'basis':basis,'window':window,'as_of_trade_date':str(max(item['trade_date'] for item in items)) if items else None,'snapshot_id':selected['snapshot_id'],'snapshot_capability':'AVAILABLE','items':items}
  return self._add_quotes(p,self._add_stock_payloads(p,result))
 def technical_history(self,p,security_id,days=20,price_basis='ADJUSTED',fields=''):
  if price_basis not in ('RAW','ADJUSTED','TDX_NATIVE_QFQ'): raise ValueError('PRICE_BASIS_UNSUPPORTED')
  bindings=self._analysis_bindings(p);selected=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected: raise ValueError('ANALYSIS_NOT_BUILT')
  days=int(days);requested=tuple(x for x in str(fields).split(',') if x) if fields else ('ohlc','ma','amount','rps')
  key=chart_cache_key(selected['snapshot_id'],security_id,price_basis,selected['cutoff_date'],days,requested)
  cached=self._chart_cache.get(key)
  if cached is not None: return cached
  self._quotes(p)
  source_info=self._source_cache.get(p)
  if not source_info:
   with self._con() as check:
    reconstructed=check.execute("select 1 from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'",[p]).fetchone()
   fallback=self._root/'data/normalized/adjusted_daily.parquet'
   if reconstructed and fallback.is_file(): source_info=(fallback,{'preview':True});self._source_cache[p]=source_info
  if not source_info: raise ValueError('SOURCE_NOT_FROZEN')
  source_path,_=source_info;cutoff=date.fromisoformat(selected['cutoff_date'])
  with duckdb.connect() as source:
   frame=source.execute('select date,raw_open,raw_high,raw_low,raw_close,adj_open,adj_high,adj_low,adj_close,raw_volume,raw_amount from read_parquet(?) where security_id=? and date<=? order by date',[str(source_path),security_id,cutoff]).df()
   expected=[row[0] for row in source.execute('select distinct date from read_parquet(?) where is_master_session and date<=? order by date',[str(source_path),cutoff]).fetchall()]
  rps={}
  with self._con() as c:
   rows=c.execute("""select s.trade_date,s.rps20 from analysis_snapshot_entries e join stock_strength_daily s on s.slice_id=e.slice_id and s.trade_date=e.trade_date and s.security_id=? where e.snapshot_id=? and e.domain='strength'""",[security_id,selected['snapshot_id']]).fetchall()
  rps={row[0]:row[1] for row in rows}
  result=build_chart_points(frame,cutoff=cutoff,days=days,price_basis=price_basis,fields=requested,expected_dates=expected,rps_by_date=rps)
  result.update({'publication_id':p,'security_id':security_id,'snapshot_id':selected['snapshot_id'],'factor_evidence_basis':{'snapshot_id':selected['snapshot_id'],'rps_available':bool(rps)},'rps_capability':'AVAILABLE' if rps else 'NOT_BUILT'})
  self._chart_cache.put(key,result)
  return result
 def structure_history(self,p,security_id,days=20,queue=''):
  bindings=self._analysis_bindings(p);selected=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected:raise ValueError('ANALYSIS_NOT_BUILT')
  days=int(days)
  if not 1<=days<=250:raise ValueError('STRUCTURE_DAYS_OUT_OF_RANGE')
  canonical=str(queue).removesuffix('_QUEUE').upper()+'_QUEUE' if queue else ''
  if canonical and canonical not in ('STEADY_QUEUE','PULLBACK_QUEUE','BREAKOUT_QUEUE','LEADER_QUEUE','EARLY_QUEUE'):raise ValueError('QUEUE_UNSUPPORTED')
  params=[selected['snapshot_id'],security_id,days]
  queue_filter=''
  if canonical:queue_filter=' and h.queue_name=?';params.append(canonical)
  with self._con() as c:
   available=c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='structure'",[selected['snapshot_id']]).fetchone()[0]
   if not available:raise ValueError('ANALYSIS_NOT_BUILT')
   rows=c.execute("with recent_dates as (select distinct e.trade_date from analysis_snapshot_entries e join historical_structure_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date where e.snapshot_id=? and e.domain='structure' and h.security_id=? order by e.trade_date desc limit ?) select h.trade_date,h.queue_name,h.hit,h.tier,h.source_class,h.research_band,h.queue_rank,h.tier_rank,h.transition,h.structure_basis,h.contract_id,h.evidence,h.quality_codes from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='structure' and e.trade_date=d.trade_date join historical_structure_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date where h.security_id=?"+queue_filter+" order by h.trade_date,h.queue_name",params[:3]+[selected['snapshot_id'],security_id]+params[3:]).fetchall()
  names=('trade_date','queue_name','hit','tier','source_class','research_band','queue_rank','tier_rank','transition','source_basis','contract_id','evidence','quality_codes');points=[]
  for row in rows:
   item=dict(zip(names,row));item['trade_date']=str(item['trade_date']);item['evidence']=json.loads(item['evidence']) if item['evidence'] else {};item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];points.append(item)
  return {'publication_id':p,'security_id':security_id,'snapshot_id':selected['snapshot_id'],'history_basis':selected['domain'].removeprefix('LOCAL_'),'window_left_censored':len({item['trade_date'] for item in points})<days,'points':points}
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
 def queues(self,p,name,page,size,q='',band='',include_analysis=False):
  if include_analysis:return self._analysis_queues(p,name,page,size,q,band)
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
 def _analysis_queues(self,p,name,page,size,q='',band=''):
  canonical=str(name).removesuffix('_QUEUE').upper()+'_QUEUE'
  if canonical not in ('STEADY_QUEUE','PULLBACK_QUEUE','BREAKOUT_QUEUE','LEADER_QUEUE','EARLY_QUEUE'):raise ValueError('QUEUE_UNSUPPORTED')
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p)
  bindings=self._analysis_bindings(p);selected=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
  if not selected:raise ValueError('ANALYSIS_NOT_BUILT')
  with self._con() as c:latest=c.execute("select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='structure'",[selected['snapshot_id']]).fetchone()[0]
  if latest is None:raise ValueError('ANALYSIS_NOT_BUILT')
  filters=["e.snapshot_id=?","e.domain='structure'","e.trade_date=?","h.queue_name=?","h.hit=true","h.tier in ('CORE','SUPPORTED')"];where_params=[selected['snapshot_id'],latest,canonical]
  if q:filters.append("(h.security_id ilike ? or json_extract_string(sd.payload_json,'$.security_name') ilike ?)");where_params.extend([f'%{q}%',f'%{q}%'])
  bands=[value for value in str(band).split(',') if value]
  if bands:filters.append('h.research_band in ('+','.join('?' for _ in bands)+')');where_params.extend(bands)
  where=' and '.join(filters);joins=" from analysis_snapshot_entries e join historical_structure_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date left join stock_daily sd on sd.publication_id=? and sd.security_id=h.security_id left join analysis_snapshot_entries te on te.snapshot_id=e.snapshot_id and te.domain='technical' and te.trade_date=e.trade_date left join stock_technical_daily t on t.slice_id=te.slice_id and t.trade_date=te.trade_date and t.security_id=h.security_id left join analysis_snapshot_entries se on se.snapshot_id=e.snapshot_id and se.domain='strength' and se.trade_date=e.trade_date left join stock_strength_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=h.security_id"
  params=[p,*where_params]
  with self._con() as c:
   total=c.execute('select count(*)'+joins+' where '+where,params).fetchone()[0]
   rows=c.execute('select h.security_id,h.trade_date,h.queue_name,h.hit,h.tier,h.source_class,h.research_band,h.queue_rank,h.tier_rank,h.transition,h.structure_basis,h.contract_id,h.evidence,h.quality_codes,t.ret20,st.rps20,t.ma_alignment,t.amount_class,sd.payload_json'+joins+' where '+where+' order by h.queue_rank nulls last,h.security_id limit ? offset ?',params+[size,(page-1)*size]).fetchall()
  names=('security_id','trade_date','queue_name','hit','tier','source_class','research_band','queue_rank','tier_rank','transition','source_basis','contract_id','evidence','quality_codes','ret20','rps20','ma_alignment','amount_class','stock_payload');items=[]
  for index,row in enumerate(rows):
   item=dict(zip(names,row));payload=json.loads(item.pop('stock_payload')) if item.get('stock_payload') else {};item={**payload,**item};item['trade_date']=str(item['trade_date']);item['evidence']=json.loads(item['evidence']) if item['evidence'] else {};item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];item['filtered_row_number']=(page-1)*size+index+1;items.append(item)
  result={'publication_id':p,'snapshot_id':selected['snapshot_id'],'trade_date':str(latest),'page':page,'page_size':size,'total':total,'items':items}
  return self._add_quotes(p,result)
 def evidence(self,p,queue,security,format=''):
  # The UI uses stable lowercase route keys while the publication contract
  # stores queue names in uppercase.  Normalize both forms before lookup.
  detail=str(queue).removesuffix('_QUEUE').upper(); canonical=detail+'_QUEUE'
  if format!='groups':
   with self._con() as c: row=c.execute('select payload_json from structure_details where publication_id=? and queue_name=? and security_id=?',[p,detail,security]).fetchone()
   return {'publication_id':p,'item':json.loads(row[0]) if row else None}
  history=self.structure_history(p,security,20,canonical)
  if not history['points']:return {'publication_id':p,'item':None,'status':'NOT_FOUND'}
  latest=history['points'][-1]
  return {'publication_id':p,'item':{'summary':{'security_id':security,'queue_name':canonical,'trade_date':latest['trade_date'],'hit':latest['hit'],'tier':latest['tier'],'source_basis':latest['source_basis']},'groups':[{'group_id':'historical_structure','label':'历史结构证据','items':history['points']}],'contracts':[latest['contract_id']]},'status':'AVAILABLE'}
 def identity(self,p,include_analysis=False):
  d,rev=self._pub(p)
  with self._con() as c:
   x=c.execute('select source_manifest_sha256,source_identity_sha256,computation_identity_sha256,render_identity_sha256,revision,production_version from publications where publication_id=?',[p]).fetchone()
   membership=c.execute('select membership_snapshot_id from publication_memberships where publication_id=?',[p]).fetchone()
  result={'publication_id':p,'trade_date':d,'source_revision_id':rev,'source_manifest_sha256':x[0],'source_identity_sha256':x[1],'computation_identity_sha256':x[2],'render_identity_sha256':x[3],'membership_snapshot_id':membership[0] if membership else None,'api_contract':'m2-read-only-api-v1.2'}
  if include_analysis:
   bindings=self._analysis_bindings(p);preferred=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
   result.update({
    'api_contract':API_CONTRACT,
    'revision':x[4],
    'production_version':x[5],
    'cutoff_date':d,
    'analysis_snapshot_id':preferred['snapshot_id'] if preferred else None,
    'analysis_snapshots':bindings,
    'contracts':{'universe':'workbench-universe-v2.1','quote':'workbench-quote-v2.1','semantic':'workbench-semantic-v2.1','publication':'m4-one-click-publication-contract-v1.1'},
    'capabilities':self._analysis_capabilities(p),
    'data_quality':{'status':'AVAILABLE' if preferred else 'PARTIAL','codes':[] if preferred else ['HISTORY_ANALYSIS_NOT_BUILT'],'field_coverage':{}},
   })
  return result
 def field_catalog(self,api_contract=API_CONTRACT,language='zh-CN'):
  return field_catalog(api_contract,language)
 def _window_sessions(self):
  if self._window_sessions_cache is None:
   path=self._root/'data/normalized/adjusted_daily.parquet'
   with duckdb.connect() as c:
    sessions=c.execute('select distinct date from read_parquet(?) where is_master_session order by date',[str(path)]).fetchall()
    observed=c.execute('select distinct date from read_parquet(?) where is_master_session and data_observed order by date',[str(path)]).fetchall()
   self._window_sessions_cache=([row[0] for row in sessions],[row[0] for row in observed])
  return self._window_sessions_cache
 def history_coverage(self,p,days=MAX_OUTPUT_DAYS,basis='AUTO'):
  if basis not in ('AUTO','OBSERVED','RECONSTRUCTED'):
   raise ValueError('BASIS_UNSUPPORTED')
  cutoff_text,_=self._pub(p); cutoff=date.fromisoformat(cutoff_text)
  sessions,observed=self._window_sessions()
  result=plan_window(sessions,cutoff_date=cutoff,output_days=int(days),observed_sessions=observed,dependencies=self._window_dependencies)
  bindings=self._analysis_bindings(p)
  requested_domain={'OBSERVED':'LOCAL_OBSERVED','RECONSTRUCTED':'LOCAL_RECONSTRUCTED'}.get(basis)
  selected=(bindings.get(requested_domain) if requested_domain else bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED'))
  resolved=(selected['domain'].removeprefix('LOCAL_') if selected else ('OBSERVED' if basis=='AUTO' else basis))
  result.update({'api_contract':API_CONTRACT,'publication_id':p,'snapshot_id':selected['snapshot_id'] if selected else None,'snapshot_capability':'AVAILABLE' if selected else 'NOT_BUILT','requested_basis':basis,'resolved_basis':resolved,'analysis_capability':'AVAILABLE' if selected else 'NOT_BUILT'})
  return {'publication_id':p,'item':result}
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
 api=Api(db,root=root); history=HistoryJobService(root,db); history.recover_interrupted(background=True); activation=AnalysisActivationService(root,db); operations=OperationsConfig(root,db); storage=StorageGovernance(root,db); backups=BackupService(root,db); maintenance=MaintenanceService(root,db); static=Path(root)/'src/workbench_service/static';csrf=secrets.token_urlsafe(24);publishers={};daily_jobs={};daily_jobs_lock=threading.Lock()
 def today_status(job_id):
  task=daily_jobs.get(job_id)
  if not task: return None
  publisher=task.get('publisher')
  if publisher and task.get('phase')!='ANALYSIS_BINDING':
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
  task.update(publisher=publisher,publication_job_id=publication_job_id,status='RUNNING',progress={'status':'PUBLISHING'})
  published=publisher.wait(publication_job_id,timeout=3600)
  if published.get('status')!='SUCCESS':
   task.update(status='FAILED',progress={'status':'PUBLISH_FAILED','error':published.get('error') or published.get('details') or 'M4发布未完成'});return
  task.update(phase='ANALYSIS_BINDING',progress={'status':'ANALYSIS_BINDING'})
  preview=subprocess.run([sys.executable,str(Path(root)/'scripts/build_m8_m9_preview.py')],cwd=root,capture_output=True,text=True,timeout=3600)
  if preview.returncode:
   task.update(status='FAILED',progress={'status':'ANALYSIS_BINDING_FAILED','error':preview.stderr[-1000:] or preview.stdout[-1000:]});return
  task.update(phase='READY',status='SUCCESS',progress={'status':'READY','publication_id':published.get('publication_id')})
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
    if u.path=='/api/publications': out=api.publications(x.get('include_analysis')=='1')
    elif u.path=='/api/dashboard': out=api.dashboard(x['publication_id'])
    elif u.path=='/api/sectors': out=api.sectors(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50),x.get('type',''))
    elif u.path=='/api/sectors/cycle': out=api.sector_cycle(x['publication_id'],x.get('page',1),x.get('page_size',20),x.get('sector_type',x.get('type','')),x.get('q',''),x.get('days',10),x.get('metric','rank'),x.get('hierarchy_level',''))
    elif u.path.startswith('/api/sectors/') and u.path.endswith('/timeline'):
     sector_id=unquote(u.path[len('/api/sectors/'): -len('/timeline')].strip('/'));out=api.sector_timeline(x['publication_id'],sector_id,x.get('days',30))
    elif u.path.startswith('/api/sectors/') and u.path.endswith('/members/history'):
     sector_id=unquote(u.path[len('/api/sectors/'): -len('/members/history')].strip('/'));out=api.sector_members_history(x['publication_id'],sector_id,x.get('days',10),x.get('page',1),x.get('page_size',50),x.get('state','ALL'),x.get('security_id',''))
    elif u.path.startswith('/api/sectors/') and u.path.endswith('/leader-history'):
     sector_id=unquote(u.path[len('/api/sectors/'): -len('/leader-history')].strip('/'));out=api.sector_leader_history(x['publication_id'],sector_id,x.get('days',30))
    elif u.path=='/api/stocks': out=api.stocks(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50))
    elif u.path=='/api/stocks/technical': out=api.technical(x['publication_id'],x.get('page',1),x.get('page_size',50),x.get('basis','AUTO'),x.get('ma_state',''),x.get('rps_window',''),x.get('rps_min',''),x.get('amount_class',''),x.get('turnover_min',''),x.get('quality_filter',''),x.get('research_band',''))
    elif u.path=='/api/stocks/new-highs': out=api.new_highs(x['publication_id'],x.get('page',1),x.get('page_size',50),x.get('basis','AUTO'),x.get('window',20),x.get('streak_min',''),x.get('include_ties','0')=='1',x.get('rps_min',''),x.get('research_band',''))
    elif u.path.startswith('/api/stocks/') and u.path.endswith('/technical-history'):
     security_id=unquote(u.path[len('/api/stocks/'): -len('/technical-history')].strip('/'));out=api.technical_history(x['publication_id'],security_id,x.get('days',20),x.get('price_basis','ADJUSTED'),x.get('fields',''))
    elif u.path.startswith('/api/stocks/') and u.path.endswith('/structure-history'):
     security_id=unquote(u.path[len('/api/stocks/'): -len('/structure-history')].strip('/'));out=api.structure_history(x['publication_id'],security_id,x.get('days',20),x.get('queue',''))
    elif u.path=='/api/candidates': out=api.candidates(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50),x.get('grade',''),x.get('pattern',''))
    elif u.path=='/api/queues': out=api.queues(x['publication_id'],x.get('queue','STEADY'),x.get('page',1),x.get('page_size',50),x.get('q',''),x.get('band',''),x.get('include_analysis')=='1')
    elif u.path=='/api/evidence': out=api.evidence(x['publication_id'],x['queue'],x['security_id'],x.get('format',''))
    elif u.path=='/api/identity': out=api.identity(x['publication_id'],x.get('include_analysis')=='1')
    elif u.path=='/api/metadata/field-catalog': out=api.field_catalog(x.get('api_contract',API_CONTRACT),x.get('language','zh-CN'))
    elif u.path=='/api/history/coverage': out=api.history_coverage(x['publication_id'],x.get('days',MAX_OUTPUT_DAYS),x.get('basis','AUTO'))
    elif u.path.startswith('/api/history/jobs/'):
     job_id=unquote(u.path.split('/api/history/jobs/',1)[1]).strip('/')
     try: out=history.status(job_id)
     except HistoryJobError as e:
      if str(e)=='JOB_NOT_FOUND': return self._send(404,{'code':'JOB_NOT_FOUND','message':'任务不存在','retryable':False})
      raise
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
   except (KeyError,ValueError) as e:
    code=str(e).strip("'");status=409 if code in ('ANALYSIS_NOT_BUILT','BASIS_UNAVAILABLE','SOURCE_NOT_FROZEN') else 400
    self._send(status,{'code':code,'message':'请求参数或发布版本无效','retryable':False,'next_action':'重新选择日期'})
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
    if self.path=='/api/history/jobs':
     return self._send(202,history.submit(body))
    if self.path.startswith('/api/history/jobs/') and self.path.endswith('/activate'):
     job_id=unquote(self.path.split('/api/history/jobs/',1)[1][:-len('/activate')]).strip('/')
     return self._send(202,activation.activate(job_id,expected_head_id=str(body.get('expected_head_id') or ''),idempotency_key=str(body.get('idempotency_key') or '')))
    if self.path.startswith('/api/history/jobs/') and self.path.endswith('/cancel'):
     job_id=unquote(self.path.split('/api/history/jobs/',1)[1][:-len('/cancel')]).strip('/')
     return self._send(202,history.cancel(job_id,body.get('expected_attempt')))
    if self.path!='/api/jobs':return self._send(404,{'code':'NOT_FOUND','message':'接口不存在','retryable':False})
    with daily_jobs_lock:
     active=next((task for task in daily_jobs.values() if task.get('status') in ('QUEUED','RUNNING')),None)
     if active:return self._send(409,{'code':'DAILY_INPUT_ALREADY_RUNNING','message':'已有当日数据生成任务正在运行，请稍后查看任务状态','retryable':True})
     job_id='daily-'+uuid.uuid4().hex;daily_jobs[job_id]={'status':'QUEUED','progress':{'status':'INPUT_QUEUED'}}
    thread=threading.Thread(target=run_today,args=(job_id,body),daemon=True,name=job_id);thread.start()
    self._send(202,{'job_id':job_id,'status':'QUEUED','message':'已提交当日输入更新与发布任务'})
   except HistoryJobError as e:
     code=str(e);status=404 if code=='JOB_NOT_FOUND' else 409 if code in ('ATTEMPT_MISMATCH','JOB_NOT_CANCELLABLE','JOB_NOT_INTERRUPTED') else 400
     self._send(status,{'code':code,'message':'历史分析任务请求未通过','retryable':status in (409,500)})
   except AnalysisActivationError as e:
    code=str(e);status=404 if code=='JOB_NOT_FOUND' else 409 if code in ('EXPECTED_HEAD_MISMATCH','ACTIVATION_IDENTITY_CONFLICT','PUBLICATION_IDENTITY_CONFLICT','SNAPSHOT_IDENTITY_CONFLICT','SNAPSHOT_ENTRY_IDENTITY_CONFLICT','SNAPSHOT_ENTRY_SET_MISMATCH','PUBLICATION_SNAPSHOT_BINDING_CONFLICT') else 400
    self._send(status,{'code':code,'message':'历史分析快照激活未通过','retryable':status in (409,500)})
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
