"""
GeoFinder - Geocodificador para Cataluña
=========================================

Clase principal para geocodificación usando los servicios del ICGC.
"""

import asyncio
import hashlib
import json
import logging
import re
import time

import httpx

from .exceptions import CoordinateError, ParsingError, ServiceError
from .models import GeoResponse, GeoResult
from .pelias import PeliasClient
from .transformations import transform_point
from .utils.cache import AsyncLRUCache


class GeoFinder:
    """Geocodificador para Cataluña usando el servicio del ICGC.

    Soporta búsqueda de:
        - Topónimos (municipios, comarcas, montañas, etc.)
        - Direcciones (calle + número + municipio)
        - Coordenadas (X Y EPSG:código)
        - Rectángulos (X1 Y1 X2 Y2)
        - Carreteras (C-32 km 10)

    Example:
        gf = GeoFinder()

        # Buscar un topónimo
        results = await gf.find("Barcelona", 25831)

        # Buscar coordenadas
        results = await gf.find("430000 4580000 EPSG:25831", 25831)

        # Buscar dirección
        results = await gf.find("Barcelona, Diagonal 100", 25831)

    Attributes:
        timeout: Timeout en segundos para peticiones
        geoencoder_epsg: EPSG del geocodificador (4326 WGS84)
    """

    # Configuración del servicio
    timeout = 5
    geoencoder_epsg = 4326

    def __init__(
        self,
        logger=None,
        icgc_url="https://eines.icgc.cat/geocodificador",
        timeout=5,
        verify_ssl=True,
        cache_size=128,
        cache_ttl=3600,
        max_retries=3,
        retry_base_delay=0.5,
        retry_max_delay=10.0,
        retry_on_5xx=True,
        default_size=10,
        http_client: httpx.AsyncClient | None = None,
    ):
        """Inicializa el geocodificador.

        Args:
            logger: Logger opcional para debug
            icgc_url: URL del geocodificador ICGC
            timeout: Timeout en segundos
            verify_ssl: Verificar certificados SSL (default: True).
            cache_size: Tamaño máximo de la caché (0 para desactivar).
            cache_ttl: Tiempo de vida en segundos de la caché.
            max_retries: Número máximo de reintentos en errores transitorios.
            retry_base_delay: Delay inicial del backoff exponencial (segundos).
            retry_max_delay: Delay máximo entre reintentos (segundos).
            retry_on_5xx: Reintentar automáticamente en errores 5xx.
            default_size: Número de resultados por defecto.
            http_client: Cliente httpx.AsyncClient externo opcional. Si se proporciona,
                        permite compartir el pool de conexiones entre múltiples instancias.
                        GeoFinder NO cerrará este cliente; el usuario es responsable.
        """
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._icgc_url = icgc_url
        self._icgc_client = None
        self._external_http_client = http_client  # Almacenar cliente externo

        # Configuración de reintentos
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay
        self._retry_on_5xx = retry_on_5xx
        self._default_size = default_size

        # Inicializar caché
        self._cache = AsyncLRUCache(maxsize=cache_size, ttl=cache_ttl) if cache_size > 0 else None

        # Lock para inicialización segura del cliente
        self._client_lock = asyncio.Lock()

        # Configurar logger
        if logger:
            self.log = logger
        else:
            self.log = logging.getLogger("geofinder")
            self.log.addHandler(logging.NullHandler())

    async def get_icgc_client(self) -> PeliasClient:
        """Obtiene el cliente Pelias del ICGC de forma segura y perezosa."""
        if self._icgc_client is None:
            async with self._client_lock:
                # Doble chequeo dentro del lock
                if self._icgc_client is None:
                    self._icgc_client = PeliasClient(
                        self._icgc_url,
                        self.timeout,
                        default_search_call="cerca",
                        default_reverse_call="invers",
                        default_autocomplete_call="autocompletar",
                        max_retries=self._max_retries,
                        retry_base_delay=self._retry_base_delay,
                        retry_max_delay=self._retry_max_delay,
                        retry_on_5xx=self._retry_on_5xx,
                        verify_ssl=self.verify_ssl,
                        http_client=self._external_http_client,  # Pasar cliente externo
                    )
        return self._icgc_client

    async def _reset_client(self):
        """Resetea el cliente cerrando el anterior de forma segura."""
        async with self._client_lock:
            if self._icgc_client:
                await self._icgc_client.close()
                self._icgc_client = None

    async def close(self):
        """Cierra el cliente http subyacente."""
        if self._icgc_client:
            await self._icgc_client.close()

    async def __aenter__(self):
        """Soporte para async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra el cliente al salir del async context manager."""
        await self.close()

    def clear_cache(self):
        """Limpia la caché de resultados."""
        if self._cache is not None:
            self._cache.clear()

    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Genera una clave única (hash) para la caché de forma robusta."""
        # Usar JSON para serializar de forma estable y evitar inyecciones de separadores
        key_data = {
            "m": method,
            "a": args,
            "k": sorted(kwargs.items())
        }
        raw_key = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(raw_key.encode()).hexdigest()

    # =========================================================================
    # API Principal
    # =========================================================================

    async def find(self, user_text: str, default_epsg: int = 25831, size: int | None = None, use_cache: bool = True) -> list[GeoResult]:
        """Busca ubicaciones a partir de un texto.

        Detecta automáticamente el tipo de búsqueda:
            - Coordenadas: "X Y" o "X Y EPSG:código"
            - Rectángulo: "X1 Y1 X2 Y2"
            - Carretera: "C-32 km 10"
            - Dirección: "Barcelona, Diagonal 100"
            - Topónimo: cualquier otro texto

        Args:
            user_text: Texto de búsqueda
            default_epsg: EPSG por defecto para coordenadas sin especificar
            use_cache: Si es True, utiliza la caché si está disponible

        Returns:
            list[GeoResult]: Lista de resultados validados
        """
        if not isinstance(user_text, str):
            raise ParsingError(
                "El texto de búsqueda debe ser string",
                details={"received_type": type(user_text).__name__, "value": str(user_text)[:100]}
            )

        if not user_text or not user_text.strip():
            return []

        # Consultar caché
        cache_key = self._get_cache_key("find", user_text, default_epsg, size=size)
        if use_cache and self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.log.info("[CACHE_HIT] find: %s", user_text)
                return cached

        self.log.debug("[CACHE_MISS] find: %s", user_text)
        start_time = time.time()
        final_size = size if size is not None else self._default_size
        results = await self._find_data(user_text, default_epsg, size=final_size)
        elapsed = (time.time() - start_time) * 1000

        self.log.info(
            "[NETWORK_REQ] find: %s | Results: %d | Time: %.2fms",
            user_text, len(results), elapsed
        )

        # Guardar en caché
        if use_cache and self._cache is not None:
            self._cache.set(cache_key, results)

        # Asegurar que respetamos el size final solicitado
        return results[:final_size]

    async def find_response(self, user_text: str, default_epsg: int = 25831, size: int | None = None, use_cache: bool = True) -> GeoResponse:
        """Busca ubicaciones y devuelve un objeto GeoResponse completo.

        Args:
            user_text: Texto de búsqueda
            default_epsg: EPSG por defecto
            size: Número máximo de resultados
            use_cache: Si es True, utiliza la caché

        Returns:
            GeoResponse: Objeto con la query y los resultados validados
        """
        start_time = time.time()
        results = await self.find(user_text, default_epsg, size=size, use_cache=use_cache)
        elapsed_ms = (time.time() - start_time) * 1000
        return GeoResponse(query=user_text, results=results, count=len(results), time_ms=elapsed_ms)

    async def find_reverse(
        self, x: float, y: float, epsg: int = 25831, layers: str = "address,tops,pk", size: int | None = None, use_cache: bool = True
    ) -> list[GeoResult]:
        """Geocodificación inversa: encuentra lugares en unas coordenadas.

        Args:
            x: Coordenada X / Longitud
            y: Coordenada Y / Latitud
            epsg: Código EPSG de las coordenadas (default: 25831)
            layers: Capas a buscar (address, tops, pk)
            size: Número máximo de resultados (usa default_size si es None)
            use_cache: Si es True, utiliza la caché

        Returns:
            list[GeoResult]: Lista de resultados validados
        """
        response = await self.find_reverse_response(x, y, epsg, layers, size, use_cache)
        return response.results

    async def find_reverse_response(
        self, x: float, y: float, epsg: int = 25831, layers: str = "address,tops,pk", size: int | None = None, use_cache: bool = True
    ) -> GeoResponse:
        """Geocodificación inversa y devuelve un objeto GeoResponse completo."""
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
             raise ParsingError(
                 "Las coordenadas x, y deben ser numéricas",
                 details={"x_type": type(x).__name__, "y_type": type(y).__name__}
             )

        final_size = size if size is not None else self._default_size
        query_text = f"{x} {y} EPSG:{epsg}"
        cache_key = self._get_cache_key("find_reverse", x, y, epsg, layers, final_size)

        if use_cache and self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.log.info("[CACHE_HIT] find_reverse: %s", query_text)
                return GeoResponse(query=query_text, results=cached, count=len(cached))

        self.log.debug("[CACHE_MISS] find_reverse: %s", query_text)
        start_time = time.time()
        try:
            results = await self.find_point_coordinate_icgc(x, y, epsg, layers, size=final_size)
            elapsed = (time.time() - start_time) * 1000

            self.log.info(
                "[NETWORK_REQ] find_reverse: %s | Results: %d | Time: %.2fms",
                query_text, len(results), elapsed
            )

            if use_cache and self._cache is not None:
                self._cache.set(cache_key, results)

            elapsed_ms = (time.time() - start_time) * 1000
            return GeoResponse(query=query_text, results=results, count=len(results), time_ms=elapsed_ms)
        except Exception as e:
            self.log.exception("Find reverse error for %s: %s", query_text, e)
            # Envolver excepciones genéricas en ServiceError si no son ya GeoFinderError
            if not isinstance(e, (ParsingError, CoordinateError, ServiceError)):
                raise ServiceError(
                    f"Error en geocodificación inversa: {e}",
                    details={"query": query_text, "error_type": type(e).__name__}
                ) from e
            raise

    async def autocomplete(self, partial_text: str, size: int | None = None, use_cache: bool = True) -> list[GeoResult]:
        """Obtiene sugerencias de autocompletado."""
        final_size = size if size is not None else self._default_size
        cache_key = self._get_cache_key("autocomplete", partial_text, final_size)
        if use_cache and self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.log.info("[CACHE_HIT] autocomplete: %s", partial_text)
                return cached

        self.log.debug("[CACHE_MISS] autocomplete: %s", partial_text)
        start_time = time.time()
        try:
            client = await self.get_icgc_client()
            res_dict = await client.autocomplete(partial_text, size=final_size)
            results = self._parse_icgc_response(res_dict)
            elapsed = (time.time() - start_time) * 1000

            self.log.info(
                "[NETWORK_REQ] autocomplete: %s | Results: %d | Time: %.2fms",
                partial_text, len(results), elapsed
            )

            if use_cache and self._cache is not None:
                self._cache.set(cache_key, results)

            return results
        except Exception as e:
            self.log.exception("Autocomplete error: %s", e)
            # Envolver excepciones genéricas en ServiceError
            if not isinstance(e, ServiceError):
                raise ServiceError(
                    f"Error en autocompletado: {e}",
                    details={"query": partial_text, "error_type": type(e).__name__}
                ) from e
            raise

    # =========================================================================
    # Detección de tipo de búsqueda
    # =========================================================================

    async def _find_data(self, text, default_epsg, size=None):
        """Detecta el tipo de búsqueda y ejecuta la consulta apropiada."""
        final_size = size or self._default_size

        # Rectángulo de coordenadas
        west, north, east, south, epsg = self._parse_rectangle(text)
        if all(c is not None for c in (west, north, east, south)):
            return await self._find_rectangle(west, north, east, south, epsg or default_epsg, size=final_size)

        # Punto de coordenadas
        x, y, epsg = self._parse_point(text)
        if x is not None and y is not None:
            return await self._find_point_coordinate(x, y, epsg or default_epsg, size=final_size)

        # Carretera y kilómetro
        road, km = self._parse_road(text)
        if road is not None and km is not None:
            return await self.find_road(road, km, size=final_size)

        # Dirección
        municipality, street_type, street, number = self._parse_address(text)
        if (municipality and street and number) or (street and number):
            return await self.find_address(municipality, street_type, street, number, size=final_size)

        # Por defecto: topónimo
        return await self.find_placename(text, size=final_size)

    @staticmethod
    def _parse_rectangle(text):
        """Detecta un rectángulo de coordenadas en el texto.

        Formatos aceptados:
            - X1 Y1 X2 Y2
            - EPSG:código X1 Y1 X2 Y2
            - X1 Y1 X2 Y2 EPSG:código
        """
        # Expresión regular mejorada para permitir comas o múltiples espacios
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)[\s,]+([+-]?[0-9]*[.,]?[0-9]+)[\s,]+([+-]?[0-9]*[.,]?[0-9]+)[\s,]+([+-]?[0-9]*[.,]?[0-9]+)\s*(?:\s+EPSG:(\d+))?\s*$"
        found = re.search(expression, text, re.IGNORECASE)

        if found:
            epsg1, west, north, east, south, epsg2 = found.groups()
            w = float(west.replace(",", "."))
            n = float(north.replace(",", "."))
            e = float(east.replace(",", "."))
            s = float(south.replace(",", "."))
            epsg = int(epsg1 or epsg2) if (epsg1 or epsg2) else None

            # Validación básica de plausibilidad si es WGS84
            if epsg == 4326:
                if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= n <= 90 and -90 <= s <= 90):
                    return None, None, None, None, None

            return w, n, e, s, epsg
        return None, None, None, None, None

    @staticmethod
    def _parse_point(text):
        """Detecta coordenadas de un punto en el texto.

        Formatos aceptados:
            - X Y
            - EPSG:código X Y
            - X Y EPSG:código
        """
        # Expresión regular mejorada para permitir comas o múltiples espacios
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)[\s,]+([+-]?[0-9]*[.,]?[0-9]+)(?:\s+EPSG:(\d+))?\s*$"
        found = re.search(expression, text, re.IGNORECASE)

        if found:
            epsg1, x, y, epsg2 = found.groups()
            fx = float(x.replace(",", "."))
            fy = float(y.replace(",", "."))
            epsg = int(epsg1 or epsg2) if (epsg1 or epsg2) else None

            # Validación básica de plausibilidad si es WGS84
            if epsg == 4326:
                if not (-180 <= fx <= 180 and -90 <= fy <= 90):
                    return None, None, None

            return fx, fy, epsg
        return None, None, None

    @staticmethod
    def _parse_road(text):
        """Detecta una carretera y kilómetro.

        Formatos aceptados:
            - C-32 km 10
            - C32, 10.5
            - AP7 km 150
        """
        # Soporte para kilómetros decimales
        expression = r"^\s*([A-Za-z]+)-*(\d+)\s*(?:(?:km)|,|\s)\s*(\d*[.,]?\d+)\s*$"
        found = re.search(expression, text, re.IGNORECASE)

        if found:
            road, road_number, km = found.groups()
            return f"{road}-{road_number}", km.replace(",", ".")
        return None, None

    @staticmethod
    def _parse_address(text):
        """Detecta una dirección de forma robusta.

        Formatos aceptados:
            - Barcelona, Diagonal 100
            - C/ Aragó 50, Barcelona
            - Gran Via 123
            - Passeig de Gràcia s/n, Barcelona
        """
        # Limpieza previa
        text = text.strip()

        # 1. Intentar formato con comas (más fiable)
        # Formato: [Municipio], [Tipo] Calle [Num], [Municipio]
        # O: [Calle], [Num], [Municipio]
        parts = [p.strip() for p in text.split(",")]

        # Regex comunes
        addr_regex = r"^([\w\s./]+)\s+(\d+[\d-]*|[Ss]/[Nn])$"
        type_regex = r"^([\w]{1,4}[./])\s*(.*)$"
        num_only_regex = r"^(\d+[\d-]*|[Ss]/[Nn])$"

        if len(parts) >= 3:
            # Caso: Calle, Num, Municipio
            if re.match(num_only_regex, parts[1], re.IGNORECASE):
                street_full = parts[0]
                type_match = re.search(type_regex, street_full)
                if type_match:
                    return parts[2], type_match.group(1), type_match.group(2).strip(), parts[1]
                return parts[2], None, street_full.strip(), parts[1]

        if len(parts) >= 2:
            # Caso: Calle Num, Municipio
            found = re.search(addr_regex, parts[0], re.IGNORECASE)
            if found:
                street_full, number = found.groups()
                type_match = re.search(type_regex, street_full)
                if type_match:
                    return parts[1], type_match.group(1), type_match.group(2).strip(), number
                return parts[1], None, street_full.strip(), number

            # Caso: Municipio, Calle Num
            found = re.search(addr_regex, parts[1], re.IGNORECASE)
            if found:
                street_full, number = found.groups()
                type_match = re.search(type_regex, street_full)
                if type_match:
                    return parts[0], type_match.group(1), type_match.group(2).strip(), number
                return parts[0], None, street_full.strip(), number

        # 2. Formato sin comas (heuristic)
        # Regex: [Tipo] [Calle...] [Num/S/N] [Municipio...]
        # Asumimos que el número o s/n es el separador entre calle y municipio
        heuristic_regex = r"^(?:([\w]{1,4}[./])\s+)?([\w\s]{3,})\s+(\d+[\d-]*|[Ss]/[Nn])(?:\s+([\w\s]{3,}))?$"
        found = re.search(heuristic_regex, text, re.IGNORECASE)
        if found:
            stype, street, number, municipality = found.groups()
            return (municipality or "").strip(), stype, street.strip(), number

        return None, None, None, None

    # =========================================================================
    # Métodos de búsqueda
    # =========================================================================

    async def _find_rectangle(self, west, north, east, south, epsg, size=5) -> list[GeoResult]:
        """Busca en un rectángulo de coordenadas."""
        self.log.info("Search rectangle: %s %s %s %s EPSG:%s", west, north, east, south, epsg)

        # Buscar en el punto central
        central_x = west + (east - west) / 2.0
        central_y = south + (north - south) / 2.0

        results = []
        # No añadimos el punto central aún, obtenemos la lista cruda
        point_results = await self._find_point_coordinate(central_x, central_y, epsg, add_point=False, size=size)

        # Transformar punto central y bounds a WGS84 para consistencia
        wgs_x, wgs_y = transform_point(central_x, central_y, epsg, self.geoencoder_epsg)
        wgs_west, wgs_north = transform_point(west, north, epsg, self.geoencoder_epsg)
        wgs_east, wgs_south = transform_point(east, south, epsg, self.geoencoder_epsg)

        for point_obj in point_results:
            # Crear copia con coordenadas del rectángulo (en el EPSG que toque)
            results.append(point_obj.model_copy(update={
                "west": wgs_west if wgs_west is not None else west,
                "north": wgs_north if wgs_north is not None else north,
                "east": wgs_east if wgs_east is not None else east,
                "south": wgs_south if wgs_south is not None else south
            }))

        # Añadir entrada del rectángulo
        results.append(
            GeoResult(
                nom=f"Rectangle ({west} {north} {east} {south}) EPSG:{epsg}",
                idTipus=None,
                nomTipus="Rectangle",
                nomMunicipi="",
                nomComarca="",
                x=wgs_x if wgs_x is not None else central_x,
                y=wgs_y if wgs_y is not None else central_y,
                west=wgs_west if wgs_west is not None else west,
                north=wgs_north if wgs_north is not None else north,
                east=wgs_east if wgs_east is not None else east,
                south=wgs_south if wgs_south is not None else south,
                epsg=self.geoencoder_epsg if wgs_x is not None else epsg,
            )
        )

        return results

    async def _find_point_coordinate(self, x, y, epsg, add_point=True, size=None) -> list[GeoResult]:
        """Busca lugares en un punto de coordenadas."""
        self.log.info("Search coordinate: %s %s EPSG:%s", x, y, epsg)

        final_size = size or self._default_size
        # Dividir el size entre los dos tipos de búsqueda (direcciones y topónimos)
        size_addr = max(1, final_size // 2)
        size_tops = max(1, final_size - size_addr)

        # Ejecutar búsquedas en paralelo
        tasks = [
            self.find_point_coordinate_icgc(
                x, y, epsg, layers="address,pk", search_radius_km=0.05, size=size_addr
            ),
            self.find_point_coordinate_icgc(
                x, y, epsg, layers="tops", search_radius_km=None, size=size_tops
            )
        ]

        results_groups = await asyncio.gather(*tasks)
        all_results = results_groups[0] + results_groups[1]

        # Deduplicar resultados del ICGC
        seen_keys = set()
        results = []
        for r in all_results:
            # Usar ID si está disponible, si no una clave compuesta
            if r.id:
                key = f"id:{r.id}"
            else:
                key = (r.nom, r.nomTipus, round(r.x, 6), round(r.y, 6))

            if key not in seen_keys:
                seen_keys.add(key)
                results.append(r)

        # Añadir entrada del punto
        if add_point:
            municipality = results[0].nomMunicipi if results else ""
            county = results[0].nomComarca if results else ""

            # Coordenadas en WGS84 para consistencia con los resultados del ICGC
            wgs_x, wgs_y = transform_point(x, y, epsg, self.geoencoder_epsg)

            format_str = "Punt %.2f %.2f EPSG:%s" if x > 100 else "Punt %.8f %.8f EPSG:%s"
            results.append(
                GeoResult(
                    nom=format_str % (x, y, epsg),
                    idTipus=None,
                    nomTipus="Coordenada",
                    nomMunicipi=municipality,
                    nomComarca=county,
                    x=wgs_x if wgs_x is not None else x,
                    y=wgs_y if wgs_y is not None else y,
                    epsg=self.geoencoder_epsg if wgs_x is not None else epsg,
                )
            )

        return results

    async def find_point_coordinate_icgc(
        self, x, y, epsg, layers="address,tops,pk", search_radius_km=0.05, size=2
    ):
        """Busca en el geocodificador ICGC por coordenadas."""
        # Transformar a WGS84 para la consulta
        query_x, query_y = transform_point(x, y, epsg, self.geoencoder_epsg)

        if query_x is None or query_y is None:
            self.log.error("Coordinate transform error: %s %s EPSG:%s", x, y, epsg)
            raise CoordinateError(
                "Error transformando coordenadas",
                details={"x": x, "y": y, "epsg": epsg}
            )

        try:
            extra_params = {}
            if search_radius_km:
                extra_params["boundary.circle.radius"] = search_radius_km

            client = await self.get_icgc_client()
            res_dict = await client.reverse(
                query_y, query_x, layers=layers, size=size, **extra_params
            )
        except Exception as e:
            self.log.exception("ICGC geocoder error: %s", e)
            # Envolver excepciones genéricas en ServiceError
            if not isinstance(e, (CoordinateError, ServiceError)):
                raise ServiceError(
                    f"Error en geocodificación por coordenadas: {e}",
                    details={"x": x, "y": y, "epsg": epsg, "error_type": type(e).__name__}
                ) from e
            raise

        return self._parse_icgc_response(res_dict)

    async def find_road(self, road, km, size=None):
        """Busca un punto kilométrico de carretera."""
        self.log.info("Search road: %s km %s", road, km)
        final_size = size or self._default_size

        try:
            client = await self.get_icgc_client()
            res_dict = await client.geocode(f"{road} {km}", layers="pk", size=final_size)
        except Exception as e:
            self.log.exception("Road search error: %s", e)
            if not isinstance(e, ServiceError):
                raise ServiceError(
                    f"Error en búsqueda de carretera: {e}",
                    details={"road": road, "km": km, "error_type": type(e).__name__}
                ) from e
            raise

        return self._parse_icgc_response(res_dict, default_type="Punt quilomètric")

    async def find_address(self, municipality, street_type, street, number, size=None):
        """Busca una dirección."""
        self.log.info("Search address: %s, %s %s %s", municipality, street_type, street, number)
        final_size = size or self._default_size

        # Usar street_type si está disponible, si no defecto "Carrer"
        final_street_type = street_type.strip() if street_type else "Carrer"
        # Limpiar puntos finales si existen (ej: "Avda." -> "Avda")
        final_street_type = final_street_type.rstrip(".")

        query = f"{final_street_type} {street} {number}"
        if municipality:
            query += f", {municipality}"

        try:
            client = await self.get_icgc_client()
            res_dict = await client.geocode(query, layers="address", size=final_size)
        except Exception as e:
            self.log.exception("Address search error: %s", e)
            if not isinstance(e, ServiceError):
                raise ServiceError(
                    f"Error en búsqueda de dirección: {e}",
                    details={"query": query, "error_type": type(e).__name__}
                ) from e
            raise

        return self._parse_icgc_response(res_dict, default_type="Adreça")

    async def find_placename(self, text, size=None):
        """Busca un topónimo."""
        self.log.info("Search placename: %s", text)
        final_size = size or self._default_size

        try:
            client = await self.get_icgc_client()
            res_dict = await client.geocode(text, size=final_size)
        except Exception as e:
            self.log.exception("Placename search error: %s", e)
            if not isinstance(e, ServiceError):
                raise ServiceError(
                    f"Error en búsqueda de topónimo: {e}",
                    details={"query": text, "error_type": type(e).__name__}
                ) from e
            raise

        return self._parse_icgc_response(res_dict)

    # =========================================================================
    # Parsing de respuestas
    # =========================================================================

    def _parse_icgc_response(self, res_dict, default_type=None) -> list[GeoResult]:
        """Convierte respuesta ICGC a formato de modelos GeoResult."""
        return [
            GeoResult.from_icgc_feature(f, self.geoencoder_epsg, default_type)
            for f in res_dict.get("features", [])
        ]

    # =========================================================================
    # Utilidades
    # =========================================================================

    def is_rectangle(self, results: list[GeoResult]) -> bool:
        """Comprueba si los resultados son de tipo rectángulo."""
        return len(results) == 1 and results[0].west is not None

    def get_rectangle(self, results: list[GeoResult]):
        """Extrae coordenadas de un resultado de tipo rectángulo.

        Returns:
            tuple: (west, north, east, south, epsg)
        """
        r = results[0]
        return r.west, r.north, r.east, r.south, r.epsg

    def get_point(self, results: list[GeoResult], index=0):
        """Extrae coordenadas de un resultado.

        Returns:
            tuple: (x, y, epsg)
        """
        r = results[index]
        return r.x, r.y, r.epsg

    def get_name(self, results: list[GeoResult], index=0):
        """Extrae el nombre de un resultado."""
        return results[index].nom

    # =========================================================================
    # Utilidades de Procesamiento por Lote (Batch)
    # =========================================================================

    async def search_nearby(
        self,
        place_name: str,
        radius_km: float = 1.0,
        layers: str = "address,tops,pk",
        max_results: int = 10,
        use_cache: bool = True
    ) -> list[GeoResult]:
        """Busca lugares cerca de una ubicación nombrada.

        Primero encuentra el lugar especificado, luego busca otros lugares
        en un radio determinado.

        Args:
            place_name: Nombre del lugar de referencia (ej: "Barcelona", "Montserrat")
            radius_km: Radio de búsqueda en kilómetros (default: 1.0)
            layers: Capas a buscar (address, tops, pk)
            max_results: Número máximo de resultados
            use_cache: Si es True, utiliza la caché

        Returns:
            List[GeoResult]: Lista de lugares encontrados cerca de la ubicación
        """
        cache_key = self._get_cache_key("search_nearby", place_name, radius_km, layers, max_results)
        if use_cache and self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.log.info("[CACHE_HIT] search_nearby: %s", place_name)
                return cached

        self.log.debug("[CACHE_MISS] search_nearby: %s", place_name)

        # Primero encontrar el lugar de referencia
        reference_results = await self.find(place_name, use_cache=use_cache)
        if not reference_results:
            self.log.warning("search_nearby: No se encontró el lugar '%s'", place_name)
            return []

        # Obtener coordenadas del primer resultado
        ref_place = reference_results[0]

        # Buscar cerca de esas coordenadas
        nearby_results = await self.find_point_coordinate_icgc(
            ref_place.x, ref_place.y, ref_place.epsg,
            layers=layers,
            search_radius_km=radius_km,
            size=max_results
        )

        # Incluir el lugar de referencia al inicio y eliminar duplicados
        all_results = [ref_place] + nearby_results
        seen = set()
        unique_results = []
        for r in all_results:
            # Clave de unicidad más fuerte incluyento coordenadas redondeadas
            key = (r.nom, r.nomTipus, round(r.x, 6), round(r.y, 6))
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        if use_cache and self._cache is not None:
            self._cache.set(cache_key, unique_results)

        return unique_results

    async def find_batch(
        self,
        queries: list[str],
        default_epsg: int = 25831,
        max_concurrency: int = 5,
        use_cache: bool = True,
        ignore_errors: bool = False,
    ) -> list[GeoResponse]:
        """Procesa múltiples búsquedas en paralelo con control de concurrencia.

        Args:
            queries: Lista de textos de búsqueda
            default_epsg: EPSG por defecto si no se especifica en la query
            max_concurrency: Número máximo de peticiones simultáneas
            use_cache: Si es True, utiliza la caché
            ignore_errors: Si es True, ignora errores individuales y devuelve respuestas vacías

        Returns:
            List[GeoResponse]: Lista de respuestas en el mismo orden que las queries
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        # Deduplicar queries para ahorrar red
        unique_queries = list(set(queries))
        query_to_response = {}

        async def _bounded_find(query: str) -> None:
            async with semaphore:
                try:
                    resp = await self.find_response(query, default_epsg, use_cache)
                    query_to_response[query] = resp
                except Exception as e:
                    self.log.error("Batch query failed for '%s': %s", query, e)
                    query_to_response[query] = GeoResponse(
                        query=query,
                        results=[],
                        count=0,
                        error=str(e)
                    )
                    if not ignore_errors:
                        raise

        tasks = [_bounded_find(q) for q in unique_queries]
        await asyncio.gather(*tasks)

        # Recomponer en el orden original
        return [query_to_response[q] for q in queries]

    async def find_reverse_batch(
        self,
        coordinates: list[tuple[float, float]],
        epsg: int = 25831,
        layers: str = "address,tops,pk",
        size: int = 5,
        max_concurrency: int = 5,
        use_cache: bool = True,
        ignore_errors: bool = False,
    ) -> list[GeoResponse]:
        """Procesa múltiples geocodificaciones inversas en paralelo con control de concurrencia.

        Args:
            coordinates: Lista de tuplas (x, y)
            epsg: Código EPSG de las coordenadas
            layers: Capas a buscar (address, tops, pk)
            size: Número máximo de resultados por coordenada
            max_concurrency: Número máximo de peticiones simultáneas
            use_cache: Si es True, utiliza la caché
            ignore_errors: Si es True, ignora errores individuales

        Returns:
            List[GeoResponse]: Lista de respuestas en el mismo orden que las coordenadas
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        # Deduplicar coordenadas
        unique_coords = list(set(coordinates))
        coords_to_response = {}

        async def _bounded_find_reverse(coords: tuple[float, float]) -> None:
            x, y = coords
            async with semaphore:
                try:
                    resp = await self.find_reverse_response(x, y, epsg, layers, size, use_cache)
                    coords_to_response[coords] = resp
                except Exception as e:
                    query_text = f"{x} {y} EPSG:{epsg}"
                    self.log.error("Batch reverse query failed for '%s': %s", query_text, e)
                    coords_to_response[coords] = GeoResponse(
                        query=query_text,
                        results=[],
                        count=0,
                        error=str(e)
                    )
                    if not ignore_errors:
                        raise

        tasks = [_bounded_find_reverse(c) for c in unique_coords]
        await asyncio.gather(*tasks)

        # Recomponer en el orden original
        return [coords_to_response[c] for c in coordinates]

    # =========================================================================
    # Wrappers Síncronos (para scripts simples que no usan async)
    # =========================================================================

    def find_batch_sync(
        self,
        queries: list[str],
        default_epsg: int = 25831,
        max_concurrency: int = 5,
        use_cache: bool = True,
    ) -> list[GeoResponse]:
        """Versión síncrona de find_batch."""
        return self._sync(self.find_batch(queries, default_epsg, max_concurrency, use_cache))

    def find_reverse_batch_sync(
        self,
        coordinates: list[tuple[float, float]],
        epsg: int = 25831,
        layers: str = "address,tops,pk",
        size: int = 5,
        max_concurrency: int = 5,
        use_cache: bool = True,
    ) -> list[GeoResponse]:
        """Versión síncrona de find_reverse_batch."""
        return self._sync(
            self.find_reverse_batch(coordinates, epsg, layers, size, max_concurrency, use_cache)
        )


    def _sync(self, coro):
        """Ejecuta una corrutina de forma síncrona, gestionando el loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Estamos en un entorno asíncrono, no deberíamos usar wrappers síncronos
                raise RuntimeError(
                    "No se pueden usar métodos '_sync' dentro de un entorno asíncrono. "
                    "Usa 'await' con el método asíncrono correspondiente."
                )
            return loop.run_until_complete(coro)
        except RuntimeError:
            # No hay loop en este hilo o asyncio.run es preferible si el loop no existe
            # NOTA: asyncio.run cierra el loop al terminar.
            # Esto invalida el cliente Pelias interno si fue creado en ese loop.
            # Forzamos un reset del cliente para que la siguiente llamada cree uno nuevo.
            try:
                return asyncio.run(coro)
            finally:
                # Reset seguro del cliente (el loop de run ya se cerró)
                try:
                    asyncio.run(self._reset_client())
                except Exception:
                    pass

    def find_sync(self, user_text: str, default_epsg: int = 25831, use_cache: bool = True) -> list[GeoResult]:
        """Busca ubicaciones a partir de un texto (versión síncrona)."""
        return self._sync(self.find(user_text, default_epsg, use_cache=use_cache))

    def find_response_sync(self, user_text: str, default_epsg: int = 25831, use_cache: bool = True) -> GeoResponse:
        """Busca ubicaciones y devuelve un objeto GeoResponse (versión síncrona)."""
        return self._sync(self.find_response(user_text, default_epsg, use_cache=use_cache))

    def find_reverse_sync(
        self, x: float, y: float, epsg: int = 25831, layers: str = "address,tops,pk", size: int = 5, use_cache: bool = True
    ) -> list[GeoResult]:
        """Geocodificación inversa (versión síncrona)."""
        return self._sync(self.find_reverse(x, y, epsg, layers, size, use_cache=use_cache))

    def find_reverse_response_sync(
        self, x: float, y: float, epsg: int = 25831, layers: str = "address,tops,pk", size: int = 5, use_cache: bool = True
    ) -> GeoResponse:
        """Geocodificación inversa response (versión síncrona)."""
        return self._sync(self.find_reverse_response(x, y, epsg, layers, size, use_cache=use_cache))

    def autocomplete_sync(self, partial_text: str, size: int = 10, use_cache: bool = True) -> list[GeoResult]:
        """Obtiene sugerencias de autocompletado (versión síncrona)."""
        return self._sync(self.autocomplete(partial_text, size, use_cache=use_cache))
