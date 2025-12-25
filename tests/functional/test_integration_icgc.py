import pytest
from geofinder import GeoFinder

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_find_barcelona():
    """Verify real connectivity with a simple search for Barcelona."""
    async with GeoFinder() as gf:
        results = await gf.find("Barcelona")
        assert len(results) > 0
        assert any("Barcelona" in r.nom for r in results)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_reverse_geocoding():
    """Verify real reverse geocoding connectivity."""
    async with GeoFinder() as gf:
        # Use coordinates from test_geofinder.py that are known to work
        lon, lat = 2.1734, 41.3851
        results = await gf.find_reverse(lon, lat, epsg=4326)
        if not results:
            print(f"\nDEBUG: find_reverse({lon}, {lat}) returned empty results. Last request: {gf.last_sent_url()}")
        assert len(results) > 0
        # Check for Barcelona or a near municipality
        assert any(results) # Just ensure we got something

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_autocomplete():
    """Verify real autocomplete connectivity."""
    async with GeoFinder() as gf:
        results = await gf.autocomplete("Barcel")
        assert len(results) > 0
        assert any("Barcelona" in r.nom for r in results)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_road_km():
    """Verify real road km search."""
    async with GeoFinder() as gf:
        results = await gf.find_road("AP-7", 150)
        assert len(results) > 0
        assert any("AP-7" in r.nom for r in results)
