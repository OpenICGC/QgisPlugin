"""
Pytest configuration and fixtures for geofinder tests.
"""

import pytest
from geofinder import GeoFinder


@pytest.fixture
def gf():
    """Create a GeoFinder instance for testing."""
    return GeoFinder(icgc_url="https://eines.icgc.cat/geocodificador")
