import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geofinder import GeoFinder
from geofinder.pelias import PeliasClient


@pytest.mark.asyncio
async def test_concurrency_lazy_loading():
    """Verifica que múltiples llamadas simultáneas solo crean un cliente."""
    gf = GeoFinder(icgc_url="http://localhost")

    # Contar cuántas veces se instancia PeliasClient
    creation_count = 0
    original_init = PeliasClient.__init__

    def mocked_init(self, *args, **kwargs):
        nonlocal creation_count
        creation_count += 1
        original_init(self, *args, **kwargs)

    with patch.object(PeliasClient, "__init__", side_effect=mocked_init, autospec=True):
        # Lanzar 50 peticiones simultáneas
        tasks = [gf.get_icgc_client() for _ in range(50)]
        clients = await asyncio.gather(*tasks)

        # Todos deben ser el mismo objeto
        first_client = clients[0]
        for c in clients:
            assert c is first_client

        # El constructor solo debe haberse llamado UNA VEZ
        assert creation_count == 1

    await gf.close()

@pytest.mark.asyncio
async def test_reset_client_safety():
    """Verifica que reset_client cierra el cliente anterior."""
    gf = GeoFinder(icgc_url="http://localhost")
    client = await gf.get_icgc_client()

    assert client._closed is False

    # Resetear
    await gf._reset_client()

    # El cliente original debe estar cerrado
    assert client._closed is True
    # La variable interna debe ser None
    assert gf._icgc_client is None

    await gf.close()

@pytest.mark.asyncio
async def test_cache_key_robustness():
    """Verifica que las claves de caché son seguras contra inyecciones de separadores."""
    gf = GeoFinder()

    # Claves que podrían colisionar si se usa un simple string con ":" como separador
    key1 = gf._get_cache_key("find", "a:b", "c")
    key2 = gf._get_cache_key("find", "a", "b:c")

    assert key1 != key2
