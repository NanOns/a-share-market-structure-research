from production.daily import changed_components
def test_gbbq_revision():assert changed_components({'source_fingerprint_components':{'gbbq':'a'}},{'source_fingerprint_components':{'gbbq':'b'}})==['gbbq']
