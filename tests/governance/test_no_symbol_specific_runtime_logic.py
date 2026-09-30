from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from scan_no_symbol_specific_runtime_logic import _numeric_code_literals,_string_literals,run

def test_complete_repository_runtime_symbol_guard_passes():
    result=run(ROOT)
    assert result['status']=='PASS',result['runtime_hits']
    assert result['production_runtime_hits']==0
    assert not result['unclassified_paths']
    assert all(entry.get('sha256') and entry.get('byte_count') is not None for entry in result['results'])
    categories={entry['path']:entry['category'] for entry in result['results']}
    assert categories['reports/v4_08/audit_inputs/V4_08_R3_LIFECYCLE_CAPTURE_MANIFEST.json']=='EVIDENCE_ONLY'
    assert categories['reports/v4_08/audit_inputs/V4_08_R3_LIFECYCLE_SOURCE_CONTRACT_V1_ORIGINAL.json']=='EVIDENCE_ONLY'
    assert categories['docs/evidence/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC_GUARD_20260930.md']=='EVIDENCE_ONLY'

def test_ast_guard_detects_direct_symbol_comparison_but_ignores_docstrings_and_digests():
    import ast
    source='"""A docstring with an instrument example."""\ndef admit(code):\n    """A function docstring."""\n    return code == "SH.123456"\n\nDIGEST = "SEC-ABCDEF0123456789ABCDEF0123456789"\n'
    hits=list(_string_literals(ast.parse(source)))
    assert [(value,kind) for value,_,kind in hits]==[('SH.123456','EXPLICIT_SECURITY_OR_SYMBOL_LITERAL')]

def test_ast_guard_detects_qualified_numeric_symbol_comparison():
    import ast
    tree=ast.parse('def admit(security_code):\n    return security_code == 600519\n')
    assert [(value,kind) for value,_,kind in _numeric_code_literals(tree)]==[('600519','NUMERIC_SECURITY_CODE_IN_IDENTIFIER_CONTEXT')]
    assert [(value,kind) for value,_,kind in _string_literals(ast.parse('def admit(code):\n    return code == "600519"\n'))]==[('600519','UNQUALIFIED_SECURITY_CODE_IN_IDENTIFIER_CONTEXT')]
