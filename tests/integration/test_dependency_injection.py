#!/usr/bin/env python
"""
Tests para Inyección de Dependencias (DI) en GeoFinder y PeliasClient.

Verifica que se puede pasar un httpx.AsyncClient externo y que el ownership
tracking funciona correctamente.
"""

import pytest
import sys
from pathlib import Path
import httpx

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geofinder.pelias import PeliasClient
from geofinder import GeoFinder


class TestPeliasClientDI:
    """Tests para dependency injection en PeliasClient."""

    @pytest.mark.asyncio
    async def test_pelias_with_external_client(self):
        """Verifica que PeliasClient usa cliente externo."""
        external_client = httpx.AsyncClient()
        
        pelias = PeliasClient(
            "https://test.example.com",
            http_client=external_client
        )
        
        # Debe usar el cliente externo
        assert pelias.client is external_client
        assert not pelias._owns_client
        
        # Cerrar PeliasClient NO debe cerrar el cliente externo
        await pelias.close()
        assert not external_client.is_closed
        
        # Limpiar
        await external_client.aclose()

    @pytest.mark.asyncio
    async def test_pelias_creates_own_client(self):
        """Verifica que PeliasClient crea su propio cliente por defecto."""
        pelias = PeliasClient("https://test.example.com")
        
        # Debe crear su propio cliente
        assert pelias.client is not None
        assert pelias._owns_client
        
        # Guardar referencia al cliente
        client = pelias.client
        
        # Cerrar PeliasClient DEBE cerrar el cliente
        await pelias.close()
        assert client.is_closed

    @pytest.mark.asyncio
    async def test_pelias_warns_on_verify_ssl_conflict(self, caplog):
        """Verifica que PeliasClient advierte si hay conflicto con verify_ssl."""
        external_client = httpx.AsyncClient(verify=True)
        
        pelias = PeliasClient(
            "https://test.example.com",
            verify_ssl=False,  # Conflicto: cliente externo tiene verify=True
            http_client=external_client
        )
        
        # Debe haber una advertencia en los logs
        assert any("verify_ssl=False ignorado" in record.message for record in caplog.records)
        
        # Limpiar
        await pelias.close()
        await external_client.aclose()

    @pytest.mark.asyncio
    async def test_pelias_close_idempotent_with_external_client(self):
        """Verifica que close() es idempotente con cliente externo."""
        external_client = httpx.AsyncClient()
        pelias = PeliasClient("https://test.example.com", http_client=external_client)
        
        # Llamar close() múltiples veces no debe causar error
        await pelias.close()
        await pelias.close()
        await pelias.close()
        
        # El cliente externo no debe estar cerrado
        assert not external_client.is_closed
        
        # Limpiar
        await external_client.aclose()


class TestGeoFinderDI:
    """Tests para dependency injection en GeoFinder."""

    @pytest.mark.asyncio
    async def test_geofinder_with_external_client(self):
        """Verifica que GeoFinder usa cliente externo."""
        external_client = httpx.AsyncClient()
        
        gf = GeoFinder(
            icgc_url="https://eines.icgc.cat/geocodificador",
            http_client=external_client
        )
        
        # Obtener el cliente Pelias (inicialización perezosa)
        pelias_client = await gf.get_icgc_client()
        
        # El PeliasClient debe usar el cliente externo
        assert pelias_client.client is external_client
        assert not pelias_client._owns_client
        
        # Cerrar GeoFinder NO debe cerrar el cliente externo
        await gf.close()
        assert not external_client.is_closed
        
        # Limpiar
        await external_client.aclose()

    @pytest.mark.asyncio
    async def test_geofinder_creates_own_client(self):
        """Verifica que GeoFinder crea su propio cliente por defecto."""
        gf = GeoFinder(icgc_url="https://eines.icgc.cat/geocodificador")
        
        # Obtener el cliente Pelias
        pelias_client = await gf.get_icgc_client()
        
        # El PeliasClient debe haber creado su propio cliente
        assert pelias_client.client is not None
        assert pelias_client._owns_client
        
        # Guardar referencia
        client = pelias_client.client
        
        # Cerrar GeoFinder DEBE cerrar el cliente
        await gf.close()
        assert client.is_closed

    @pytest.mark.asyncio
    async def test_multiple_geofinders_share_client(self):
        """Verifica que múltiples GeoFinders pueden compartir un cliente."""
        shared_client = httpx.AsyncClient()
        
        gf1 = GeoFinder(
            icgc_url="https://eines.icgc.cat/geocodificador",
            http_client=shared_client
        )
        gf2 = GeoFinder(
            icgc_url="https://eines.icgc.cat/geocodificador",
            http_client=shared_client
        )
        
        # Ambos deben usar el mismo cliente
        pelias1 = await gf1.get_icgc_client()
        pelias2 = await gf2.get_icgc_client()
        
        assert pelias1.client is shared_client
        assert pelias2.client is shared_client
        
        # Cerrar ambos GeoFinders NO debe cerrar el cliente compartido
        await gf1.close()
        await gf2.close()
        assert not shared_client.is_closed
        
        # Limpiar
        await shared_client.aclose()

    @pytest.mark.asyncio
    async def test_geofinder_context_manager_with_external_client(self):
        """Verifica que el context manager funciona con cliente externo."""
        external_client = httpx.AsyncClient()
        
        async with GeoFinder(
            icgc_url="https://eines.icgc.cat/geocodificador",
            http_client=external_client
        ) as gf:
            pelias = await gf.get_icgc_client()
            assert pelias.client is external_client
        
        # Después del context manager, el cliente externo NO debe estar cerrado
        assert not external_client.is_closed
        
        # Limpiar
        await external_client.aclose()

    @pytest.mark.asyncio
    async def test_geofinder_context_manager_with_own_client(self):
        """Verifica que el context manager cierra el cliente propio."""
        gf = GeoFinder(icgc_url="https://eines.icgc.cat/geocodificador")
        pelias = await gf.get_icgc_client()
        client = pelias.client
        
        async with gf:
            pass
        
        # Después del context manager, el cliente propio DEBE estar cerrado
        assert client.is_closed


class TestDIBackwardCompatibility:
    """Tests para verificar compatibilidad hacia atrás."""

    @pytest.mark.asyncio
    async def test_existing_code_still_works(self):
        """Verifica que código existente sin DI sigue funcionando."""
        # Código antiguo sin cambios
        gf = GeoFinder(icgc_url="https://eines.icgc.cat/geocodificador")
        pelias = await gf.get_icgc_client()
        
        assert pelias.client is not None
        assert pelias._owns_client
        
        await gf.close()

    @pytest.mark.asyncio
    async def test_pelias_standalone_still_works(self):
        """Verifica que PeliasClient standalone sigue funcionando."""
        # Código antiguo sin cambios
        async with PeliasClient("https://test.example.com") as pelias:
            assert pelias.client is not None
            assert pelias._owns_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
