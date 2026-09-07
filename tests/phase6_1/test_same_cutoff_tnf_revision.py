from production.daily import changed_components
def test_tnf_revision():assert changed_components({'source_fingerprint_components':{'sh_tnf':'a'}},{'source_fingerprint_components':{'sh_tnf':'b'}})==['sh_tnf']
