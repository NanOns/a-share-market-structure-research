from __future__ import annotations
import hashlib, json, math, mimetypes, os, secrets, subprocess, sys, threading, time, uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import duckdb
from workbench_db import (
 ApiConnectionProvider, DuckDBApiConnectionProvider, PostgresDuckDBApiConnectionProvider,
 PostgresHistoryJobRepository, PostgresAnalysisActivationRepository, PostgresWriteRepository,
 PostgresConfigVersionStore, PostgresBackupCatalogRepository, PostgresOperationsMetadataReader,
)
from workbench_db.postgres_repository import PostgresRepository
from workbench_publish.orchestrator import submit_one_click, ControlledProduction
from workbench_publish import OneClickPublisher
from workbench_ops import OperationsConfig, ConfigConflict, ConfigValidationError
from workbench_ops import StorageGovernance, BackupService, MaintenanceService
from workbench_service.strength_association import choose_association
from workbench_service.universe import (
 A_SHARE_SQL,
 WORKBENCH_SCOPE_SQL,
 WORKBENCH_STATISTICAL_SCOPE_SQL,
 is_workbench_visible_security_id,
 is_workbench_statistical_security_id,
 summarize_universe,
 workbench_display_scope,
 workbench_statistical_scope,
)
from workbench_service.quotes import QuoteService
from workbench_service.online_hot_rank import build_hot_rank_direct_response
from workbench_online.eastmoney_quotes import fetch_eastmoney_quotes
from workbench_service.catalog import API_CONTRACT, field_catalog
from workbench_service.attribute_library import BUCKET_LABELS, build_source_metadata, membership_item, sector_attribute_item
from workbench_service.intersection import CONTRACT_ID as INTERSECTION_CONTRACT_ID, P10_CONTRACT_ID as P10_INTERSECTION_CONTRACT_ID, normalize_request, passes_filters, safe_value, sort_items
from workbench_service.association import CONTRACT_ID as ASSOCIATION_CONTRACT_ID
from workbench_service.window_planner import MAX_OUTPUT_DAYS, load_dependencies, plan_window
from workbench_service.history_jobs import HistoryJobError, HistoryJobService
from workbench_service.analysis_activation import AnalysisActivationError, AnalysisActivationService
from workbench_service.research_context import ResearchContextError, ResearchContextReader
from workbench_service.research_queries import ResearchQueryError, ResearchQueries
from workbench_service.research_builder import build_latest_research_run
from workbench_service.today_research_bundle import TodayResearchBundleReader
from workbench_service.turnover_enrichment_service import TurnoverEnrichmentService
from workbench_service.legacy_feature_matrix import build_legacy_matrix
from workbench_service.online_events import OnlineEventQueries
from workbench_service.p09_context import load_mapping, select_mappings, intersect_members
from workbench_online.p09_products import P09OnlineProducts, P09ProductError
from workbench_service.source_freezer import SourceFreezeError, validate_source_manifest
from workbench_service.membership_resolver import VersionedMembershipResolver
from workbench_analysis.chart import ChartCache, build_chart_points, chart_cache_key
from workbench_analysis.hierarchy import load_bound_nodes
from workbench_analysis.mainline import mainline_history_policy
from workbench_analysis.market_cycle import aggregate_market_point, group_queue_counts, group_sector_state_counts, CONTRACT_ID as MARKET_CYCLE_CONTRACT_ID
from workbench_analysis.limit_ladder import CONTRACT_VERSION as LIMIT_LADDER_CONTRACT_ID, canonical_limit_state
from workbench_analysis.limit_promotion import CONTRACT_VERSION as LIMIT_PROMOTION_CONTRACT_ID

MAX_PAGE_SIZE=100
OVERVIEW_CONTRACT_ID='M15_OVERVIEW_V1_0'
PRIORITY_RESEARCH_CONTRACT_ID='M15_PRIORITY_RESEARCH_V1_0'

def _json_default(value):
 # DuckDB returns DECIMAL columns as Decimal.  Keep numeric API fields numeric
 # instead of allowing one response to fail at the HTTP serialization layer.
 if isinstance(value, Decimal):
  return float(value) if value.is_finite() else None
 raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')

def _json_safe(value):
 if isinstance(value, date):
  return value.isoformat()
 if isinstance(value, Decimal):
  return float(value) if value.is_finite() else None
 if isinstance(value, float):
  return value if math.isfinite(value) else None
 if isinstance(value, dict):
  return {key: _json_safe(item) for key, item in value.items()}
 if isinstance(value, (list, tuple)):
  return [_json_safe(item) for item in value]
 return value

def _sector_code(sector_id):
 return str(sector_id).split(':',1)[-1]


def _p09_sector_online_context(root, research, p09, sector_id, params):
 topics=p09.topics(trade_date=params.get('trade_date'))
 context_id=params.get('context_id')
 local=research.sector_detail(context_id,sector_id) if context_id else {'status':'NOT_REQUESTED','sector_id':sector_id,'items':[]}
 mapping=load_mapping(Path(root))
 hashes=topics.get('source_hashes') or {}
 if mapping.get('source_ext03_sha256') != hashes.get('EXT03') or mapping.get('source_ext04_sha256') != hashes.get('EXT04'):
  mapping={**mapping,'entries':[],'status':'SOURCE_HASH_MISMATCH'}
 publication_id=(local.get('context') or {}).get('publication_id')
 mapped=select_mappings(mapping,publication_id=publication_id or '',sector_id=sector_id,topics=topics.get('items',[]),source_date=params.get('trade_date'),local_run_id=(local.get('context') or {}).get('run_id'),local_date=(local.get('context') or {}).get('local_date'))
 local_ids=set();complete=False
 if mapped and context_id:
  complete=True
  for page in range(1,21):
   members=research.sector_members(context_id,sector_id,role='ALL_MEMBERS',page=page,page_size=50)
   local_ids.update(str(item.get('security_id')) for item in members.get('items',[]) if item.get('security_id'))
   if not members.get('has_more'): break
  else: complete=False
 intersection=intersect_members(mapped,local_ids,local_complete=complete)
 previews=[{'source_topic_key':pair['mapping']['source_topic_key'],'relation':pair['mapping']['relation'],'evidence_id':pair['mapping']['evidence_id'],'topic_name':pair['topic'].get('topic_name'),'source_member_count':pair['topic'].get('unique_member_count')} for pair in mapped]
 return {'api_contract':'v3-p09-sector-online-context-v1.2','status':'AVAILABLE' if topics['status']=='AVAILABLE' and intersection['status']=='AVAILABLE' else 'DEGRADED' if topics['status']!='UNAVAILABLE' else 'UNAVAILABLE','sector_id':sector_id,'event_context':{'status':topics['status'],'mapping_status':intersection['status'],'mapped_topics':previews,'intersection':intersection,'available_source_topics':[{'source_topic_id':item.get('source_topic_id'),'topic_name':item.get('topic_name')} for item in topics.get('items',[])],'reason':mapping.get('status') if mapping.get('status')=='SOURCE_HASH_MISMATCH' else intersection['reason'],'source_trade_date':params.get('trade_date')},'local_context':local,'quote_context':{'status':'UNAVAILABLE','source_id':'EXT11','reason':'V3 §22 target chain retires EXT11; no unsupported quote URL is substituted.'},'mapping_policy':'EXACT_OR_RELATED_VERSIONED_MAPPING; RELATED_NOT_IN_LOCAL_WIDTH_DENOMINATOR','storage':topics.get('storage')}

def _mainline_group(items, hierarchy_nodes=None):
 # Mainline evidence uses the immutable hierarchy version bound to the
 # analysis snapshot. Unknown/internal types are deliberately excluded.
 hierarchy_nodes = hierarchy_nodes or {}
 for item in items:
  sector_type=str(item.get('sector_type') or '').upper();item['sector_type']=sector_type
  item['hierarchy_level_code']='FLAT';item['hierarchy_level']='平级板块';item['mainline_group']=sector_type
  node=hierarchy_nodes.get((sector_type,str(item.get('sector_id'))))
  if node:
   item['hierarchy_level_code']=node['hierarchy_level_code']
   item['hierarchy_level']='细分行业' if node['hierarchy_level_code']=='LEAF' else '一级行业' if node['hierarchy_level_code']=='ROOT' else '平级板块'
   item['parent_sector_id']=node.get('parent_sector_id')
   item['parent_sector_name']=node.get('parent_sector_name')
   item['mainline_group']=f"{sector_type}_{node['hierarchy_level_code']}" if sector_type=='INDUSTRY' else sector_type
 return items

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

def _annotate_sector_hierarchy(items,dates,hierarchy_nodes=None):
 # Parentage is read from the immutable hierarchy materialised from local TDX
 # data.  No name matching or prefix inference is performed at request time.
 hierarchy_nodes = hierarchy_nodes or {}
 for item in items:
  item['sector_code']=_sector_code(item['sector_id'])
  item['parent_sector_id']=None;item['parent_sector_name']=None
  node=hierarchy_nodes.get((str(item['sector_type']).upper(),str(item['sector_id'])))
  if node:
   item['parent_sector_id']=node.get('parent_sector_id');item['parent_sector_name']=node.get('parent_sector_name')
   item['hierarchy_level_code']=node.get('hierarchy_level_code') or 'FLAT'
   item['hierarchy_level']='细分行业' if item['hierarchy_level_code']=='LEAF' else '一级大板块' if item['hierarchy_level_code']=='ROOT' else '平级板块'
  else:
   item['hierarchy_level_code']='UNKNOWN';item['hierarchy_level']='层级未绑定'
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

def _json_value(value, fallback):
 if isinstance(value,(dict,list)): return value
 if value in (None,''): return fallback
 try: return json.loads(value)
 except (TypeError,ValueError,json.JSONDecodeError): return fallback

def _canonical_query(value):
 if isinstance(value,dict): return {str(key):_canonical_query(item) for key,item in sorted(value.items(),key=lambda pair:str(pair[0]))}
 if isinstance(value,list): return sorted((_canonical_query(item) for item in value),key=lambda item:json.dumps(item,ensure_ascii=False,sort_keys=True,default=str))
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
 # MIGRATION_CONTRACT: API still has legacy DuckDB route/query consumers; the
 # provider boundary is only the first slice until all routes use PG adapters.
 def __init__(self,db,root=None,*,connection_provider: ApiConnectionProvider | None = None): self.db=str(Path(db).resolve());self._root=Path(root).resolve() if root else Path(__file__).resolve().parents[2];self._connection_provider=connection_provider or DuckDBApiConnectionProvider(self.db);self._display_scope=workbench_display_scope(self._root);self._db_lock=threading.RLock();self._request_state=threading.local();self._quote_cache={};self._quote_full_cache=set();self._quote_lock=threading.Lock();self._quote_service_cache={};self._source_cache={};self._chart_cache=ChartCache();self._association_cache={};self._association_lock=threading.Lock();self._hierarchy_cache={};self._hierarchy_lock=threading.Lock();self._analysis_quality_cache={};self._insight_cache={};self._window_dependencies=load_dependencies(self._root);self._window_sessions_cache=None;self._research_contexts=ResearchContextReader(lambda: self._con())
 @contextmanager
 def request_scope(self):
  """Reuse one serialized read connection for one HTTP request only."""
  with self._db_lock:
   with self._connection_provider.connect() as connection:
    self._request_state.connection=connection
    try:
     yield
    finally:
     self._request_state.connection=None
 @contextmanager
 def _con(self):
  # DuckDB permits a normal connection to coexist with the publisher, but on
  # Windows concurrent normal connections can contend for the file lock.  API
  # handlers share one Api instance, so serialize only connection lifetimes;
  # this keeps concurrent page requests deterministic without changing the
  # publisher's read-during-write behavior.
  connection=getattr(self._request_state,'connection',None)
  if connection is not None:
   yield connection
   return
  with self._db_lock:
   with self._connection_provider.connect() as connection:
    yield connection
 def _publication_relation(self, connection, publication_id):
  return VersionedMembershipResolver(connection).publication_binding(publication_id)
 def _publication_edges(self, connection, publication_id):
  resolver=VersionedMembershipResolver(connection);binding=resolver.publication_binding(publication_id)
  if not binding:return binding,()
  return binding,resolver.edges_at(str(binding['source_scope']),int(binding['revision_no']))
 def _hierarchy_nodes(self,snapshot_id):
  if snapshot_id in self._hierarchy_cache:return self._hierarchy_cache[snapshot_id]
  with self._hierarchy_lock:
   if snapshot_id not in self._hierarchy_cache:
    try:
     with self._con() as c:self._hierarchy_cache[snapshot_id]=load_bound_nodes(c,snapshot_id)
    except Exception:
     self._hierarchy_cache[snapshot_id]={}
  return self._hierarchy_cache[snapshot_id]
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
 def hot_rankings(self,source='EASTMONEY_HOT_RANK',list_type=None,mode='LATEST',as_of=None,batch_id=None,page=1,page_size=50,co_listed=False):
  if str(mode).upper() != 'LATEST' or as_of or batch_id:
   raise ValueError('HOT_RANK_DIRECT_LATEST_ONLY')
  if list_type not in (None, '', 'A_STOCK_HOT_RANK', 'HOUR_NORMAL'):
   raise ValueError('HOT_RANK_LIST_TYPE_UNSUPPORTED')
  latest=self.publications().get('latest_publication_id')
  # P01-01 boundary: the network phase must run without request_scope().
  # Names are attached only after all remote source/quote calls complete, in
  # one short local read.  The handler routes this method outside the request
  # scope; publications() and _security_names() retain their own short locks.
  result=build_hot_rank_direct_response(root=self._root,source=source,page=int(page),page_size=int(page_size),co_listed=co_listed,name_lookup=None,quote_fetcher=fetch_eastmoney_quotes)
  views=result.get('source_views') or [result]
  items=[item for view in views for item in view.get('items',[]) if isinstance(item,dict)]
  security_ids={item.get('security_id') for item in items if item.get('security_id')}
  if latest and security_ids:
   names=self._security_names(latest,security_ids)
   for item in items:
    security_id=item.get('security_id')
    if security_id in names:
     item['security_name']=names[security_id]
     item['mapping_status']='MAPPED'
    elif not item.get('security_name'):
     item['mapping_status']='UNMAPPED'
  return result
 def sector_cycle(self,p,page=1,size=20,sector_type='',q='',days=10,metric='rank',hierarchy_level='',basis='AUTO',trade_date=None):
  if metric not in ('rank','sector_rs20_pct','breadth_ret1'): raise ValueError('SECTOR_CYCLE_METRIC_UNSUPPORTED')
  days=max(1,min(30,int(days)));size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p)
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('sector_cycle',));date_filter=" and trade_date<=?" if as_of else ''
  filters=['e.snapshot_id=?',"e.domain='sector_cycle'"];args=[selected['snapshot_id']]
  if sector_type: filters.append('c.sector_type=?');args.append(sector_type)
  if q: filters.append('(c.sector_id ilike ? or c.sector_name ilike ?)');args.extend([f'%{q}%',f'%{q}%'])
  where=' and '.join(filters)
  query="with recent_dates as (select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='sector_cycle'"+date_filter+" order by trade_date desc limit ?) select c.sector_id,c.trade_date,c.sector_name,c.sector_type,c.board_quote_ret1,c.board_quote_source,c.member_ret1_median,c.member_ret5_median,c.member_ret20_median,c.member_amount_sum,c.amount_valid_count,c.total_member_count,c.quote_valid_count,c.factor_valid_count,c.coverage,c.breadth_ret1,c.breadth_ret1_common,c.breadth_ret1_common_valid_count,c.breadth_ret1_common_change_1d,c.breadth_ret1_common_change_1d_valid_count,c.breadth_ret1_common_change_3d,c.breadth_ret1_common_change_3d_valid_count,c.strong_count,c.high20_count,c.high30_count,c.high60_count,c.high100_count,c.high20_valid_count,c.high30_valid_count,c.high40_valid_count,c.comparable_count,c.previous_strong_total,c.comparable_previous_strong,c.retained_count,c.entered_count,c.exited_count,c.uncomparable_count,c.retention_rate,c.comparison_coverage,c.diffusion_state,c.breadth_ma20,c.sector_rs5,c.sector_rs20,c.sector_rs5_pct,c.sector_rs20_pct,c.amount_vs_prior20,c.rank,c.rank_change,c.window_stats,c.member_amount_ratio_median_vs_prior20,c.sector_amount_vs_prior20,c.sector_amount_comparable_sum,c.sector_amount_prior20_mean,c.amount_comparable_member_count,c.amount_target_member_count,c.amount_comparable_coverage,c.amount_window_coverage,c.amount_window_target_member_max,c.amount_target_denominator_source,c.amount_window_denominator_source,c.amount_basis,c.amount_quality_codes,c.amount_excluded_member_ids,c.amount_member_set_hash,c.amount_membership_snapshot_id,c.amount_window_start,c.amount_window_end,c.amount_contract_id,c.sector_amount_ratio_delta_3sessions_common,c.amount_comparison_date,c.amount_comparison_current_a,c.amount_comparison_prior_a,c.amount_comparison_current_sum,c.amount_comparison_current_prior20_mean,c.amount_comparison_prior_sum,c.amount_comparison_prior_prior20_mean,c.amount_comparison_member_set_hash,c.amount_comparison_current_coverage,c.amount_comparison_prior_coverage,c.amount_comparison_window_coverage,c.amount_comparison_window_start,c.amount_comparison_window_end,c.amount_comparison_quality_codes,c.amount_comparison_excluded_member_ids,c.amount_comparison_evidence from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='sector_cycle' and e.trade_date=d.trade_date join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where "+where+" order by c.trade_date,c.rank nulls last,c.sector_id"
  query=query.replace(",c.high40_valid_count", ",c.high60_valid_count,c.high100_valid_count")
  with self._con() as c: rows=c.execute(query,[selected['snapshot_id'],*([as_of] if as_of else []),days,selected['snapshot_id'],*args]).fetchall()
  with self._con() as c:
   formal_rows=c.execute("select c.sector_id,cast(c.trade_date as varchar),c.member_amount_ratio_median_vs_prior20,c.sector_amount_vs_prior20,c.sector_amount_comparable_sum,c.sector_amount_prior20_mean,c.amount_comparable_member_count,c.amount_target_member_count,c.amount_comparable_coverage,c.amount_window_coverage,c.amount_window_target_member_max,c.amount_target_denominator_source,c.amount_window_denominator_source,c.amount_basis,c.amount_quality_codes,c.amount_excluded_member_ids,c.amount_member_set_hash,c.amount_membership_snapshot_id,cast(c.amount_window_start as varchar),cast(c.amount_window_end as varchar),c.amount_contract_id,c.sector_amount_ratio_delta_3sessions_common,cast(c.amount_comparison_date as varchar),c.amount_comparison_current_a,c.amount_comparison_prior_a,c.amount_comparison_current_sum,c.amount_comparison_current_prior20_mean,c.amount_comparison_prior_sum,c.amount_comparison_prior_prior20_mean,c.amount_comparison_member_set_hash,c.amount_comparison_current_coverage,c.amount_comparison_prior_coverage,c.amount_comparison_window_coverage,cast(c.amount_comparison_window_start as varchar),cast(c.amount_comparison_window_end as varchar),c.amount_comparison_quality_codes,c.amount_comparison_excluded_member_ids,c.amount_comparison_evidence from analysis_snapshot_entries e join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where e.snapshot_id=? and e.domain='sector_cycle'",[selected['snapshot_id']]).fetchall()
  formal_names=('sector_id','trade_date','member_amount_ratio_median_vs_prior20','sector_amount_vs_prior20','sector_amount_comparable_sum','sector_amount_prior20_mean','amount_comparable_member_count','amount_target_member_count','amount_comparable_coverage','amount_window_coverage','amount_window_target_member_max','amount_target_denominator_source','amount_window_denominator_source','amount_basis','amount_quality_codes','amount_excluded_member_ids','amount_member_set_hash','amount_membership_snapshot_id','amount_window_start','amount_window_end','amount_contract_id','sector_amount_ratio_delta_3sessions_common','amount_comparison_date','amount_comparison_current_a','amount_comparison_prior_a','amount_comparison_current_sum','amount_comparison_current_prior20_mean','amount_comparison_prior_sum','amount_comparison_prior_prior20_mean','amount_comparison_member_set_hash','amount_comparison_current_coverage','amount_comparison_prior_coverage','amount_comparison_window_coverage','amount_comparison_window_start','amount_comparison_window_end','amount_comparison_quality_codes','amount_comparison_excluded_member_ids','amount_comparison_evidence')
  formal_by_key={(str(row[0]),str(row[1])):dict(zip(formal_names,row)) for row in formal_rows}
  names=('sector_id','trade_date','sector_name','sector_type','board_quote_ret1','board_quote_source','member_ret1_median','member_ret5_median','member_ret20_median','member_amount_sum','amount_valid_count','total_member_count','quote_valid_count','factor_valid_count','coverage','breadth_ret1','breadth_ret1_common','breadth_ret1_common_valid_count','breadth_ret1_common_change_1d','breadth_ret1_common_change_1d_valid_count','breadth_ret1_common_change_3d','breadth_ret1_common_change_3d_valid_count','strong_count','high20_count','high30_count','high60_count','high100_count','high20_valid_count','high30_valid_count','high60_valid_count','high100_valid_count','comparable_count','previous_strong_total','comparable_previous_strong','retained_count','entered_count','exited_count','uncomparable_count','retention_rate','comparison_coverage','diffusion_state','breadth_ma20','sector_rs5','sector_rs20','sector_rs5_pct','sector_rs20_pct','amount_vs_prior20','rank','rank_change','window_stats')
  names += ('member_amount_ratio_median_vs_prior20','sector_amount_vs_prior20','sector_amount_comparable_sum','sector_amount_prior20_mean','amount_comparable_member_count','amount_target_member_count','amount_comparable_coverage','amount_window_coverage','amount_window_target_member_max','amount_target_denominator_source','amount_window_denominator_source','amount_basis','amount_quality_codes','amount_excluded_member_ids','amount_member_set_hash','amount_membership_snapshot_id','amount_window_start','amount_window_end','amount_contract_id','sector_amount_ratio_delta_3sessions_common','amount_comparison_date','amount_comparison_current_a','amount_comparison_prior_a','amount_comparison_current_sum','amount_comparison_current_prior20_mean','amount_comparison_prior_sum','amount_comparison_prior_prior20_mean','amount_comparison_member_set_hash','amount_comparison_current_coverage','amount_comparison_prior_coverage','amount_comparison_window_coverage','amount_comparison_window_start','amount_comparison_window_end','amount_comparison_quality_codes','amount_comparison_excluded_member_ids','amount_comparison_evidence')
  grouped={};date_values=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['window_stats']=json.loads(item['window_stats']) if item['window_stats'] else {};date_values.append(item['trade_date']);key=(item['sector_id'],item['sector_type']);grouped.setdefault(key,{'sector_id':item['sector_id'],'sector_name':item['sector_name'],'sector_type':item['sector_type'],'_rows':[]})['_rows'].append(item)
  dates=sorted(set(date_values));items=[]
  for item in grouped.values():
   cells={row['trade_date']:row for row in item.pop('_rows')};item['cells']=[{'trade_date':day,'rank':cells[day]['rank'] if day in cells else None,'hierarchy_rank':None,'hierarchy_sector_rs20_pct':None,'sector_rs20':cells[day]['sector_rs20'] if day in cells else None,'sector_rs20_pct':cells[day]['sector_rs20_pct'] if day in cells else None,'board_quote_ret1':cells[day]['board_quote_ret1'] if day in cells else None,'member_ret1_median':cells[day]['member_ret1_median'] if day in cells else None,'breadth_ret1':cells[day]['breadth_ret1'] if day in cells else None,'breadth_ret1_common':cells[day]['breadth_ret1_common'] if day in cells else None,'breadth_ret1_common_valid_count':cells[day]['breadth_ret1_common_valid_count'] if day in cells else None,'breadth_ret1_common_change_1d':cells[day]['breadth_ret1_common_change_1d'] if day in cells else None,'breadth_ret1_common_change_1d_valid_count':cells[day]['breadth_ret1_common_change_1d_valid_count'] if day in cells else None,'breadth_ret1_common_change_3d':cells[day]['breadth_ret1_common_change_3d'] if day in cells else None,'breadth_ret1_common_change_3d_valid_count':cells[day]['breadth_ret1_common_change_3d_valid_count'] if day in cells else None,'strong_count':cells[day]['strong_count'] if day in cells else None,'high20_count':cells[day]['high20_count'] if day in cells else None,'high30_count':cells[day]['high30_count'] if day in cells else None,'high60_count':cells[day]['high60_count'] if day in cells else None,'high100_count':cells[day]['high100_count'] if day in cells else None,'high20_valid_count':cells[day]['high20_valid_count'] if day in cells else None,'high30_valid_count':cells[day]['high30_valid_count'] if day in cells else None,'high60_valid_count':cells[day]['high60_valid_count'] if day in cells else None,'high100_valid_count':cells[day]['high100_valid_count'] if day in cells else None,'comparable_count':cells[day]['comparable_count'] if day in cells else None,'previous_strong_total':cells[day]['previous_strong_total'] if day in cells else None,'comparable_previous_strong':cells[day]['comparable_previous_strong'] if day in cells else None,'retained_count':cells[day]['retained_count'] if day in cells else None,'entered_count':cells[day]['entered_count'] if day in cells else None,'exited_count':cells[day]['exited_count'] if day in cells else None,'uncomparable_count':cells[day]['uncomparable_count'] if day in cells else None,'retention_rate':cells[day]['retention_rate'] if day in cells else None,'comparison_coverage':cells[day]['comparison_coverage'] if day in cells else None,'diffusion_state':cells[day]['diffusion_state'] if day in cells else None,'coverage':cells[day]['coverage'] if day in cells else None} for day in dates];items.append(item)
  for grouped_item in items:
   for cell in grouped_item['cells']:
    values=formal_by_key.get((str(grouped_item['sector_id']),cell['trade_date']))
    if values:
     for key in ('amount_quality_codes','amount_excluded_member_ids','amount_comparison_quality_codes','amount_comparison_excluded_member_ids','amount_comparison_evidence'):
      values[key]=_json_value(values.get(key),[] if key.endswith('codes') or key.endswith('ids') else {})
     cell.update(values)
  _annotate_sector_hierarchy(items,dates,self._hierarchy_nodes(selected['snapshot_id']))
  level_filter=str(hierarchy_level or '').upper()
  if level_filter not in ('','ALL','ROOT','LEAF','FLAT'): raise ValueError('SECTOR_HIERARCHY_LEVEL_UNSUPPORTED')
  if level_filter and level_filter!='ALL': items=[item for item in items if item['hierarchy_level_code']==level_filter]
  latest_index=len(dates)-1
  level_order={'ROOT':0,'LEAF':1,'FLAT':0}
  items.sort(key=lambda value: (level_order.get(value['hierarchy_level_code'],9),(value['cells'][latest_index]['hierarchy_rank'] if latest_index >= 0 and value['cells'][latest_index]['hierarchy_rank'] is not None else 10**9),value['sector_id']))
  total=len(items);start=(page-1)*size
  result={'publication_id':p,'snapshot_id':selected['snapshot_id'],'page':page,'page_size':size,'total':total,'days':days,'dates':dates,'metric':metric,'hierarchy_level_filter':level_filter or 'ALL','hierarchy_levels':sorted({item['hierarchy_level_code'] for item in items}),'as_of_trade_date':dates[-1] if dates else None,'items':items[start:start+size],'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root)}
  result.update(self._analysis_meta(context,{'page':page,'page_size':size,'sector_type':sector_type,'q':q,'days':days,'metric':metric,'hierarchy_level':level_filter or 'ALL','trade_date':trade_date},as_of or (dates[-1] if dates else None),{'from':dates[0] if dates else None,'to':dates[-1] if dates else None,'dates':dates}))
  return result
 def sector_timeline(self,p,sector_id,days=30,basis='AUTO',trade_date=None):
  days=max(1,min(250,int(days)));self._pub(p);context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('sector_cycle',));date_filter=" and e.trade_date<=?" if as_of else ''
  with self._con() as c:
   rows=c.execute("with recent_dates as (select distinct e.trade_date from analysis_snapshot_entries e join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where e.snapshot_id=? and e.domain='sector_cycle' and c.sector_id=?"+date_filter+" order by e.trade_date desc limit ?) select c.trade_date,c.sector_id,c.sector_name,c.sector_type,c.board_quote_ret1,c.board_quote_source,c.member_ret1_median,c.member_ret5_median,c.member_ret20_median,c.member_amount_sum,c.amount_valid_count,c.total_member_count,c.quote_valid_count,c.factor_valid_count,c.coverage,c.breadth_ret1,c.breadth_ret1_common,c.breadth_ret1_common_valid_count,c.breadth_ret1_common_change_1d,c.breadth_ret1_common_change_1d_valid_count,c.breadth_ret1_common_change_3d,c.breadth_ret1_common_change_3d_valid_count,c.strong_count,c.high20_count,c.high30_count,c.high60_count,c.high100_count,c.high20_valid_count,c.high30_valid_count,c.high60_valid_count,c.high100_valid_count,c.comparable_count,c.previous_strong_total,c.comparable_previous_strong,c.retained_count,c.entered_count,c.exited_count,c.uncomparable_count,c.retention_rate,c.comparison_coverage,c.diffusion_state,c.breadth_ma20,c.sector_rs5,c.sector_rs20,c.sector_rs5_pct,c.sector_rs20_pct,c.amount_vs_prior20,c.rank,c.rank_change,c.window_stats from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='sector_cycle' and e.trade_date=d.trade_date join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where c.sector_id=? order by c.trade_date",[selected['snapshot_id'],sector_id,*([as_of] if as_of else []),days,selected['snapshot_id'],sector_id]).fetchall()
  names=('trade_date','sector_id','sector_name','sector_type','board_quote_ret1','board_quote_source','member_ret1_median','member_ret5_median','member_ret20_median','member_amount_sum','amount_valid_count','total_member_count','quote_valid_count','factor_valid_count','coverage','breadth_ret1','breadth_ret1_common','breadth_ret1_common_valid_count','breadth_ret1_common_change_1d','breadth_ret1_common_change_1d_valid_count','breadth_ret1_common_change_3d','breadth_ret1_common_change_3d_valid_count','strong_count','high20_count','high30_count','high60_count','high100_count','high20_valid_count','high30_valid_count','high60_valid_count','high100_valid_count','comparable_count','previous_strong_total','comparable_previous_strong','retained_count','entered_count','exited_count','uncomparable_count','retention_rate','comparison_coverage','diffusion_state','breadth_ma20','sector_rs5','sector_rs20','sector_rs5_pct','sector_rs20_pct','amount_vs_prior20','rank','rank_change','window_stats');points=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['member_amount_sum']=float(item['member_amount_sum']) if item['member_amount_sum'] is not None else None;item['window_stats']=json.loads(item['window_stats']) if item['window_stats'] else {};points.append(item)
  with self._con() as c:
   formal_rows=c.execute("select c.sector_id,cast(c.trade_date as varchar),c.member_amount_ratio_median_vs_prior20,c.sector_amount_vs_prior20,c.sector_amount_comparable_sum,c.sector_amount_prior20_mean,c.amount_comparable_member_count,c.amount_target_member_count,c.amount_comparable_coverage,c.amount_window_coverage,c.amount_window_target_member_max,c.amount_target_denominator_source,c.amount_window_denominator_source,c.amount_basis,c.amount_quality_codes,c.amount_excluded_member_ids,c.amount_member_set_hash,c.amount_membership_snapshot_id,cast(c.amount_window_start as varchar),cast(c.amount_window_end as varchar),c.amount_contract_id,c.sector_amount_ratio_delta_3sessions_common,cast(c.amount_comparison_date as varchar),c.amount_comparison_current_a,c.amount_comparison_prior_a,c.amount_comparison_current_sum,c.amount_comparison_current_prior20_mean,c.amount_comparison_prior_sum,c.amount_comparison_prior_prior20_mean,c.amount_comparison_member_set_hash,c.amount_comparison_current_coverage,c.amount_comparison_prior_coverage,c.amount_comparison_window_coverage,cast(c.amount_comparison_window_start as varchar),cast(c.amount_comparison_window_end as varchar),c.amount_comparison_quality_codes,c.amount_comparison_excluded_member_ids,c.amount_comparison_evidence from analysis_snapshot_entries e join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date where e.snapshot_id=? and e.domain='sector_cycle' and c.sector_id=?",[selected['snapshot_id'],sector_id]).fetchall()
  formal_names=('sector_id','trade_date','member_amount_ratio_median_vs_prior20','sector_amount_vs_prior20','sector_amount_comparable_sum','sector_amount_prior20_mean','amount_comparable_member_count','amount_target_member_count','amount_comparable_coverage','amount_window_coverage','amount_window_target_member_max','amount_target_denominator_source','amount_window_denominator_source','amount_basis','amount_quality_codes','amount_excluded_member_ids','amount_member_set_hash','amount_membership_snapshot_id','amount_window_start','amount_window_end','amount_contract_id','sector_amount_ratio_delta_3sessions_common','amount_comparison_date','amount_comparison_current_a','amount_comparison_prior_a','amount_comparison_current_sum','amount_comparison_current_prior20_mean','amount_comparison_prior_sum','amount_comparison_prior_prior20_mean','amount_comparison_member_set_hash','amount_comparison_current_coverage','amount_comparison_prior_coverage','amount_comparison_window_coverage','amount_comparison_window_start','amount_comparison_window_end','amount_comparison_quality_codes','amount_comparison_excluded_member_ids','amount_comparison_evidence')
  formal_by_key={(str(row[0]),str(row[1])):dict(zip(formal_names,row)) for row in formal_rows}
  for point in points:
   values=formal_by_key.get((str(point['sector_id']),point['trade_date']))
   if values:
    for key in ('amount_quality_codes','amount_excluded_member_ids','amount_comparison_quality_codes','amount_comparison_excluded_member_ids','amount_comparison_evidence'):
     values[key]=_json_value(values.get(key),[] if key.endswith('codes') or key.endswith('ids') else {})
    point.update(values)
  if not points:
   result={'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'points':[],'status':'NOT_FOUND'}
   result.update(self._analysis_meta(context,{'sector_id':sector_id,'days':days,'trade_date':trade_date},None,{'from':None,'to':None,'dates':[]}));return result
  hierarchy_item=None;sector_type=points[-1]['sector_type'];page=1
  while hierarchy_item is None:
   matrix=self.sector_cycle(p,page=page,size=MAX_PAGE_SIZE,sector_type=sector_type,days=min(days,30),hierarchy_level='ALL',basis=basis,trade_date=as_of)
   hierarchy_item=next((item for item in matrix['items'] if item['sector_id']==sector_id),None)
   if hierarchy_item is not None or page*MAX_PAGE_SIZE>=matrix['total']:break
   page+=1
  rank_by_date={cell['trade_date']:cell.get('hierarchy_rank') for cell in hierarchy_item['cells']} if hierarchy_item else {}
  pct_by_date={cell['trade_date']:cell.get('hierarchy_sector_rs20_pct') for cell in hierarchy_item['cells']} if hierarchy_item else {}
  for point in points:
   point['hierarchy_rank']=rank_by_date.get(point['trade_date']);point['hierarchy_sector_rs20_pct']=pct_by_date.get(point['trade_date'])
  result={'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'sector_name':points[-1]['sector_name'],'sector_type':points[-1]['sector_type'],'history_basis':selected['domain'].removeprefix('LOCAL_'),'points':points,'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root)}
  if hierarchy_item:
   result.update({'hierarchy_level':hierarchy_item['hierarchy_level'],'hierarchy_level_code':hierarchy_item['hierarchy_level_code'],'parent_sector_id':hierarchy_item['parent_sector_id'],'parent_sector_name':hierarchy_item['parent_sector_name'],'rank_scope':hierarchy_item['rank_scope']})
  result.update(self._analysis_meta(context,{'sector_id':sector_id,'days':days,'trade_date':trade_date},as_of or points[-1]['trade_date'],{'from':points[0]['trade_date'],'to':points[-1]['trade_date'],'dates':[point['trade_date'] for point in points]}))
  return result
 def sector_members_history(self,p,sector_id,days=10,page=1,size=50,state='',security_id='',basis='AUTO',trade_date=None):
  allowed={'ALL','ADDED','REMOVED','RETAINED','ENTERED','EXITED','UNKNOWN','UNCHANGED'};state=str(state or 'ALL').upper()
  if state not in allowed: raise ValueError('MEMBER_HISTORY_STATE_UNSUPPORTED')
  days=max(1,min(30,int(days)));size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p);context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('member_state',));date_filter=" and trade_date<=?" if as_of else ''
  filters=['e.snapshot_id=?',"e.domain='member_state'",'s.sector_id=?'];args=[selected['snapshot_id'],sector_id]
  if security_id:
   if not is_workbench_visible_security_id(security_id, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
   filters.append('s.security_id=?');args.append(security_id)
  filters.append(WORKBENCH_SCOPE_SQL.format(id='s.security_id'))
  if state!='ALL': filters.append('s.member_change_kind=?');args.append(state)
  where=' and '.join(filters)
  query="with recent_dates as (select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='member_state'"+date_filter+" order by trade_date desc limit ?) select s.sector_id,s.security_id,s.trade_date,s.member_present,s.member_rank,s.rank_valid_count,s.member_percentile,s.strong_state,s.strong_predicates,s.structure_hit,s.high_hit,s.member_change_kind,s.strength_change_kind,s.previous_rank,s.rank_delta,s.queue_refs,s.high_refs,s.history_basis,s.contract_id from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='member_state' and e.trade_date=d.trade_date join member_state_result_daily s on s.slice_id=e.slice_id and s.trade_date=e.trade_date where "+where+" order by s.trade_date desc,s.member_rank nulls last,s.security_id"
  with self._con() as c: rows=c.execute(query,[selected['snapshot_id'],*([as_of] if as_of else []),days,selected['snapshot_id'],*args]).fetchall()
  names=('sector_id','security_id','trade_date','member_present','member_rank','rank_valid_count','member_percentile','strong_state','strong_predicates','structure_hit','high_hit','member_change_kind','strength_change_kind','previous_rank','rank_delta','queue_refs','high_refs','history_basis','contract_id');items=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['member_rank']=_finite_or_none(item['member_rank']);item['rank_valid_count']=_finite_or_none(item['rank_valid_count']);item['member_percentile']=_finite_or_none(item['member_percentile']);item['previous_rank']=_finite_or_none(item['previous_rank']);item['rank_delta']=_finite_or_none(item['rank_delta']);item['strong_predicates']=json.loads(item['strong_predicates']) if item['strong_predicates'] else {};item['queue_refs']=json.loads(item['queue_refs']) if item['queue_refs'] else [];item['high_refs']=json.loads(item['high_refs']) if item['high_refs'] else [];items.append(item)
  security_names=self._security_names(p,{item['security_id'] for item in items if item.get('security_id')})
  for item in items:item['security_name']=security_names.get(item.get('security_id'))
  total=len(items);result={'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'page':page,'page_size':size,'days':days,'state':state,'total':total,'items':items[(page-1)*size:page*size],'display_scope':self._display_scope}
  result.update(self._analysis_meta(context,{'sector_id':sector_id,'days':days,'page':page,'page_size':size,'state':state,'security_id':security_id,'trade_date':trade_date},as_of or (items[0]['trade_date'] if items else None),{'from':items[-1]['trade_date'] if items else None,'to':items[0]['trade_date'] if items else None,'dates':sorted({item['trade_date'] for item in items}) if items else []}))
  return result
 def sector_leader_history(self,p,sector_id,days=30,basis='AUTO',trade_date=None):
  days=max(1,min(250,int(days)));self._pub(p);context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('representative',));date_filter=" and e.trade_date<=?" if as_of else ''
  with self._con() as c:
   rows=c.execute("with recent_dates as (select distinct e.trade_date from analysis_snapshot_entries e join representative_state_daily r on r.slice_id=e.slice_id and r.trade_date=e.trade_date where e.snapshot_id=? and e.domain='representative' and r.sector_id=?"+date_filter+" order by e.trade_date desc limit ?) select r.sector_id,r.trade_date,r.ranked_first_id,r.ranked_second_id,r.rank_gap,r.confirmed_id,r.candidate_id,r.candidate_since,r.candidate_streak,r.confirmed_since,r.confirmation_event,r.previous_confirmed_id,r.stale,r.representative_rank_basis,r.history_basis,r.contract_id from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='representative' and e.trade_date=d.trade_date join representative_state_daily r on r.slice_id=e.slice_id and r.trade_date=e.trade_date where r.sector_id=? order by r.trade_date",[selected['snapshot_id'],sector_id,*([as_of] if as_of else []),days,selected['snapshot_id'],sector_id]).fetchall()
  names=('sector_id','trade_date','ranked_first_id','ranked_second_id','rank_gap','confirmed_id','candidate_id','candidate_since','candidate_streak','confirmed_since','confirmation_event','previous_confirmed_id','stale','representative_rank_basis','history_basis','contract_id');points=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['candidate_since']=str(item['candidate_since']) if item['candidate_since'] else None;item['confirmed_since']=str(item['confirmed_since']) if item['confirmed_since'] else None;points.append(item)
  security_ids={item.get(key) for item in points for key in ('ranked_first_id','ranked_second_id','confirmed_id','candidate_id','previous_confirmed_id') if item.get(key)};security_names=self._security_names(p,security_ids)
  for item in points:
   for key in ('ranked_first_id','ranked_second_id','confirmed_id','candidate_id','previous_confirmed_id'):
    if item.get(key) and not is_workbench_visible_security_id(item[key], self._root):
     item[key]=None
    item[key.replace('_id','_name')]=security_names.get(item.get(key))
  result={'publication_id':p,'sector_id':sector_id,'snapshot_id':selected['snapshot_id'],'days':days,'points':points,'status':'AVAILABLE' if points else 'NOT_FOUND','display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root)}
  result.update(self._analysis_meta(context,{'sector_id':sector_id,'days':days,'trade_date':trade_date},as_of or (points[-1]['trade_date'] if points else None),{'from':points[0]['trade_date'] if points else None,'to':points[-1]['trade_date'] if points else None,'dates':[point['trade_date'] for point in points]}))
  return result
 def _mainline_policy(self,connection,snapshot_id):
  policy=mainline_history_policy()
  row=connection.execute("select s.basis_json from analysis_snapshot_entries e join analysis_slices s on s.slice_id=e.slice_id where e.snapshot_id=? and e.domain='mainline' limit 1",[snapshot_id]).fetchone()
  if row and row[0]:
   try:
    stored=json.loads(row[0]) if isinstance(row[0],str) else row[0]
    if isinstance(stored,dict) and isinstance(stored.get('history_policy'),dict): policy.update(stored['history_policy'])
   except (TypeError,ValueError,json.JSONDecodeError):
    pass
  return policy
 def mainlines(self,p,page=1,size=50,mainline_class='',days=30,sector_type='',group='',basis='AUTO',trade_date=None):
  allowed={'DATA_INSUFFICIENT','FADING','HIGH_LEVEL_CONTRACTION','REACCELERATING','SUSTAINED','NEW','BROADENING','OBSERVING'}
  allowed_types={'INDUSTRY','THEME','STYLE'}
  allowed_groups={'INDUSTRY_ROOT','INDUSTRY_LEAF','THEME','STYLE'}
  mainline_class=str(mainline_class or '').upper();sector_type=str(sector_type or '').upper();group=str(group or '').upper()
  if mainline_class and mainline_class not in allowed: raise ValueError('MAINLINE_CLASS_UNSUPPORTED')
  if sector_type and sector_type not in allowed_types: raise ValueError('MAINLINE_SECTOR_TYPE_UNSUPPORTED')
  if group and group not in allowed_groups: raise ValueError('MAINLINE_GROUP_UNSUPPORTED')
  days=max(1,min(30,int(days)));size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p)
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('mainline',));date_filter=" and trade_date<=?" if as_of else ''
  with self._con() as c:
   if not c.execute("select count(*) from information_schema.tables where table_name='mainline_daily'").fetchone()[0] or not c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='mainline'",[selected['snapshot_id']]).fetchone()[0]: raise ValueError('MAINLINE_NOT_BUILT')
   filters=['e.snapshot_id=?',"e.domain='mainline'","m.sector_type in ('INDUSTRY','THEME','STYLE')","m.trade_date=(select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='mainline'"+date_filter+")"];params=[selected['snapshot_id'],selected['snapshot_id'],*([as_of] if as_of else [])]
   if sector_type:filters.append('m.sector_type=?');params.append(sector_type)
   where=' and '.join(filters)
   rows=c.execute('select m.sector_id,m.trade_date,m.sector_name,m.sector_type,m.mainline_class,m.previous_class,m.transition,m.observation_days,m.valid_observation_days,m.on_list_days,m.consecutive_on_list,m.current_percentile,m.current_breadth,m.current_amount_vs_prior20,m.percentile_change_3d,m.breadth_change_3d,m.amount_change_3d,m.retention_rate,m.entered_count,m.exited_count,m.predicates,m.missing_fields,m.conflict_resolution,m.history_basis,m.contract_id,m.config_hash from analysis_snapshot_entries e join mainline_daily m on m.slice_id=e.slice_id and m.trade_date=e.trade_date where '+where+' order by m.mainline_class,m.current_percentile desc nulls last,m.sector_id',params).fetchall()
   formal_rows=c.execute("select m.sector_id,cast(m.trade_date as varchar),m.current_sector_amount_vs_prior20,m.sector_amount_ratio_delta_3sessions_common,m.sector_amount_quality_codes,m.sector_amount_basis,m.sector_amount_membership_snapshot_id,m.sector_amount_comparison_evidence,m.sector_amount_contract_id from analysis_snapshot_entries e join mainline_daily m on m.slice_id=e.slice_id and m.trade_date=e.trade_date where e.snapshot_id=? and e.domain='mainline'",[selected['snapshot_id']]).fetchall()
   dates=c.execute("select cast(trade_date as varchar) from analysis_snapshot_entries where snapshot_id=? and domain='mainline'"+date_filter+" order by trade_date desc limit ?",[selected['snapshot_id'],*([as_of] if as_of else []),days]).fetchall()
   policy=self._mainline_policy(c,selected['snapshot_id'])
  names=('sector_id','trade_date','sector_name','sector_type','mainline_class','previous_class','transition','observation_days','valid_observation_days','on_list_days','consecutive_on_list','current_percentile','current_breadth','current_amount_vs_prior20','percentile_change_3d','breadth_change_3d','amount_change_3d','retention_rate','entered_count','exited_count','predicates','missing_fields','conflict_resolution','history_basis','contract_id','config_hash');items=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['on_list_days']=json.loads(item['on_list_days']) if item['on_list_days'] else {};item['predicates']=json.loads(item['predicates']) if item['predicates'] else {};item['missing_fields']=json.loads(item['missing_fields']) if item['missing_fields'] else [];items.append(item)
  formal_by_key={(str(row[0]),str(row[1])):{'current_sector_amount_vs_prior20':row[2],'sector_amount_ratio_delta_3sessions_common':row[3],'sector_amount_quality_codes':_json_value(row[4],[]),'sector_amount_basis':row[5],'sector_amount_membership_snapshot_id':row[6],'sector_amount_comparison_evidence':_json_value(row[7],{}),'sector_amount_contract_id':row[8]} for row in formal_rows}
  for item in items:item.update(formal_by_key.get((str(item['sector_id']),str(item['trade_date'])),{}))
  items=_mainline_group(items,self._hierarchy_nodes(selected['snapshot_id']))
  grouped_items=[item for item in items if not group or item['mainline_group']==group]
  class_counts={key:sum(1 for item in grouped_items if item['mainline_class']==key) for key in ('FADING','HIGH_LEVEL_CONTRACTION','REACCELERATING','SUSTAINED','NEW','BROADENING','OBSERVING','DATA_INSUFFICIENT')}
  items=[item for item in grouped_items if not mainline_class or item['mainline_class']==mainline_class]
  class_order={'FADING':0,'HIGH_LEVEL_CONTRACTION':1,'REACCELERATING':2,'SUSTAINED':3,'NEW':4,'BROADENING':5,'OBSERVING':6,'DATA_INSUFFICIENT':9}
  items.sort(key=lambda item:(class_order.get(item['mainline_class'],8),-(item['current_percentile'] if item['current_percentile'] is not None else -1),item['sector_id']))
  total=len(items);start=(page-1)*size
  result={'publication_id':p,'snapshot_id':selected['snapshot_id'],'page':page,'page_size':size,'total':total,'days':days,'dates':[row[0] for row in dates],'mainline_class_filter':mainline_class or 'ALL','sector_type_filter':sector_type or 'ALL','group_filter':group or 'ALL','group_counts':{key:sum(1 for item in items if item['mainline_group']==key) for key in ('INDUSTRY_ROOT','INDUSTRY_LEAF','THEME','STYLE')},'class_counts':class_counts,'history_basis':selected['domain'].removeprefix('LOCAL_'),'history_policy':policy,'items':items[start:start+size]}
  result.update(self._analysis_meta(context,{'page':page,'page_size':size,'mainline_class':mainline_class,'days':days,'sector_type':sector_type,'group':group,'trade_date':trade_date},as_of or (dates[0][0] if dates else None),{'from':dates[-1][0] if dates else None,'to':dates[0][0] if dates else None,'dates':[row[0] for row in dates]}))
  return result
 def mainline_evidence(self,p,sector_id,days=30,basis='AUTO',trade_date=None):
  days=max(1,min(30,int(days)));self._pub(p);context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('mainline',));date_filter=" and e.trade_date<=?" if as_of else ''
  with self._con() as c:
   if not c.execute("select count(*) from information_schema.tables where table_name='mainline_daily'").fetchone()[0] or not c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='mainline'",[selected['snapshot_id']]).fetchone()[0]: raise ValueError('MAINLINE_NOT_BUILT')
   rows=c.execute("with recent_dates as (select trade_date from analysis_snapshot_entries where snapshot_id=? and domain='mainline'"+date_filter+" order by trade_date desc limit ?) select m.sector_id,m.trade_date,m.sector_name,m.sector_type,m.mainline_class,m.previous_class,m.transition,m.observation_days,m.valid_observation_days,m.on_list_days,m.consecutive_on_list,m.current_percentile,m.current_breadth,m.current_amount_vs_prior20,m.percentile_change_3d,m.breadth_change_3d,m.amount_change_3d,m.retention_rate,m.entered_count,m.exited_count,m.predicates,m.missing_fields,m.conflict_resolution,m.history_basis,m.contract_id,m.config_hash from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='mainline' and e.trade_date=d.trade_date join mainline_daily m on m.slice_id=e.slice_id and m.trade_date=e.trade_date where m.sector_id=? order by m.trade_date",[selected['snapshot_id'],*([as_of] if as_of else []),days,selected['snapshot_id'],sector_id]).fetchall()
   policy=self._mainline_policy(c,selected['snapshot_id'])
  names=('sector_id','trade_date','sector_name','sector_type','mainline_class','previous_class','transition','observation_days','valid_observation_days','on_list_days','consecutive_on_list','current_percentile','current_breadth','current_amount_vs_prior20','percentile_change_3d','breadth_change_3d','amount_change_3d','retention_rate','entered_count','exited_count','predicates','missing_fields','conflict_resolution','history_basis','contract_id','config_hash');points=[]
  for raw in rows:
   item=dict(zip(names,raw));item['trade_date']=str(item['trade_date']);item['on_list_days']=json.loads(item['on_list_days']) if item['on_list_days'] else {};item['predicates']=json.loads(item['predicates']) if item['predicates'] else {};item['missing_fields']=json.loads(item['missing_fields']) if item['missing_fields'] else [];points.append(item)
  with self._con() as c:
   formal_rows=c.execute("select cast(m.trade_date as varchar),m.current_sector_amount_vs_prior20,m.sector_amount_ratio_delta_3sessions_common,m.sector_amount_quality_codes,m.sector_amount_basis,m.sector_amount_membership_snapshot_id,m.sector_amount_comparison_evidence,m.sector_amount_contract_id from analysis_snapshot_entries e join mainline_daily m on m.slice_id=e.slice_id and m.trade_date=e.trade_date where e.snapshot_id=? and e.domain='mainline' and m.sector_id=?",[selected['snapshot_id'],sector_id]).fetchall()
  formal_by_date={str(row[0]):{'current_sector_amount_vs_prior20':row[1],'sector_amount_ratio_delta_3sessions_common':row[2],'sector_amount_quality_codes':_json_value(row[3],[]),'sector_amount_basis':row[4],'sector_amount_membership_snapshot_id':row[5],'sector_amount_comparison_evidence':_json_value(row[6],{}),'sector_amount_contract_id':row[7]} for row in formal_rows}
  for point in points:point.update(formal_by_date.get(point['trade_date'],{}))
  result={'publication_id':p,'snapshot_id':selected['snapshot_id'],'sector_id':sector_id,'days':days,'history_policy':policy,'points':points,'status':'AVAILABLE' if points else 'NOT_FOUND'}
  result.update(self._analysis_meta(context,{'sector_id':sector_id,'days':days,'trade_date':trade_date},as_of or (points[-1]['trade_date'] if points else None),{'from':points[0]['trade_date'] if points else None,'to':points[-1]['trade_date'] if points else None,'dates':[point['trade_date'] for point in points]}))
  return result
 def _analysis_capabilities(self,p):
   with self._con() as c:
    counts={table:c.execute(f'select count(*) from {table} where publication_id=?',[p]).fetchone()[0] for table in ('stock_daily','sector_daily','queue_memberships')}
   bindings=self._analysis_bindings(p)
   preferred=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
   quality=self._analysis_quality(preferred) if preferred else {'field_coverage':{},'status':'PARTIAL','codes':['HISTORY_ANALYSIS_NOT_BUILT']}
   domain_capabilities={domain:('AVAILABLE' if value.get('date_count',0)>0 else 'UNAVAILABLE') for domain,value in quality.get('field_coverage',{}).items()}
   return {
    'overview':'AVAILABLE' if counts['stock_daily'] else 'UNAVAILABLE',
    'universe':'AVAILABLE' if counts['stock_daily'] else 'UNAVAILABLE',
    'sector':'AVAILABLE' if counts['sector_daily'] else 'UNAVAILABLE',
    'structure':'AVAILABLE' if counts['queue_memberships'] else 'UNAVAILABLE',
    'history_analysis':'AVAILABLE' if bindings else 'NOT_BUILT',
    'analysis_domains':domain_capabilities,
    'field_coverage':quality.get('field_coverage',{}),
   }
 def _analysis_bindings(self,p):
   with self._con() as c:
    rows=c.execute('''select b.domain,b.snapshot_id,cast(s.cutoff_date as varchar),cast(s.query_start as varchar),s.manifest_hash,
                             s.universe_contract,s.config_hash,cast(s.created_at as varchar)
       from publication_analysis_snapshots b join analysis_snapshots s using(snapshot_id)
       left join analysis_snapshot_audit_status a on a.snapshot_id=s.snapshot_id
      where b.publication_id=? and s.status='SUCCESS' and coalesce(a.audit_status,'ACTIVE') not in ('BLOCKED','PENDING_REVIEW') order by case b.domain when 'LOCAL_OBSERVED' then 0 else 1 end''',[p]).fetchall()
   return {row[0]:{'domain':row[0],'snapshot_id':row[1],'analysis_snapshot_id':row[1],'cutoff_date':row[2],'query_start':row[3],'manifest_hash':row[4],'universe_contract':row[5],'config_hash':row[6],'created_at':row[7]} for row in rows}
 def _analysis_quality(self,selected):
   if not selected: return {'status':'PARTIAL','codes':['HISTORY_ANALYSIS_NOT_BUILT'],'field_coverage':{}}
   snapshot_id=selected['snapshot_id']
   cached=self._analysis_quality_cache.get(snapshot_id)
   if cached is not None:return cached
   with self._con() as c:
    rows=c.execute('''select e.domain,cast(e.trade_date as varchar),s.slice_id,cast(s.trade_date as varchar),s.contract_id,s.input_hash,s.dependency_hash,
                             s.logical_hash,s.row_count,s.basis_json,b.universe_basis,b.membership_snapshot_id,b.price_basis,
                             cast(b.adjustment_as_of as varchar),cast(b.source_observed_at as varchar),b.coverage,b.capabilities_json
                        from analysis_snapshot_entries e
                        join analysis_slices s on s.slice_id=e.slice_id
                   left join analysis_daily_basis b on b.slice_id=e.slice_id
                       where e.snapshot_id=? order by e.domain,e.trade_date,s.slice_id''',[snapshot_id]).fetchall()
   all_dates=sorted({row[1] for row in rows})
   coverage={}
   for row in rows:
    domain,trade_date,slice_id,slice_trade_date,contract_id,input_hash,dependency_hash,logical_hash,row_count,basis_json,universe_basis,membership_snapshot_id,price_basis,adjustment_as_of,source_observed_at,covered,capabilities_json=row
    item=coverage.setdefault(domain,{'available_from':trade_date,'available_to':trade_date,'date_count':0,'slice_count':0,'row_count':0,'contract_ids':set(),'slice_ids':[],'input_hashes':set(),'dependency_hashes':set(),'logical_hashes':set(),'missing_dates':[],'coverage_values':[],'basis_metadata_complete':True,'basis':None,'latest_slice':None,'slice_trade_date_mismatches':[]})
    item['available_from']=min(item['available_from'],trade_date);item['available_to']=max(item['available_to'],trade_date);item['date_count']+=1;item['row_count']+=int(row_count or 0);item['contract_ids'].add(contract_id);item['input_hashes'].add(input_hash);item['dependency_hashes'].add(dependency_hash);item['logical_hashes'].add(logical_hash)
    if slice_id not in item['slice_ids']: item['slice_ids'].append(slice_id)
    if slice_trade_date != trade_date: item['slice_trade_date_mismatches'].append({'entry_trade_date':trade_date,'slice_trade_date':slice_trade_date,'slice_id':slice_id})
    if covered is not None:item['coverage_values'].append(float(covered))
    else:item['basis_metadata_complete']=False
    if item['latest_slice'] is None or trade_date>=item['latest_slice']['trade_date']:
     item['latest_slice']={'slice_id':slice_id,'trade_date':trade_date,'slice_trade_date':slice_trade_date,'contract_id':contract_id,'input_hash':input_hash,'dependency_hash':dependency_hash,'logical_hash':logical_hash,'row_count':int(row_count or 0),'basis_json':_json_value(basis_json,{}),'universe_basis':universe_basis,'membership_snapshot_id':membership_snapshot_id,'price_basis':price_basis,'adjustment_as_of':adjustment_as_of,'source_observed_at':source_observed_at,'coverage':float(covered) if covered is not None else None,'capabilities':_json_value(capabilities_json,{})}
   for domain,item in coverage.items():
    item['missing_dates']=[day for day in all_dates if item['available_from']<=day<=item['available_to'] and day not in {row[1] for row in rows if row[0]==domain}]
    item['coverage']=round(sum(item['coverage_values'])/len(item['coverage_values']),8) if item['coverage_values'] else None
    item['contract_ids']=sorted(item['contract_ids']);item['input_hashes']=sorted(item['input_hashes']);item['dependency_hashes']=sorted(item['dependency_hashes']);item['logical_hashes']=sorted(item['logical_hashes']);item['slice_ids']=sorted(set(item['slice_ids']))[-10:];item['slice_count']=len(set(item['slice_ids']));item.pop('coverage_values',None)
    latest=item['latest_slice']
    latest_capabilities=latest.get('capabilities',{}) if latest else {}
    membership_metadata_ok=domain not in ('mainline','sector_cycle','member_state') or bool(latest and latest.get('membership_snapshot_id'))
    semantic_metadata_ok=domain != 'mainline' or bool(latest and (latest.get('basis_json',{}).get('semantic_version') or latest_capabilities.get('semantic_version')))
    item['basis_metadata_complete']=bool(item['basis_metadata_complete'] and latest and latest.get('coverage') is not None and membership_metadata_ok and semantic_metadata_ok and not item['slice_trade_date_mismatches'])
    if item['slice_trade_date_mismatches']: item['basis_metadata_complete']=False
   codes=[]
   if any(item['missing_dates'] for item in coverage.values()):codes.append('SNAPSHOT_DOMAIN_DATE_GAPS')
   if any(item.get('slice_trade_date_mismatches') for item in coverage.values()):codes.append('SNAPSHOT_SLICE_TRADE_DATE_MISMATCH')
   if any(not item['basis_metadata_complete'] for item in coverage.values()):codes.append('BASIS_METADATA_INCOMPLETE')
   result={'status':'AVAILABLE' if coverage and not codes else ('PARTIAL' if coverage else 'UNAVAILABLE'),'codes':codes,'field_coverage':coverage}
   self._analysis_quality_cache[snapshot_id]=result
   return result
 def _analysis_context(self,p,basis='AUTO'):
   if basis not in ('AUTO','OBSERVED','RECONSTRUCTED'): raise ValueError('BASIS_UNSUPPORTED')
   bindings=self._analysis_bindings(p);requested={'OBSERVED':'LOCAL_OBSERVED','RECONSTRUCTED':'LOCAL_RECONSTRUCTED'}.get(basis)
   selected=bindings.get(requested) if requested else bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED')
   if not selected:
    if bindings: raise ValueError('BASIS_UNAVAILABLE')
    raise ValueError('ANALYSIS_NOT_BUILT')
   selected=dict(selected);selected['publication_id']=p
   quality=self._analysis_quality(selected)
   contracts={'universe':selected.get('universe_contract'),'quote':'workbench-quote-v2.1','semantic':'workbench-semantic-v2.1','publication':'m4-one-click-publication-contract-v1.1','analysis_domains':{domain:value.get('contract_ids',[]) for domain,value in quality.get('field_coverage',{}).items()}}
   return {'requested_basis':basis,'resolved_basis':selected['domain'].removeprefix('LOCAL_'),'selected':selected,'quality':quality,'contracts':contracts}
 def _analysis_meta(self,context,query=None,trade_date=None,returned_range=None):
   selected=context['selected'];quality=context['quality'];query_payload={'publication_id':selected.get('publication_id'),'snapshot_id':selected['snapshot_id'],'basis':context['requested_basis'],'query':_canonical_query(query or {})}
   query_hash=hashlib.sha256(json.dumps(query_payload,ensure_ascii=False,sort_keys=True,default=str).encode('utf-8')).hexdigest()
   basis_metadata={domain:{key:value.get('latest_slice',{}).get(key) for key in ('slice_id','trade_date','slice_trade_date','contract_id','universe_basis','membership_snapshot_id','price_basis','adjustment_as_of','source_observed_at','coverage','capabilities')} for domain,value in quality.get('field_coverage',{}).items() if value.get('latest_slice')}
   result={'api_contract':API_CONTRACT,'publication_id':selected.get('publication_id'),'analysis_snapshot_id':selected['snapshot_id'],'snapshot_id':selected['snapshot_id'],'cutoff_date':selected['cutoff_date'],'trade_date':trade_date or selected['cutoff_date'],'requested_basis':context['requested_basis'],'resolved_basis':context['resolved_basis'],'history_basis':context['resolved_basis'],'query_hash':query_hash,'contracts':context['contracts'],'capabilities':{domain:('AVAILABLE' if value.get('date_count',0)>0 else 'UNAVAILABLE') for domain,value in quality.get('field_coverage',{}).items()},'basis_metadata':basis_metadata,'data_quality':quality,'display_scope':self._display_scope}
   if returned_range is not None:result['returned_range']=returned_range
   return result
 def _analysis_as_of(self,context,trade_date,domains):
  if trade_date in (None,''): return None
  try: requested=date.fromisoformat(str(trade_date).strip()).isoformat()
  except (TypeError,ValueError): raise ValueError('DATE_INVALID')
  selected=context['selected']
  if requested>selected['cutoff_date']: raise ValueError('DATE_AFTER_CUTOFF')
  domain_values=tuple(str(value) for value in domains)
  placeholders=','.join('?' for _ in domain_values)
  with self._con() as c:
   found=c.execute('select 1 from analysis_snapshot_entries where snapshot_id=? and trade_date=? and domain in ('+placeholders+') limit 1',[selected['snapshot_id'],requested,*domain_values]).fetchone()
  if not found: raise ValueError('TRADE_DATE_UNAVAILABLE')
  return requested
 def _m13c_capabilities(self,connection,snapshot_id,effective_date):
  """Return evidence-backed M8C capability states for materialized ladder rows."""
  row = connection.execute(
   """
   with ladder_rows as (
    select l.slice_id,l.security_id,l.trade_date,l.rule_id
      from analysis_snapshot_entries e
      join limit_ladder_daily l on l.slice_id=e.slice_id and l.trade_date=e.trade_date
     where e.snapshot_id=? and e.domain='limit_ladder' and e.trade_date=?
   ), reference_matches as (
    select l.security_id,l.trade_date,l.rule_id,r.status_known,r.rule_id as reference_rule_id,r.quote_capability,r.reference_status,r.ex_rights_reference_unknown
      from ladder_rows l join market_reference_daily r
        on r.slice_id=l.slice_id and r.security_id=l.security_id and r.trade_date=l.trade_date
    union
    select l.security_id,l.trade_date,l.rule_id,r.status_known,r.rule_id as reference_rule_id,r.quote_capability,r.reference_status,r.ex_rights_reference_unknown
      from ladder_rows l
      join analysis_slice_dependencies d on d.slice_id=l.slice_id and (d.input_domain in ('market_reference','m8c_reference') or d.input_domain like 'market_reference_%')
      join market_reference_daily r on r.slice_id=d.input_slice_id and r.security_id=l.security_id and r.trade_date=l.trade_date
   ), bound_refs as (
    select l.security_id,l.trade_date,l.rule_id,
           max(case when r.quote_capability='EXACT' and r.reference_status='KNOWN' and coalesce(r.ex_rights_reference_unknown,true)=false and r.reference_rule_id=l.rule_id then 1 else 0 end) as reference_bound,
           max(case when r.quote_capability='EXACT' and r.reference_status='KNOWN' and coalesce(r.ex_rights_reference_unknown,true)=false and r.reference_rule_id=l.rule_id and v.rule_id is not null and v.contract_id='LIMIT_RULES_V1_1' and v.rule_verified=true and v.audit_status='VERIFIED' then 1 else 0 end) as rule_bound
      from ladder_rows l
      left join reference_matches r on r.security_id=l.security_id and r.trade_date=l.trade_date and r.rule_id=l.rule_id
      left join limit_rule_versions v on v.rule_id=l.rule_id and v.valid_from<=l.trade_date and (v.valid_to is null or v.valid_to>=l.trade_date)
     group by l.security_id,l.trade_date,l.rule_id
   )
   select count(*),
          coalesce(sum(reference_bound),0),
          coalesce(sum(rule_bound),0)
     from bound_refs
   """,
   [snapshot_id,effective_date],
  ).fetchone()
  total, reference_bound, rules_bound = (int(value or 0) for value in row)
  def state(bound):
   if not total: return 'NOT_BUILT'
   return 'BOUND' if bound == total else 'PARTIAL'
  return {
   'm8c_reference': state(reference_bound),
   'm8c_rules': state(rules_bound),
   'evidence': {'ladder_rows': total, 'reference_bound_rows': reference_bound, 'rule_bound_rows': rules_bound},
  }
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
 def _quotes(self,p,security_ids=None):
  requested={str(value) for value in (security_ids or ()) if value}
  with self._quote_lock:
   if not requested:
    if p not in self._quote_full_cache:
     self._quote_cache[p]=self._load_quotes(p) or {}
     self._quote_full_cache.add(p)
    return self._quote_cache[p]
   if p in self._quote_full_cache:return self._quote_cache[p]
   cached=self._quote_cache.setdefault(p,{})
   missing=requested-set(cached)
   if missing:cached.update(self._load_quotes(p,missing) or {})
   return {security_id:cached[security_id] for security_id in requested if cached.get(security_id) is not None}
 def _load_quotes(self,p,security_ids=None):
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
     key=str(source_path)
     service=self._quote_service_cache.get(key)
     if service is None:
      service=QuoteService(source_path);self._quote_service_cache[key]=service
     return service.load(trade_date=current,publication_id=p,source_identity_sha256=identity.get('source_identity_sha256'),expected_file_sha256=source['sha256'],source_path=relative.as_posix(),security_ids=security_ids)
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
   with DuckDBApiConnectionProvider(source_path).memory() as parquet_con:
    normalized_latest=parquet_con.execute('select max(date) from read_parquet(?)',[str(source_path)]).fetchone()[0]
  except Exception:return {}
  if normalized_latest!=current:return {}
  manifest={'contract':'m4-normalized-quote-binding-v1','source_bundle_id':bundle_id,'source_path':'data/normalized/adjusted_daily.parquet','source_identity_sha256':identity.get('source_identity_sha256')}
  self._source_cache[p]=(source_path,manifest)
  key=str(source_path)
  service=self._quote_service_cache.get(key)
  if service is None:
   service=QuoteService(source_path);self._quote_service_cache[key]=service
  return service.load(trade_date=current,publication_id=p,source_identity_sha256=identity.get('source_identity_sha256'),source_path='data/normalized/adjusted_daily.parquet',security_ids=security_ids)
 def _add_quotes(self,p,result):
  quotes=self._quotes(p,{item.get('security_id') for item in result['items']})
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
       binding,relation_edges=self._publication_edges(c,p)
       if binding:
        wanted=set(missing)
        rows=[(edge.security_id,edge.sector_id) for edge in relation_edges if edge.security_id in wanted]
        sector_ids=sorted({sector_id for _,sector_id in rows})
        if sector_ids:
         placeholders=','.join('?' for _ in sector_ids)
         sector_rows=c.execute(f'''select sector_id,payload_json from sector_daily
           where publication_id=? and sector_id in ({placeholders})''',[p,*sector_ids]).fetchall()
         sector_payloads={sector_id:json.loads(payload) for sector_id,payload in sector_rows if payload}
        else: sector_payloads={}
        sector_ids=sorted(sector_payloads)
        grouped={sector_id:[] for sector_id in sector_ids}
        member_edges={}
        for edge in relation_edges:
         if edge.sector_id in grouped and is_workbench_statistical_security_id(edge.security_id,self._root):
          member_edges[(edge.sector_id,edge.security_id)]=edge
        member_ids=sorted({security_id for _,security_id in member_edges})
        stock_payloads={}
        if member_ids:
         placeholders=','.join('?' for _ in member_ids)
         stock_rows=c.execute(f'''select security_id,payload_json from stock_daily
           where publication_id=? and security_id in ({placeholders})''',[p,*member_ids]).fetchall()
         stock_payloads={security_id:json.loads(payload) for security_id,payload in stock_rows if payload}
        for sector_id,security_id in sorted(member_edges):
         payload=stock_payloads.get(security_id,{})
         grouped[sector_id].append({'security_id':security_id,'member_rank':None,'rank_valid_count':0,'RET5':payload.get('RET5'),'RET20':payload.get('RET20')})
        memberships={sid:[] for sid in missing}
        for security_id,sector_id in rows:
         if sector_id in sector_payloads:
          memberships[security_id].append((sector_payloads[sector_id],grouped.get(sector_id,[])))
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
  return {'publication_id':p,'page':page,'page_size':size,'total':total,'items':[json.loads(x[0]) for x in vals],'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root)}
 def dashboard(self,p,include_analysis=False,basis='AUTO',trade_date=None):
  d,rev=self._pub(p)
  with self._con() as c:
   market=c.execute('select payload_json from market_daily where publication_id=?',[p]).fetchone()
   counts={'sector_daily':c.execute('select count(*) from sector_daily where publication_id=?',[p]).fetchone()[0]}
   for table,column in (('stock_daily','security_id'),('candidate_daily','security_id'),('queue_memberships','security_id')):
    counts[table]=c.execute(f'select count(*) from {table} where publication_id=? and {WORKBENCH_STATISTICAL_SCOPE_SQL.format(id=column)}',[p]).fetchone()[0]
  result={'publication_id':p,'selected_date':d,'actual_input_date':d,'latest_success_date':self.publications()['items'][0]['trade_date'],'source_revision_id':rev,'market':json.loads(market[0]) if market else None,'counts':counts,'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root)}
  if include_analysis:
   context=self._analysis_context(p,basis)
   result['item']=self._dashboard_analysis(p,d,trade_date,context,result['market'])
   result['item']['contract_id']=OVERVIEW_CONTRACT_ID
   result.update(self._analysis_meta(context,{'include_analysis':True,'basis':basis,'trade_date':trade_date},result['item'].get('trade_date') or d,result['item'].get('returned_range')))
   result['contract_id']=OVERVIEW_CONTRACT_ID
  return result
 def _dashboard_analysis(self,p,publication_date,trade_date,context,market_payload):
  """Build the bounded API30 overview from the selected analysis snapshot.

  Every optional section is read from the snapshot's own entry for its latest
  available date.  A missing domain is represented as UNAVAILABLE, rather
  than being filled with a publication-table proxy.
  """
  selected=context['selected'];requested=str(trade_date or publication_date)
  try: requested=date.fromisoformat(requested).isoformat()
  except (TypeError,ValueError): raise ValueError('DATE_INVALID')
  if requested>selected['cutoff_date']: raise ValueError('DATE_AFTER_CUTOFF')
  with self._con() as c:
   def latest_entry(domain):
    return c.execute("""select e.slice_id,cast(e.trade_date as varchar),s.contract_id
                         from analysis_snapshot_entries e join analysis_slices s using(slice_id)
                        where e.snapshot_id=? and e.domain=? and e.trade_date<=?
                        order by e.trade_date desc limit 1""",[selected['snapshot_id'],domain,requested]).fetchone()
   cycle=latest_entry('sector_cycle'); mainline=latest_entry('mainline'); representative=latest_entry('representative')
   market_cycle=latest_entry('market_cycle')
   market_summary=self._overview_market_summary(market_payload,market_cycle,c,requested)
   sectors=self._overview_strong_sectors(c,selected['snapshot_id'],cycle)
   mainline_counts=self._overview_mainline_counts(c,selected['snapshot_id'],mainline)
   representatives=self._overview_representatives(c,p,selected['snapshot_id'],representative)
  dates=[value for value in (cycle[1] if cycle else None,mainline[1] if mainline else None,representative[1] if representative else None) if value]
  return {'publication_id':p,'trade_date':requested,'snapshot_id':selected['snapshot_id'],'resolved_basis':context['resolved_basis'],'market_summary':market_summary,'strong_sectors':sectors,'mainline_counts':mainline_counts,'representatives':representatives,'priority_research':{'contract_id':PRIORITY_RESEARCH_CONTRACT_ID,'endpoint':'/api/candidates','page_size':50},'returned_range':{'from':min(dates) if dates else None,'to':max(dates) if dates else None,'dates':sorted(set(dates))}}
 def _overview_market_summary(self,payload,market_cycle,connection,trade_date):
  payload=payload or {}
  had_market_payload=bool(payload)
  source='market_daily'
  if market_cycle:
   row=connection.execute("""select quote_valid_count,up_count,down_count,flat_count,amount_sum,amount_valid_count,
          ma20_above_count,ma20_valid_count,ma60_above_count,ma60_valid_count,queue_unique_count,capabilities
     from market_cycle_daily where slice_id=? and trade_date=?""",[market_cycle[0],market_cycle[1]]).fetchone()
   if row:
    quote_valid,up,down,flat,amount,amount_valid,ma20_above,ma20_valid,ma60_above,ma60_valid,queue_unique,capabilities=row
    cycle_payload={'breadth_ret5_pos':None,'breadth_ret20_pos':(up/quote_valid if quote_valid else None),'breadth_above_ma20':(ma20_above/ma20_valid if ma20_valid else None),'amount_ratio_5_20_median':None,'market_ret20_median':None,'valid_universe_count':quote_valid,'up_count':up,'down_count':down,'flat_count':flat,'amount_sum':amount,'amount_valid_count':amount_valid,'ma20_above_count':ma20_above,'ma20_valid_count':ma20_valid,'ma60_above_count':ma60_above,'ma60_valid_count':ma60_valid,'queue_unique_count':queue_unique,'capabilities':_json_value(capabilities,{})}
    payload={**cycle_payload,**payload} if payload else cycle_payload
    source='market_cycle' if not had_market_payload else source
  cards=[
   {'id':'breadth_ret5_pos','label':'5日上涨宽度','value':payload.get('breadth_ret5_pos'),'unit':'percent','target':'market'},
   {'id':'breadth_ret20_pos','label':'20日上涨宽度','value':payload.get('breadth_ret20_pos'),'unit':'percent','target':'market'},
   {'id':'breadth_above_ma20','label':'站上MA20','value':payload.get('breadth_above_ma20'),'unit':'percent','target':'technical'},
   {'id':'amount_ratio_5_20_median','label':'5/20日量额比','value':payload.get('amount_ratio_5_20_median'),'unit':'ratio','target':'market'},
   {'id':'market_ret20_median','label':'20日市场中位收益','value':payload.get('market_ret20_median'),'unit':'percent','target':'market'},
   {'id':'valid_universe_count','label':'有效统计股票','value':payload.get('valid_universe_count') or payload.get('normal_universe_count'),'unit':'count','target':'technical'},
  ]
  result={'status':'AVAILABLE' if payload else 'UNAVAILABLE','trade_date':trade_date,'cards':cards,'quality_flag':payload.get('quality_flag'),'source':source}
  if market_cycle:
   result['market_cycle']={'trade_date':market_cycle[1],'slice_id':market_cycle[0],'contract_id':market_cycle[2]}
  return result
 def _overview_strong_sectors(self,connection,snapshot_id,entry):
  groups={key:{'label':'行业' if key=='INDUSTRY' else '概念','status':'UNAVAILABLE','total':0,'items':[]} for key in ('INDUSTRY','THEME')}
  if not entry:return groups
  rows=connection.execute("""select sector_id,cast(trade_date as varchar),sector_name,sector_type,rank,
         sector_rs20_pct,board_quote_ret1,member_ret1_median,member_amount_sum,
         total_member_count,quote_valid_count,coverage,breadth_ret1,diffusion_state,
         history_basis,contract_id
    from sector_cycle_daily where slice_id=? and trade_date=?
      and sector_type in ('INDUSTRY','THEME')
    order by sector_type,rank nulls last,sector_id""",[entry[0],entry[1]]).fetchall()
  for row in rows:
   key=str(row[3]).upper()
   if key not in groups:continue
   groups[key]['total']+=1
   if len(groups[key]['items'])>=10:continue
   groups[key]['status']='AVAILABLE'
   names=('sector_id','trade_date','sector_name','sector_type','rank','sector_rs20_pct','board_quote_ret1','member_ret1_median','member_amount_sum','total_member_count','quote_valid_count','coverage','breadth_ret1','diffusion_state','history_basis','contract_id')
   groups[key]['items'].append(dict(zip(names,row)))
  for group in groups.values():
   if group['total'] and group['status']=='UNAVAILABLE':group['status']='AVAILABLE'
  return groups
 def _overview_mainline_counts(self,connection,snapshot_id,entry):
  counts={key:0 for key in ('FADING','HIGH_LEVEL_CONTRACTION','REACCELERATING','SUSTAINED','NEW','BROADENING','OBSERVING','DATA_INSUFFICIENT')}
  if not entry:return {'status':'UNAVAILABLE','trade_date':None,'total':0,'counts':counts,'contract_id':None}
  rows=connection.execute("select mainline_class,count(*) from mainline_daily where slice_id=? and trade_date=? group by mainline_class",[entry[0],entry[1]]).fetchall()
  for key,value in rows:counts[str(key)]=int(value)
  return {'status':'AVAILABLE','trade_date':entry[1],'total':sum(counts.values()),'counts':counts,'contract_id':entry[2]}
 def _overview_representatives(self,connection,p,snapshot_id,entry):
  result={'status':'UNAVAILABLE','trade_date':entry[1] if entry else None,'total_unique':0,'items':[],'contract_id':entry[2] if entry else None}
  if not entry:return result
  rows=connection.execute("""select r.sector_id,cast(r.trade_date as varchar),r.ranked_first_id,r.ranked_second_id,
         r.confirmed_id,r.candidate_id,r.candidate_since,r.candidate_streak,r.confirmed_since,
         r.confirmation_event,r.previous_confirmed_id,r.stale,r.representative_rank_basis,
         r.history_basis,r.contract_id,sd.sector_name,sd.sector_type
    from representative_state_daily r
    left join sector_daily sd on sd.publication_id=? and sd.sector_id=r.sector_id and cast(sd.trade_date as varchar)=cast(r.trade_date as varchar)
   where r.slice_id=? and r.trade_date=?
     and coalesce(r.confirmed_id,r.candidate_id,r.ranked_first_id) is not null
   order by case when r.confirmed_id is not null then 0 when r.candidate_id is not null then 1 else 2 end,
            r.candidate_streak desc nulls last,r.sector_id""",[p,entry[0],entry[1]]).fetchall()
  names=('sector_id','trade_date','ranked_first_id','ranked_second_id','confirmed_id','candidate_id','candidate_since','candidate_streak','confirmed_since','confirmation_event','previous_confirmed_id','stale','representative_rank_basis','history_basis','contract_id','sector_name','sector_type')
  by_security={}
  ids=set()
  for raw in rows:
   value=dict(zip(names,raw));security_id=value.get('confirmed_id') or value.get('candidate_id') or value.get('ranked_first_id')
   if not security_id:continue
   ids.add(str(security_id)); group=by_security.setdefault(str(security_id),{'security_id':str(security_id),'representative_status':'CANDIDATE','candidate_streak':None,'stale':True,'sector_sources':[],'history_basis':value.get('history_basis'),'contract_id':value.get('contract_id')})
   status='CONFIRMED' if value.get('confirmed_id') else 'CANDIDATE'
   if status=='CONFIRMED':group['representative_status']='CONFIRMED'
   streak=value.get('candidate_streak')
   if streak is not None and (group['candidate_streak'] is None or streak>group['candidate_streak']):group['candidate_streak']=streak
   group['stale']=bool(group['stale'] and value.get('stale'))
   group['sector_sources'].append({'sector_id':value.get('sector_id'),'sector_name':value.get('sector_name') or value.get('sector_id'),'sector_type':value.get('sector_type'),'status':status,'candidate_since':value.get('candidate_since'),'confirmed_since':value.get('confirmed_since'),'confirmation_event':value.get('confirmation_event')})
  labels=self._security_names(p,ids)
  items=list(by_security.values())
  for item in items:item['security_name']=labels.get(item['security_id'],item['security_id']);item['source_sector_count']=len(item['sector_sources'])
  items.sort(key=lambda item:(0 if item['representative_status']=='CONFIRMED' else 1,-item['source_sector_count'],-(item['candidate_streak'] or 0),item['security_id']))
  result.update({'status':'AVAILABLE','total_unique':len(items),'items':items[:20]})
  return result
 def sectors(self,p,q,page,size,sector_type='',include_analysis=False,basis='AUTO',trade_date=None):
  extra='and (sector_name ilike ? or sector_id ilike ?)'; args=(f'%{q}%',f'%{q}%')
  if sector_type: extra+=' and sector_type=?'; args += (sector_type,)
  result=self._rows('sector_daily',p,extra,args,'display_rank nulls last, sector_id',page,size)
  ids={item['sector_id'] for item in result['items']};quotes=self._quotes(p)
  if ids:
   with self._con() as c:
    _,relation_edges=self._publication_edges(c,p)
    members=sorted({(edge.sector_id,edge.security_id) for edge in relation_edges if edge.sector_id in ids and is_workbench_statistical_security_id(edge.security_id,self._root)})
   grouped={sid:{'members':[],'quotes':[]} for sid in ids}
   for sid,security_id in members:
    if is_workbench_statistical_security_id(security_id, self._root):
     grouped[sid]['members'].append(security_id)
     if security_id in quotes: grouped[sid]['quotes'].append(quotes[security_id])
   for item in result['items']:
    group=grouped[item['sector_id']];values=group['quotes'];returns=sorted(x['RET1'] for x in values if x.get('RET1') is not None)
    item['sector_ret1_median']=returns[len(returns)//2] if len(returns)%2 else (returns[len(returns)//2-1]+returns[len(returns)//2])/2 if returns else None
    item['sector_turnover_amount']=sum(x['turnover_amount'] for x in values if x.get('turnover_amount') is not None)
    item['total_member_count']=len(group['members'])
    item['quote_valid_count']=len(values)
  if include_analysis:
   context=self._analysis_context(p,basis);as_of=self._analysis_as_of(context,trade_date,('sector_cycle','sector_base'))
   meta_trade=as_of or (result['items'][0].get('trade_date') if result['items'] else None)
   result.update(self._analysis_meta(context,{'q':q,'page':page,'page_size':size,'sector_type':sector_type,'basis':basis,'trade_date':trade_date},meta_trade,None))
  return result
 def _attribute_snapshot(self,p,basis='AUTO',trade_date=None):
  self._pub(p)
  basis=str(basis or 'AUTO').strip().upper()
  if basis not in {'AUTO','OBSERVED','RECONSTRUCTED'}: raise ValueError('BASIS_UNSUPPORTED')
  requested={'OBSERVED':'LOCAL_OBSERVED','RECONSTRUCTED':'LOCAL_RECONSTRUCTED'}.get(basis)
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('sector_base','member_state'));date_filter=' and e.trade_date<=?' if as_of else ''
  with self._con() as c:
   base=c.execute("select e.slice_id,cast(e.trade_date as varchar),s.contract_id,s.input_hash,s.logical_hash,s.basis_json from analysis_snapshot_entries e join analysis_slices s on s.slice_id=e.slice_id where e.snapshot_id=? and e.domain='sector_base'"+date_filter+" order by e.trade_date desc limit 1",[selected['snapshot_id'],*([as_of] if as_of else [])]).fetchone()
   member=c.execute("select e.slice_id,cast(e.trade_date as varchar),s.contract_id,s.input_hash,s.logical_hash,s.basis_json from analysis_snapshot_entries e join analysis_slices s on s.slice_id=e.slice_id where e.snapshot_id=? and e.domain='member_state'"+date_filter+" order by e.trade_date desc limit 1",[selected['snapshot_id'],*([as_of] if as_of else [])]).fetchone()
  if not base or not member: raise ValueError('ATTRIBUTE_LIBRARY_NOT_BUILT')
  if as_of and (base[1]!=as_of or member[1]!=as_of): raise ValueError('TRADE_DATE_UNAVAILABLE')
  names=('slice_id','trade_date','contract_id','input_hash','logical_hash','basis_json')
  base_meta=dict(zip(names,base));member_meta=dict(zip(names,member));as_of=max(base_meta['trade_date'],member_meta['trade_date'])
  source=build_source_metadata(snapshot_id=selected['snapshot_id'],as_of_trade_date=as_of,base_slice=base_meta,member_slice=member_meta)
  return selected['snapshot_id'],base_meta,member_meta,as_of,source
 def sector_library(self,p,page=1,size=50,q='',sector_type='',bucket='',basis='AUTO',trade_date=None):
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));sector_type=str(sector_type or '').strip().upper();bucket=str(bucket or '').strip().upper();q=str(q or '').strip()
  if sector_type not in {'','INDUSTRY','THEME','STYLE'}: raise ValueError('SECTOR_TYPE_UNSUPPORTED')
  if bucket not in set(BUCKET_LABELS)|{''}: raise ValueError('SEMANTIC_BUCKET_UNSUPPORTED')
  snapshot_id,base,_,as_of,source=self._attribute_snapshot(p,basis,trade_date);context=self._analysis_context(p,basis)
  conditions=['slice_id=?','trade_date=?'];params=[base['slice_id'],as_of]
  if sector_type:conditions.append('upper(sector_type)=?');params.append(sector_type)
  if q:conditions.append('(sector_id ilike ? or sector_name ilike ?)');params.extend([f'%{q}%',f'%{q}%'])
  with self._con() as c:
   rows=c.execute('select sector_id,sector_name,sector_type,sector_role,bucket,sector_valid,total_member_count,quote_valid_count,factor_valid_count,coverage from sector_base_daily where '+' and '.join(conditions)+' order by sector_name,sector_id',params).fetchall()
  items=[]
  for row in rows:
   raw=dict(zip(('sector_id','sector_name','sector_type','sector_role','bucket','sector_valid','total_member_count','quote_valid_count','factor_valid_count','coverage'),row));item=sector_attribute_item(raw,source)
   if not bucket or item['semantic_bucket']==bucket:items.append(item)
  total=len(items);start=(page-1)*size;page_items=items[start:start+size];counts={key:sum(1 for item in items if item['semantic_bucket']==key) for key in BUCKET_LABELS}
  result={'publication_id':p,'contract_id':'M11_ATTRIBUTE_LIBRARY_V1_0','snapshot_id':snapshot_id,'as_of_trade_date':as_of,'page':page,'page_size':size,'total':total,'bucket_counts':counts,'source':source,'items':page_items,'statistical_scope':workbench_statistical_scope(self._root)}
  result.update(self._analysis_meta(context,{'page':page,'page_size':size,'q':q,'sector_type':sector_type,'bucket':bucket,'basis':basis,'trade_date':trade_date},as_of,{'from':as_of,'to':as_of,'dates':[as_of]}))
  return result
 def stock_memberships(self,p,security_id,page=1,size=50,bucket='',basis='AUTO',trade_date=None):
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));security_id=str(security_id or '').strip();bucket=str(bucket or '').strip().upper()
  if not security_id: raise ValueError('SECURITY_ID_REQUIRED')
  if not is_workbench_visible_security_id(security_id, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  if bucket not in set(BUCKET_LABELS)|{''}: raise ValueError('SEMANTIC_BUCKET_UNSUPPORTED')
  snapshot_id,base,member,as_of,source=self._attribute_snapshot(p,basis,trade_date);context=self._analysis_context(p,basis)
  with self._con() as c:
   rows=c.execute('''select b.sector_id,b.sector_name,b.sector_type,b.sector_role,b.bucket,b.sector_valid,b.total_member_count,b.quote_valid_count,b.factor_valid_count,b.coverage,
          m.member_present,m.member_rank,m.rank_valid_count
       from member_state_result_daily m join sector_base_daily b on b.slice_id=? and b.trade_date=? and b.sector_id=m.sector_id
      where m.slice_id=? and m.trade_date=? and m.security_id=? and m.member_present=true
      order by b.sector_name,b.sector_id''',[base['slice_id'],as_of,member['slice_id'],as_of,security_id]).fetchall()
  items=[]
  for row in rows:
   raw=dict(zip(('sector_id','sector_name','sector_type','sector_role','bucket','sector_valid','total_member_count','quote_valid_count','factor_valid_count','coverage','member_present','member_rank','rank_valid_count'),row));sector=sector_attribute_item(raw,source)
   if not bucket or sector['semantic_bucket']==bucket:items.append(membership_item(raw,sector,source))
  total=len(items);start=(page-1)*size;page_items=items[start:start+size];groups=[]
  for group_bucket,label in BUCKET_LABELS.items():
   group_items=[item for item in page_items if item['semantic_bucket']==group_bucket]
   group_total=sum(1 for item in items if item['semantic_bucket']==group_bucket)
   if group_items:groups.append({'semantic_bucket':group_bucket,'label':label,'total':group_total,'items':group_items})
  result={'publication_id':p,'security_id':security_id,'contract_id':'M11_ATTRIBUTE_LIBRARY_V1_0','snapshot_id':snapshot_id,'as_of_trade_date':as_of,'page':page,'page_size':size,'total':total,'source':source,'items':page_items,'groups':groups,'display_scope':self._display_scope}
  result.update(self._analysis_meta(context,{'security_id':security_id,'page':page,'page_size':size,'bucket':bucket,'basis':basis,'trade_date':trade_date},as_of,{'from':as_of,'to':as_of,'dates':[as_of]}))
  return result
 def _resolve_intersection_sector_names(self,connection,slice_id,trade_date,names,field):
  resolved=[];labels={}
  for name in names:
   rows=connection.execute('select sector_id,sector_name from sector_base_daily where slice_id=? and trade_date=? and lower(trim(sector_name))=lower(trim(?)) order by sector_id',[slice_id,trade_date,name]).fetchall()
   if not rows: raise ValueError(field+'_NOT_FOUND')
   if len(rows)>1: raise ValueError(field+'_AMBIGUOUS')
   sector_id,sector_name=str(rows[0][0]),str(rows[0][1] or name)
   resolved.append(sector_id);labels[sector_id]=sector_name
  return resolved,labels

 def _filter_intersection_research_roles(self,connection,candidates,request,publication_id,trade_date):
  context_id=request.get('research_context_id');member_role=request.get('member_role')
  if not context_id and not member_role:
   return candidates,None,None
  if not context_id:
   raise ValueError('RESEARCH_CONTEXT_REQUIRED')
  try:
   context=self._research_contexts.resolve_id(context_id,connection)
  except ResearchContextError as exc:
   raise ValueError(str(exc)) from exc
  if context['publication_id']!=str(publication_id): raise ValueError('CONTEXT_PUBLICATION_MISMATCH')
  if str(context['local_date'])!=str(trade_date): raise ValueError('CONTEXT_TRADE_DATE_MISMATCH')
  role=member_role or 'ALL_MEMBERS'
  if role=='ALL_MEMBERS':
   return candidates,context,role
  include_ids=request['include_sector_ids']
  placeholders=','.join('?' for _ in include_ids)
  try:
   role_rows=connection.execute('select distinct security_id from research_sector_member_roles where run_id=? and role=? and sector_id in ('+placeholders+')',[context['run_id'],role,*include_ids]).fetchall()
  except duckdb.CatalogException:
   role_rows=[]
  allowed={str(row[0]) for row in role_rows}
  return [item for item in candidates if item[0] in allowed],context,role

 def sector_intersection_query(self,body):
  request=normalize_request(body)
  p=request['publication_id'];snapshot_id,base,member,latest_date,source=self._attribute_snapshot(p,request['basis'],request['trade_date'])
  with self._con() as c:
   available_dates=[str(row[0]) for row in c.execute("select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='member_state' order by trade_date",[snapshot_id]).fetchall()]
   trade_date=request['trade_date'] or (available_dates[-1] if available_dates else str(latest_date))
   if trade_date not in available_dates: raise ValueError('TRADE_DATE_UNAVAILABLE')
   include_name_ids,include_name_labels=self._resolve_intersection_sector_names(c,base['slice_id'],trade_date,request.get('include_sector_names',[]),'INCLUDE_SECTOR_NAME')
   exclude_name_ids,exclude_name_labels=self._resolve_intersection_sector_names(c,base['slice_id'],trade_date,request.get('exclude_sector_names',[]),'EXCLUDE_SECTOR_NAME')
   def merge_ids(values):
    result=[];seen=set()
    for value in values:
     value=str(value)
     if value not in seen: seen.add(value);result.append(value)
    return result
   request['include_sector_ids']=merge_ids(request['include_sector_ids']+include_name_ids)
   request['exclude_sector_ids']=merge_ids(request['exclude_sector_ids']+exclude_name_ids)
   if len(request['include_sector_ids'])<2: raise ValueError('INCLUDE_SECTOR_IDS_MIN_2')
   if len(request['include_sector_ids'])>4: raise ValueError('INCLUDE_SECTOR_IDS_MAX_4')
   if len(request['exclude_sector_ids'])>20: raise ValueError('EXCLUDE_SECTOR_IDS_MAX_20')
   sector_ids=request['include_sector_ids']+request['exclude_sector_ids'];placeholders=','.join('?' for _ in sector_ids)
   rows=c.execute('''select m.security_id,m.sector_id,m.member_rank,m.rank_valid_count,b.sector_name,b.sector_type,b.sector_role,b.bucket,b.sector_valid,b.total_member_count,b.factor_valid_count,b.coverage
       from member_state_result_daily m join sector_base_daily b on b.slice_id=? and b.trade_date=? and b.sector_id=m.sector_id
      where m.slice_id=? and m.trade_date=? and m.member_present=true and m.sector_id in ('''+placeholders+''')''',[base['slice_id'],trade_date,member['slice_id'],trade_date,*sector_ids]).fetchall()
   grouped={};include_set=set(request['include_sector_ids']);exclude_set=set(request['exclude_sector_ids'])
   from workbench_service.universe import is_workbench_visible_security_id
   for row in rows:
    values=dict(zip(('security_id','sector_id','member_rank','rank_valid_count','sector_name','sector_type','sector_role','bucket','sector_valid','total_member_count','factor_valid_count','coverage'),row))
    if not is_workbench_visible_security_id(values['security_id'], self._root): continue
    entry=grouped.setdefault(values['security_id'],{'include':{},'all_sector_ids':set()});entry['all_sector_ids'].add(values['sector_id'])
    if values['sector_id'] in include_set: entry['include'][values['sector_id']]=values
   candidates=[]
   for security_id,entry in grouped.items():
    matched=entry['include'];qualifies=len(matched)==len(include_set) if request['operator']=='INTERSECTION' else bool(matched)
    if qualifies and not (entry['all_sector_ids'] & exclude_set): candidates.append((security_id,entry))
   candidates,research_context,member_role=self._filter_intersection_research_roles(c,candidates,request,p,trade_date)
   candidate_ids=[item[0] for item in candidates];domain_slices={}
   for domain in ('technical','strength','summary','high'):
    found=c.execute("select slice_id from analysis_snapshot_entries where snapshot_id=? and domain=? and trade_date=?",[snapshot_id,domain,trade_date]).fetchone();domain_slices[domain]=found[0] if found else None
   technical={};strength={};summary={};high={}
   if candidate_ids:
    ids_sql=','.join('?' for _ in candidate_ids)
    if domain_slices['technical']:
     for row in c.execute('select security_id,raw_close,adj_close,quote_ret1,raw_amount,raw_volume,ret20,amount_vs_prior20,amount_class,ma_alignment,validity,quality_codes from technical_result_daily where slice_id=? and trade_date=? and security_id in ('+ids_sql+')',[domain_slices['technical'],trade_date,*candidate_ids]).fetchall(): technical[row[0]]=dict(zip(('security_id','raw_close','adj_close','quote_ret1','raw_amount','raw_volume','ret20','amount_vs_prior20','amount_class','ma_alignment','validity','quality_codes'),row))
    if domain_slices['strength']:
     for row in c.execute('select security_id,rps20 from strength_result_daily where slice_id=? and trade_date=? and security_id in ('+ids_sql+')',[domain_slices['strength'],trade_date,*candidate_ids]).fetchall(): strength[row[0]]={'rps20':row[1]}
    if domain_slices['summary']:
     for row in c.execute('select security_id,queues_json,research_band,research_band_quality,unique_hit_count from structure_summary_result_daily where slice_id=? and trade_date=? and security_id in ('+ids_sql+')',[domain_slices['summary'],trade_date,*candidate_ids]).fetchall(): summary[row[0]]=dict(zip(('security_id','queues_json','research_band','research_band_quality','unique_hit_count'),row))
    if domain_slices['high'] and request['filters'].get('new_high_window') is not None:
     high_window=request['filters']['new_high_window']
     for row in c.execute('select security_id,"window",new_high,prior_max_close,streak,is_left_censored,dist_prior_high,valid_n,quality_codes from high_result_daily where slice_id=? and trade_date=? and "window"=? and security_id in ('+ids_sql+')',[domain_slices['high'],trade_date,high_window,*candidate_ids]).fetchall(): high[row[0]]=dict(zip(('security_id','window','new_high','prior_max_close','streak','is_left_censored','dist_prior_high','valid_n','quality_codes'),row))
    names=self._security_names(p,set(candidate_ids))
   else:names={}
  output=[]
  for security_id,entry in candidates:
   tech=technical.get(security_id,{});rps=strength.get(security_id,{});structure=summary.get(security_id,{});high_state=high.get(security_id);queues=structure.get('queues_json')
   if isinstance(queues,str):
    try: queues=json.loads(queues)
    except (TypeError,json.JSONDecodeError): queues={}
   quality=tech.get('quality_codes')
   if isinstance(quality,str):
    try: quality=json.loads(quality)
    except (TypeError,json.JSONDecodeError): quality=[]
   matched=entry['include'];ranks={sid:values.get('member_rank') for sid,values in matched.items()};rank_counts={sid:values.get('rank_valid_count') for sid,values in matched.items()};finite_ranks=[float(value) for value in ranks.values() if isinstance(value,(int,float)) and math.isfinite(float(value))]
   item={'security_id':security_id,'security_name':names.get(security_id,security_id),'trade_date':trade_date,'matched_sector_ids':sorted(matched),'matched_sector_names':{sid:values.get('sector_name') for sid,values in sorted(matched.items())},'matched_sector_member_ranks':ranks,'matched_sector_rank_valid_counts':rank_counts,'matched_sector_count':len(matched),'member_rank':min(finite_ranks) if finite_ranks else None,'raw_close':tech.get('raw_close'),'adj_close':tech.get('adj_close'),'quote_ret1':tech.get('quote_ret1'),'raw_amount':tech.get('raw_amount'),'raw_volume':tech.get('raw_volume'),'ret20':tech.get('ret20'),'rps20':rps.get('rps20'),'amount_vs_prior20':tech.get('amount_vs_prior20'),'amount_class':tech.get('amount_class'),'ma_alignment':tech.get('ma_alignment'),'validity':tech.get('validity'),'quality_codes':quality or [],'queues_json':queues or {},'research_band':structure.get('research_band'),'research_band_quality':structure.get('research_band_quality'),'unique_hit_count':structure.get('unique_hit_count'),'new_high_state':high_state}
   if passes_filters(item,request['filters']):output.append(item)
  output=sort_items(output,request['sort']);total=len(output);start=(request['page']-1)*request['page_size'];page_items=[safe_value(item) for item in output[start:start+request['page_size']]];source=dict(source);source['filter_slice_ids']=domain_slices
  context=self._analysis_context(p,request['basis'])
  result={'publication_id':p,'contract_id':INTERSECTION_CONTRACT_ID,'snapshot_id':snapshot_id,'trade_date':trade_date,'operator':request['operator'],'include_sector_ids':request['include_sector_ids'],'exclude_sector_ids':request['exclude_sector_ids'],'filters':request['filters'],'sort':request['sort'],'page':request['page'],'page_size':request['page_size'],'candidate_total_before_filters':len(candidates),'total':total,'source':source,'items':page_items,'display_scope':self._display_scope}
  if request.get('include_sector_names') or request.get('exclude_sector_names') or request.get('research_context_id') or request.get('member_role'):
   result.update({'p10_contract_id':P10_INTERSECTION_CONTRACT_ID,'include_sector_names':request.get('include_sector_names',[]),'exclude_sector_names':request.get('exclude_sector_names',[]),'resolved_sector_selections':{'include':[{'sector_id':sector_id,'sector_name':include_name_labels.get(sector_id)} for sector_id in request['include_sector_ids']],'exclude':[{'sector_id':sector_id,'sector_name':exclude_name_labels.get(sector_id)} for sector_id in request['exclude_sector_ids']]},'research_context_id':request.get('research_context_id'),'member_role':member_role or 'ALL_MEMBERS'})
   if research_context: result['research_context']={'context_id':research_context['context_id'],'run_id':research_context['run_id'],'local_date':research_context['local_date']}
  result.update(self._analysis_meta(context,request,trade_date,{'from':trade_date,'to':trade_date,'dates':[trade_date]}))
  return result
 def sector_associations(self,p,security_id,days=1,include_rejected=False,page=1,size=50,basis='AUTO',trade_date=None):
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));days=max(1,min(250,int(days)))
  security_id=str(security_id or '').strip()
  if not security_id: raise ValueError('SECURITY_ID_REQUIRED')
  if not is_workbench_visible_security_id(security_id, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  if include_rejected and days!=1: raise ValueError('REJECTED_DETAILS_REQUIRE_DAYS_1')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('association',))
  with self._con() as c:
   dates=[str(row[0]) for row in c.execute("select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='association' order by trade_date desc",[selected['snapshot_id']]).fetchall()]
   if not dates: raise ValueError('ASSOCIATION_NOT_BUILT')
   if as_of and as_of not in dates: raise ValueError('TRADE_DATE_UNAVAILABLE')
   end=as_of or dates[0];selected_dates=[value for value in dates if value<=end][:days]
   if include_rejected: selected_dates=selected_dates[:1]
   placeholders=','.join('?' for _ in selected_dates)
   eligible_clause='' if include_rejected else ' and a.eligible=true and a.association_rank is not null and a.association_rank<=3'
   rows=c.execute(f'''select a.trade_date,a.sector_id,a.sector_name,a.sector_type,a.semantic_bucket,
                             a.association_rank,a.eligible,a.rejection_reasons,a.pattern,a.member_rank,
                             a.member_rank_valid_count,a.member_percentile,a.sector_coverage,a.sector_rs5_pct,
                             a.sector_rs20_pct,a.loo_ret20_median,a.loo_breadth20,a.loo_ret5_median,
                             a.loo_breadth5,a.evidence_json,a.contract_id,a.history_basis,a.membership_snapshot_id
                        from stock_sector_associations_daily a
                        join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='association'
                         and e.trade_date=a.trade_date and e.slice_id=a.slice_id
                       where a.security_id=? and a.trade_date in ({placeholders}){eligible_clause}
                       order by a.trade_date desc, a.association_rank nulls last, a.sector_id''',[selected['snapshot_id'],security_id,*selected_dates]).fetchall()
  columns=('trade_date','sector_id','sector_name','sector_type','semantic_bucket','association_rank','eligible','rejection_reasons','pattern','member_rank','member_rank_valid_count','member_percentile','sector_coverage','sector_rs5_pct','sector_rs20_pct','loo_ret20_median','loo_breadth20','loo_ret5_median','loo_breadth5','evidence_json','contract_id','history_basis','membership_snapshot_id')
  items=[]
  for row in rows:
   item=dict(zip(columns,row));item['trade_date']=str(item['trade_date']);item['eligible']=bool(item['eligible'])
   for field in ('rejection_reasons','evidence_json'):
    item[field]=_json_value(item[field],[] if field=='rejection_reasons' else {})
   items.append(item)
  total=len(items);start=(page-1)*size;page_items=items[start:start+size]
  result={'publication_id':p,'security_id':security_id,'contract_id':ASSOCIATION_CONTRACT_ID,'days':days,'include_rejected':bool(include_rejected),'page':page,'page_size':size,'total':total,'items':page_items,'groups':[{'trade_date':day,'items':[item for item in page_items if item['trade_date']==day]} for day in selected_dates if any(item['trade_date']==day for item in page_items)],'display_scope':self._display_scope}
  result.update(self._analysis_meta(context,{'security_id':security_id,'days':days,'include_rejected':bool(include_rejected),'page':page,'page_size':size,'basis':basis,'trade_date':trade_date},selected_dates[-1] if selected_dates else end,{'from':selected_dates[-1] if selected_dates else end,'to':selected_dates[0] if selected_dates else end,'dates':selected_dates}))
  return result
 def stocks(self,p,q,page,size): return self._add_quotes(p,self._rows('stock_daily',p,'and '+WORKBENCH_STATISTICAL_SCOPE_SQL.format(id='security_id')+' and (security_name ilike ? or security_id ilike ?)',(f'%{q}%',f'%{q}%'),'security_id',page,size))
 def technical(self,p,page=1,size=50,basis='AUTO',ma_state='',rps_window='',rps_min='',amount_class_filter='',turnover_min='',quality_filter='',research_band='',trade_date=None):
  if basis not in ('AUTO','OBSERVED','RECONSTRUCTED'): raise ValueError('BASIS_UNSUPPORTED')
  if quality_filter not in ('','INCLUDE_UNKNOWN'): raise ValueError('QUALITY_FILTER_UNSUPPORTED')
  research_band=str(research_band or '').strip().upper()
  if research_band not in ('','RESEARCHABLE','CORE_RESEARCH','SUPPORTED_RESEARCH','DIAGNOSTIC_ONLY'): raise ValueError('RESEARCH_BAND_UNSUPPORTED')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('technical',));date_filter=" and trade_date<=?" if as_of else ''
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
  joins=" left join analysis_snapshot_entries se on se.snapshot_id=e.snapshot_id and se.domain='strength' and se.trade_date=e.trade_date left join strength_result_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=t.security_id left join analysis_snapshot_entries ue on ue.snapshot_id=e.snapshot_id and ue.domain='summary' and ue.trade_date=e.trade_date left join structure_summary_result_daily ss on ss.slice_id=ue.slice_id and ss.trade_date=ue.trade_date and ss.security_id=t.security_id"
  include_unknown=quality_filter=='INCLUDE_UNKNOWN';filters=['e.snapshot_id=?',"e.trade_date=(select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='technical'"+date_filter+")",WORKBENCH_SCOPE_SQL.format(id='t.security_id')];params=[selected['snapshot_id'],selected['snapshot_id'],*([as_of] if as_of else [])]
  if ma_state:filters.append('(t.ma_alignment=?'+(' or t.ma_alignment is null)' if include_unknown else ')'));params.append(ma_state)
  if amount_class_filter:filters.append('(t.amount_class=?'+(' or t.amount_class is null)' if include_unknown else ')'));params.append(amount_class_filter)
  if rps_value is not None:filters.append(f'(st.rps{rps_width}>=?'+(f' or st.rps{rps_width} is null)' if include_unknown else ')'));params.append(rps_value)
  if research_band=='RESEARCHABLE':
   filters.append("ss.research_band in ('CORE_RESEARCH','SUPPORTED_RESEARCH')")
  elif research_band=='DIAGNOSTIC_ONLY':
   # v2 contract: diagnostic is a small, explainable technical watch set,
   # not every stock which failed to hit a structure queue.
   filters.append("coalesce(ss.research_band,'DIAGNOSTIC_ONLY')='DIAGNOSTIC_ONLY'")
   filters.append("t.validity='VALID' and (st.rps20>=0.90 or (t.ma_alignment='BULLISH' and t.ret20>=0.15 and coalesce(t.amount_vs_prior20,0)>=1.20))")
  elif research_band:
   filters.append("ss.research_band=?");params.append(research_band)
  where=' and '.join(filters)
  select="t.security_id,t.trade_date,t.contract_id,t.price_basis,t.raw_close,t.adj_close,t.quote_ret1,t.raw_amount,t.raw_volume,t.ma5,t.ma10,t.ma20,t.ma60,t.ret5,t.ret10,t.ret20,t.ret60,t.rs5,t.rs10,t.rs20,t.rs60,t.amount_ma5,t.amount_ma10,t.amount_ma20,t.amount_ratio20,t.amount_vs_prior20,t.volume_vs_prior20,t.amount_class,t.ma_alignment,t.validity,t.quality_codes,t.basis_json,st.rps5,st.rps10,st.rps20,st.rps60,st.rps_valid_universe_count5,st.rps_valid_universe_count10,st.rps_valid_universe_count20,st.rps_valid_universe_count60,coalesce(ss.research_band,'DIAGNOSTIC_ONLY'),coalesce(ss.research_band_quality,'DATA_INSUFFICIENT')"
  with self._con() as c:
   total=c.execute("select count(*) from analysis_snapshot_entries e join technical_result_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date"+joins+" where e.domain='technical' and "+where,params).fetchone()[0]
   rows=c.execute("select "+select+" from analysis_snapshot_entries e join technical_result_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date"+joins+" where e.domain='technical' and "+where+" order by st.rps20 desc nulls last,t.ret20 desc nulls last,t.security_id limit ? offset ?",params+[size,(page-1)*size]).fetchall()
  names=('security_id','trade_date','contract_id','price_basis','raw_close','adj_close','quote_ret1','raw_amount','raw_volume','ma5','ma10','ma20','ma60','ret5','ret10','ret20','ret60','rs5','rs10','rs20','rs60','amount_ma5','amount_ma10','amount_ma20','amount_ratio20','amount_vs_prior20','volume_vs_prior20','amount_class','ma_alignment','validity','quality_codes','basis','rps5','rps10','rps20','rps60','rps_valid_universe_count5','rps_valid_universe_count10','rps_valid_universe_count20','rps_valid_universe_count60','research_band','research_band_quality')
  items=[]
  for row in rows:
   item=dict(zip(names,row));item['trade_date']=str(item['trade_date']);item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];item['basis']=json.loads(item['basis']) if item['basis'] else {};items.append(item)
  result={'publication_id':p,'page':page,'page_size':size,'total':total,'basis':basis,'rps_window':rps_width,'as_of_trade_date':str(max(item['trade_date'] for item in items)) if items else None,'snapshot_id':selected['snapshot_id'],'snapshot_capability':'AVAILABLE','diagnostic_scope_contract':'TECHNICAL_DIAGNOSTIC_SCOPE_V2','diagnostic_scope':'数据有效，且 RPS20≥0.90；或多头排列、20日收益不低于15%且额比前20不低于1.20','items':items}
  result.update(self._analysis_meta(context,{'page':page,'page_size':size,'basis':basis,'ma_state':ma_state,'rps_window':rps_window,'rps_min':rps_min,'amount_class':amount_class_filter,'quality_filter':quality_filter,'research_band':research_band,'trade_date':trade_date},as_of or result['as_of_trade_date'],{'from':result['as_of_trade_date'],'to':result['as_of_trade_date'],'dates':[result['as_of_trade_date']] if result['as_of_trade_date'] else []}))
  security_names=self._security_names(p,{item['security_id'] for item in items if item.get('security_id')})
  for item in items:item['security_name']=security_names.get(item.get('security_id'))
  return self._add_quotes(p,result)
 def new_highs(self,p,page=1,size=50,basis='AUTO',window=20,streak_min='',include_ties=False,rps_min='',research_band='',trade_date=None):
  if basis not in ('AUTO','OBSERVED','RECONSTRUCTED'): raise ValueError('BASIS_UNSUPPORTED')
  research_band=str(research_band or '').strip().upper()
  if research_band not in ('','RESEARCHABLE','CORE_RESEARCH','SUPPORTED_RESEARCH','DIAGNOSTIC_ONLY'): raise ValueError('RESEARCH_BAND_UNSUPPORTED')
  try: window=int(window)
  except (TypeError,ValueError): raise ValueError('WINDOW_UNSUPPORTED')
  if window not in (20,30,60,100): raise ValueError('WINDOW_UNSUPPORTED')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('high',));date_filter=" and trade_date<=?" if as_of else ''
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));filters=["he.snapshot_id=?","he.domain='high'",'h."window"=?',"he.trade_date=(select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='high'"+date_filter+")",WORKBENCH_SCOPE_SQL.format(id='h.security_id')];params=[selected['snapshot_id'],window,selected['snapshot_id'],*([as_of] if as_of else [])]
  if not include_ties: filters.append('h.new_high=true')
  if streak_min not in ('',None): filters.append('h.streak>=?');params.append(int(streak_min))
  if rps_min not in ('',None):
   rps_value=float(rps_min)
   with self._con() as check:
    if not check.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='strength'",[selected['snapshot_id']]).fetchone()[0]: raise ValueError('RPS_NOT_BUILT')
   filters.append('st.rps20>=?');params.append(rps_value)
  if research_band=='RESEARCHABLE':
   filters.append("ss.research_band in ('CORE_RESEARCH','SUPPORTED_RESEARCH')")
  elif research_band:
   filters.append("coalesce(ss.research_band,'DIAGNOSTIC_ONLY')=?");params.append(research_band)
  where=' and '.join(filters)
  summary_joins=" left join analysis_snapshot_entries ue on ue.snapshot_id=he.snapshot_id and ue.domain='summary' and ue.trade_date=he.trade_date left join structure_summary_result_daily ss on ss.slice_id=ue.slice_id and ss.trade_date=ue.trade_date and ss.security_id=h.security_id"
  with self._con() as c:
   available=c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='high'",[selected['snapshot_id']]).fetchone()[0]
   if not available: raise ValueError('ANALYSIS_NOT_BUILT')
   total=c.execute('select count(*) from analysis_snapshot_entries he join high_result_daily h on h.slice_id=he.slice_id and h.trade_date=he.trade_date left join analysis_snapshot_entries se on se.snapshot_id=he.snapshot_id and se.domain=\'strength\' and se.trade_date=he.trade_date left join strength_result_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=h.security_id'+summary_joins+' where '+where,params).fetchone()[0]
   rows=c.execute('select h.security_id,h.trade_date,h."window",h.contract_id,h.price_basis,h.prior_max_close,h.new_high,h.at_prior_high,h.streak,h.is_left_censored,h.dist_prior_high,h.valid_n,h.quality_codes,h.basis_json,st.rps5,st.rps10,st.rps20,st.rps60,st.rps_valid_universe_count5,st.rps_valid_universe_count10,st.rps_valid_universe_count20,st.rps_valid_universe_count60,st.quality_codes,st.basis_json,coalesce(ss.research_band,\'DIAGNOSTIC_ONLY\'),coalesce(ss.research_band_quality,\'DATA_INSUFFICIENT\') from analysis_snapshot_entries he join high_result_daily h on h.slice_id=he.slice_id and h.trade_date=he.trade_date left join analysis_snapshot_entries se on se.snapshot_id=he.snapshot_id and se.domain=\'strength\' and se.trade_date=he.trade_date left join strength_result_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=h.security_id'+summary_joins+' where '+where+' order by h.streak desc nulls last,st.rps20 desc nulls last,h.security_id limit ? offset ?',params+[size,(page-1)*size]).fetchall()
  names=('security_id','trade_date','window','contract_id','price_basis','prior_max_close','new_high','at_prior_high','streak','is_left_censored','dist_prior_high','valid_n','quality_codes','basis','rps5','rps10','rps20','rps60','rps_valid_universe_count5','rps_valid_universe_count10','rps_valid_universe_count20','rps_valid_universe_count60','strength_quality_codes','strength_basis','research_band','research_band_quality')
  items=[]
  for row in rows:
   item=dict(zip(names,row));item['trade_date']=str(item['trade_date']);item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];item['basis']=json.loads(item['basis']) if item['basis'] else {};item['strength_quality_codes']=json.loads(item['strength_quality_codes']) if item['strength_quality_codes'] else [];item['strength_basis']=json.loads(item['strength_basis']) if item['strength_basis'] else {};items.append(item)
  result={'publication_id':p,'page':page,'page_size':size,'total':total,'basis':basis,'window':window,'as_of_trade_date':str(max(item['trade_date'] for item in items)) if items else None,'snapshot_id':selected['snapshot_id'],'snapshot_capability':'AVAILABLE','items':items}
  result.update(self._analysis_meta(context,{'page':page,'page_size':size,'basis':basis,'window':window,'streak_min':streak_min,'include_ties':include_ties,'rps_min':rps_min,'research_band':research_band,'trade_date':trade_date},as_of or result['as_of_trade_date'],{'from':result['as_of_trade_date'],'to':result['as_of_trade_date'],'dates':[result['as_of_trade_date']] if result['as_of_trade_date'] else []}))
  return self._add_quotes(p,self._add_stock_payloads(p,result))
 def technical_history(self,p,security_id,days=20,price_basis='ADJUSTED',fields='',basis='AUTO',trade_date=None):
  if not is_workbench_visible_security_id(security_id, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  if price_basis not in ('RAW','ADJUSTED','TDX_NATIVE_QFQ'): raise ValueError('PRICE_BASIS_UNSUPPORTED')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('technical',));cutoff_text=as_of or selected['cutoff_date']
  days=int(days);requested=tuple(x for x in str(fields).split(',') if x) if fields else ('ohlc','ma','amount','rps')
  key=chart_cache_key(selected['snapshot_id'],security_id,price_basis,cutoff_text,days,requested)
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
  source_path,_=source_info;cutoff=date.fromisoformat(cutoff_text)
  with DuckDBApiConnectionProvider(source_path).memory() as source:
   frame=source.execute('select date,raw_open,raw_high,raw_low,raw_close,adj_open,adj_high,adj_low,adj_close,raw_volume,raw_amount from read_parquet(?) where security_id=? and date<=? order by date',[str(source_path),security_id,cutoff]).df()
   expected=[row[0] for row in source.execute('select distinct date from read_parquet(?) where is_master_session and date<=? order by date',[str(source_path),cutoff]).fetchall()]
  rps={}
  with self._con() as c:
   rows=c.execute("""select s.trade_date,s.rps20 from analysis_snapshot_entries e join strength_result_daily s on s.slice_id=e.slice_id and s.trade_date=e.trade_date and s.security_id=? where e.snapshot_id=? and e.domain='strength'""",[security_id,selected['snapshot_id']]).fetchall()
  rps={row[0]:row[1] for row in rows}
  result=build_chart_points(frame,cutoff=cutoff,days=days,price_basis=price_basis,fields=requested,expected_dates=expected,rps_by_date=rps)
  result.update({'publication_id':p,'security_id':security_id,'snapshot_id':selected['snapshot_id'],'factor_evidence_basis':{'snapshot_id':selected['snapshot_id'],'rps_available':bool(rps)},'rps_capability':'AVAILABLE' if rps else 'NOT_BUILT'})
  point_dates=[point['date'] for point in result.get('points',[]) if point.get('date')]
  result.update(self._analysis_meta(context,{'security_id':security_id,'days':days,'price_basis':price_basis,'fields':list(requested),'basis':basis,'trade_date':trade_date},as_of or (point_dates[-1] if point_dates else None),{'from':point_dates[0] if point_dates else None,'to':point_dates[-1] if point_dates else None,'dates':point_dates}))
  self._chart_cache.put(key,result)
  return result
 def structure_history(self,p,security_id,days=20,queue='',basis='AUTO',trade_date=None):
  if not is_workbench_visible_security_id(security_id, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('structure',));date_filter=" and e.trade_date<=?" if as_of else ''
  days=int(days)
  if not 1<=days<=250:raise ValueError('STRUCTURE_DAYS_OUT_OF_RANGE')
  canonical=str(queue).removesuffix('_QUEUE').upper()+'_QUEUE' if queue else ''
  if canonical and canonical not in ('STEADY_QUEUE','PULLBACK_QUEUE','BREAKOUT_QUEUE','LEADER_QUEUE','EARLY_QUEUE'):raise ValueError('QUEUE_UNSUPPORTED')
  queue_filter=''
  if canonical:queue_filter=' and h.queue_name=?'
  with self._con() as c:
   available=c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='structure'",[selected['snapshot_id']]).fetchone()[0]
   if not available:raise ValueError('ANALYSIS_NOT_BUILT')
   rows=c.execute("with recent_dates as (select distinct e.trade_date from analysis_snapshot_entries e join historical_structure_result_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date where e.snapshot_id=? and e.domain='structure' and h.security_id=?"+date_filter+" order by e.trade_date desc limit ?) select h.trade_date,h.queue_name,h.hit,h.tier,h.source_class,h.research_band,h.queue_rank,h.tier_rank,h.transition,h.structure_basis,h.contract_id,h.evidence,h.quality_codes from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='structure' and e.trade_date=d.trade_date join historical_structure_result_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date where h.security_id=?"+queue_filter+" order by h.trade_date,h.queue_name",[selected['snapshot_id'],security_id,*([as_of] if as_of else []),days,selected['snapshot_id'],security_id,*([canonical] if canonical else [])]).fetchall()
  names=('trade_date','queue_name','hit','tier','source_class','research_band','queue_rank','tier_rank','transition','source_basis','contract_id','evidence','quality_codes');points=[]
  for row in rows:
   item=dict(zip(names,row));item['trade_date']=str(item['trade_date']);item['evidence']=json.loads(item['evidence']) if item['evidence'] else {};item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];points.append(item)
  point_dates=sorted({item['trade_date'] for item in points})
  result={'publication_id':p,'security_id':security_id,'snapshot_id':selected['snapshot_id'],'history_basis':selected['domain'].removeprefix('LOCAL_'),'window_left_censored':len(point_dates)<days,'points':points}
  result.update(self._analysis_meta(context,{'security_id':security_id,'days':days,'queue':queue,'basis':basis,'trade_date':trade_date},as_of or (point_dates[-1] if point_dates else None),{'from':point_dates[0] if point_dates else None,'to':point_dates[-1] if point_dates else None,'dates':point_dates}))
  return result
 def stock_insight(self,p,security_id,include='overview,technical,sector_context',days=20,basis='AUTO',trade_date=None):
  security_id=str(security_id or '').strip();days=int(days)
  if not security_id: raise ValueError('SECURITY_ID_REQUIRED')
  if not is_workbench_visible_security_id(security_id, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  if not 1<=days<=250: raise ValueError('INSIGHT_DAYS_OUT_OF_RANGE')
  requested=tuple(dict.fromkeys(value.strip() for value in str(include or 'overview,technical,sector_context').split(',') if value.strip()))
  allowed={'overview','technical','structures','sector_context'}
  if not requested or any(value not in allowed for value in requested): raise ValueError('INSIGHT_INCLUDE_UNSUPPORTED')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('technical',))
  cache_key=(selected['snapshot_id'],security_id,requested,days,as_of,context['requested_basis'])
  if cache_key in self._insight_cache: return self._insight_cache[cache_key]
  with self._con() as c:
   latest=c.execute("select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='technical'"+(' and trade_date<=?' if as_of else ''),[selected['snapshot_id'],*([as_of] if as_of else [])]).fetchone()[0]
   if latest is None: raise ValueError('INSIGHT_NOT_BUILT')
   technical_row=c.execute("""select t.raw_close,t.adj_close,t.quote_ret1,t.raw_amount,t.raw_volume,t.ma5,t.ma10,t.ma20,t.ma60,
                                    t.ret5,t.ret10,t.ret20,t.ret60,t.rs20,t.amount_ratio20,t.amount_vs_prior20,t.volume_vs_prior20,
                                    t.amount_class,t.ma_alignment,null as turnover_rate,null as turnover_basis,t.validity,t.quality_codes,t.contract_id
                               from analysis_snapshot_entries e join technical_result_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date
                              where e.snapshot_id=? and e.domain='technical' and e.trade_date=? and t.security_id=?""",[selected['snapshot_id'],latest,security_id]).fetchone()
   summary_row=c.execute("""select s.queues_json,s.research_band,s.research_band_quality,s.unique_hit_count,s.queue_contract
                             from analysis_snapshot_entries e join structure_summary_result_daily s on s.slice_id=e.slice_id and s.trade_date=e.trade_date
                            where e.snapshot_id=? and e.domain='summary' and e.trade_date=? and s.security_id=?""",[selected['snapshot_id'],latest,security_id]).fetchone()
  if not technical_row and 'technical' in requested: raise ValueError('INSIGHT_NOT_FOUND')
  quote=self._quotes(p).get(security_id,{})
  overview={'security_id':security_id,'name':quote.get('security_name') or self._security_names(p,{security_id}).get(security_id,security_id),'raw_close':quote.get('raw_close'),'quote_ret1':quote.get('quote_ret1'),'amount':quote.get('raw_amount',quote.get('turnover_amount')),'quote_state':quote.get('quote_state','UNAVAILABLE')}
  item={}
  if 'overview' in requested: item['overview']=overview
  if 'technical' in requested:
   names=('raw_close','adj_close','quote_ret1','raw_amount','raw_volume','ma5','ma10','ma20','ma60','ret5','ret10','ret20','ret60','rs20','amount_ratio20','amount_vs_prior20','volume_vs_prior20','amount_class','ma_alignment','turnover_rate','turnover_basis','validity','quality_codes','contract_id')
   technical=dict(zip(names,technical_row or [None]*len(names)));technical['trade_date']=str(latest);technical['quality_codes']=_json_value(technical.get('quality_codes'),[]);item['technical']=technical
  if 'structures' in requested:
   item['structures']={'queues':_json_value(summary_row[0],{}) if summary_row else {},'research_band':summary_row[1] if summary_row else None,'research_band_quality':summary_row[2] if summary_row else None,'unique_hit_count':summary_row[3] if summary_row else None,'queue_contract':summary_row[4] if summary_row else None,'trade_date':str(latest)}
  if 'sector_context' in requested:
   association_error=None
   try: associations=self.sector_associations(p,security_id,days=1,include_rejected=False,basis=basis,trade_date=str(latest))
   except ValueError as error: associations={'items':[],'reason':str(error)};association_error=str(error)
   association_items=associations.get('items',[])
   evidence_items=list(association_items)
   if not association_items:
    try:
     rejected=self.sector_associations(p,security_id,days=1,include_rejected=True,page=1,size=6,basis=basis,trade_date=str(latest))
     evidence_items=list(rejected.get('items',[]))[:6]
     if rejected.get('history_basis'): associations=rejected
    except ValueError as error:
     association_error=association_error or str(error)
   primary=next((row for row in association_items if row.get('association_rank')==1),None);alternatives=[row for row in association_items if row.get('association_rank') in (2,3)]
   item['sector_context']={'primary':primary,'alternatives':alternatives,'evidence_items':evidence_items,'evidence_status':'AVAILABLE' if evidence_items else ('UNAVAILABLE' if association_error else 'NO_ELIGIBLE_ASSOCIATION'),'evidence_error':association_error,'reason':'暂无可确认的强势关联板块' if not primary else None,'contract_id':ASSOCIATION_CONTRACT_ID,'history_basis':associations.get('history_basis',context['resolved_basis'])}
  result={'publication_id':p,'security_id':security_id,'status':'AVAILABLE','item':item}
  result.update(self._analysis_meta(context,{'security_id':security_id,'include':list(requested),'days':days,'basis':basis,'trade_date':trade_date},str(as_of or latest),{'from':str(as_of or latest),'to':str(as_of or latest),'dates':[str(as_of or latest)]}))
  self._insight_cache[cache_key]=result
  return result
 def market_cycle(self,p,days=60,metrics='',basis='AUTO',trade_date=None):
  days=max(1,min(250,int(days)));context=self._analysis_context(p,basis);selected=context['selected'];as_of=None;date_filter=''
  requested=tuple(dict.fromkeys(value.strip() for value in str(metrics or '').split(',') if value.strip()))
  allowed={'breadth','amount','ma','new_high','queues'}
  if any(value not in allowed for value in requested): raise ValueError('MARKET_METRIC_UNSUPPORTED')
  with self._con() as c:
   tables={row[0] for row in c.execute('show tables').fetchall()}
   materialized_count=(c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='market_cycle'",[selected['snapshot_id']]).fetchone()[0] if 'market_cycle_daily' in tables else 0)
  if materialized_count:
   materialized_as_of=self._analysis_as_of(context,trade_date,('market_cycle',)) if trade_date else None
   with self._con() as c:
    effective_date=materialized_as_of or c.execute("select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='market_cycle'",[selected['snapshot_id']]).fetchone()[0]
    rows=c.execute("select cast(m.trade_date as varchar),m.display_count,m.quote_valid_count,m.up_count,m.down_count,m.flat_count,m.amount_sum,m.amount_valid_count,m.ma20_above_count,m.ma20_valid_count,m.ma60_above_count,m.ma60_valid_count,m.new_high_counts,m.queue_counts,m.queue_unique_count,m.sector_state_counts,m.limit_up_count,m.limit_down_count,m.unknown_limit_count,m.field_coverage,m.capabilities from analysis_snapshot_entries e join market_cycle_daily m on m.slice_id=e.slice_id and m.trade_date=e.trade_date where e.snapshot_id=? and e.domain='market_cycle' and e.trade_date<=? order by e.trade_date desc limit ?",[selected['snapshot_id'],effective_date,days]).fetchall()
   points=[]
   names=('trade_date','display_count','quote_valid_count','up_count','down_count','flat_count','amount_sum','amount_valid_count','ma20_above_count','ma20_valid_count','ma60_above_count','ma60_valid_count','new_high_counts','queue_counts','queue_unique_count','sector_state_counts','limit_up_count','limit_down_count','unknown_limit_count','field_coverage','capabilities')
   for raw in reversed(rows):
    point=dict(zip(names,raw))
    for field,default in (('new_high_counts',{}),('queue_counts',{}),('sector_state_counts',None),('field_coverage',{}),('capabilities',{})):
     point[field]=_json_value(point[field],default)
    point['contract_id']=MARKET_CYCLE_CONTRACT_ID
    points.append(point)
   if not points: raise ValueError('MARKET_CYCLE_NOT_BUILT')
   result={'publication_id':p,'contract_id':MARKET_CYCLE_CONTRACT_ID,'snapshot_id':selected['snapshot_id'],'history_basis':context['resolved_basis'],'points':points,'metrics':list(requested) if requested else sorted(allowed),'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root),'materialization':'MARKET_CYCLE_DAILY'}
   result.update(self._analysis_meta(context,{'days':days,'metrics':list(requested),'basis':basis,'trade_date':trade_date},points[0]['trade_date'],{'from':points[0]['trade_date'],'to':points[-1]['trade_date'],'dates':[point['trade_date'] for point in points]}))
   return result
  as_of=self._analysis_as_of(context,trade_date,('technical',)) if trade_date else None
  date_filter=' and e.trade_date<=?' if as_of else ''
  with self._con() as c:
   dates=[str(row[0]) for row in c.execute("select distinct e.trade_date from analysis_snapshot_entries e where e.snapshot_id=? and e.domain='technical'"+date_filter+" order by e.trade_date desc limit ?",[selected['snapshot_id'],*([as_of] if as_of else []),days]).fetchall()]
   if not dates: raise ValueError('MARKET_CYCLE_NOT_BUILT')
   placeholders=','.join('?' for _ in dates)
   tech_rows=c.execute("""select cast(e.trade_date as varchar),t.security_id,t.quote_ret1,t.raw_amount,t.adj_close,t.ma20,t.ma60
                           from analysis_snapshot_entries e join technical_result_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date
                          where e.snapshot_id=? and e.domain='technical' and e.trade_date in ("""+placeholders+") order by e.trade_date,t.security_id",[selected['snapshot_id'],*dates]).fetchall()
   grouped=defaultdict(list)
   for row in tech_rows:
    if is_workbench_statistical_security_id(row[1], self._root): grouped[str(row[0])].append({'security_id':row[1],'quote_ret1':row[2],'raw_amount':row[3],'adj_close':row[4],'ma20':row[5],'ma60':row[6]})
   high=defaultdict(lambda: defaultdict(lambda: {'valid_count':0,'hit_count':0}))
   queues=defaultdict(list)
   if 'new_high' in requested or not requested:
    rows=c.execute("select cast(e.trade_date as varchar),h.\"window\",h.new_high from analysis_snapshot_entries e join high_result_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date where e.snapshot_id=? and e.domain='high' and e.trade_date in ("+placeholders+")",[selected['snapshot_id'],*dates]).fetchall()
    for date_value,window,hit in rows:
     key=str(date_value);high[key][str(window)]['valid_count']+=int(hit is not None);high[key][str(window)]['hit_count']+=int(hit is True)
   if 'queues' in requested or not requested:
    rows=c.execute("select cast(e.trade_date as varchar),h.security_id,h.queue_name,h.hit from analysis_snapshot_entries e join historical_structure_result_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date where e.snapshot_id=? and e.domain='structure' and e.trade_date in ("+placeholders+")",[selected['snapshot_id'],*dates]).fetchall()
    for date_value,security_id,queue_name,hit in rows: queues[str(date_value)].append({'security_id':security_id,'queue_name':queue_name,'hit':hit})
   sector_states=defaultdict(list)
   rows=c.execute("select cast(e.trade_date as varchar),s.sector_id,s.diffusion_state from analysis_snapshot_entries e join sector_cycle_daily s on s.slice_id=e.slice_id and s.trade_date=e.trade_date where e.snapshot_id=? and e.domain='sector_cycle' and e.trade_date in ("+placeholders+")",[selected['snapshot_id'],*dates]).fetchall()
   for date_value,sector_id,diffusion_state in rows: sector_states[str(date_value)].append({'sector_id':sector_id,'diffusion_state':diffusion_state})
   points=[]
   for date_value in sorted(dates):
    high_counts={key:{'valid_count':item['valid_count'],'hit_count':item['hit_count']} for key,item in sorted(high[date_value].items(),key=lambda pair:int(pair[0]))}
    queue_count,unique=group_queue_counts(queues[date_value]) if date_value in queues else ({},None)
    sector_count=group_sector_state_counts(sector_states[date_value]) if date_value in sector_states else None
    points.append(aggregate_market_point(date_value,grouped.get(date_value,[]),high_counts=high_counts,queue_counts=queue_count if date_value in queues else None,queue_unique_count=unique,sector_state_counts=sector_count))
  points.reverse();result={'publication_id':p,'contract_id':MARKET_CYCLE_CONTRACT_ID,'snapshot_id':selected['snapshot_id'],'history_basis':context['resolved_basis'],'points':points,'metrics':list(requested) if requested else sorted(allowed),'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root)}
  result.update(self._analysis_meta(context,{'days':days,'metrics':list(requested),'basis':basis,'trade_date':trade_date},points[0]['trade_date'] if points else None,{'from':points[0]['trade_date'] if points else None,'to':points[-1]['trade_date'] if points else None,'dates':[point['trade_date'] for point in points]}))
  return result
 def market_day_detail(self,p,trade_date,basis='AUTO'):
  result=self.market_cycle(p,days=250,basis=basis,trade_date=trade_date)
  point=next((item for item in result['points'] if item['trade_date']==str(trade_date)),None)
  if point is None: raise ValueError('TRADE_DATE_UNAVAILABLE')
  return {'publication_id':p,'contract_id':MARKET_CYCLE_CONTRACT_ID,'snapshot_id':result['snapshot_id'],'trade_date':str(trade_date),'item':point,'statistical_scope':result.get('statistical_scope'),'drilldown':{'technical':'/api/stocks/technical','new_highs':'/api/stocks/new-highs','queues':'/api/queues'}}
 def limit_ladder(self,p,page=1,size=50,level='ALL',state='ALL',promotion='ALL',basis='AUTO',trade_date=None):
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p)
  level=str(level or 'ALL').strip().upper();promotion=str(promotion or 'ALL').strip().upper();raw_state=str(state or 'ALL').strip().upper()
  allowed_levels={'ALL','1','2','3','4PLUS'};allowed_promotions={'ALL','NOT_EVALUATED','SUCCESS','NOT_ELIGIBLE','UNKNOWN','SUSPENDED','NO_LIMIT'}
  if level not in allowed_levels: raise ValueError('LIMIT_LADDER_LEVEL_UNSUPPORTED')
  if promotion not in allowed_promotions: raise ValueError('LIMIT_LADDER_PROMOTION_UNSUPPORTED')
  if raw_state=='ALL': normalized_state='ALL'
  else:
   normalized_state=canonical_limit_state(raw_state)
   if normalized_state not in {'UP','DOWN','NONE','UNKNOWN','NO_LIMIT','SUSPENDED'}: raise ValueError('LIMIT_LADDER_STATE_UNSUPPORTED')
  context=self._analysis_context(p,basis);selected=context['selected']
  query={'page':page,'page_size':size,'level':level,'state':normalized_state,'promotion':promotion,'basis':basis,'trade_date':trade_date}
  with self._con() as c:
   tables={row[0] for row in c.execute('show tables').fetchall()}
   entry_count=c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='limit_ladder'",[selected['snapshot_id']]).fetchone()[0]
  if 'limit_ladder_daily' not in tables or not entry_count:
   result={'publication_id':p,'contract_id':LIMIT_LADDER_CONTRACT_ID,'snapshot_id':selected['snapshot_id'],'history_basis':context['resolved_basis'],'status':'NOT_BUILT','page':page,'page_size':size,'total':0,'level':level,'state':normalized_state,'promotion':promotion,'as_of_trade_date':None,'items':[],'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root),'capabilities':{'limit_ladder':'NOT_BUILT','m8c_reference':'NOT_BUILT','m8c_rules':'NOT_BUILT'}}
   result.update(self._analysis_meta(context,query,None,{'from':None,'to':None,'dates':[]}));result['status']='NOT_BUILT';result['capabilities'].update({'limit_ladder':'NOT_BUILT','m8c_reference':'NOT_BUILT','m8c_rules':'NOT_BUILT'});return result
  as_of=self._analysis_as_of(context,trade_date,('limit_ladder',));date_filter=' and e.trade_date<=?' if as_of else ''
  with self._con() as c:
   effective_date=as_of or c.execute("select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='limit_ladder'",[selected['snapshot_id']]).fetchone()[0]
   filters=["e.snapshot_id=?","e.domain='limit_ladder'","e.trade_date=?",WORKBENCH_STATISTICAL_SCOPE_SQL.format(id='l.security_id')];args=[selected['snapshot_id'],effective_date]
   if level!='ALL': filters.append('l.ladder_level=?');args.append(level)
   if normalized_state!='ALL': filters.append('l.limit_state=?');args.append(normalized_state)
   if promotion!='ALL': filters.append('l.promotion_state=?');args.append(promotion)
   where=' and '.join(filters)
   joins=' from analysis_snapshot_entries e join limit_ladder_daily l on l.slice_id=e.slice_id and l.trade_date=e.trade_date left join technical_result_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date and t.security_id=l.security_id'
   total=c.execute('select count(*)'+joins+' where '+where,args).fetchone()[0]
   level_counts={str(row[0]): int(row[1]) for row in c.execute(
    "select coalesce(l.ladder_level,'UNKNOWN'),count(*)"+joins+" where e.snapshot_id=? and e.domain='limit_ladder' and e.trade_date=? and "+WORKBENCH_STATISTICAL_SCOPE_SQL.format(id='l.security_id')+" group by 1",
    [selected['snapshot_id'],effective_date],
   ).fetchall()}
   rows=c.execute('select cast(l.trade_date as varchar),l.security_id,l.limit_state,l.reference_basis,l.rule_id,l.limit_up_price,l.limit_down_price,l.streak,l.streak_known,l.streak_min_known,l.previous_state,l.previous_streak,l.ladder_level,l.promotion_state,l.denominator_eligible,l.exclusion_reason,l.association_ref,l.contract_id,t.raw_amount'+joins+' where '+where+' order by case l.ladder_level when \'4PLUS\' then 4 when \'3\' then 3 when \'2\' then 2 when \'1\' then 1 else 0 end desc,t.raw_amount desc nulls last,l.security_id limit ? offset ?',args+[size,(page-1)*size]).fetchall()
   capabilities=self._m13c_capabilities(c,selected['snapshot_id'],effective_date)
  names=('trade_date','security_id','limit_state','reference_basis','rule_id','limit_up_price','limit_down_price','streak','streak_known','streak_min_known','previous_state','previous_streak','ladder_level','promotion_state','denominator_eligible','exclusion_reason','association_ref','contract_id','raw_amount');items=[dict(zip(names,row)) for row in rows]
  result={'publication_id':p,'contract_id':LIMIT_LADDER_CONTRACT_ID,'snapshot_id':selected['snapshot_id'],'history_basis':context['resolved_basis'],'status':'AVAILABLE','page':page,'page_size':size,'total':total,'level':level,'state':normalized_state,'promotion':promotion,'as_of_trade_date':str(effective_date),'items':items,'level_counts':{key:level_counts.get(key,0) for key in ('1','2','3','4PLUS','UNKNOWN')},'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root),'capabilities':{'limit_ladder':'AVAILABLE',**{key:value for key,value in capabilities.items() if key != 'evidence'},'m8c_evidence':capabilities['evidence']}}
  result.update(self._analysis_meta(context,query,str(effective_date),{'from':str(effective_date),'to':str(effective_date),'dates':[str(effective_date)]}));result['status']='AVAILABLE';result['capabilities'].update({'limit_ladder':'AVAILABLE',**{key:value for key,value in capabilities.items() if key != 'evidence'},'m8c_evidence':capabilities['evidence']});return result
 def limit_promotion_history(self,p,days=30,previous_level='ALL',basis='AUTO',trade_date=None):
  days=max(1,min(250,int(days)));previous_level=str(previous_level or 'ALL').strip().upper()
  allowed_levels={'ALL','1','2','3','4PLUS'}
  if previous_level not in allowed_levels: raise ValueError('LIMIT_PROMOTION_LEVEL_UNSUPPORTED')
  self._pub(p);context=self._analysis_context(p,basis);selected=context['selected']
  query={'days':days,'previous_level':previous_level,'basis':basis,'trade_date':trade_date}
  with self._con() as c:
   tables={row[0] for row in c.execute('show tables').fetchall()}
   entry_count=c.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='limit_promotion'",[selected['snapshot_id']]).fetchone()[0]
  if 'limit_promotion_daily' not in tables or not entry_count:
   result={'publication_id':p,'contract_id':LIMIT_PROMOTION_CONTRACT_ID,'snapshot_id':selected['snapshot_id'],'history_basis':context['resolved_basis'],'status':'NOT_BUILT','days':days,'previous_level':previous_level,'points':[],'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root),'capabilities':{'limit_promotion':'NOT_BUILT','limit_ladder':'NOT_BUILT','m8c_reference':'NOT_BUILT','m8c_rules':'NOT_BUILT'}}
   result.update(self._analysis_meta(context,query,None,{'from':None,'to':None,'dates':[]}));result['status']='NOT_BUILT';result['capabilities'].update({'limit_promotion':'NOT_BUILT','limit_ladder':'NOT_BUILT','m8c_reference':'NOT_BUILT','m8c_rules':'NOT_BUILT'});return result
  as_of=self._analysis_as_of(context,trade_date,('limit_promotion',))
  level_filter='' if previous_level=='ALL' else ' and p.previous_level=?'
  level_args=[] if previous_level=='ALL' else [previous_level]
  with self._con() as c:
   effective_date=as_of or c.execute("select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='limit_promotion'",[selected['snapshot_id']]).fetchone()[0]
   dates=c.execute("select cast(trade_date as varchar) from analysis_snapshot_entries where snapshot_id=? and domain='limit_promotion' and trade_date<=? order by trade_date desc limit ?",[selected['snapshot_id'],effective_date,days]).fetchall()
   rows=c.execute("with recent_dates as (select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='limit_promotion' and trade_date<=? order by trade_date desc limit ?) select cast(p.previous_trade_date as varchar),cast(p.trade_date as varchar),p.previous_level,p.previous_up_count,p.previous_unconfirmed_count,p.success_count,p.eligible_count,p.excluded_unknown,p.excluded_suspended,p.excluded_no_limit,p.rate,p.contract_id from recent_dates d join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='limit_promotion' and e.trade_date=d.trade_date join limit_promotion_daily p on p.slice_id=e.slice_id and p.trade_date=e.trade_date where 1=1"+level_filter+" order by p.trade_date asc,case p.previous_level when '4PLUS' then 4 when '3' then 3 when '2' then 2 when '1' then 1 else 0 end desc",[selected['snapshot_id'],effective_date,days,selected['snapshot_id'],*level_args]).fetchall()
  names=('previous_trade_date','trade_date','previous_level','previous_up_count','previous_unconfirmed_count','success_count','eligible_count','excluded_unknown','excluded_suspended','excluded_no_limit','rate','contract_id');points=[dict(zip(names,row)) for row in rows]
  for point in points:
   point['previous_trade_date']=str(point['previous_trade_date']);point['trade_date']=str(point['trade_date'])
  returned_dates=[str(row[0]) for row in reversed(dates)]
  with self._con() as c:
   capabilities=self._m13c_capabilities(c,selected['snapshot_id'],effective_date)
  result={'publication_id':p,'contract_id':LIMIT_PROMOTION_CONTRACT_ID,'snapshot_id':selected['snapshot_id'],'history_basis':context['resolved_basis'],'status':'AVAILABLE','days':days,'previous_level':previous_level,'points':points,'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root),'capabilities':{'limit_promotion':'AVAILABLE','limit_ladder':'AVAILABLE',**{key:value for key,value in capabilities.items() if key != 'evidence'},'m8c_evidence':capabilities['evidence']}}
  result.update(self._analysis_meta(context,query,str(effective_date),{'from':returned_dates[0] if returned_dates else None,'to':returned_dates[-1] if returned_dates else None,'dates':returned_dates}));result['status']='AVAILABLE';result['capabilities'].update({'limit_promotion':'AVAILABLE','limit_ladder':'AVAILABLE',**{key:value for key,value in capabilities.items() if key != 'evidence'},'m8c_evidence':capabilities['evidence']});return result
 def universe_summary(self,p,basis=None,trade_date=None):
  publication_trade_date,source_revision=self._pub(p)
  with self._con() as c:
   rows=c.execute('select security_id,payload_json from stock_daily where publication_id=? order by security_id',[p]).fetchall()
  records=[]
  for security_id,payload in rows:
   record=json.loads(payload);record['security_id']=security_id
   records.append(record)
  records=[record for record in records if is_workbench_statistical_security_id(record.get('security_id'), self._root)]
  quote_ids=set(self._quotes(p))
  summary=summarize_universe(records,quote_valid_ids=quote_ids)
  statistical_count=summary['display_count']
  display_records=[record for record in records if is_workbench_visible_security_id(record.get('security_id'), self._root)]
  summary['statistical_count']=statistical_count
  summary['display_count']=len(display_records)
  summary['display_quote_valid_count']=sum(str(record.get('security_id')).upper() in quote_ids for record in display_records)
  summary['display_scope']=self._display_scope
  summary['statistical_scope']=workbench_statistical_scope(self._root)
  summary.pop('items',None)
  identity=self.identity(p)
  summary.update({
   'publication_id':p,
   'trade_date':publication_trade_date,
   'source_revision_id':source_revision,
   'source_identity_sha256':identity.get('source_identity_sha256'),
   'source_manifest_sha256':identity.get('source_manifest_sha256'),
  })
  result={'publication_id':p,'item':summary,'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root)}
  if basis is not None:
   context=self._analysis_context(p,basis);as_of=self._analysis_as_of(context,trade_date,('summary','technical'));result.update(self._analysis_meta(context,{'basis':basis,'trade_date':trade_date},as_of or trade_date or publication_trade_date,None))
  return result
 def candidates(self,p,q,page,size,grade='',pattern='',include_analysis=False,basis='AUTO',final_only=False):
  extra='and (security_name ilike ? or security_id ilike ?)'; args=(f'%{q}%',f'%{q}%')
  if grade: extra+=' and research_priority=?'; args += (grade,)
  if pattern: extra+=' and primary_pattern=?'; args += (pattern,)
  extra='and '+WORKBENCH_SCOPE_SQL.format(id='security_id')+' '+extra
  order="case research_priority when 'A+' then 0 when 'A' then 1 when 'B' then 2 when 'C' then 3 else 9 end, cast(json_extract_string(payload_json,'$.priority_score') as double) desc, security_id"
  if final_only:
   size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p)
   source_query=f" from candidate_daily where publication_id=? {extra}";source_params=[p,*args]
   final_extra=extra+" and research_priority in ('A+','A') and upper(json_extract_string(payload_json,'$.primary_leader_sector_type')) in ('INDUSTRY','THEME')"
   query=f" from candidate_daily where publication_id=? {final_extra}";params=[p,*args]
   with self._con() as c:
    source_total=int(c.execute('select count(*)'+source_query,source_params).fetchone()[0]);pool_total=int(c.execute('select count(*)'+query,params).fetchone()[0]);total=min(100,pool_total);offset=(page-1)*size;limit=max(0,min(size,total-offset))
    vals=c.execute('select payload_json'+query+' order by '+order+' limit ? offset ?',params+[limit,offset]).fetchall() if limit else []
   result={'publication_id':p,'page':page,'page_size':size,'total':total,'source_candidate_total':source_total,'eligible_pool_total':pool_total,'items':[json.loads(value[0]) for value in vals],'display_scope':self._display_scope,'statistical_scope':workbench_statistical_scope(self._root),'contract_id':'FINAL_LOCAL_RESEARCH_CANDIDATES_V1','selection_basis':'A_PLUS_OR_A_AND_PRIMARY_INDUSTRY_OR_THEME_THEN_PRIORITY_SCORE_DESC','max_results':100}
   for index,item in enumerate(result['items'],start=offset+1):
    item['final_research_rank']=index
    item['final_selection_reasons']=['RESEARCH_PRIORITY_A_PLUS_OR_A','PRIMARY_SECTOR_INDUSTRY_OR_THEME','LOCAL_COMPOSITE_PRIORITY_ORDER']
  else:
   result=self._rows('candidate_daily',p,extra,args,order,page,size)
  result=self._add_quotes(p,self._add_strength_associations(p,result))
  if include_analysis:
   context=self._analysis_context(p,basis);result.update(self._analysis_meta(context,{'q':q,'page':page,'page_size':size,'grade':grade,'pattern':pattern,'basis':basis},result['items'][0].get('trade_date') if result['items'] else None,None))
   if final_only: result['base_candidate_contract_id']=PRIORITY_RESEARCH_CONTRACT_ID
   else: result['contract_id']=PRIORITY_RESEARCH_CONTRACT_ID
   result['stock_row_contract']='StockRow_V1_0'
  return result
 def queues(self,p,name,page,size,q='',band='',include_analysis=False,basis='AUTO',trade_date=None):
  if include_analysis:return self._analysis_queues(p,name,page,size,q,band,basis,trade_date)
  canonical=str(name).removesuffix('_QUEUE').upper()+'_QUEUE'
  size=max(1,min(MAX_PAGE_SIZE,int(size))); page=max(1,int(page)); self._pub(p)
  filters=['q.publication_id=?','q.queue_name=?',WORKBENCH_SCOPE_SQL.format(id='q.security_id')]; args=[p,canonical]
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
 def _analysis_queues(self,p,name,page,size,q='',band='',basis='AUTO',trade_date=None):
  canonical=str(name).removesuffix('_QUEUE').upper()+'_QUEUE'
  if canonical not in ('STEADY_QUEUE','PULLBACK_QUEUE','BREAKOUT_QUEUE','LEADER_QUEUE','EARLY_QUEUE'):raise ValueError('QUEUE_UNSUPPORTED')
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));self._pub(p)
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('structure',));date_filter=' and trade_date<=?' if as_of else ''
  with self._con() as c:latest=c.execute("select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='structure'"+date_filter,[selected['snapshot_id'],*([as_of] if as_of else [])]).fetchone()[0]
  if latest is None:raise ValueError('ANALYSIS_NOT_BUILT')
  filters=["e.snapshot_id=?","e.domain='structure'","e.trade_date=?","h.queue_name=?","h.hit=true","h.tier in ('CORE','SUPPORTED')",WORKBENCH_SCOPE_SQL.format(id='h.security_id')];where_params=[selected['snapshot_id'],latest,canonical]
  if q:filters.append("(h.security_id ilike ? or json_extract_string(sd.payload_json,'$.security_name') ilike ?)");where_params.extend([f'%{q}%',f'%{q}%'])
  bands=[value for value in str(band).split(',') if value]
  if bands:filters.append('h.research_band in ('+','.join('?' for _ in bands)+')');where_params.extend(bands)
  where=' and '.join(filters);joins=" from analysis_snapshot_entries e join historical_structure_result_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date left join stock_daily sd on sd.publication_id=? and sd.security_id=h.security_id left join analysis_snapshot_entries te on te.snapshot_id=e.snapshot_id and te.domain='technical' and te.trade_date=e.trade_date left join technical_result_daily t on t.slice_id=te.slice_id and t.trade_date=te.trade_date and t.security_id=h.security_id left join analysis_snapshot_entries se on se.snapshot_id=e.snapshot_id and se.domain='strength' and se.trade_date=e.trade_date left join strength_result_daily st on st.slice_id=se.slice_id and st.trade_date=se.trade_date and st.security_id=h.security_id"
  params=[p,*where_params]
  with self._con() as c:
   total=c.execute('select count(*)'+joins+' where '+where,params).fetchone()[0]
   rows=c.execute('select h.security_id,h.trade_date,h.queue_name,h.hit,h.tier,h.source_class,h.research_band,h.queue_rank,h.tier_rank,h.transition,h.structure_basis,h.contract_id,h.evidence,h.quality_codes,t.ret20,st.rps20,t.ma_alignment,t.amount_class,sd.payload_json'+joins+' where '+where+' order by h.queue_rank nulls last,h.security_id limit ? offset ?',params+[size,(page-1)*size]).fetchall()
  names=('security_id','trade_date','queue_name','hit','tier','source_class','research_band','queue_rank','tier_rank','transition','source_basis','contract_id','evidence','quality_codes','ret20','rps20','ma_alignment','amount_class','stock_payload');items=[]
  for index,row in enumerate(rows):
   item=dict(zip(names,row));payload=json.loads(item.pop('stock_payload')) if item.get('stock_payload') else {};item={**payload,**item};item['trade_date']=str(item['trade_date']);item['evidence']=json.loads(item['evidence']) if item['evidence'] else {};item['quality_codes']=json.loads(item['quality_codes']) if item['quality_codes'] else [];item['filtered_row_number']=(page-1)*size+index+1;items.append(item)
  result={'publication_id':p,'snapshot_id':selected['snapshot_id'],'trade_date':str(latest),'page':page,'page_size':size,'total':total,'items':items}
  result.update(self._analysis_meta(context,{'queue':canonical,'page':page,'page_size':size,'q':q,'band':band,'basis':basis,'trade_date':trade_date},str(latest),{'from':str(latest),'to':str(latest),'dates':[str(latest)]}))
  return self._add_quotes(p,result)
 def evidence(self,p,queue,security,format='',basis='AUTO',trade_date=None):
  if not is_workbench_visible_security_id(security, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  # The UI uses stable lowercase route keys while the publication contract
  # stores queue names in uppercase.  Normalize both forms before lookup.
  detail=str(queue).removesuffix('_QUEUE').upper(); canonical=detail+'_QUEUE'
  if format!='groups':
   with self._con() as c: row=c.execute('select payload_json from structure_details where publication_id=? and queue_name=? and security_id=?',[p,detail,security]).fetchone()
   result={'publication_id':p,'item':json.loads(row[0]) if row else None}
   try:
    context=self._analysis_context(p,basis);as_of=self._analysis_as_of(context,trade_date,('structure',));result.update(self._analysis_meta(context,{'queue':canonical,'security_id':security,'format':format,'basis':basis,'trade_date':trade_date},as_of,None))
   except ValueError:
    if trade_date not in (None,''): raise
   return result
  history=self.structure_history(p,security,20,canonical,basis,trade_date)
  if not history['points']:
   result={'publication_id':p,'item':None,'status':'NOT_FOUND'};result.update({key:history[key] for key in ('api_contract','analysis_snapshot_id','snapshot_id','cutoff_date','trade_date','requested_basis','resolved_basis','history_basis','query_hash','contracts','capabilities','data_quality') if key in history});return result
  latest=history['points'][-1]
  try:
   associations=self.sector_associations(p,security,days=1,include_rejected=True,page=1,size=50,basis=basis,trade_date=trade_date)
   association_group={'group_id':'m11_association','label':'M11 板块关联证据','status':'AVAILABLE' if associations.get('items') else 'NO_ELIGIBLE_ASSOCIATION','trade_date':associations.get('trade_date'),'history_basis':associations.get('history_basis'),'contract_id':associations.get('contract_id',ASSOCIATION_CONTRACT_ID),'items':associations.get('items',[])}
  except ValueError as error:
   association_group={'group_id':'m11_association','label':'M11 板块关联证据','status':'UNAVAILABLE','reason':str(error),'items':[],'contract_id':ASSOCIATION_CONTRACT_ID}
  contracts=[latest['contract_id'],ASSOCIATION_CONTRACT_ID]
  result={'publication_id':p,'item':{'summary':{'security_id':security,'queue_name':canonical,'trade_date':latest['trade_date'],'hit':latest['hit'],'tier':latest['tier'],'source_basis':latest['source_basis']},'groups':[{'group_id':'historical_structure','label':'历史结构证据','items':history['points']},association_group],'contracts':contracts},'status':'AVAILABLE'}
  result.update({key:history[key] for key in ('api_contract','analysis_snapshot_id','snapshot_id','cutoff_date','trade_date','requested_basis','resolved_basis','history_basis','query_hash','capabilities','data_quality') if key in history});return result
 def identity(self,p,include_analysis=False):
  d,rev=self._pub(p)
  with self._con() as c:
   x=c.execute('select source_manifest_sha256,source_identity_sha256,computation_identity_sha256,render_identity_sha256,revision,production_version from publications where publication_id=?',[p]).fetchone()
   relation=self._publication_relation(c,p)
  result={'publication_id':p,'trade_date':d,'source_revision_id':rev,'source_manifest_sha256':x[0],'source_identity_sha256':x[1],'computation_identity_sha256':x[2],'render_identity_sha256':x[3],'membership_snapshot_id':relation.get('legacy_snapshot_id') if relation else None,'relation_source_scope':relation.get('source_scope') if relation else None,'relation_observation_id':relation.get('observation_id') if relation else None,'relation_revision':relation.get('revision_no') if relation else None,'relation_attribute_version_id':relation.get('attribute_version_id') if relation else None,'relation_hierarchy_version':relation.get('hierarchy_version') if relation else None,'relation_binding_mode':'PUBLICATION' if relation and relation.get('legacy_snapshot_id') is None else 'LEGACY_ID_BRIDGE' if relation else 'UNAVAILABLE','api_contract':'m2-read-only-api-v1.2'}
  if include_analysis:
   bindings=self._analysis_bindings(p);preferred=bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED');context=self._analysis_context(p) if preferred else None
   quality=context['quality'] if context else {'status':'PARTIAL','codes':['HISTORY_ANALYSIS_NOT_BUILT'],'field_coverage':{}}
   snapshot_details={domain:{**binding,'data_quality':self._analysis_quality(binding)} for domain,binding in bindings.items()}
   result.update({
    'api_contract':API_CONTRACT,
    'revision':x[4],
    'production_version':x[5],
    'cutoff_date':d,
    'analysis_snapshot_id':preferred['snapshot_id'] if preferred else None,
    'analysis_snapshots':bindings,
    'analysis_snapshot_details':snapshot_details,
    'resolved_basis':context['resolved_basis'] if context else None,
    'history_basis':context['resolved_basis'] if context else None,
    'query_hash':hashlib.sha256(json.dumps({'publication_id':p,'include_analysis':True},sort_keys=True).encode('utf-8')).hexdigest(),
    'contracts':context['contracts'] if context else {'universe':'workbench-universe-v2.1','quote':'workbench-quote-v2.1','semantic':'workbench-semantic-v2.1','publication':'m4-one-click-publication-contract-v1.1','analysis_domains':{}},
    'capabilities':self._analysis_capabilities(p),
    'data_quality':quality,
   })
  return result
 def field_catalog(self,api_contract=API_CONTRACT,language='zh-CN'):
  return field_catalog(api_contract,language)
 def _window_sessions(self):
  if self._window_sessions_cache is None:
   path=self._root/'data/normalized/adjusted_daily.parquet'
   with self._connection_provider.memory() as c:
    sessions=c.execute('select distinct date from read_parquet(?) where is_master_session order by date',[str(path)]).fetchall()
    observed=c.execute('select distinct date from read_parquet(?) where is_master_session and data_observed order by date',[str(path)]).fetchall()
   self._window_sessions_cache=([row[0] for row in sessions],[row[0] for row in observed])
  return self._window_sessions_cache
 def history_coverage(self,p,days=MAX_OUTPUT_DAYS,basis='AUTO',trade_date=None):
  if basis not in ('AUTO','OBSERVED','RECONSTRUCTED'):
   raise ValueError('BASIS_UNSUPPORTED')
  cutoff_text,_=self._pub(p)
  if trade_date not in (None,''):
   try: cutoff=date.fromisoformat(str(trade_date).strip())
   except (TypeError,ValueError): raise ValueError('DATE_INVALID')
   if cutoff.isoformat()>cutoff_text: raise ValueError('DATE_AFTER_CUTOFF')
   cutoff_text=cutoff.isoformat()
  else: cutoff=date.fromisoformat(cutoff_text)
  sessions,observed=self._window_sessions()
  result=plan_window(sessions,cutoff_date=cutoff,output_days=int(days),observed_sessions=observed,dependencies=self._window_dependencies)
  bindings=self._analysis_bindings(p)
  requested_domain={'OBSERVED':'LOCAL_OBSERVED','RECONSTRUCTED':'LOCAL_RECONSTRUCTED'}.get(basis)
  selected=(bindings.get(requested_domain) if requested_domain else bindings.get('LOCAL_OBSERVED') or bindings.get('LOCAL_RECONSTRUCTED'))
  resolved=(selected['domain'].removeprefix('LOCAL_') if selected else ('OBSERVED' if basis=='AUTO' else basis))
  result.update({'api_contract':API_CONTRACT,'publication_id':p,'snapshot_id':selected['snapshot_id'] if selected else None,'snapshot_capability':'AVAILABLE' if selected else 'NOT_BUILT','requested_basis':basis,'resolved_basis':resolved,'analysis_capability':'AVAILABLE' if selected else 'NOT_BUILT'})
  if selected:
   result.update(self._analysis_meta(self._analysis_context(p,basis),{'days':int(days),'basis':basis,'trade_date':trade_date},result.get('output_end') or result.get('cutoff_date'),{'from':result.get('output_start'),'to':result.get('output_end'),'dates':result.get('output_dates',[])}))
  else:
   result.update({'analysis_snapshot_id':None,'cutoff_date':cutoff_text,'trade_date':cutoff_text,'history_basis':resolved,'query_hash':hashlib.sha256(json.dumps({'publication_id':p,'days':int(days),'basis':basis,'trade_date':trade_date},sort_keys=True).encode('utf-8')).hexdigest(),'contracts':{'window_planner':result.get('contract_version'),'analysis_domains':{}},'capabilities':{},'data_quality':{'status':'UNAVAILABLE','codes':['HISTORY_ANALYSIS_NOT_BUILT'],'field_coverage':{}}})
  return {'publication_id':p,'item':result}
 def _analysis_linkage(self,p,sector,security,page=1,size=100,q='',basis='AUTO',trade_date=None):
  size=max(1,min(MAX_PAGE_SIZE,int(size)));page=max(1,int(page));sector=str(sector or '').strip();security=str(security or '').strip();q=str(q or '').strip()
  if not sector and not security: raise ValueError('LINKAGE_KEY_REQUIRED')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('member_state','association'))
  with self._con() as c:
   dates=[str(row[0]) for row in c.execute("select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='member_state' order by trade_date desc",[selected['snapshot_id']]).fetchall()]
   if not dates: raise ValueError('LINKAGE_NOT_BUILT')
   effective_date=as_of or dates[0]
   member_slice=c.execute("select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='member_state' and trade_date=?",[selected['snapshot_id'],effective_date]).fetchone()
   base_slice=c.execute("select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='sector_base' and trade_date=?",[selected['snapshot_id'],effective_date]).fetchone()
   association_slice=c.execute("select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='association' and trade_date=?",[selected['snapshot_id'],effective_date]).fetchone()
   if not member_slice or not base_slice: raise ValueError('LINKAGE_NOT_BUILT')
   conditions=["m.member_present=true", "m.slice_id=?", "b.slice_id=?", WORKBENCH_SCOPE_SQL.format(id='m.security_id')]
   params=[member_slice[0],base_slice[0]]
   if sector: conditions.append('m.sector_id=?');params.append(sector)
   if security: conditions.append('m.security_id=?');params.append(security)
   association_join=''
   association_select='null as association_rank,null as association_eligible,null as association_rejection_reasons,null as association_pattern,null as association_contract_id,null as association_history_basis'
   if association_slice:
    association_join=" left join stock_sector_associations_daily a on a.slice_id=? and a.trade_date=m.trade_date and a.sector_id=m.sector_id and a.security_id=m.security_id"
    params.insert(0,association_slice[0])
    association_select='a.association_rank,a.eligible as association_eligible,a.rejection_reasons as association_rejection_reasons,a.pattern as association_pattern,a.contract_id as association_contract_id,a.history_basis as association_history_basis'
   rows=c.execute(f'''select m.sector_id,m.security_id,m.member_rank,m.rank_valid_count,m.member_percentile,
                             b.sector_name,b.sector_type,b.sector_role,b.bucket,b.total_member_count,b.coverage,
                             {association_select}
                        from member_state_result_daily m
                        join sector_base_daily b on b.sector_id=m.sector_id and b.trade_date=m.trade_date
                        {association_join}
                       where {' and '.join(conditions)}
                       order by m.sector_id,m.member_rank nulls last,m.security_id''',params).fetchall()
  names=self._security_names(p,{str(row[1]) for row in rows})
  items=[]
  for row in rows:
   values=dict(zip(('sector_id','security_id','sector_member_rank','sector_member_count_valid','member_percentile','sector_name','sector_type','sector_role','semantic_bucket','total_member_count','sector_coverage','association_rank','association_eligible','association_rejection_reasons','association_pattern','association_contract_id','association_history_basis'),row))
   values['security_name']=names.get(str(values['security_id']),str(values['security_id']))
   if q and q.lower() not in values['security_name'].lower() and q.lower() not in str(values['security_id']).lower(): continue
   rank_value=_finite_or_none(values['sector_member_rank']);total_count=_finite_or_none(values['total_member_count']);valid_count=_finite_or_none(values['sector_member_count_valid'])
   values['sector_member_rank']=int(rank_value) if rank_value is not None else None
   values['sector_member_count']=int(total_count) if total_count is not None else int(valid_count or 0)
   values['member_rank_valid_count']=int(valid_count or 0)
   values['association_eligible']=None if values['association_eligible'] is None else bool(values['association_eligible'])
   values['association_rejection_reasons']=_json_value(values['association_rejection_reasons'],[])
   values['association']={'rank':values['association_rank'],'eligible':values['association_eligible'],'pattern':values['association_pattern'],'rejection_reasons':values['association_rejection_reasons'],'contract_id':values['association_contract_id'],'history_basis':values['association_history_basis']}
   values.update(self._quotes(p).get(str(values['security_id']),{}))
   items.append(values)
  total=len(items);start=(page-1)*size;page_items=items[start:start+size]
  result={'publication_id':p,'snapshot_id':selected['snapshot_id'],'trade_date':effective_date,'page':page,'page_size':size,'total':total,'sector_id':sector or None,'security_id':security or None,'sector_member_count':page_items[0]['sector_member_count'] if sector and page_items else (items[0]['sector_member_count'] if sector and items else None),'sector_member_rank_basis':'member_state_daily.member_rank','association_contract_id':ASSOCIATION_CONTRACT_ID if association_slice else None,'items':page_items}
  result.update(self._analysis_meta(context,{'sector_id':sector,'security_id':security,'page':page,'page_size':size,'q':q,'basis':basis,'trade_date':trade_date},effective_date,{'from':effective_date,'to':effective_date,'dates':[effective_date]}))
  return result
 def linkage_history(self,p,sector_id,days=10,security_id='',page=1,size=100,basis='AUTO',trade_date=None):
  sector_id=str(sector_id or '').strip();security_id=str(security_id or '').strip();days=max(1,min(250,int(days)));page=max(1,int(page));size=max(1,min(MAX_PAGE_SIZE,int(size)))
  if not sector_id: raise ValueError('SECTOR_ID_REQUIRED')
  if security_id and not is_workbench_visible_security_id(security_id, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  context=self._analysis_context(p,basis);selected=context['selected'];as_of=self._analysis_as_of(context,trade_date,('member_state',))
  with self._con() as c:
   dates=[str(row[0]) for row in c.execute("select distinct trade_date from analysis_snapshot_entries where snapshot_id=? and domain='member_state' order by trade_date desc",[selected['snapshot_id']]).fetchall()]
   if not dates: raise ValueError('LINKAGE_HISTORY_NOT_BUILT')
   if as_of and as_of not in dates: raise ValueError('TRADE_DATE_UNAVAILABLE')
   selected_dates=[value for value in dates if not as_of or value<=as_of][:days]
   placeholders=','.join('?' for _ in selected_dates)
   rows=c.execute('''select m.trade_date,m.sector_id,m.security_id,m.member_present,m.member_rank,m.rank_valid_count,m.member_percentile,
                            m.strong_state,m.member_change_kind,m.strength_change_kind,m.previous_rank,m.rank_delta,m.history_basis,m.contract_id
                       from member_state_result_daily m
                       join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='member_state' and e.slice_id=m.slice_id and e.trade_date=m.trade_date
                       where m.sector_id=? and m.trade_date in ('''+placeholders+''')'''+(' and m.security_id=?' if security_id else '')+''' order by m.trade_date desc,m.member_rank nulls last,m.security_id''',[selected['snapshot_id'],sector_id,*selected_dates,*([security_id] if security_id else [])]).fetchall()
  names=self._security_names(p,{str(row[2]) for row in rows});columns=('trade_date','sector_id','security_id','member_present','member_rank','rank_valid_count','member_percentile','strong_state','member_change_kind','strength_change_kind','previous_rank','rank_delta','history_basis','contract_id');items=[]
  for row in rows:
   item=dict(zip(columns,row));item['trade_date']=str(item['trade_date']);item['security_name']=names.get(str(item['security_id']),str(item['security_id']));item['member_present']=bool(item['member_present']);item['status']={'member_change':item['member_change_kind'],'strength_change':item['strength_change_kind'],'member_present':item['member_present']};items.append(item)
  total=len(items);start=(page-1)*size;result={'publication_id':p,'snapshot_id':selected['snapshot_id'],'sector_id':sector_id,'security_id':security_id or None,'days':days,'page':page,'page_size':size,'total':total,'items':items[start:start+size]};result.update(self._analysis_meta(context,{'sector_id':sector_id,'security_id':security_id,'days':days,'page':page,'page_size':size,'basis':basis,'trade_date':trade_date},selected_dates[-1] if selected_dates else as_of,{'from':selected_dates[-1] if selected_dates else as_of,'to':selected_dates[0] if selected_dates else as_of,'dates':selected_dates}));return result
 def linkage(self,p,sector,security,page=1,size=100,q='',basis='AUTO',trade_date=None):
  if security and not is_workbench_visible_security_id(security, self._root): raise ValueError('SECURITY_OUT_OF_DISPLAY_SCOPE')
  if self._analysis_bindings(p): return self._analysis_linkage(p,sector,security,page,size,q,basis,trade_date)
  size=max(1,min(MAX_PAGE_SIZE,int(size))); page=max(1,int(page))
  self._pub(p)
  with self._con() as c:
   if not sector and not security: raise ValueError('LINKAGE_KEY_REQUIRED')
   _,relation_edges=self._publication_edges(c,p)
   if not relation_edges:return {'publication_id':p,'page':page,'page_size':size,'total':0,'items':[]}
   edge_map={(edge.sector_id,edge.security_id):edge for edge in relation_edges if (not sector or edge.sector_id==sector) and is_workbench_statistical_security_id(edge.security_id,self._root)}
   sector_ids=sorted({sector_id for sector_id,_ in edge_map})
   security_ids=sorted({security_id for _,security_id in edge_map})
   def payload_rows(table,ids):
    if not ids:return {}
    placeholders=','.join('?' for _ in ids)
    rows=c.execute(f'select '+('sector_id' if table=='sector_daily' else 'security_id')+',payload_json from '+table+f' where publication_id=? and '+('sector_id' if table=='sector_daily' else 'security_id')+f' in ({placeholders})',[p,*ids]).fetchall()
    return {key:json.loads(payload) for key,payload in rows if payload}
   sector_payloads=payload_rows('sector_daily',sector_ids)
   stock_payloads=payload_rows('stock_daily',security_ids)
   board_payloads=payload_rows('unified_board',security_ids)
   grouped={sector_id:[] for sector_id in sector_ids if sector_id in sector_payloads}
   for sector_id,security_id in sorted(edge_map):
    if sector_id not in grouped:continue
    merged={**sector_payloads.get(sector_id,{}),**stock_payloads.get(security_id,{}),**board_payloads.get(security_id,{})}
    merged.update({'sector_id':sector_id,'security_id':security_id,'member_present':True})
    grouped[sector_id].append(merged)
   def rank_key(item):
    rs20=item.get('stock_rs20_pct')
    ret20=item.get('RET20')
    try:rs20=float(rs20);rs20_ok=math.isfinite(rs20)
    except (TypeError,ValueError):rs20=None;rs20_ok=False
    try:ret20=float(ret20);ret20_ok=math.isfinite(ret20)
    except (TypeError,ValueError):ret20=None;ret20_ok=False
    return (not rs20_ok,-rs20 if rs20_ok else 0,not ret20_ok,-ret20 if ret20_ok else 0,str(item.get('security_id') or ''))
   ranked=[]
   for sector_id,rows in grouped.items():
    rows.sort(key=rank_key)
    for rank,item in enumerate(rows,1):
     item['sector_member_rank']=rank;item['sector_member_count']=len(rows);ranked.append(item)
   filtered=[item for item in ranked if (not security or item['security_id']==security) and (not q or q.lower() in str(item.get('security_name') or item.get('name') or '').lower() or q.lower() in item['security_id'].lower())]
   filtered.sort(key=lambda item:(item['sector_id'],item['sector_member_rank']))
   total=len(filtered);items=filtered[(page-1)*size:page*size]
   for item in items:item.update(self._quotes(p).get(item.get('security_id'),{}))
   sector_member_count=(len(grouped.get(sector,())) if sector else None)
   return {'publication_id':p,'page':page,'page_size':size,'total':total,'sector_member_count':sector_member_count,'sector_member_rank_basis':'stock_rs20_pct_desc_then_ret20_desc_then_security_id','items':items}

def make_handler(root,db):
 pg_api = str(os.environ.get('WORKBENCH_API_BACKEND','')).lower() == 'postgresql'
 api_provider = PostgresDuckDBApiConnectionProvider() if pg_api else DuckDBApiConnectionProvider(db)
 api=Api(db,root=root,connection_provider=api_provider)
 pg_repository = PostgresRepository() if pg_api else None
 if pg_repository:
  pg_repository.open()
 pg_history_repository = None
 if pg_api:
  pg_history_repository = PostgresRepository()
  pg_history_repository.open()
 pg_ops_repository = None
 if pg_api:
  pg_ops_repository = PostgresRepository()
  pg_ops_repository.open()
 pg_ops_write = PostgresWriteRepository(pg_ops_repository) if pg_ops_repository else None
 pg_config_store = PostgresConfigVersionStore(pg_ops_repository) if pg_ops_repository else None
 pg_backup_catalog = PostgresBackupCatalogRepository(pg_ops_repository) if pg_ops_repository else None
 research=ResearchQueries(lambda: api._con(),root=root); today_research=TodayResearchBundleReader(root,database_path=None if pg_api else db,repository=pg_repository); turnover_enrichment=TurnoverEnrichmentService(root,today_research); events=OnlineEventQueries(lambda: api._con()); p09=P09OnlineProducts(); history=HistoryJobService(root,db,repository=PostgresHistoryJobRepository(pg_history_repository) if pg_history_repository else None); history.recover_interrupted(background=True); activation=AnalysisActivationService(root,db,repository=PostgresAnalysisActivationRepository() if pg_api else None); operations=OperationsConfig(root,db,version_store=pg_config_store) if pg_config_store else OperationsConfig(root,db); storage=StorageGovernance(root,db,storage_repository=pg_ops_write) if pg_ops_write else StorageGovernance(root,db); backups=BackupService(root,db,catalog=pg_backup_catalog) if pg_backup_catalog else BackupService(root,db); maintenance=MaintenanceService(root,db,metadata_reader=PostgresOperationsMetadataReader(pg_ops_repository) if pg_ops_repository else None); static=Path(root)/'src/workbench_service/static';csrf=secrets.token_urlsafe(24);publishers={};daily_jobs={};research_jobs={};daily_jobs_lock=threading.Lock()
 last_operations_status=maintenance.status()
 database_subprocess_active=threading.Event()
 def run_database_subprocess(command,**kwargs):
  # DuckDB supports either one read/write process or multiple read-only
  # processes.  These builders read and write the production database in a
  # child process, so stop HTTP handlers from opening it until they exit.
  database_subprocess_active.set()
  try:
   with api._db_lock:
    return subprocess.run(command,**kwargs)
  finally:
   database_subprocess_active.clear()
 def run_research(job_id):
  task=research_jobs[job_id];task.update(status='RUNNING',progress={'status':'BUILDING_RESEARCH_V3'})
  try:
   result=build_latest_research_run(root,db);task.update(status='SUCCESS',result=result,progress={'status':'READY','run_id':result['run_id']})
  except Exception as exc:
   task.update(status='FAILED',progress={'status':'RESEARCH_BUILD_FAILED','error':str(exc)})
 def today_status(job_id):
  task=daily_jobs.get(job_id)
  if not task: return None
  publisher=task.get('publisher')
  if publisher and task.get('status') not in ('SUCCESS','FAILED') and task.get('phase') not in ('ANALYSIS_BINDING','READY','FAILED'):
   child=publisher.status(task['publication_job_id'])
   task.update(status=child['status'],progress=child.get('progress',{}),updated_at_utc=child.get('updated_at_utc'))
  return {'job_id':job_id,'status':task['status'],'details':{'trade_date':task.get('trade_date'),'source_bundle_id':task.get('source_bundle_id')},'progress':task.get('progress',{}),'updated_at_utc':task.get('updated_at_utc')}
 def run_today(job_id,body):
  task=daily_jobs[job_id];task.update(status='RUNNING',progress={'status':'INPUT_DOWNLOADING'})
  result=subprocess.run([sys.executable,str(Path(root)/'run_upgrade_m3.py')],cwd=root,capture_output=True,text=True)
  receipt_path=Path(root)/'reports/upgrade_m3/M3_AUTOMATIC_INPUT_RECEIPT.json'
  receipt=json.loads(receipt_path.read_text('utf-8')) if receipt_path.is_file() else {}
  if not result.returncode and receipt.get('final_status')!='FULL_PASS':
   # A successful input command may be supplied by an embedded/test runner
   # that records only the versioned source-bundle catalog. Recover only a
   # unique, fully identified bundle; ambiguity still fails closed.
   with api._connection_provider.connect() as receipt_connection:
    candidates=[json.loads(row[0]) for row in receipt_connection.execute('select payload_json from source_bundles').fetchall()]
   candidates=[item for item in candidates if item.get('source_bundle_id') and item.get('target_trade_date')]
   if len(candidates)==1:
    item=candidates[0];receipt={'final_status':'FULL_PASS','source_bundle_id':item['source_bundle_id'],'day_validation':{'target_trade_date':str(item['target_trade_date']).replace('-','')}}
  if result.returncode or receipt.get('final_status')!='FULL_PASS':
   task.update(status='FAILED',progress={'status':'INPUT_FAILED','error':receipt.get('blockers') or result.stderr[-500:]});return
  bundle=receipt['source_bundle_id'];day=receipt['day_validation']['target_trade_date'];trade_date=date(int(str(day)[:4]),int(str(day)[4:6]),int(str(day)[6:]))
  expected_date=str(body.get('expected_trade_date') or '').strip()
  if body.get('build_research_v3') and not expected_date:
   task.update(status='FAILED',progress={'status':'INPUT_DATE_EXPECTED_REQUIRED','error':'页面未提供在线确认的目标交易日，已拒绝发布；请刷新页面后重试'});return
  if expected_date and trade_date.isoformat()!=expected_date:
   task.update(status='FAILED',progress={'status':'INPUT_DATE_MISMATCH','error':f'预期 {expected_date}，官方数据为 {trade_date.isoformat()}；未发布'});return
  task.update(source_bundle_id=bundle,trade_date=trade_date.isoformat(),progress={'status':'PUBLISHING'})
  publisher,publication_job_id=submit_one_click(Path(root),bundle,trade_date,body.get('economic_model_id','current-economic-model'),body.get('computation_contract_id','current-computation-contract'),db)
  task.update(publisher=publisher,publication_job_id=publication_job_id,status='RUNNING',progress={'status':'PUBLISHING'})
  published=publisher.wait(publication_job_id,timeout=3600)
  if published.get('status')!='SUCCESS':
   task.update(status='FAILED',progress={'status':'PUBLISH_FAILED','error':published.get('error') or published.get('details') or 'M4发布未完成'});return
  task.update(phase='ANALYSIS_BINDING',progress={'status':'ANALYSIS_BINDING'})
  preview=run_database_subprocess([sys.executable,str(Path(root)/'scripts/build_m8_m9_preview.py'),'--incremental-current'],cwd=root,capture_output=True,text=True,timeout=3600)
  if preview.returncode:
   task.update(status='FAILED',progress={'status':'ANALYSIS_BINDING_FAILED','error':preview.stderr[-1000:] or preview.stdout[-1000:]});return
  try:
   v3_report=json.loads(preview.stdout) if isinstance(preview.stdout,str) else {'status':'TEST_DOUBLE_NO_STDOUT'}
  except Exception as exc:
   task.update(status='FAILED',progress={'status':'ANALYSIS_REPORT_INVALID','error':str(exc)});return
  task.update(progress={'status':'BUILDING_MAINLINE_BACKGROUND'})
  mainline=run_database_subprocess([sys.executable,str(Path(root)/'scripts/build_m10_mainline_preview.py')],cwd=root,capture_output=True,text=True,timeout=3600)
  if mainline.returncode:
   task.update(status='FAILED',progress={'status':'MAINLINE_BUILD_FAILED','error':mainline.stderr[-1000:] or mainline.stdout[-1000:]});return
  try:
   task['mainline_result']=json.loads(mainline.stdout) if isinstance(mainline.stdout,str) else {'status':'TEST_DOUBLE_NO_STDOUT'}
  except Exception as exc:
   task.update(status='FAILED',progress={'status':'MAINLINE_REPORT_INVALID','error':str(exc)});return
  if body.get('build_research_v3'):
   task.update(progress={'status':'BUILDING_RESEARCH_V3'})
   try:
    research_result=build_latest_research_run(root,db)
   except Exception as exc:
    task.update(status='FAILED',progress={'status':'RESEARCH_BUILD_FAILED','error':str(exc)});return
   task['research_result']=research_result
   task.update(progress={'status':'BUILDING_RESEARCH_V3_3'})
   p12=run_database_subprocess([sys.executable,str(Path(root)/'scripts/run_p12_daily_pipeline.py'),'--publication-id',str(published.get('publication_id')),'--trade-date',trade_date.isoformat()],cwd=root,capture_output=True,text=True,timeout=3600)
   if p12.returncode:
    task.update(status='FAILED',progress={'status':'RESEARCH_V3_3_BUILD_FAILED','error':p12.stderr[-2000:] or p12.stdout[-2000:]});return
   try:
    task['research_v3_3_result']=json.loads(p12.stdout.strip().splitlines()[-1])
   except Exception as exc:
    task.update(status='FAILED',progress={'status':'RESEARCH_V3_3_REPORT_INVALID','error':str(exc)});return
  snapshot_binding=v3_report.get('snapshot_binding',{}) if isinstance(v3_report,dict) else {}
  hierarchy=v3_report.get('hierarchy',{}) if isinstance(v3_report,dict) else {}
  mainline_result=task.get('mainline_result') or {}
  research_result=task.get('research_result') or {}
  research_v3_3_result=task.get('research_v3_3_result') or {}
  # When the API is running on PostgreSQL, generation remains an isolated
  # DuckDB compute step and must publish its completed head into PG before the
  # job can become visible to the page.  The synchronizer is transactional and
  # fail-closed; no successful UI state is reported for a missing PG copy.
  if str(os.environ.get('WORKBENCH_API_BACKEND','')).lower() == 'postgresql':
   task.update(progress={'status':'SYNCING_POSTGRES_PUBLICATION'})
   pg_sync=run_database_subprocess([sys.executable,str(Path(root)/'scripts/sync_latest_publication_to_postgres.py'),'--trade-date',trade_date.isoformat()],cwd=root,capture_output=True,text=True,timeout=3600)
   if pg_sync.returncode:
    task.update(status='FAILED',progress={'status':'POSTGRES_SYNC_FAILED','error':pg_sync.stderr[-2000:] or pg_sync.stdout[-2000:]});return
   try:
    sync_payload=json.loads(pg_sync.stdout) if isinstance(pg_sync.stdout,str) else {}
   except Exception:
    sync_payload={}
   if sync_payload.get('status')!='FULL_PASS':
    task.update(status='FAILED',progress={'status':'POSTGRES_SYNC_FAILED','error':sync_payload.get('error') or 'PG 同步未通过硬校验'});return
   task['postgres_sync']=sync_payload
  task.update(
   v3_report=v3_report,
   phase='READY',
   status='SUCCESS',
   progress={
    'status':'READY',
    'trade_date':trade_date.isoformat(),
    'publication_id':published.get('publication_id'),
    'v3_snapshot_id':snapshot_binding.get('snapshot_id') if isinstance(snapshot_binding,dict) else None,
    'preserved_entry_count':v3_report.get('preserved_entry_count') if isinstance(v3_report,dict) else None,
    'hierarchy_version':hierarchy.get('hierarchy_version') if isinstance(hierarchy,dict) else None,
    'hierarchy_node_count':hierarchy.get('hierarchy_node_count') if isinstance(hierarchy,dict) else None,
    'mainline_snapshot_id':mainline_result.get('snapshot_id'),
    'research_run_id':research_result.get('run_id'),
    'research_v3_3_bundle_digest':research_v3_3_result.get('bundle_digest'),
   },
  )
 def run_today_guarded(job_id,body):
  try:
   run_today(job_id,body)
  except Exception as exc:
   daily_jobs[job_id].update(status='FAILED',phase='FAILED',progress={'status':'PIPELINE_FAILED','error':f'{type(exc).__name__}: {exc}'})
 def legacy_workbench(publication_id):
  trade_date,_=api._pub(publication_id)
  return resolve_workbench_path(root,trade_date,publication_id).read_bytes()
 class Handler(BaseHTTPRequestHandler):
  def _send(self,status,body,ctype='application/json; charset=utf-8'):
   raw=(json.dumps(_json_safe(body),ensure_ascii=False,default=_json_default,allow_nan=False) if not isinstance(body,bytes) else body); raw=raw.encode() if isinstance(raw,str) else raw
   try:
    self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(raw)
   except (BrokenPipeError,ConnectionAbortedError,ConnectionResetError,TimeoutError):
    self.close_connection=True
    return False
   return True
  def do_GET(self):
   path=urlparse(self.path).path
   allowed_while_database_exclusive=(
    path in ('/api/jobs','/api/operations/status','/api/operations/restart-status','/','/index.html','/v3','/v3/','/v3/index.html','/v2','/v2/','/v2/index.html')
    or path.startswith('/v2/')
   )
   if database_subprocess_active.is_set():
    query={k:v[0] for k,v in parse_qs(urlparse(self.path).query).items()}
    if path=='/api/operations/status':
     active_count=sum(1 for item in daily_jobs.values() if item.get('status') in ('QUEUED','RUNNING'))
     out={**last_operations_status,'service_state':'BUSY','active_job_count':active_count,'service_pid':os.getpid(),'service_url':'http://'+self.headers.get('Host','127.0.0.1:28765'),'service_control_contract':'WORKBENCH_LOCAL_SERVICE_CONTROL_V1','database_access':'SUSPENDED_FOR_BUILD'}
     return self._send(200,out)
    if path=='/api/jobs':
     job_id=query.get('job_id')
     if job_id in daily_jobs:return self._send(200,today_status(job_id))
     if query.get('active')=='1':
      return self._send(200,{'items':[today_status(key) for key,item in daily_jobs.items() if item.get('status') in ('QUEUED','RUNNING')]})
     return self._send(503,{'code':'DATABASE_BUILD_IN_PROGRESS','message':'当日分析正在独占更新，请稍后重试','retryable':True})
    if not allowed_while_database_exclusive:
     return self._send(503,{'code':'DATABASE_BUILD_IN_PROGRESS','message':'当日分析正在独占更新，请稍后重试','retryable':True})
   if allowed_while_database_exclusive:
    return self._do_GET()
   with api.request_scope():
    return self._do_GET()
  def _do_GET(self):
   u=urlparse(self.path); x={k:v[0] for k,v in parse_qs(u.query).items()}
   try:
    if u.path=='/api/publications': out=api.publications(x.get('include_analysis')=='1')
    elif u.path=='/api/hot-rankings': out=api.hot_rankings(x.get('source','EASTMONEY_HOT_RANK'),x.get('list_type') or None,x.get('mode','LATEST'),x.get('as_of'),x.get('batch_id'),x.get('page',1),x.get('page_size',50),x.get('co_listed','0')=='1')
    elif u.path=='/api/v3/research/context':
     context=research.contexts.resolve_request(x.get('publication_id',''),x.get('trade_date',''),x.get('mode','CLOSE'));out={'status':context['status'],'context':context,'items':[]}
    elif u.path=='/api/v3/research/today':
     out=today_research.list(page=x.get('page',1),page_size=x.get('page_size',20),category=x.get('category',''),selection_mode=x.get('selection_mode',''),q=x.get('q',''))
    elif u.path=='/api/v3/research/today-turnover':
     out=turnover_enrichment.load_materialized(expected_digest=x.get('bundle_digest',''))
    elif u.path.startswith('/api/v3/research/today/'):
     security_id=unquote(u.path[len('/api/v3/research/today/'):].strip('/'));out=today_research.detail(security_id,x.get('bundle_digest',''))
    elif u.path=='/api/v3/legacy-matrix':
     publication_id=str(x.get('publication_id') or '').strip();trade_date=str(x.get('trade_date') or '').strip()
     if bool(publication_id)!=bool(trade_date): raise ValueError('CONTEXT_MODE_CONFLICT')
     if publication_id:
      canonical_trade_date,_=api._pub(publication_id)
      canonical_trade_date=str(canonical_trade_date)
      if trade_date and trade_date!=canonical_trade_date: raise ValueError('TRADE_DATE_UNAVAILABLE')
      trade_date=canonical_trade_date
     out=build_legacy_matrix(publication_id,trade_date)
    elif u.path=='/api/v3/events/overview':
     close=events.ladder(event_bundle_id=x.get('event_bundle_id'),trade_date=x.get('trade_date'),page=1,page_size=20,sort='DEFAULT')
     overview_date=x.get('trade_date') or close.get('trade_date')
     down=p09.view(p09.fetch('EXT02',{'date':overview_date}),request={'date':overview_date},page=1,page_size=20)
     market=p09.fetch('EXT06',{'date':overview_date}) if overview_date else None
     market_view={'status':market.status,'date':overview_date,'source_time':{'requested_at':market.requested_at,'received_at':market.received_at,'source_as_of':market.source_as_of},'data':market.normalized,'source_id':'EXT06'} if market else {'status':'UNAVAILABLE','date':None,'data':None,'source_id':'EXT06','reason':'TRADE_DATE_REQUIRED'}
     promotion=p09.promotion(trade_date=overview_date)
     statuses=[close.get('status'),down.get('status'),market_view['status']]
     out={'api_contract':'v3-p09-events-overview-v1.3','status':'AVAILABLE' if all(s=='AVAILABLE' for s in statuses) else 'DEGRADED' if any(s=='AVAILABLE' for s in statuses) else 'UNAVAILABLE','event_close':close,'limit_down':down,'market_overview':market_view,'source_status':{'EXT01':close.get('status'),'EXT02':down.get('status'),'EXT05:yesterday_limit_up':promotion.get('status'),'EXT06':market_view['status']},'promotion':promotion,'count_basis':{'limit_up':'EXT01_ARCHIVED_PAGE_WITH_HEADER_SEPARATE','limit_down':'EXT02_RETURNED_PAGE_NOT_FULL_MARKET','market_rise_fall':'EXT06_SOURCE_RISE_FALL','promotion':'EXT05_YESTERDAY_LIMIT_UP_TRANSITIONS'},'next_action':'各在线数据集按自身来源状态展示。'}
    elif u.path=='/api/v3/events/pools':
     out=p09.events_pools(pool_type=x.get('pool_type'),trade_date=x.get('trade_date'),page=x.get('page',1),page_size=x.get('page_size',30),sort=x.get('sort','SOURCE_ORDER'))
    elif u.path=='/api/v3/events/topics':
     out=p09.topics(trade_date=x.get('trade_date'))
    elif u.path=='/api/v3/events/distribution':
     topics=p09.topics(trade_date=x.get('trade_date'));out={'api_contract':'v3-p09-events-distribution-v1.2','status':topics['status'],'date':topics.get('date'),'items':[{'source_topic_id':item.get('source_topic_id'),'topic_name':item.get('topic_name'),'limit_up_member_count':item.get('limit_up_member_count',0),'unique_member_count':item.get('unique_member_count',0),'membership_count':item.get('membership_count',0),'amount_sum':item.get('amount_sum'),'amount_valid_count':item.get('amount_valid_count',0),'amount_coverage':item.get('amount_coverage'),'dragon_estimated_amount_yi':item.get('dragon_estimated_amount_yi'),'dragon_estimated_valid_count':item.get('dragon_estimated_valid_count',0),'dragon_estimated_basis':item.get('dragon_estimated_basis'),'preview_members':[member for member in item.get('members',[]) if member.get('is_limit_up') is True][:5]} for item in topics.get('items',[])],'global_unique_member_count':topics.get('global_unique_member_count'),'membership_count':topics.get('membership_count'),'amount_sum':topics.get('amount_sum'),'amount_valid_count':topics.get('amount_valid_count'),'amount_coverage':topics.get('amount_coverage'),'dragon_estimated_amount_yi':topics.get('dragon_estimated_amount_yi'),'dragon_estimated_valid_count':topics.get('dragon_estimated_valid_count',0),'dragon_estimated_basis':topics.get('dragon_estimated_basis'),'source_status':topics.get('source_status'),'coverage':topics.get('coverage'),'storage':topics.get('storage'),'empty_state':topics.get('empty_state')}
    elif u.path.startswith('/api/v3/events/topics/') and u.path.endswith('/members'):
     topic_id=unquote(u.path[len('/api/v3/events/topics/'): -len('/members')].strip('/'));topics=p09.topics(trade_date=x.get('trade_date'));matches=[member for item in topics.get('items',[]) if str(item.get('source_topic_id'))==topic_id for member in item.get('members',[])];page=int(x.get('page',1));size=min(30,max(1,int(x.get('page_size',30))));start=(page-1)*size;out={'api_contract':'v3-p09-events-topic-members-v1.0','status':topics['status'],'source_topic_id':topic_id,'items':matches[start:start+size],'total':len(matches),'returned_count':len(matches[start:start+size]),'has_more':start+size<len(matches),'storage':topics.get('storage'),'empty_state':None if matches else {'code':'TOPIC_MEMBER_UNAVAILABLE','message':'当前题材没有可展示的来源成员，未以本地板块成员补写。'}}
    elif u.path.startswith('/api/v3/events/stocks/'):
     security_id=unquote(u.path[len('/api/v3/events/stocks/'):].strip('/'));event=events.ladder_evidence(security_id=security_id,event_bundle_id=x.get('event_bundle_id'),trade_date=x.get('trade_date'));local=research.stock_detail(x['local_context_id'],security_id) if x.get('local_context_id') else {'status':'NOT_REQUESTED','basis':'OPTIONAL_CONTEXT_ID','items':[]};out={'api_contract':'v3-p09-events-stock-context-v1.0','status':event.get('status'),'security_id':security_id,'online_event':event,'local_context':local,'hot_rank':{'status':'REQUEST_TIME_ONLY','value':None,'raw_payload_persisted':False},'next_action':'在线事实与本地研究分别依据各自日期及来源展示；缺失项保持UNKNOWN。'}
    elif u.path=='/api/v3/hot-rankings':
     modes=None
     if x.get('type') and x.get('list_type'): modes=[(x['type'],x['list_type'])]
     out=p09.hot_rankings(modes=modes or (('hour','normal'),('hour','skyrocket'),('day','normal'),('day','skyrocket')),page=x.get('page',1),page_size=x.get('page_size',30))
    elif u.path=='/api/v3/hot-plates':
     out=p09.hot_plates(plate_type=x.get('type','concept'),page=x.get('page',1),page_size=x.get('page_size',30))
    elif u.path=='/api/v3/hot-topics':
     out=p09.hot_topics(page=x.get('page',1),page_size=x.get('page_size',30))
    elif u.path=='/api/v3/online/latest-trade-date':
     probes=p09.batch((('EXT03',{}),('EXT02',{})))
     valid=sorted({item.source_trade_date for item in probes if item.status=='AVAILABLE' and item.source_trade_date})
     out={'api_contract':'V3_ONLINE_LATEST_TRADE_DATE_V1','status':'AVAILABLE' if valid else 'UNAVAILABLE','trade_date':valid[-1] if valid else None,'confirmation_sources':[{'source_id':item.source_id,'status':item.status,'source_trade_date':item.source_trade_date,'source_as_of':item.source_as_of} for item in probes],'basis':'LATEST_CONFIRMED_PUBLIC_SOURCE_TRADE_DATE','independent_from_local_publication':True}
    elif u.path.startswith('/api/v3/events/ladder/'):
     security_id=unquote(u.path[len('/api/v3/events/ladder/'):].strip('/'))
     out=events.ladder_evidence(security_id=security_id,event_bundle_id=x.get('event_bundle_id'),trade_date=x.get('trade_date'))
    elif u.path=='/api/v3/events/ladder': out=events.ladder(event_bundle_id=x.get('event_bundle_id'),trade_date=x.get('trade_date'),page=x.get('page',1),page_size=x.get('page_size',20),sort=x.get('sort','DEFAULT'))
    elif u.path=='/api/v3/research/jobs':
     out=research_jobs.get(x.get('job_id'))
     if out is None: raise ValueError('JOB_NOT_FOUND')
    elif u.path=='/api/v3/home/local': out=research.home(x['context_id'])
    elif u.path=='/api/v3/research/sectors': out=research.list_sectors(x['context_id'],track=x.get('track','ALL'),sector_type=x.get('type',''),q=x.get('q',''),page=x.get('page',1),page_size=x.get('page_size',20))
    elif u.path.startswith('/api/v3/research/sectors/') and u.path.endswith('/members'):
     sector_id=unquote(u.path[len('/api/v3/research/sectors/'): -len('/members')].strip('/'));out=research.sector_members(x['context_id'],sector_id,role=x.get('role','ALL_MEMBERS'),q=x.get('q',''),page=x.get('page',1),page_size=x.get('page_size',20),sort=x.get('sort','ROLE'))
    elif u.path.startswith('/api/v3/research/sectors/') and u.path.endswith('/online-context'):
     sector_id=unquote(u.path[len('/api/v3/research/sectors/'): -len('/online-context')].strip('/'));out=_p09_sector_online_context(root,research,p09,sector_id,x)
    elif u.path.startswith('/api/v3/research/sectors/') and u.path.endswith('/signals'):
     sector_id=unquote(u.path[len('/api/v3/research/sectors/'): -len('/signals')].strip('/'));out=research.sector_signals(x['context_id'],sector_id,x.get('days',10))
    elif u.path=='/api/v3/research/evaluation': out=research.signal_evaluation(x['context_id'])
    elif u.path.startswith('/api/v3/research/sectors/'):
     sector_id=unquote(u.path[len('/api/v3/research/sectors/'):].strip('/'));out=research.sector_detail(x['context_id'],sector_id)
    elif u.path=='/api/v3/research/shortlist': out=research.shortlist(x['context_id'],list_type=x.get('list_type','CURRENT_FOCUS'),page=x.get('page',1),page_size=x.get('page_size',20))
    elif u.path.startswith('/api/v3/research/stocks/') and u.path.endswith('/evidence'):
     security_id=unquote(u.path[len('/api/v3/research/stocks/'): -len('/evidence')].strip('/'));out=research.stock_evidence(x['context_id'],security_id,x.get('section','selection'))
    elif u.path.startswith('/api/v3/research/stocks/'):
     security_id=unquote(u.path[len('/api/v3/research/stocks/'):].strip('/'));out=research.stock_detail(x['context_id'],security_id)
    elif u.path=='/api/v3/search/suggest': out=research.search(x['context_id'],x.get('q',''),x.get('entity_type','ALL'))
    elif u.path=='/api/dashboard': out=api.dashboard(x['publication_id'],x.get('include_analysis')=='1',x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/sectors': out=api.sectors(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50),x.get('type',''),x.get('include_analysis')=='1',x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/sector-library': out=api.sector_library(x['publication_id'],x.get('page',1),x.get('page_size',50),x.get('q',''),x.get('type',''),x.get('bucket',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/sectors/cycle': out=api.sector_cycle(x['publication_id'],x.get('page',1),x.get('page_size',20),x.get('sector_type',x.get('type','')),x.get('q',''),x.get('days',10),x.get('metric','rank'),x.get('hierarchy_level',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/sectors/') and u.path.endswith('/timeline'):
     sector_id=unquote(u.path[len('/api/sectors/'): -len('/timeline')].strip('/'));out=api.sector_timeline(x['publication_id'],sector_id,x.get('days',30),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/sectors/') and u.path.endswith('/members/history'):
     sector_id=unquote(u.path[len('/api/sectors/'): -len('/members/history')].strip('/'));out=api.sector_members_history(x['publication_id'],sector_id,x.get('days',10),x.get('page',1),x.get('page_size',50),x.get('state','ALL'),x.get('security_id',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/sectors/') and u.path.endswith('/leader-history'):
     sector_id=unquote(u.path[len('/api/sectors/'): -len('/leader-history')].strip('/'));out=api.sector_leader_history(x['publication_id'],sector_id,x.get('days',30),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/mainlines': out=api.mainlines(x['publication_id'],x.get('page',1),x.get('page_size',50),x.get('class',''),x.get('days',30),x.get('type',''),x.get('group',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/mainlines/') and u.path.endswith('/evidence'):
     sector_id=unquote(u.path[len('/api/mainlines/'): -len('/evidence')].strip('/'));out=api.mainline_evidence(x['publication_id'],sector_id,x.get('days',30),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/market/cycle': out=api.market_cycle(x['publication_id'],x.get('days',60),x.get('metrics',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/market/day-detail': out=api.market_day_detail(x['publication_id'],x.get('trade_date',''),x.get('basis','AUTO'))
    elif u.path=='/api/limit-ladder': out=api.limit_ladder(x['publication_id'],x.get('page',1),x.get('page_size',50),x.get('level','ALL'),x.get('state','ALL'),x.get('promotion','ALL'),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/limit-ladder/promotion-history': out=api.limit_promotion_history(x['publication_id'],x.get('days',30),x.get('previous_level','ALL'),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/stocks': out=api.stocks(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50))
    elif u.path=='/api/stocks/technical': out=api.technical(x['publication_id'],x.get('page',1),x.get('page_size',50),x.get('basis','AUTO'),x.get('ma_state',''),x.get('rps_window',''),x.get('rps_min',''),x.get('amount_class',''),x.get('turnover_min',''),x.get('quality_filter',''),x.get('research_band',''),x.get('trade_date'))
    elif u.path=='/api/stocks/new-highs': out=api.new_highs(x['publication_id'],x.get('page',1),x.get('page_size',50),x.get('basis','AUTO'),x.get('window',20),x.get('streak_min',''),x.get('include_ties','0')=='1',x.get('rps_min',''),x.get('research_band',''),x.get('trade_date'))
    elif u.path.startswith('/api/stocks/') and u.path.endswith('/memberships'):
     security_id=unquote(u.path[len('/api/stocks/'): -len('/memberships')].strip('/'));out=api.stock_memberships(x['publication_id'],security_id,x.get('page',1),x.get('page_size',50),x.get('bucket',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/stocks/') and u.path.endswith('/sector-associations'):
     security_id=unquote(u.path[len('/api/stocks/'): -len('/sector-associations')].strip('/'));out=api.sector_associations(x['publication_id'],security_id,x.get('days',1),x.get('include_rejected','0')=='1',x.get('page',1),x.get('page_size',50),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/stocks/') and u.path.endswith('/insight'):
     security_id=unquote(u.path[len('/api/stocks/'): -len('/insight')].strip('/'));out=api.stock_insight(x['publication_id'],security_id,x.get('include','overview,technical,sector_context'),x.get('days',20),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/stocks/') and u.path.endswith('/technical-history'):
     security_id=unquote(u.path[len('/api/stocks/'): -len('/technical-history')].strip('/'));out=api.technical_history(x['publication_id'],security_id,x.get('days',20),x.get('price_basis','ADJUSTED'),x.get('fields',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/stocks/') and u.path.endswith('/structure-history'):
     security_id=unquote(u.path[len('/api/stocks/'): -len('/structure-history')].strip('/'));out=api.structure_history(x['publication_id'],security_id,x.get('days',20),x.get('queue',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/candidates': out=api.candidates(x['publication_id'],x.get('q',''),x.get('page',1),x.get('page_size',50),x.get('grade',''),x.get('pattern',''),x.get('include_analysis')=='1',x.get('basis','AUTO'),x.get('final')=='1')
    elif u.path=='/api/queues': out=api.queues(x['publication_id'],x.get('queue','STEADY'),x.get('page',1),x.get('page_size',50),x.get('q',''),x.get('band',''),x.get('include_analysis')=='1',x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/evidence': out=api.evidence(x['publication_id'],x['queue'],x['security_id'],x.get('format',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/identity': out=api.identity(x['publication_id'],x.get('include_analysis')=='1')
    elif u.path=='/api/metadata/field-catalog': out=api.field_catalog(x.get('api_contract',API_CONTRACT),x.get('language','zh-CN'))
    elif u.path=='/api/history/coverage': out=api.history_coverage(x['publication_id'],x.get('days',MAX_OUTPUT_DAYS),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path.startswith('/api/history/jobs/'):
     job_id=unquote(u.path.split('/api/history/jobs/',1)[1]).strip('/')
     try: out=history.status(job_id)
     except HistoryJobError as e:
      if str(e)=='JOB_NOT_FOUND': return self._send(404,{'code':'JOB_NOT_FOUND','message':'任务不存在','retryable':False})
      raise
    elif u.path=='/api/universe/summary': out=api.universe_summary(x['publication_id'],x.get('basis') if 'basis' in x else None,x.get('trade_date'))
    elif u.path=='/api/linkage/history': out=api.linkage_history(x['publication_id'],x.get('sector_id'),x.get('days',10),x.get('security_id',''),x.get('page',1),x.get('page_size',100),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/linkage': out=api.linkage(x['publication_id'],x.get('sector_id'),x.get('security_id'),x.get('page',1),x.get('page_size',100),x.get('q',''),x.get('basis','AUTO'),x.get('trade_date'))
    elif u.path=='/api/input/latest': out=api.latest_bundle()
    elif u.path=='/api/operations/config': out=operations.current()
    elif u.path=='/api/operations/config/history':
     out=operations.history()
    elif u.path=='/api/operations/status':
     out=maintenance.status();out.update({'service_pid':os.getpid(),'service_url':'http://'+self.headers.get('Host','127.0.0.1:28765'),'service_control_contract':'WORKBENCH_LOCAL_SERVICE_CONTROL_V1'})
     if str(os.environ.get('WORKBENCH_API_BACKEND','')).lower()=='postgresql':
      out.update({'backend':'postgresql','database_path':'postgresql://workbench@127.0.0.1:5432/market_research'})
    elif u.path=='/api/operations/restart-status':
     status_path=Path(root)/'runtime/controlled_restart_status.json';out=json.loads(status_path.read_text('utf-8')) if status_path.is_file() else {'state':'尚未执行'}
    elif u.path=='/api/operations/storage':
     out={'items':storage.payload_rows('storage_objects')}
    elif u.path=='/api/operations/backups':
     out={'items':storage.payload_rows('backup_catalog')}
    elif u.path=='/api/operations/cleanup-plans':
     out={'items':storage.payload_rows('cleanup_jobs')}
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
     page=(static/'v2/index.html').read_text('utf-8')
     page=page.replace('__CSRF_TOKEN__',csrf).replace('__WORKBENCH_VERSION__','v2 兼容').replace('__WORKBENCH_MODE__','v2').replace('__WORKBENCH_BASE__','/v2').replace('__WORKBENCH_LABEL__','M7')
     return self._send(200,page.encode(),'text/html; charset=utf-8')
    elif u.path in ('/','/index.html','/v3','/v3/','/v3/index.html'):
     page=(static/'v2/index.html').read_text('utf-8')
     page=page.replace('__CSRF_TOKEN__',csrf).replace('__WORKBENCH_VERSION__','CURRENT').replace('__WORKBENCH_MODE__','v3').replace('__WORKBENCH_BASE__','/').replace('__WORKBENCH_LABEL__','')
     return self._send(200,page.encode(),'text/html; charset=utf-8')
    elif u.path in ('/v3/research-preview','/v3/research-preview/'):
     return self._send(200,(static/'research-v3.html').read_bytes(),'text/html; charset=utf-8')
    elif u.path in ('/v3/online','/v3/online/','/v3/online/index.html'):
     return self._send(200,(static/'online-p09-v3.html').read_bytes(),'text/html; charset=utf-8')
    elif u.path in ('/v3/events','/v3/events/','/v3/events/index.html'):
     return self._send(200,(static/'online-events-v3.html').read_bytes(),'text/html; charset=utf-8')
    elif u.path.startswith('/v2/'):
     relative=unquote(u.path[len('/v2/'):])
     candidate=(static/'v2'/relative).resolve()
     v2_root=(static/'v2').resolve()
     if v2_root not in candidate.parents or not candidate.is_file():
      return self._send(404,{'code':'NOT_FOUND','message':'v2资源不存在','retryable':False,'next_action':'检查地址'})
     content_type=mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
     return self._send(200,candidate.read_bytes(),content_type+'; charset=utf-8' if content_type.startswith(('text/','application/javascript')) else content_type)
    elif u.path in ('/v1','/v1/','/v1/index.html'): return self._send(200,(static/'index.html').read_text('utf-8').replace('__CSRF_TOKEN__',csrf).encode(),'text/html; charset=utf-8')
    elif u.path=='/view': return self._send(200,legacy_workbench(x['publication_id']),'text/html; charset=utf-8')
    elif u.path=='/operations': return self._send(200,(static/'operations.html').read_text('utf-8').replace('__CSRF_TOKEN__',csrf).replace('</body>','<script src="/operations-i18n.js"></script></body>').encode(),'text/html; charset=utf-8')
    elif u.path=='/operations-i18n.js': return self._send(200,(static/'operations-i18n.js').read_bytes(),'application/javascript; charset=utf-8')
    elif u.path=='/fixes.js': return self._send(200,(static/'fixes.js').read_bytes(),'application/javascript; charset=utf-8')
    else:return self._send(404,{'code':'NOT_FOUND','message':'页面不存在','retryable':False,'next_action':'检查地址'})
    self._send(200,out)
   except (KeyError,ValueError) as e:
    code=str(e).strip("'");status=404 if code in ('CONTEXT_NOT_FOUND','SECTOR_NOT_FOUND','STOCK_NOT_FOUND') else 409 if code in ('ANALYSIS_NOT_BUILT','BASIS_UNAVAILABLE','TRADE_DATE_UNAVAILABLE','SOURCE_NOT_FROZEN','LINKAGE_NOT_BUILT','LINKAGE_HISTORY_NOT_BUILT','ASSOCIATION_NOT_BUILT','INSIGHT_NOT_BUILT','CONTEXT_MODE_CONFLICT') else 400
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
    if self.path=='/api/sector-intersection/query':
     return self._send(200,api.sector_intersection_query(body))
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
    if self.path=='/api/operations/stop':
     maintenance._guard(body.get('confirmation'));maintenance.lock.release()
     self._send(202,{'state':'STOPPING','message':'服务正在停止','service_pid':os.getpid()})
     threading.Thread(target=lambda:(time.sleep(.4),self.server.shutdown()),daemon=True).start();return
    if self.path=='/api/history/jobs':
     return self._send(202,history.submit(body))
    if self.path=='/api/v3/research/jobs':
     with daily_jobs_lock:
      active=next((item for item in research_jobs.values() if item.get('status') in ('QUEUED','RUNNING')),None)
      if active:return self._send(409,{'code':'RESEARCH_BUILD_ALREADY_RUNNING','message':'V3研究构建正在运行','retryable':True})
      job_id='research-job-'+uuid.uuid4().hex;research_jobs[job_id]={'job_id':job_id,'job_type':'BUILD_RESEARCH_V3','status':'QUEUED','progress':{'status':'QUEUED'}}
     threading.Thread(target=run_research,args=(job_id,),daemon=True,name=job_id).start()
     return self._send(202,research_jobs[job_id])
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
    thread=threading.Thread(target=run_today_guarded,args=(job_id,body),daemon=True,name=job_id);thread.start()
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

def _database_lock_error(exc):
 text=str(exc).lower()
 return isinstance(exc,duckdb.IOException) and any(marker in text for marker in ('already open','being used by another process','另一个程序正在使用','file is already open','could not set lock','conflicting lock'))

def _recover_startup(root,db,timeout_seconds=60):
 # Desktop SQL clients can briefly hold DuckDB's file lock.  Wait only for
 # that specific, recoverable condition; corruption and other IO failures
 # must still fail closed.
 deadline=time.monotonic()+max(0,int(timeout_seconds))
 while True:
  try:
   return OneClickPublisher(root,db).recover_interrupted(ControlledProduction(Path(root)),background=True)
  except Exception as exc:
   if not _database_lock_error(exc) or time.monotonic()>=deadline: raise
   time.sleep(1)

def serve(root,host='127.0.0.1',port=8765,database_path=None):
 db=Path(database_path).resolve() if database_path else Path(root)/'data/database/market_research.duckdb'
 # Persisted jobs are resumed before accepting new commands.  The controlled
 # worker is supplied explicitly so an interrupted production request cannot
 # be mistakenly published as an empty request.
 _recover_startup(Path(root),db)
 ThreadingHTTPServer((host,port),make_handler(root,db)).serve_forever()
