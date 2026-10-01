"""Explicit, per-call dependency views for immutable publication validators.

Function code objects come from the frozen validators. Their private globals
receive a read-only filesystem view; module globals and sys.modules never change.
This wrapper grants historical readback only, never current publication authority.
"""
import builtins
import importlib
import types
from copy import deepcopy
from pathlib import Path
from .dm01_accepted_chain_v1 import (
    HEAD_PATH, ANCHOR_SHA, HEAD_CONTRACT, binding, load,
    resolve_frozen_binding, validate_head_v2,
)


class HistoricalBindingResolver:
    def __init__(self, root):
        self.root = Path(root).resolve()
        current = load(self.root, binding(self.root, HEAD_PATH))
        if current.get('contract_id') != HEAD_CONTRACT:
            raise ValueError('ACCEPTED_V2_PUBLICATION_ARCHIVE_REQUIRED')
        validate_head_v2(self.root, current)
        self.current = current
        self.archive = resolve_frozen_binding(self.root, dict(path=HEAD_PATH, sha256=ANCHOR_SHA))

    def resolve(self, logical_path, expected_sha=None):
        raw = str(logical_path).replace('\\', '/')
        path = Path(raw)
        if path.is_absolute() or '..' in path.parts or ':' in raw:
            raise ValueError('PUBLICATION_VIEW_PATH_INVALID')
        physical = (self.root / path).resolve()
        if not physical.is_relative_to(self.root):
            raise ValueError('PUBLICATION_VIEW_PATH_INVALID')
        if raw == HEAD_PATH:
            if expected_sha is not None and expected_sha != ANCHOR_SHA:
                raise ValueError('PUBLICATION_ARCHIVE_HASH_MISMATCH')
            return resolve_frozen_binding(self.root, dict(path=HEAD_PATH, sha256=ANCHOR_SHA))
        if expected_sha is not None:
            from hashlib import sha256
            if sha256(physical.read_bytes()).hexdigest() != expected_sha:
                raise ValueError('PUBLICATION_BINDING_HASH_MISMATCH')
        return physical


class ProjectView:
    def __init__(self, resolver):
        self.resolver = resolver

    def __truediv__(self, logical_path):
        return self.resolver.resolve(logical_path)

    def __fspath__(self):
        return str(self.resolver.root)

    def resolve(self):
        return self


def injected_validators(root):
    """Clone immutable callable code, injecting only explicit per-call dependencies."""
    resolver = HistoricalBindingResolver(root)
    names = ('scripts.promote_v4_09_accepted_head', 'scripts.validate_v4_10_promotion_r1')
    modules = {name: importlib.import_module(name) for name in names}
    private = {}
    for name, module in modules.items():
        namespace = {key: deepcopy(value) if isinstance(value, (dict,list,set)) and key != '__builtins__' else value for key,value in vars(module).items()}
        namespace['ROOT'] = ProjectView(resolver)
        private[name] = namespace

    def local_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and name in private and fromlist:
            return types.SimpleNamespace(**private[name])
        return builtins.__import__(name, globals, locals, fromlist, level)

    for name, module in modules.items():
        namespace = private[name]
        namespace['__builtins__'] = dict(vars(builtins), __import__=local_import)
        for key, value in vars(module).items():
            if isinstance(value, types.FunctionType) and value.__module__ == name:
                clone = types.FunctionType(value.__code__, namespace, value.__name__, value.__defaults__, value.__closure__)
                clone.__kwdefaults__ = value.__kwdefaults__
                namespace[key] = clone
    return resolver, *(types.SimpleNamespace(**private[n]) for n in names)


def _scope(result, resolver):
    return dict(result, validation_scope='ACCEPTED_PUBLICATION_HISTORY_ONLY',
        historical_data_head_resolution='EXPLICIT_EXACT_20260924_ORIGINAL_BYTE_ARCHIVE',
        current_data_head=binding(resolver.root, HEAD_PATH),
        current_data_head_date=resolver.current['accepted_trade_date'],
        business_reacceptance_performed=False, production_authorization=False)


def validate_v4_09_history(*, project_root):
    resolver, v9, _ = injected_validators(project_root)
    return _scope(v9.validate(), resolver)


def validate_v4_10_history(candidate=None, *, project_root):
    resolver, _, v10 = injected_validators(project_root)
    return _scope(v10.validate(candidate), resolver)


def validate_v4_09_history_head(candidate, global_head, receipt, *, project_root):
    resolver, v9, _ = injected_validators(project_root)
    return _scope(v9.validate_head(candidate, global_head, receipt), resolver)
