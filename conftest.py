"""Repository-wide isolated test startup and live input protection."""
pytest_plugins = ["tests.runtime_isolation_plugin", "tests.remainder_isolation_plugin", "tests.final_blocker_plugin"]
