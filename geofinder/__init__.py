"""
GeoFinder - Geocodificador para Cataluña
=========================================

Paquete Python standalone para geocodificación usando el servicio del ICGC
(Institut Cartogràfic i Geològic de Catalunya).

API Dual (Async/Sync):
    # API Async (para batch processing con asyncio.gather)
    import asyncio
    from geofinder import GeoFinder

    async def main():
        gf = GeoFinder()
        results = await gf.find("Barcelona")
        await gf.close()

    asyncio.run(main())

    # API Sync (para scripts simples)
    from geofinder import GeoFinder

    gf = GeoFinder()
    results = gf.find_sync("Barcelona")

Tipos de búsqueda soportados:
    - Topónimos: "Montserrat", "Barcelona"
    - Coordenadas: "430000 4580000 EPSG:25831"
    - Direcciones: "Barcelona, Diagonal 100"
    - Carreteras: "C-32 km 10"

Modelos de Datos (Pydantic):
    Los resultados son objetos GeoResult validados, permitiendo acceso
    tanto por atributo (r.nom) como por clave (r['nom']).
"""

from .geofinder import GeoFinder
from .pelias import PeliasClient, PeliasConnectionError, PeliasError, PeliasTimeoutError
from .models import GeoResult, GeoResponse
from .exceptions import (
    GeoFinderError,
    ConfigurationError,
    ParsingError,
    CoordinateError,
    ServiceError,
    ServiceConnectionError,
    ServiceTimeoutError,
    ServiceHTTPError,
)

__version__ = "2.2.2"
__author__ = "ICGC / Adapted for standalone use by Goalnefesh"
__all__ = [
    "GeoFinder",
    "PeliasClient",
    "GeoResult",
    "GeoResponse",
    # New exception hierarchy
    "GeoFinderError",
    "ConfigurationError",
    "ParsingError",
    "CoordinateError",
    "ServiceError",
    "ServiceConnectionError",
    "ServiceTimeoutError",
    "ServiceHTTPError",
    # Legacy aliases (deprecated, use new names above)
    "PeliasError",
    "PeliasTimeoutError",
    "PeliasConnectionError",
]
