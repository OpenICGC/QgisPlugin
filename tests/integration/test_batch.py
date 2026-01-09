#!/usr/bin/env python
"""
Test script for batch processing in GeoFinder.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add root directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from geofinder import GeoFinder


@pytest.fixture
async def gf():
    """Fixture para GeoFinder."""
    client = GeoFinder()
    yield client
    await client.close()


async def test_find_batch(gf):
    print("\n--- Testing find_batch ---")
    queries = [
        "Barcelona",
        "Girona",
        "Lleida",
        "Tarragona",
        "Montserrat",
        "Diagonal 100, Barcelona",
        "C-32 km 10",
        "430000 4580000 EPSG:25831"
    ]

    start_time = time.perf_counter()
    results = await gf.find_batch(queries, max_concurrency=3)
    end_time = time.perf_counter()

    print(f"Processed {len(results)} queries in {end_time - start_time:.2f} seconds")

    for query, response in zip(queries, results, strict=False):
        print(f"  Query: '{query}' -> {len(response.results)} results")
        if response.results:
            print(f"    First: {response.results[0].nom} ({response.results[0].nomTipus})")


async def test_find_reverse_batch(gf):
    print("\n--- Testing find_reverse_batch ---")
    coords = [
        (2.1734, 41.3851),  # Barcelona
        (2.8249, 41.9794),  # Girona
        (0.6231, 41.6176),  # Lleida
        (1.2445, 41.1189),  # Tarragona
    ]

    # We use EPSG:4326 for these coords
    start_time = time.perf_counter()
    results = await gf.find_reverse_batch(coords, epsg=4326, max_concurrency=2)
    end_time = time.perf_counter()

    print(f"Processed {len(results)} reverse geocoding requests in {end_time - start_time:.2f} seconds")

    for coord, response in zip(coords, results, strict=False):
        res_list = response.results
        print(f"  Coord: {coord} -> {len(res_list)} results")
        if res_list:
            print(f"    First: {res_list[0].nom} ({res_list[0].nomTipus})")


def test_batch_sync():
    """Test sync wrappers - each call needs its own GeoFinder instance.

    Note: We don't explicitly close the clients because that would require
    running async code in a new event loop, which causes issues with
    connections tied to the previous (closed) loop.
    """
    print("\n--- Testing Sync Batch Methods ---")

    # First batch call
    gf1 = GeoFinder()
    queries = ["Barcelona", "Girona"]
    results = gf1.find_batch_sync(queries)
    print(f"Sync find_batch: {len(results)} results")

    # Second batch call - needs fresh instance
    gf2 = GeoFinder()
    coords = [(2.1734, 41.3851), (2.8249, 41.9794)]
    results_rev = gf2.find_reverse_batch_sync(coords, epsg=4326)
    print(f"Sync find_reverse_batch: {len(results_rev)} results")

    print("✅ Sync batch tests completed")


async def main():
    gf = GeoFinder()
    try:
        await test_find_batch(gf)
        await test_find_reverse_batch(gf)
    finally:
        await gf.close()


if __name__ == "__main__":
    # Test Async
    asyncio.run(main())

    # Test Sync (outside of any event loop)
    test_batch_sync()
