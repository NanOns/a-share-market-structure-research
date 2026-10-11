"""Explicit V4 audit startup or the preserved historical repository test profile."""
import os

pytest_plugins = (["tests.v4_native_isolation_plugin_r4"] if os.environ.get('R4_NATIVE_ISOLATION') else
                  ["tests.v4_audit_isolation_plugin_r3"]
                  if os.environ.get("V4_AUDIT_SCOPE_MANIFEST") else
                  ["tests.runtime_isolation_plugin", "tests.remainder_isolation_plugin", "tests.final_blocker_plugin"])
