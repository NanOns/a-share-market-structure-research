from workbench_analysis.operational_runtime_acceptance_r1_1 import owner_metadata_cleanup_only

BASE="def seal(root,context):\n    candidate={}\n    candidate['owners']=dict(parent['owners'])\n    return candidate\n"
CLEAN="    inherited={key:candidate.pop(key) for key in ('sealed_numeric_preparation','component_source_conservation') if key in candidate}\n    if inherited:candidate['predecessor_generation_evidence']=dict(predecessor=candidate['predecessor'],receipts=inherited)\n"

def test_exact_metadata_cleanup_only():
    updated=BASE.replace("    candidate['owners']",CLEAN+"    candidate['owners']")
    assert owner_metadata_cleanup_only(BASE,updated)
    assert not owner_metadata_cleanup_only(BASE,updated.replace('candidate={}','candidate={"numeric":1}'))
    assert not owner_metadata_cleanup_only(BASE,updated.replace("'component_source_conservation'","'owners'"))
