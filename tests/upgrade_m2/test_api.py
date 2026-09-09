import json
import re
from pathlib import Path
from workbench_service.app import Api,MAX_PAGE_SIZE,resolve_workbench_path
from workbench_db import WorkbenchRepository

ROOT=Path(__file__).resolve().parents[2]
with WorkbenchRepository(ROOT) as _repo:
 PUBS={str(day):publication_id for day,publication_id in _repo.connection.execute("select trade_date,publication_id from publication_heads where trade_date in ('2026-09-04','2026-09-07','2026-09-08') order by trade_date").fetchall()}

def test_publications_and_dashboard_are_bound_to_one_publication():
 api=Api(ROOT/'data/database/market_research.duckdb'); pubs=api.publications()
 assert [(x['trade_date'],x['publication_id']) for x in pubs['items']]==list(reversed(list(PUBS.items())))
 for date,pub in PUBS.items():
  d=api.dashboard(pub); assert d['publication_id']==pub and d['selected_date']==date and d['actual_input_date']==date

def test_cross_date_lists_do_not_mix():
 api=Api(ROOT/'data/database/market_research.duckdb')
 for date,pub in PUBS.items():
  for method in (api.sectors,api.stocks):
   x=method(pub,'',1,MAX_PAGE_SIZE); assert x['publication_id']==pub and x['items']
   assert all(str(r.get('date',date))[:10]==date for r in x['items'])

def test_pagination_is_bounded_and_linkage_is_publication_bound():
 api=Api(ROOT/'data/database/market_research.duckdb'); pub=PUBS['2026-09-07']
 assert api.stocks(pub,'',1,9999)['page_size']==MAX_PAGE_SIZE
 assert api.queues(pub,'STEADY',1,50)['items']
 sector=api.sectors(pub,'',1,1)['items'][0]['sector_id']; x=api.linkage(pub,sector,None)
 assert x['publication_id']==pub and x['items'] and all(r['sector_id']==sector for r in x['items'])
 assert x['sector_member_count']>=x['total']
 assert [r['sector_member_rank'] for r in x['items']]==list(range(1,len(x['items'])+1))
 assert all(r['sector_member_count']==x['sector_member_count'] for r in x['items'])


def test_reverse_linkage_preserves_real_sector_rank_and_count():
 api=Api(ROOT/'data/database/market_research.duckdb'); pub=PUBS['2026-09-07']
 sector=api.sectors(pub,'',1,1)['items'][0]['sector_id']
 member=api.linkage(pub,sector,None,1,1)['items'][0]
 reverse=api.linkage(pub,None,member['security_id'])
 same=next(row for row in reverse['items'] if row['sector_id']==sector)
 assert same['sector_member_rank']==member['sector_member_rank']
 assert same['sector_member_count']==member['sector_member_count']

def test_static_workbench_modules_are_preserved():
 html=(ROOT/'src/production/workbench.py').read_text(encoding='utf-8')
 for label in ('今日总览','五类结构队列','板块分类排行','板块个股联动','全市场股票查询','证据说明','核心观察','一般观察','诊断观察','查看证据'):
  assert label in html
 wrapper=(ROOT/'src/workbench_service/static/index.html').read_text(encoding='utf-8')
 assert '/view?publication_id=' in wrapper and '<iframe' in wrapper
 api=Api(ROOT/'data/database/market_research.duckdb'); pub=PUBS['2026-09-07']
 row=api.queues(pub,'STEADY',1,1)['items'][0]
 assert {'security_id','security_name','shadow_research_band','source_v2_class'} <= row.keys()
 assert row['steady_queue_rank'] is not None and row['steady_tier_rank'] is not None
 assert row['_evidence']
 assert api.identity(pub)['publication_id']==pub

def test_evidence_lookup_accepts_ui_queue_key():
 api=Api(ROOT/'data/database/market_research.duckdb'); pub=PUBS['2026-09-07']
 row=api.queues(pub,'STEADY',1,1)['items'][0]
 for queue in ('steady','STEADY_QUEUE','STEADY'):
  result=api.evidence(pub,queue,row['security_id'])
  assert result['item'] and result['item']['security_id']==row['security_id']

def test_service_resolves_latest_static_workbench_without_feature_loss():
 pub=PUBS['2026-09-07']
 path=resolve_workbench_path(ROOT,'2026-09-07',pub)
 siblings=sorted((p for p in path.parents[1].glob('*/market_structure_workbench.html') if p.stat().st_size < 1_000_000 and 'const 数据=' not in p.read_text(encoding='utf8')[:256_000] and '/api/queues' in p.read_text(encoding='utf8')[:256_000]),key=lambda p:p.stat().st_mtime_ns,reverse=True)
 assert path==siblings[0]
 html=path.read_text(encoding='utf-8')
 required=(
  'data-page="概览"','data-page="队列"','data-page="板块"','data-page="联动"',
  'data-page="全市场"','data-page="说明"','id="队列搜索"','id="板块搜索"',
  'id="联动板块搜索"','id="联动个股搜索"','id="全市场搜索"',
  '队内名次','同研究带名次','查看证据','板块内名次','输入股票查看全部所属板块',
  "api('/api/evidence?publication_id='",
  "async function 画联动板块列表()",
  "document.getElementById('查询全部').onclick=()=>{市场页=1;查市场(true)}",
 )
 assert all(token in html for token in required)
 assert '证据按钮' in html and '队列显示' in html and '不会一次性加载全部股票' in html
 assert '"证据":{' not in html


def test_evidence_ui_is_concise_and_explains_percentages():
 source=(ROOT/'src/production/workbench.py').read_text(encoding='utf-8')
 assert '友好证据' in source and '这些数值用于解释当前结构' in source
 assert '例如 -6.7% 表示当前价比近20日最高价低约6.7%' in source
 assert "Object.entries(item)" not in source and "'诊断字段'" not in source
 assert '板块内名次' in source and 'sector_member_count' in source and 'total_member_count' in source


def test_default_stock_scope_is_a_share_and_quotes_are_enriched():
 api=Api(ROOT/'data/database/market_research.duckdb'); pub=PUBS['2026-09-08']
 rows=api.stocks(pub,'',1,MAX_PAGE_SIZE)['items']
 allowed=re.compile(r'^(SH\.(600|601|603|605|688|689)\d{3}|SZ\.(000|001|002|003|300|301)\d{3}|BJ\.92\d{4})$')
 assert rows and all(allowed.fullmatch(row['security_id']) for row in rows)
 assert all({'latest_price','RET1','turnover_amount'} <= row.keys() for row in rows)
 assert all(row['latest_price']>0 and row['turnover_amount']>=0 for row in rows)


def test_queue_api_uses_contract_rank_order_and_sector_has_daily_market_fields():
 api=Api(ROOT/'data/database/market_research.duckdb'); pub=PUBS['2026-09-08']
 queue=api.queues(pub,'STEADY',1,50)
 ranks=[int(row['steady_queue_rank']) for row in queue['items']]
 assert ranks==sorted(ranks)
 assert [row['a_share_queue_rank'] for row in queue['items']]==list(range(1,len(queue['items'])+1))
 sector=api.sectors(pub,'',1,1)['items'][0]
 assert {'sector_ret1_median','sector_turnover_amount','total_member_count'} <= sector.keys()
 assert sector['sector_turnover_amount']>=0 and sector['total_member_count']>0


def test_ui_shows_price_daily_change_turnover_and_normal_sector_supplement():
 source=(ROOT/'src/production/workbench.py').read_text(encoding='utf-8')
 for token in ('最新价','当日涨幅','当日成交额','成分股当日成交额合计','金额=x=>','行业板块','概念板块','股票通用板块','严格按结构合同名次升序','默认范围仅含沪深北 A 股'):
  assert token in source


def test_candidate_api_exposes_non_circular_strength_sector_fields():
 api=Api(ROOT/'data/database/market_research.duckdb'); pub=PUBS['2026-09-08']
 rows=api.candidates(pub,'',1,5)['items']
 required={'strength_sector_name','strength_sector_reason','other_strength_sectors','market_tags','strength_association_contract'}
 assert rows and all(required <= row.keys() for row in rows)
 assert all(row['strength_sector_name']!='近期强势' for row in rows)
 source=(ROOT/'src/production/workbench.py').read_text(encoding='utf-8')
 assert '当前强势关联板块' in source and "['最佳板块','best_sector_name']" not in source.split('const candidateCols=',1)[1].split(';',1)[0]


def test_evidence_uses_modal_without_mutating_table_cells():
 source=(ROOT/'src/production/workbench.py').read_text(encoding='utf-8')
 for token in ('id="证据遮罩"','id="关闭证据"','aria-modal="true"','关闭证据弹窗','event.target===event.currentTarget','成分股当日涨幅中位数'):
  assert token in source
 assert "cell.innerHTML=证据按钮" not in source
 assert "units=[[1e12,'万亿'],[1e11,'百亿'],[1e10,'十亿']" not in source
