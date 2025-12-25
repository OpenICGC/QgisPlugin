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
        retry_base_delay=0.01,
        retry_max_delay=0.1,
        retry_on_5xx=True,
    )


class TestExponentialBackoff:
    """Tests para la estrategia de reintentos exponenciales."""

    @pytest.mark.asyncio
    async def test_retry_on_5xx_error(self, pelias_client, pelias_mock):
        """Verifica que se reintenta en errores 5xx y tiene éxito al final."""
        # Configurar mock: 2 fallos 503 y luego éxito
        pelias_mock.add_response(503).add_response(503).add_response(200)

        result = await pelias_client.geocode("Barcelona")
        
        assert pelias_mock.call_count == 3
        assert result == {"features": []}

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_error(self, pelias_client, pelias_mock):
        """Verifica que NO se reintenta en errores 4xx."""
        pelias_mock.add_response(404)

        with pytest.raises(ServiceHTTPError) as exc_info:
            await pelias_client.geocode("invalid-query")
        
        assert pelias_mock.call_count == 1
        assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, pelias_client, pelias_mock):
        """Verifica que se reintenta en timeouts."""
        timeout_exc = httpx.TimeoutException("Connection timed out")
        pelias_mock.add_response(exception=timeout_exc).add_response(exception=timeout_exc).add_response(200)

        result = await pelias_client.geocode("Barcelona")
        
        assert pelias_mock.call_count == 3
        assert result == {"features": []}

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, pelias_client, pelias_mock):
        """Verifica que se reintenta en errores de conexión."""
        conn_exc = httpx.ConnectError("Connection refused")
        pelias_mock.add_response(exception=conn_exc).add_response(200)

        result = await pelias_client.geocode("Barcelona")
        
        assert pelias_mock.call_count == 2
        assert result == {"features": []}

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_5xx(self, pelias_client, pelias_mock):
        """Verifica que lanza excepción después de agotar todos los reintentos en 5xx."""
        pelias_mock.add_response(503)

        with pytest.raises(ServiceError) as exc_info:
            await pelias_client.geocode("Barcelona")
        
        assert pelias_mock.call_count == 4
        assert "4 intentos" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_timeout(self, pelias_client, pelias_mock):
        """Verifica que lanza ServiceTimeoutError después de agotar reintentos."""
        pelias_mock.add_response(exception=httpx.TimeoutException("Timed out"))

        with pytest.raises(ServiceTimeoutError) as exc_info:
            await pelias_client.geocode("Barcelona")
        
        assert pelias_mock.call_count == 4
        assert "4 intentos" in str(exc_info.value)

    def test_backoff_delay_calculation(self, pelias_client):
        """Verifica que el cálculo del delay exponencial es correcto."""
        def check_range(val, target):
            assert target * 0.85 <= val <= target * 1.15

        check_range(pelias_client._calculate_backoff_delay(0), 0.01)
        check_range(pelias_client._calculate_backoff_delay(1), 0.02)
        check_range(pelias_client._calculate_backoff_delay(2), 0.04)
        check_range(pelias_client._calculate_backoff_delay(3), 0.08)
        assert pelias_client._calculate_backoff_delay(4) <= 0.1

    @pytest.mark.asyncio
    async def test_retry_disabled_on_5xx(self, pelias_mock):
        """Verifica que retry_on_5xx=False desactiva reintentos en 5xx."""
        async with PeliasClient(
            url="https://test.example.com",
            max_retries=3,
            retry_base_delay=0.01,
            retry_on_5xx=False,
        ) as client:
            pelias_mock.add_response(503)
            with pytest.raises(ServiceError):
                await client.geocode("Barcelona")
            assert pelias_mock.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
