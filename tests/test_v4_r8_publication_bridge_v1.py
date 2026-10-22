"""Regression checks for R8 publication finalization scope."""
import ast
import inspect

from workbench_db import v4_r8_publication_bridge_v1 as bridge


def test_finalized_receipt_head_hash_is_bound_after_cas():
    tree = ast.parse(inspect.getsource(bridge.publish_candidate))
    calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_commit_pointers"
    ]
    assignments = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "candidate_head_sha" for target in node.targets)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "sha256_file"
    ]

    assert calls
    assert any(line > min(calls) for line in assignments)
