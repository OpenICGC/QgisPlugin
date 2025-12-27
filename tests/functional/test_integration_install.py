#!/usr/bin/env python
"""
Test de integración que simula instalación limpia.
Verifica que todos los imports y funcionalidad básica funcionan.
"""

import sys
from pathlib import Path

import pytest

# Añadir el directorio raíz al path para desarrollo
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPackageImports:
    """Tests de imports del paquete."""

    def test_main_imports(self):
        """Verifica que los imports principales funcionan."""
        from geofinder import GeoFinder, GeoResponse, GeoResult, PeliasClient

        assert GeoFinder is not None
        assert PeliasClient is not None
        assert GeoResult is not None
        assert GeoResponse is not None

    def test_exception_imports(self):
        """Verifica que todas las excepciones son importables."""
        from geofinder import (
            ConfigurationError,
            CoordinateError,
            GeoFinderError,
            ParsingError,
            ServiceConnectionError,
            ServiceError,
            ServiceHTTPError,
            ServiceTimeoutError,
        )

        assert GeoFinderError is not None
        assert ConfigurationError is not None
        assert ParsingError is not None
        assert CoordinateError is not None
        assert ServiceError is not None
        assert ServiceConnectionError is not None
        assert ServiceTimeoutError is not None
        assert ServiceHTTPError is not None

    def test_legacy_exception_imports(self):
        """Verifica que los aliases legacy funcionan."""
        from geofinder import (
            PeliasConnectionError,
            PeliasError,
            PeliasTimeoutError,
        )

        assert PeliasError is not None
        assert PeliasTimeoutError is not None
        assert PeliasConnectionError is not None

    def test_all_exports(self):
        """Verifica que __all__ contiene todos los exports esperados."""
        import geofinder

        assert hasattr(geofinder, '__all__')

        expected_exports = [
            'GeoFinder',
            'PeliasClient',
            'GeoResult',
            'GeoResponse',
            'GeoFinderError',
            'ConfigurationError',
            'ParsingError',
            'CoordinateError',
            'ServiceError',
            'ServiceConnectionError',
            'ServiceTimeoutError',
            'ServiceHTTPError',
            'PeliasError',
            'PeliasTimeoutError',
            'PeliasConnectionError',
        ]

        for export in expected_exports:
            assert export in geofinder.__all__, f"{export} not in __all__"


class TestPackageMetadata:
    """Tests de metadatos del paquete."""

    def test_version_available(self):
        """Verifica que __version__ está disponible."""
        import geofinder

        assert hasattr(geofinder, '__version__')
        assert isinstance(geofinder.__version__, str)
        assert geofinder.__version__ == "2.3.0"

    def test_author_available(self):
        """Verifica que __author__ está disponible."""
        import geofinder

        assert hasattr(geofinder, '__author__')
        assert isinstance(geofinder.__author__, str)


class TestBasicFunctionality:
    """Tests de funcionalidad básica sin red."""

    def test_geofinder_instantiation(self):
        """Verifica que GeoFinder se puede instanciar."""
        from geofinder import GeoFinder

        gf = GeoFinder()
        assert gf is not None

    def test_geofinder_has_methods(self):
        """Verifica que GeoFinder tiene los métodos esperados."""
        from geofinder import GeoFinder

        gf = GeoFinder()

        # Métodos async
        assert hasattr(gf, 'find')
        assert hasattr(gf, 'find_response')
        assert hasattr(gf, 'find_reverse')
        assert hasattr(gf, 'autocomplete')
        assert hasattr(gf, 'find_batch')
        assert hasattr(gf, 'find_reverse_batch')

        # Métodos sync
        assert hasattr(gf, 'find_sync')
        assert hasattr(gf, 'find_reverse_sync')
        assert hasattr(gf, 'autocomplete_sync')
        assert hasattr(gf, 'find_batch_sync')
        assert hasattr(gf, 'find_reverse_batch_sync')

        # Métodos de gestión
        assert hasattr(gf, 'close')
        assert hasattr(gf, 'clear_cache')

    def test_pelias_client_instantiation(self):
        """Verifica que PeliasClient se puede instanciar."""
        from geofinder.pelias import PeliasClient

        client = PeliasClient("https://test.example.com")
        assert client is not None
        # httpx normaliza URLs añadiendo trailing slash
        assert client.url.rstrip('/') == "https://test.example.com"

    def test_models_instantiation(self):
        """Verifica que los modelos Pydantic funcionan."""
        from geofinder.models import GeoResponse, GeoResult

        # GeoResult con datos mínimos
        result = GeoResult(
            nom="Test",
            nomTipus="Municipi",
            x=2.0,
            y=41.0,
            epsg=4326
        )
        assert result.nom == "Test"
        assert result.x == 2.0

        # GeoResponse
        response = GeoResponse(
            results=[result],
            count=1,
            query="test"
        )
        assert response.count == 1
        assert len(response.results) == 1


class TestOptionalDependencies:
    """Tests de dependencias opcionales."""

    def test_works_without_pyproj(self):
        """Verifica que el core funciona sin pyproj."""
        # El core debe funcionar sin pyproj
        from geofinder import GeoFinder

        gf = GeoFinder()
        assert gf is not None

        # Transformations puede no estar disponible
        try:
            from geofinder.transformations import transform_point
            # Si está disponible, debe funcionar
            assert transform_point is not None
        except ImportError:
            # Si no está, es aceptable
            pass

    def test_works_without_fastmcp(self):
        """Verifica que el core funciona sin fastmcp."""
        # El core debe funcionar sin fastmcp
        from geofinder import GeoFinder

        gf = GeoFinder()
        assert gf is not None

        # MCP server puede no estar disponible
        try:
            from geofinder.mcp_server import app
            assert app is not None
        except ImportError:
            # Si no está, es aceptable para el core
            pass


class TestExceptionHierarchy:
    """Tests de la jerarquía de excepciones."""

    def test_exception_inheritance(self):
        """Verifica que las excepciones heredan correctamente."""
        from geofinder import (
            ConfigurationError,
            CoordinateError,
            GeoFinderError,
            ParsingError,
            ServiceConnectionError,
            ServiceError,
        )

        # Todas deben heredar de GeoFinderError
        assert issubclass(ConfigurationError, GeoFinderError)
        assert issubclass(ParsingError, GeoFinderError)
        assert issubclass(CoordinateError, GeoFinderError)
        assert issubclass(ServiceError, GeoFinderError)
        assert issubclass(ServiceConnectionError, ServiceError)

    def test_legacy_aliases_work(self):
        """Verifica que los aliases legacy apuntan a las clases correctas."""
        from geofinder import (
            PeliasConnectionError,
            PeliasError,
            PeliasTimeoutError,
            ServiceConnectionError,
            ServiceError,
            ServiceTimeoutError,
        )

        # Los aliases deben ser las mismas clases
        assert PeliasError is ServiceError
        assert PeliasTimeoutError is ServiceTimeoutError
        assert PeliasConnectionError is ServiceConnectionError


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
