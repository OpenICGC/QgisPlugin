"""
GeoFinder MCP Server
====================

Servidor MCP (Model Context Protocol) para GeoFinder.
Expone las capacidades de geocodificación de GeoFinder a través del protocolo MCP
para integración con asistentes AI como Claude Desktop.

Uso:
    # Ejecutar con STDIO (por defecto)
    python -m geofinder.mcp_server

    # O usando el comando instalado
    geofinder-mcp

    # Ejecutar con HTTP
    python -m geofinder.mcp_server --transport http --port 8000

    # Usando el CLI de FastMCP
    fastmcp run geofinder/mcp_server.py:mcp
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from .geofinder import GeoFinder

# ============================================================================
# Configuración de Entorno y Logging
# ============================================================================

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logging
log_level = os.getenv("FASTMCP_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("geofinder.mcp")

# Instancia compartida de GeoFinder
_geofinder_instance: GeoFinder | None = None


def get_geofinder() -> GeoFinder:
    """
    Obtiene la instancia compartida de GeoFinder (lazy loading).

    Returns:
        GeoFinder: Instancia del geocodificador configurada
    """
    global _geofinder_instance

    if _geofinder_instance is None:
        icgc_url = os.getenv("ICGC_URL", "")
        timeout = int(os.getenv("GEOFINDER_TIMEOUT", "5"))

        logger.info(
            "Inicializando GeoFinder (ICGC URL: %s, timeout: %s)",
            icgc_url or "default",
            timeout
        )

        _geofinder_instance = GeoFinder(
            logger=logger,
            icgc_url=icgc_url if icgc_url else None,
            timeout=timeout,
        )

    return _geofinder_instance


# ============================================================================
# Configuración del Servidor MCP
# ============================================================================

mcp = FastMCP(
    name="GeoFinder ICGC",
    instructions="""
    Servidor de geocodificación para Cataluña usando el servicio ICGC
    (Institut Cartogràfic i Geològic de Catalunya).

    Proporciona herramientas para:
    - Buscar lugares por nombre (topónimos, municipios, comarcas, montañas)
    - Buscar direcciones (calle + número + municipio)
    - Buscar por coordenadas (con soporte de múltiples sistemas EPSG)
    - Geocodificación inversa (coordenadas → lugar)
    - Autocompletado de búsquedas

    Para usar este servidor:
    1. Usa las herramientas disponibles según tu necesidad
    2. Todas las coordenadas de salida están en WGS84 (EPSG:4326) por defecto
    3. Puedes especificar el EPSG de entrada cuando sea necesario

    Ejemplos de uso:
    - "Busca Barcelona"
    - "¿Qué hay en las coordenadas 430000 4580000 EPSG:25831?"
    - "Encuentra la dirección Diagonal 100, Barcelona"
    """.strip(),
    version="1.0.0",
)


# ============================================================================
# Herramientas MCP
# ============================================================================

@mcp.tool()
def find_place(
    query: str,
    default_epsg: int = 25831
) -> list[dict]:
    """
    Busca lugares, direcciones o coordenadas en Cataluña.

    Esta herramienta detecta automáticamente el tipo de búsqueda:
    - Topónimos: "Barcelona", "Montserrat", "Pirineus"
    - Coordenadas: "430000 4580000 EPSG:25831" o "2.1734 41.3851"
    - Direcciones: "Barcelona, Diagonal 100" o "Carrer Aragó 50, Barcelona"
    - Carreteras: "C-32 km 10" o "AP7 km 150"
    - Rectángulos: "X1 Y1 X2 Y2" (área rectangular)

    Args:
        query: Texto de búsqueda (lugar, dirección, coordenadas, etc.)
        default_epsg: Sistema de referencia por defecto para coordenadas
                      sin EPSG especificado (default: 25831 - ETRS89 UTM31N)

    Returns:
        Lista de lugares encontrados. Cada resultado contiene:
        - nom: Nombre del lugar
        - nomTipus: Tipo (Municipi, Carrer, Coordenada, etc.)
        - nomMunicipi: Municipio
        - nomComarca: Comarca
        - x: Longitud (WGS84)
        - y: Latitud (WGS84)
        - epsg: Sistema de referencia (siempre 4326 - WGS84)

    Examples:
        >>> find_place("Barcelona")
        >>> find_place("430000 4580000 EPSG:25831")
        >>> find_place("Barcelona, Diagonal 100")
        >>> find_place("C-32 km 10")
    """
    gf = get_geofinder()
    try:
        results = gf.find(query, default_epsg=default_epsg)
        logger.info(f"find_place: {query} -> {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Error in find_place: {e}", exc_info=True)
        raise


@mcp.tool()
def autocomplete(
    partial_text: str,
    max_suggestions: int = 10
) -> list[dict]:
    """
    Obtiene sugerencias de autocompletado para búsquedas.

    Útil para implementar búsqueda tipo "as you type" o para mostrar
    sugerencias al usuario mientras escribe.

    Args:
        partial_text: Texto parcial a completar (mínimo 2-3 caracteres)
        max_suggestions: Número máximo de sugerencias (default: 10)

    Returns:
        Lista de sugerencias. Cada sugerencia contiene:
        - nom: Nombre sugerido
        - nomTipus: Tipo de lugar
        - x, y: Coordenadas WGS84
        - Otros campos de contexto (municipio, comarca)

    Examples:
        >>> autocomplete("Barcel")
        >>> autocomplete("Montserr", max_suggestions=5)
        >>> autocomplete("C-32")
    """
    gf = get_geofinder()
    try:
        results = gf.autocomplete(partial_text, size=max_suggestions)
        logger.info(f"autocomplete: '{partial_text}' -> {len(results)} suggestions")
        return results
    except Exception as e:
        logger.error(f"Error in autocomplete: {e}", exc_info=True)
        raise


@mcp.tool()
def find_reverse(
    longitude: float,
    latitude: float,
    epsg: int = 25831,
    layers: str = "address,tops,pk",
    max_results: int = 5
) -> list[dict]:
    """
    Geocodificación inversa: encuentra lugares en unas coordenadas dadas.

    Busca direcciones, topónimos y puntos kilométricos cercanos a las
    coordenadas especificadas.

    Args:
        longitude: Coordenada X / Longitud
        latitude: Coordenada Y / Latitud
        epsg: Sistema de referencia de las coordenadas
              - 4326: WGS84 (GPS estándar)
              - 25831: ETRS89 UTM 31N (Cataluña)
              - 3857: Web Mercator
        layers: Capas a buscar (separadas por comas):
                - address: Direcciones
                - tops: Topónimos (municipios, comarcas, montañas)
                - pk: Puntos kilométricos de carreteras
        max_results: Número máximo de resultados (default: 5)

    Returns:
        Lista de lugares encontrados en las coordenadas. Cada resultado
        contiene la misma estructura que find_place.

    Examples:
        >>> find_reverse(2.1734, 41.3851, epsg=4326)  # WGS84
        >>> find_reverse(430000, 4580000, epsg=25831)  # UTM31N
        >>> find_reverse(430000, 4580000, layers="address", max_results=3)
    """
    gf = get_geofinder()
    try:
        results = gf.find_reverse(
            longitude, latitude,
            epsg=epsg,
            layers=layers,
            size=max_results
        )
        logger.info(f"find_reverse: ({longitude}, {latitude}) EPSG:{epsg} -> {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Error in find_reverse: {e}", exc_info=True)
        raise


@mcp.tool()
def find_by_coordinates(
    x: float,
    y: float,
    epsg: int = 25831,
    search_radius_km: float = 0.05,
    layers: str = "address,tops,pk",
    max_results: int = 5
) -> list[dict]:
    """
    Busca lugares cerca de unas coordenadas específicas.

    Similar a find_reverse pero con más control sobre el radio de búsqueda
    y opciones de filtrado. Útil cuando trabajas directamente con coordenadas
    y necesitas ajustar el área de búsqueda.

    Args:
        x: Coordenada X / Longitud / Este
        y: Coordenada Y / Latitud / Norte
        epsg: Sistema de referencia de las coordenadas
              - 4326: WGS84 (GPS estándar) - grados decimales
              - 25831: ETRS89 UTM 31N (Cataluña) - metros
              - 3857: Web Mercator - metros
              - 23031: ED50 UTM 31N (antiguo) - metros
        search_radius_km: Radio de búsqueda en kilómetros (default: 0.05 = 50 metros)
                          Ajusta según necesidad:
                          - 0.01 = 10m (muy preciso)
                          - 0.05 = 50m (default)
                          - 0.1 = 100m
                          - 0.5 = 500m (área amplia)
        layers: Capas a buscar (separadas por comas):
                - address: Direcciones postales
                - tops: Topónimos (municipios, comarcas, montañas, ríos)
                - pk: Puntos kilométricos de carreteras
        max_results: Número máximo de resultados por capa (default: 5)

    Returns:
        Lista de lugares encontrados ordenados por proximidad.
        Cada resultado incluye toda la información del lugar.

    Examples:
        >>> # Búsqueda precisa en Barcelona con coordenadas UTM
        >>> find_by_coordinates(430000, 4580000, epsg=25831)

        >>> # Búsqueda amplia con coordenadas GPS
        >>> find_by_coordinates(2.1734, 41.3851, epsg=4326, search_radius_km=0.5)

        >>> # Solo direcciones en un radio de 100m
        >>> find_by_coordinates(
        ...     430000, 4580000,
        ...     epsg=25831,
        ...     search_radius_km=0.1,
        ...     layers="address",
        ...     max_results=10
        ... )

        >>> # Búsqueda de topónimos sin límite de radio
        >>> find_by_coordinates(
        ...     420000, 4600000,
        ...     epsg=25831,
        ...     search_radius_km=None,  # Sin límite
        ...     layers="tops"
        ... )

    Notes:
        - El radio de búsqueda se aplica solo a direcciones y puntos kilométricos
        - Los topónimos se buscan sin límite de radio por defecto
        - Las coordenadas se transforman automáticamente a WGS84 para la consulta
    """
    gf = get_geofinder()
    try:
        # Usar el método interno _find_point_coordinate_icgc con control de radio
        results = gf._find_point_coordinate_icgc(
            x, y, epsg,
            layers=layers,
            search_radius_km=search_radius_km if search_radius_km else None,
            size=max_results
        )

        logger.info(
            f"find_by_coordinates: ({x}, {y}) EPSG:{epsg} "
            f"radius:{search_radius_km}km -> {len(results)} results"
        )
        return results
    except Exception as e:
        logger.error(f"Error in find_by_coordinates: {e}", exc_info=True)
        raise


@mcp.tool()
def find_address(
    street: str,
    number: str,
    municipality: str = "",
    street_type: str = "Carrer"
) -> list[dict]:
    """
    Busca una dirección específica de forma estructurada.

    Usa el método interno de _find_address para búsqueda más precisa
    en la capa de direcciones del ICGC.

    Args:
        street: Nombre de la calle (ej: "Diagonal", "Aragó", "Rambla Catalunya")
        number: Número de portal (ej: "100", "50-52", "25 bis")
        municipality: Municipio (ej: "Barcelona", "Girona", "Lleida")
                      Muy recomendado para mejorar precisión
        street_type: Tipo de vía (ej: "Carrer", "Avinguda", "Plaça", "Passeig")
                     Default: "Carrer"

    Returns:
        Lista de direcciones encontradas. Cada resultado contiene:
        - nom: Dirección completa
        - nomTipus: "Adreça"
        - nomMunicipi: Municipio
        - nomComarca: Comarca
        - x, y: Coordenadas WGS84
        - epsg: 4326

    Examples:
        >>> find_address("Diagonal", "100", "Barcelona")
        >>> find_address("Aragó", "50", "Barcelona", "Carrer")
        >>> find_address("Rambla Catalunya", "25", "Barcelona", "Rambla")
        >>> find_address("Diagonal", "686", "Barcelona", "Avinguda")
    """
    gf = get_geofinder()
    try:
        # Usar el método interno _find_address para búsqueda precisa
        results = gf._find_address(municipality, street_type, street, number)

        logger.info(f"find_address: {street_type} {street} {number}, {municipality} -> {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Error in find_address: {e}", exc_info=True)
        raise


@mcp.tool()
def find_road_km(
    road: str,
    kilometer: float
) -> list[dict]:
    """
    Busca un punto kilométrico específico en una carretera.

    Útil para navegación, rutas y localización de puntos específicos
    en carreteras de Cataluña.

    Args:
        road: Código de la carretera (ej: "C-32", "AP-7", "N-II", "A-2")
                Formatos aceptados: "C-32", "C32", "AP7", "AP-7"
        kilometer: Kilómetro en la carretera (puede ser decimal)
                   Ej: 10, 15.5, 125.3

    Returns:
        Lista de puntos kilométricos encontrados. Cada resultado contiene:
        - nom: Descripción del punto (ej: "C-32 km 10")
        - nomTipus: "Punt quilomètric"
        - x, y: Coordenadas WGS84 del punto
        - epsg: 4326

    Examples:
        >>> find_road_km("C-32", 10)
        >>> find_road_km("AP-7", 150.5)
        >>> find_road_km("N-II", 25)
        >>> find_road_km("A-2", 500)

    Notes:
        - Las carreteras autonómicas catalanas usan formato C-XX
        - Las autopistas de peaje usan AP-X
        - Las nacionales usan N-XXX o A-X
    """
    gf = get_geofinder()
    try:
        # Usar el método interno _find_road
        results = gf._find_road(road, str(int(kilometer) if kilometer.is_integer() else kilometer))

        logger.info(f"find_road_km: {road} km {kilometer} -> {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Error in find_road_km: {e}", exc_info=True)
        raise


@mcp.tool()
def transform_coordinates(
    x: float,
    y: float,
    from_epsg: int,
    to_epsg: int = 4326
) -> dict:
    """
    Transforma coordenadas entre diferentes sistemas de referencia (EPSG).

    Requiere pyproj o GDAL instalado. Útil para convertir entre
    diferentes sistemas de coordenadas.

    Args:
        x: Coordenada X / Longitud en el sistema origen
        y: Coordenada Y / Latitud en el sistema origen
        from_epsg: Sistema de referencia origen (código EPSG)
        to_epsg: Sistema de referencia destino (default: 4326 - WGS84)

    Common EPSG codes:
        - 4326: WGS84 (GPS estándar) - coordenadas geográficas
        - 25831: ETRS89 UTM 31N (sistema oficial Cataluña)
        - 3857: Web Mercator (mapas web)
        - 23031: ED50 UTM 31N (sistema antiguo)

    Returns:
        Diccionario con coordenadas transformadas:
        - x: Coordenada X transformada
        - y: Coordenada Y transformada
        - from_epsg: Sistema origen
        - to_epsg: Sistema destino
        - success: True si la transformación fue exitosa

    Examples:
        >>> transform_coordinates(430000, 4580000, 25831, 4326)
        >>> transform_coordinates(2.1734, 41.3851, 4326, 25831)
        >>> transform_coordinates(430000, 4580000, 25831, 3857)

    Raises:
        ImportError: Si no está instalado pyproj o GDAL
    """
    try:
        from .transformations import transform_point

        dest_x, dest_y = transform_point(x, y, from_epsg, to_epsg)

        if dest_x is None or dest_y is None:
            logger.error(f"Transformation failed: ({x}, {y}) EPSG:{from_epsg} -> EPSG:{to_epsg}")
            return {
                "success": False,
                "error": "Coordinate transformation failed",
                "from_epsg": from_epsg,
                "to_epsg": to_epsg,
                "original_x": x,
                "original_y": y,
            }

        logger.info(f"transform_coordinates: ({x}, {y}) EPSG:{from_epsg} -> ({dest_x}, {dest_y}) EPSG:{to_epsg}")

        return {
            "success": True,
            "x": dest_x,
            "y": dest_y,
            "from_epsg": from_epsg,
            "to_epsg": to_epsg,
            "original_x": x,
            "original_y": y,
        }
    except ImportError as e:
        logger.error(f"Transformation backend not available: {e}")
        raise ImportError(
            "Se requiere pyproj o GDAL para transformaciones de coordenadas. "
            "Instala uno de: pip install pyproj  o  pip install GDAL"
        ) from e
    except Exception as e:
        logger.error(f"Error in transform_coordinates: {e}", exc_info=True)
        raise


@mcp.tool()
def search_nearby(
    place_name: str,
    radius_km: float = 1.0,
    layers: str = "address,tops,pk",
    max_results: int = 10
) -> list[dict]:
    """
    Busca lugares cerca de una ubicación nombrada.

    Primero encuentra el lugar especificado, luego busca otros lugares
    en un radio determinado. Útil para "buscar gasolineras cerca de Barcelona",
    "hoteles cerca del Montserrat", etc.

    Args:
        place_name: Nombre del lugar de referencia (ej: "Barcelona", "Montserrat")
        radius_km: Radio de búsqueda en kilómetros (default: 1.0)
                   - 0.5 = 500 metros
                   - 1.0 = 1 kilómetro
                   - 5.0 = 5 kilómetros
                   - 10.0 = 10 kilómetros
        layers: Capas a buscar (separadas por comas):
                - address: Direcciones
                - tops: Topónimos (municipios, comarcas, montañas)
                - pk: Puntos kilométricos de carreteras
        max_results: Número máximo de resultados (default: 10)

    Returns:
        Lista de lugares encontrados cerca de la ubicación.
        Incluye el lugar de referencia como primer resultado.

    Examples:
        >>> # Buscar cerca de Barcelona
        >>> search_nearby("Barcelona", radius_km=2.0)

        >>> # Buscar topónimos cerca del Montserrat
        >>> search_nearby("Montserrat", radius_km=5.0, layers="tops")

        >>> # Buscar direcciones cerca de Sagrada Família
        >>> search_nearby("Sagrada Família, Barcelona", radius_km=0.5, layers="address")

        >>> # Buscar todo cerca de un punto
        >>> search_nearby("Plaça Catalunya, Barcelona", radius_km=0.3, max_results=20)

    Notes:
        - Si el lugar no se encuentra, retorna lista vacía
        - Los resultados incluyen el lugar de referencia
        - El radio se aplica desde el centro del lugar encontrado
    """
    gf = get_geofinder()
    try:
        # Primero encontrar el lugar de referencia
        reference_results = gf.find(place_name)

        if not reference_results:
            logger.warning(f"search_nearby: No se encontró el lugar '{place_name}'")
            return []

        # Obtener coordenadas del primer resultado
        ref_place = reference_results[0]
        ref_x = ref_place['x']
        ref_y = ref_place['y']
        ref_epsg = ref_place.get('epsg', 4326)

        # Buscar cerca de esas coordenadas
        nearby_results = gf._find_point_coordinate_icgc(
            ref_x, ref_y, ref_epsg,
            layers=layers,
            search_radius_km=radius_km,
            size=max_results
        )

        # Incluir el lugar de referencia al inicio
        all_results = [ref_place] + nearby_results

        # Eliminar duplicados basados en nombre y tipo
        seen = set()
        unique_results = []
        for r in all_results:
            key = (r.get('nom', ''), r.get('nomTipus', ''))
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        logger.info(
            f"search_nearby: '{place_name}' radius:{radius_km}km -> "
            f"{len(unique_results)} results"
        )
        return unique_results

    except Exception as e:
        logger.error(f"Error in search_nearby: {e}", exc_info=True)
        raise


@mcp.tool()
def parse_search_query(query: str) -> dict:
    """
    Analiza una consulta de búsqueda y detecta su tipo.

    Útil para que el asistente AI entienda qué tipo de búsqueda
    realizar antes de ejecutarla, o para ayudar al usuario a
    construir búsquedas válidas.

    Args:
        query: Texto de búsqueda a analizar

    Returns:
        Diccionario con información del análisis:
        - query_type: Tipo detectado ("coordinate", "rectangle", "road", "address", "placename")
        - confidence: Nivel de confianza ("high", "medium", "low")
        - details: Detalles específicos según el tipo
        - suggestion: Sugerencia de cómo usar la herramienta apropiada

    Examples:
        >>> # Detectar coordenadas
        >>> parse_search_query("430000 4580000 EPSG:25831")
        {
            "query_type": "coordinate",
            "confidence": "high",
            "details": {"x": 430000, "y": 4580000, "epsg": 25831},
            "suggestion": "Use find_place() o find_by_coordinates()"
        }

        >>> # Detectar dirección
        >>> parse_search_query("Barcelona, Diagonal 100")
        {
            "query_type": "address",
            "confidence": "high",
            "details": {"municipality": "Barcelona", "street": "Diagonal", "number": "100"},
            "suggestion": "Use find_address() para mayor precisión"
        }

        >>> # Detectar carretera
        >>> parse_search_query("C-32 km 10")
        {
            "query_type": "road",
            "confidence": "high",
            "details": {"road": "C-32", "km": "10"},
            "suggestion": "Use find_road_km() para búsqueda exacta"
        }

        >>> # Detectar topónimo
        >>> parse_search_query("Montserrat")
        {
            "query_type": "placename",
            "confidence": "medium",
            "details": {},
            "suggestion": "Use find_place() o autocomplete() si es parcial"
        }
    """
    gf = get_geofinder()

    try:
        # Probar rectángulo
        west, north, east, south, epsg = gf._parse_rectangle(query)
        if west is not None:
            return {
                "query_type": "rectangle",
                "confidence": "high",
                "details": {
                    "west": west,
                    "north": north,
                    "east": east,
                    "south": south,
                    "epsg": epsg or 25831
                },
                "suggestion": "Use find_place() - se buscará en el área rectangular",
                "example": f'find_place("{query}")'
            }

        # Probar coordenadas
        x, y, epsg = gf._parse_point(query)
        if x is not None:
            return {
                "query_type": "coordinate",
                "confidence": "high",
                "details": {
                    "x": x,
                    "y": y,
                    "epsg": epsg or 25831
                },
                "suggestion": "Use find_place() o find_by_coordinates() para control avanzado",
                "example": f'find_by_coordinates({x}, {y}, epsg={epsg or 25831})'
            }

        # Probar carretera
        road, km = gf._parse_road(query)
        if road is not None:
            return {
                "query_type": "road",
                "confidence": "high",
                "details": {
                    "road": road,
                    "kilometer": km
                },
                "suggestion": "Use find_road_km() para búsqueda exacta de punto kilométrico",
                "example": f'find_road_km("{road}", {km})'
            }

        # Probar dirección
        municipality, street_type, street, number = gf._parse_address(query)
        if municipality is not None or (street is not None and number is not None):
            confidence = "high" if municipality and street and number else "medium"
            return {
                "query_type": "address",
                "confidence": confidence,
                "details": {
                    "municipality": municipality or "no detectado",
                    "street_type": street_type or "Carrer",
                    "street": street or "no detectado",
                    "number": number or "no detectado"
                },
                "suggestion": "Use find_address() para mayor precisión en direcciones",
                "example": f'find_address("{street or "CALLE"}", "{number or "NUM"}", "{municipality or "MUNICIPIO"}")'
            }

        # Por defecto: topónimo
        return {
            "query_type": "placename",
            "confidence": "low",
            "details": {"query": query},
            "suggestion": "Use find_place() para búsqueda general o autocomplete() si es texto parcial",
            "example": f'find_place("{query}")',
            "note": "No se detectó un formato específico, se tratará como nombre de lugar"
        }

    except Exception as e:
        logger.error(f"Error in parse_search_query: {e}", exc_info=True)
        return {
            "query_type": "error",
            "confidence": "low",
            "details": {"error": str(e)},
            "suggestion": "Verifique el formato de la consulta"
        }


# ============================================================================
# Función Principal (CLI)
# ============================================================================

def main():
    """
    Función principal para ejecutar el servidor MCP.

    Soporta argumentos de línea de comandos para configurar el transporte.
    """
    parser = argparse.ArgumentParser(
        description="Servidor MCP de GeoFinder para geocodificación en Cataluña"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Tipo de transporte (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host para transporte HTTP (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto para transporte HTTP (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nivel de logging (sobrescribe FASTMCP_LOG_LEVEL)",
    )

    args = parser.parse_args()

    # Configurar nivel de logging si se especifica
    if args.log_level:
        logging.getLogger().setLevel(getattr(logging, args.log_level))
        logger.setLevel(getattr(logging, args.log_level))

    # Preparar kwargs para el servidor
    run_kwargs = {
        "transport": args.transport,
    }

    if args.transport == "http":
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port
        logger.info("🌐 Iniciando servidor HTTP en %s:%s", args.host, args.port)
    else:
        logger.info("📡 Iniciando servidor con transporte STDIO")

    if args.log_level:
        run_kwargs["log_level"] = args.log_level

    # Ejecutar servidor
    try:
        mcp.run(**run_kwargs)
    except KeyboardInterrupt:
        logger.info("⚠️ Servidor detenido por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error("❌ Error ejecutando servidor: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
