"""Original filesystem/PG guards without unrelated frozen-stage fixture routing."""
from tests import remainder_isolation_plugin as protection


def pytest_configure(config):
    protection.pytest_configure(config)


def pytest_sessionstart(session):
    protection.pytest_sessionstart(session)


def pytest_runtest_logreport(report):
    protection.pytest_runtest_logreport(report)


def pytest_sessionfinish(session, exitstatus):
    protection.pytest_sessionfinish(session, exitstatus)


def pytest_unconfigure(config):
    protection.pytest_unconfigure(config)
