"""
GeoFinder - Geocodificador para Cataluña
=========================================

Paquete Python standalone para geocodificación usando el servicio del ICGC
(Institut Cartogràfic i Geològic de Catalunya).

Uso básico:
    from geofinder import GeoFinder

    gf = GeoFinder()
    results = gf.find("Barcelona")
    for r in results:
        print(f"{r['nom']} - ({r['x']}, {r['y']})")

Tipos de búsqueda soportados:
    - Topónimos: "Montserrat", "Barcelona"
    - Coordenadas: "430000 4580000 EPSG:25831"
    - Direcciones: "Barcelona, Diagonal 100"
    - Carreteras: "C-32 km 10"
"""

from .geofinder import GeoFinder
from .pelias import PeliasClient, PeliasConnectionError, PeliasError, PeliasTimeoutError

__version__ = "1.4.0"
__author__ = "ICGC / Adapted for standalone use by Goalnefesh"
__all__ = [
    "GeoFinder",
    "PeliasClient",
    "PeliasError",
    "PeliasTimeoutError",
    "PeliasConnectionError",
]
