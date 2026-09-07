from production.daily import semantic_guard
def test_external_resource_blocked(tmp_path):
 (tmp_path/'market_summary.html').write_text('<script src="https://x"></script>')
 for n in ('sectors.csv','stocks.csv','candidates.csv'):(tmp_path/n).write_text('security_id\na\n')
 try:semantic_guard(tmp_path);assert False
 except RuntimeError:pass
