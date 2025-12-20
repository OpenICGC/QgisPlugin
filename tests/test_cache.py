import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch
from geofinder import GeoFinder
from geofinder.models import GeoResult

@pytest.mark.asyncio
async def test_cache_hits_and_misses():
    """Verifica que la caché funcione para peticiones repetidas."""
    gf = GeoFinder(cache_size=10, cache_ttl=60)
    
    # Mockear el método interno que hace la petición real
    with patch.object(gf, '_find_data', new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [GeoResult(nom="Barcelona", x=2.1, y=41.3, epsg=4326)]
        
        # Primera llamada: Debe ser un MISS
        res1 = await gf.find("Barcelona")
        assert len(res1) == 1
        assert mock_find.call_count == 1
        
        # Segunda llamada: Debe ser un HIT
        res2 = await gf.find("Barcelona")
        assert res2 == res1
        assert mock_find.call_count == 1  # No ha vuelto a llamar a la API
        
        # Llamada con use_cache=False: Debe ignorar la caché
        res3 = await gf.find("Barcelona", use_cache=False)
        assert res3 == res1
        assert mock_find.call_count == 2

@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Verifica que los elementos expiren después del TTL."""
    ttl = 1
    gf = GeoFinder(cache_size=10, cache_ttl=ttl)
    
    with patch.object(gf, '_find_data', new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [GeoResult(nom="Girona", x=2.8, y=41.9, epsg=4326)]
        
        await gf.find("Girona")
        assert mock_find.call_count == 1
        
        # Esperar a que expire
        await asyncio.sleep(ttl + 0.1)
        
        await gf.find("Girona")
        assert mock_find.call_count == 2  # Debe haber llamado de nuevo

@pytest.mark.asyncio
async def test_cache_lru_behavior():
    """Verifica el comportamiento LRU de la caché."""
    gf = GeoFinder(cache_size=2, cache_ttl=60)
    
    with patch.object(gf, '_find_data', new_callable=AsyncMock) as mock_find:
        mock_find.side_effect = lambda text, epsg, size=None: [GeoResult(nom=text, x=0, y=0, epsg=4326)]
        
        await gf.find("A") # Cache: [A], Call 1
        await gf.find("B") # Cache: [A, B], Call 2
        assert mock_find.call_count == 2
        
        await gf.find("A") # Cache: [B, A], Call 2 (Hit)
        assert mock_find.call_count == 2
        
        await gf.find("C") # Cache: [A, C], Call 3 (B expelled)
        assert mock_find.call_count == 3
        
        await gf.find("B") # Cache: [C, B], Call 4 (A expelled)
        assert mock_find.call_count == 4
        
        await gf.find("A") # MISS (Call 5)
        assert mock_find.call_count == 5
