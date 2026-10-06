"""Repository-wide pytest safety entry point; production imports are untouched."""
pytest_plugins = ['tests.runtime_isolation_plugin']
