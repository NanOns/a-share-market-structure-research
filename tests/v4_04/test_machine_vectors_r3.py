from scripts.v4_04_machine_vectors_r3 import run


def test_all_machine_rules_have_branch_threshold_and_unknown_vectors():
    receipt = run(write_receipt=False)
    assert receipt["status"] == "PASS"
    assert receipt["machine_rule_count"] == 18
    assert receipt["branch_count"] == 70
    assert receipt["rules_missing_vector_coverage"] == []
