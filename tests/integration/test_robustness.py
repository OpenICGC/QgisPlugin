import asyncio
import pytest
import httpx
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geofinder.pelias import PeliasClient, PeliasError, PeliasConnectionError
from geofinder.exceptions import ServiceError, ServiceConnectionError

@pytest.mark.asyncio
async def test_network_instability():
    """Simula una red extremadamente inestable para verificar la robustez."""
    client = PeliasClient(
        url="https://unstable.icgc.cat",
        max_retries=5,
        retry_base_delay=0.01,
        retry_max_delay=0.1
    )
    
    call_count = 0
    
    async def mock_get(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("Network is down")
        if call_count == 2:
            raise httpx.TimeoutException("Server is slow")
        if call_count == 3:
            # Simulamos un error 500
            request = httpx.Request("GET", url)
            response = httpx.Response(500, text="Internal Server Error", request=request)
            raise httpx.HTTPStatusError("500 Error", request=request, response=response)
        
        # Éxito en el 4º intento
        request = httpx.Request("GET", url)
        return httpx.Response(200, json={"features": [{"properties": {"nom": "Test"}}, {"properties": {"nom": "Test 2"}}]}, request=request)

    client.client.get = mock_get
    
    try:
        result = await client.geocode("Barcelona")
        assert call_count == 4
        assert len(result["features"]) == 2
        print("\n✅ Robustez verificada: recuperado de fallo de red, timeout y error 500.")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_network_instability())
