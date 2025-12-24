"""
Pytest configuration and fixtures for geofinder tests.
"""

import pytest
from geofinder import GeoFinder


@pytest.fixture
def gf():
    """Create a GeoFinder instance for testing."""
    return GeoFinder(icgc_url="https://eines.icgc.cat/geocodificador")


def pytest_addoption(parser):
    """Add --integration command line option."""
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests marked with 'integration' unless --integration is provided."""
    if config.getoption("--integration"):
        # --integration given in cli: do not skip integration tests
        return
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
