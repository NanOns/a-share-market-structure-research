from production.daily import semantic_guard
def test_schema_guard(tmp_path):
 (tmp_path/'market_summary.html').write_text('<html>offline</html>')
 for n in ('sectors.csv','stocks.csv','candidates.csv'):(tmp_path/n).write_text('security_id\na\n')
 assert semantic_guard(tmp_path)
