from production.daily import manifest
def test_manifest_hashes_files(tmp_path):
 for n in ('market_summary.html','sectors.csv','stocks.csv','candidates.csv','run_audit.json','PERFORMANCE_AUDIT.json'):(tmp_path/n).write_text('x')
 h=manifest(tmp_path,{},{});assert len(h)==64 and (tmp_path/'manifest.json').exists()
