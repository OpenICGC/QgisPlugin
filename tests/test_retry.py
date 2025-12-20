#!/usr/bin/env python
"""
Tests para la estrategia de reintentos (Exponential Backoff) de PeliasClient.

Verifica que los reintentos funcionan correctamente para errores transitorios
y que NO se reintentan errores del cliente (4xx).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from geofinder.pelias import PeliasClient, PeliasError, PeliasConnectionError, PeliasTimeoutError
from geofinder.exceptions import ServiceError, ServiceConnectionError, ServiceTimeoutError, ServiceHTTPError


@pytest.fixture
def pelias_client():
    """Cliente Pelias con reintentos configurados para tests."""
    return PeliasClient(
        url="https://test.example.com",
        max_retries=3,
        retry_base_delay=0.01,  # Delay muy corto para tests rápidos
        retry_max_delay=0.1,
        retry_on_5xx=True,
    )


class TestExponentialBackoff:
    """Tests para la estrategia de reintentos exponenciales."""

    @pytest.mark.asyncio
    async def test_retry_on_5xx_error(self, pelias_client):
        """Verifica que se reintenta en errores 5xx y tiene éxito al final."""
        call_count = 0
        test_url = "https://test.example.com/v1/search"

        async def mock_get(url, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            request = httpx.Request("GET", url)
            if call_count < 3:
                # Errores 503 en los primeros 2 intentos
                response = httpx.Response(503, text="Service Unavailable", request=request)
                raise httpx.HTTPStatusError(
                    f"Error 503",
                    request=request,
                    response=response
                )
            # Éxito en el 3er intento
            return httpx.Response(200, json={"features": []}, request=request)

        pelias_client.client.get = mock_get

        result = await pelias_client.geocode("Barcelona")
        
        assert call_count == 3  # 2 reintentos + 1 éxito
        assert result == {"features": []}

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_error(self, pelias_client):
        """Verifica que NO se reintenta en errores 4xx (errores del cliente)."""
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = httpx.Response(404, text="Not Found")
            response.request = httpx.Request("GET", args[0])
            raise httpx.HTTPStatusError(
                "Error 404",
                request=response.request,
                response=response
            )

        pelias_client.client.get = mock_get

        with pytest.raises(PeliasError) as exc_info:
            await pelias_client.geocode("invalid-query")
        
        assert call_count == 1  # NO reintentos
        assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, pelias_client):
        """Verifica que se reintenta en timeouts."""
        call_count = 0

        async def mock_get(url, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Connection timed out")
            request = httpx.Request("GET", url)
            return httpx.Response(200, json={"features": []}, request=request)

        pelias_client.client.get = mock_get

        result = await pelias_client.geocode("Barcelona")
        
        assert call_count == 3
        assert result == {"features": []}

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, pelias_client):
        """Verifica que se reintenta en errores de conexión."""
        call_count = 0

        async def mock_get(url, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            request = httpx.Request("GET", url)
            return httpx.Response(200, json={"features": []}, request=request)

        pelias_client.client.get = mock_get

        result = await pelias_client.geocode("Barcelona")
        
        assert call_count == 2
        assert result == {"features": []}

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_5xx(self, pelias_client):
        """Verifica que lanza excepción después de agotar todos los reintentos en 5xx."""
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = httpx.Response(503, text="Service Unavailable")
            response.request = httpx.Request("GET", args[0])
            raise httpx.HTTPStatusError(
                "Error 503",
                request=response.request,
                response=response
            )

        pelias_client.client.get = mock_get

        with pytest.raises(PeliasError) as exc_info:
            await pelias_client.geocode("Barcelona")
        
        # 1 intento inicial + 3 reintentos = 4 intentos totales
        assert call_count == 4
        assert "4 intentos" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_timeout(self, pelias_client):
        """Verifica que lanza PeliasTimeoutError después de agotar reintentos."""
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Connection timed out")

        pelias_client.client.get = mock_get

        with pytest.raises(PeliasTimeoutError) as exc_info:
            await pelias_client.geocode("Barcelona")
        
        assert call_count == 4
        assert "4 intentos" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_connection(self, pelias_client):
        """Verifica que lanza PeliasConnectionError después de agotar reintentos."""
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        pelias_client.client.get = mock_get

        with pytest.raises(PeliasConnectionError) as exc_info:
            await pelias_client.geocode("Barcelona")
        
        assert call_count == 4
        assert "4 intentos" in str(exc_info.value)

    def test_backoff_delay_calculation(self, pelias_client):
        """Verifica que el cálculo del delay exponencial es correcto (con margen para jitter)."""
        # Con base_delay=0.01, max_delay=0.1
        # El jitter es +/- 10%
        def check_range(val, target):
            assert target * 0.85 <= val <= target * 1.15  # Un poco más de margen para seguridad

        check_range(pelias_client._calculate_backoff_delay(0), 0.01)
        check_range(pelias_client._calculate_backoff_delay(1), 0.02)
        check_range(pelias_client._calculate_backoff_delay(2), 0.04)
        check_range(pelias_client._calculate_backoff_delay(3), 0.08)
        assert pelias_client._calculate_backoff_delay(4) <= 0.1

    @pytest.mark.asyncio
    async def test_retry_disabled_on_5xx(self):
        """Verifica que retry_on_5xx=False desactiva reintentos en 5xx."""
        client = PeliasClient(
            url="https://test.example.com",
            max_retries=3,
            retry_base_delay=0.01,
            retry_on_5xx=False,  # Deshabilitado
        )
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = httpx.Response(503, text="Service Unavailable")
            response.request = httpx.Request("GET", args[0])
            raise httpx.HTTPStatusError(
                "Error 503",
                request=response.request,
                response=response
            )

        client.client.get = mock_get

        with pytest.raises(PeliasError):
            await client.geocode("Barcelona")
        
        assert call_count == 1  # NO reintentos
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
