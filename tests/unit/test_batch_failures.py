#!/usr/bin/env python
"""
Tests para procesamiento por lotes (Batch) con mocks mejorados.
Verifica el comportamiento ante fallos parciales.
"""

import pytest
import httpx
from geofinder import GeoFinder


@pytest.mark.asyncio
async def test_find_batch_partial_failures(pelias_mock):
    """Verifica cómo se comportan los lotes cuando algunos elementos fallan."""
    queries = ["QUERY_A", "QUERY_B", "QUERY_C", "QUERY_D"]
    
    # Usar patrones simples de texto para evitar problemas con otros parámetros (size, layers)
    pelias_mock.add_pattern_response("QUERY_A", 200, json_data={"features": [{"properties": {"nom": "A"}, "geometry": {"coordinates": [0,0]}}]}) \
               .add_pattern_response("QUERY_B", 500) \
               .add_pattern_response("QUERY_C", exception=httpx.TimeoutException("Too slow")) \
               .add_pattern_response("QUERY_D", 200, json_data={"features": [{"properties": {"nom": "D"}, "geometry": {"coordinates": [0,0]}}]})

    async with GeoFinder(max_retries=0) as client:
        results = await client.find_batch(queries, max_concurrency=2, ignore_errors=True)

    assert len(results) == 4
    
    # Mapear por query original para verificar
    res_map = {r.query: r for r in results}
    
    # A (Éxito)
    assert len(res_map["QUERY_A"].results) > 0
    assert res_map["QUERY_A"].results[0].nom == "A"
    
    # B (Fallo 500)
    assert len(res_map["QUERY_B"].results) == 0
    assert res_map["QUERY_B"].error is not None
    
    # C (Fallo Timeout)
    assert len(res_map["QUERY_C"].results) == 0
    assert res_map["QUERY_C"].error is not None
    
    # D (Éxito)
    assert len(res_map["QUERY_D"].results) > 0
    assert res_map["QUERY_D"].results[0].nom == "D"


@pytest.mark.asyncio
async def test_find_reverse_batch_partial_failures(pelias_mock):
    """Verifica fallos parciales en geocodificación inversa por lotes."""
    # Usar coordenadas muy distintivas
    coords = [(1.23, 1.23), (4.56, 4.56)]
    
    # Configurar mock por patrones de coordenadas
    pelias_mock.add_pattern_response("1.23", 200, json_data={"features": [{"properties": {"nom": "Lugar 1"}, "geometry": {"coordinates": [1.23, 1.23]}}]}) \
               .add_pattern_response("4.56", 404)

    async with GeoFinder() as client:
        results = await client.find_reverse_batch(coords, epsg=4326, max_concurrency=1, ignore_errors=True)

    assert len(results) == 2
    
    # Encontrar por fragmento de query
    r1 = next(r for r in results if "1.23" in r.query)
    r2 = next(r for r in results if "4.56" in r.query)
    
    assert len(r1.results) > 0
    assert r1.results[0].nom == "Lugar 1"
    
    assert len(r2.results) == 0
    assert r2.error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
