"""
Cliente para servidores Pelias (API de geocodificación)
"""

import asyncio
import logging
import random
from typing import Any, Type, Optional, cast

import httpx

from .exceptions import (
    ConfigurationError,
    ServiceConnectionError,
    ServiceError,
    ServiceHTTPError,
    ServiceTimeoutError,
)

# Aliases para compatibilidad hacia atrás (deprecated)
PeliasError = ServiceError
PeliasConnectionError = ServiceConnectionError
PeliasTimeoutError = ServiceTimeoutError


class PeliasClient:
    """Cliente genérico para servidores Pelias de geocodificación.

    Utiliza httpx para peticiones asíncronas con reintentos exponenciales.

    Attributes:
        url: URL base del servidor Pelias
        timeout: Timeout en segundos para las peticiones
        client: Cliente httpx.AsyncClient (owned o injected)
        max_retries: Número máximo de reintentos en errores 5xx o conexión
        retry_base_delay: Delay inicial en segundos para backoff exponencial
        retry_max_delay: Delay máximo en segundos para reintentos

    Note:
        Si se proporciona un `http_client` externo, PeliasClient NO lo cerrará
        al llamar a `close()`. El usuario es responsable de cerrar el cliente.

    Example:
        async with PeliasClient("https://eines.icgc.cat/geocodificador") as client:
            results = await client.geocode("Barcelona")
    """

    def __init__(
        self,
        url: str,
        default_timeout: float = 5,
        default_search_call: str = "/v1/search",
        default_reverse_call: str = "/v1/reverse",
        default_autocomplete_call: str = "/v1/autocomplete",
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
        retry_max_delay: float = 10.0,
        retry_on_5xx: bool = True,
        verify_ssl: bool = True,
        http_client: httpx.AsyncClient | None = None,
        timeout: float | None = None, # Add timeout for compatibility
    ) -> None:
        """Configura la conexión al servidor.

        Args:
            url: URL base del servidor Pelias
            default_timeout: Timeout en segundos (default: 5)
            default_search_call: Endpoint de búsqueda
            default_reverse_call: Endpoint de geocodificación inversa
            default_autocomplete_call: Endpoint de autocompletado
            max_retries: Número máximo de reintentos (default: 3)
            retry_base_delay: Delay inicial del backoff exponencial (default: 0.5s)
            retry_max_delay: Delay máximo entre reintentos (default: 10s)
            retry_on_5xx: Reintentar automáticamente en errores 5xx (default: True)
            verify_ssl: Verificar certificados SSL (default: True).
            http_client: Cliente httpx.AsyncClient externo opcional. Si se proporciona,
                        PeliasClient NO lo cerrará al llamar a close().
        """
        if not url:
            raise ConfigurationError("La URL del servidor Pelias no puede estar vacía")

        # Asegurar que la URL tiene protocolo
        if not url.startswith(("http://", "https://")):
            # Si parece un dominio pero no tiene protocolo, añadir https
            if "." in url:
                url = "https://" + url
            else:
                raise ConfigurationError(
                    f"URL inválida: '{url}'. Debe incluir el protocolo (http/https)",
                    details={"url": url}
                )

        self.url = url + ("" if url.endswith("/") else "/")
        self.timeout = timeout if timeout is not None else default_timeout
        self.search_call = default_search_call
        self.reverse_call = default_reverse_call
        self.autocomplete_call = default_autocomplete_call
        self.verify_ssl = verify_ssl
        self.last_request: str | None = None
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self.retry_on_5xx = retry_on_5xx

        # Configurar logger PRIMERO
        self.log = logging.getLogger("geofinder.pelias")

        if not verify_ssl:
            self.log.warning("SSL verification is disabled for PeliasClient.")

        # Determinar ownership del cliente
        self._owns_client = http_client is None

        # Configurar cliente httpx
        if http_client is not None:
            # Usar cliente externo proporcionado
            self.client = http_client
            # Advertir si hay conflicto de configuración
            if not verify_ssl:
                self.log.warning(
                    "verify_ssl=False ignorado: usando cliente httpx externo proporcionado"
                )
        else:
            # Crear cliente propio
            # Los reintentos se manejan a nivel de aplicación en call() con backoff exponencial
            self.client = httpx.AsyncClient(
                verify=self.verify_ssl,
                follow_redirects=True
            )

        self._closed = False

    async def geocode(self, query_string: str, **extra_params_dict: Any) -> dict[str, Any]:
        """Geocodifica un texto de búsqueda.

        Args:
            query_string: Texto a buscar (topónimo, dirección, etc.)
            **extra_params_dict: Parámetros adicionales (layers, size, etc.)

        Returns:
            dict: Respuesta GeoJSON con features encontradas

        Raises:
            PeliasError: Si hay error en la geocodificación
        """
        params_dict = {"text": query_string}
        params_dict.update(extra_params_dict)
        return await self.call(self.search_call, **params_dict)

    async def autocomplete(self, query_string: str, **extra_params_dict: Any) -> dict[str, Any]:
        """Obtiene sugerencias de autocompletado.

        Args:
            query_string: Texto parcial para autocompletar
            **extra_params_dict: Parámetros adicionales

        Returns:
            dict: Respuesta GeoJSON con sugerencias

        Raises:
            PeliasError: Si hay error en el autocompletado
        """
        params_dict = {"text": query_string}
        params_dict.update(extra_params_dict)
        return await self.call(self.autocomplete_call, **params_dict)

    async def reverse(self, lat: float, lon: float, **extra_params_dict: Any) -> dict[str, Any]:
        """Geocodificación inversa: obtiene lugares en unas coordenadas.

        Args:
            lat: Latitud (WGS84)
            lon: Longitud (WGS84)
            **extra_params_dict: Parámetros adicionales (layers, size, etc.)

        Returns:
            dict: Respuesta GeoJSON con lugares encontrados

        Raises:
            PeliasError: Si hay error en la geocodificación inversa
        """
        params_dict = {"lon": lon, "lat": lat}
        params_dict.update(extra_params_dict)
        return await self.call(self.reverse_call, **params_dict)

    async def call(self, call_name: str, **params_dict: Any) -> dict[str, Any]:
        """Ejecuta una llamada al servidor Pelias con reintentos exponenciales.

        Implementa exponential backoff para errores transitorios:
        - Errores 5xx: reintenta si retry_on_5xx está habilitado
        - Timeout/Conexión: siempre reintenta
        - Errores 4xx: NO reintenta (errores del cliente)

        Args:
            call_name: Nombre del endpoint
            **params_dict: Parámetros de la petición

        Returns:
            dict: Respuesta JSON parseada

        Raises:
            PeliasTimeoutError: Si la petición excede el timeout tras reintentos
            PeliasConnectionError: Si hay error de conexión tras reintentos
            PeliasError: Si hay otro error en la petición
        """
        # Filtrar parámetros None
        params = {k: v for k, v in params_dict.items() if v is not None}

        # Construir URL completa
        url = self.url + call_name.lstrip("/")
        self.last_request = url

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

                # Guardar URL completa con parámetros para debug
                self.last_request = str(response.url)

                # Verificar status code
                response.raise_for_status()

                # Parsear JSON
                data: dict[str, Any] = response.json()

                # Validar que tiene la estructura mínima esperada (features)
                # Esto evita KeyErrors en el llamador y nos permite lanzar ServiceError
                if not isinstance(data, dict) or "features" not in data:
                    raise ServiceError(
                        "Respuesta malformada: falta la clave 'features'",
                        url=str(response.url),
                        details={"response": data}
                    )

                return data

            except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException) as e:
                # Errores de red y timeout siempre se reintentan
                last_exception = e
                error_type = type(e).__name__
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    self.log.warning(
                        "[RETRY] %s en %s (intento %d/%d). Reintentando en %.2fs...",
                        error_type, url, attempt + 1, self.max_retries + 1, delay
                    )
                    await asyncio.sleep(delay)
                    continue

                if isinstance(e, httpx.TimeoutException):
                    raise ServiceTimeoutError(
                        f"Timeout después de {self.timeout}s ({self.max_retries + 1} intentos)",
                        url=url,
                        details={"timeout": self.timeout, "attempts": self.max_retries + 1}
                    ) from e
                raise ServiceConnectionError(
                    f"Error de conexión ({error_type}) tras {self.max_retries + 1} intentos",
                    url=url,
                    details={"error_type": error_type, "attempts": self.max_retries + 1}
                ) from e

            except httpx.HTTPStatusError as e:
                # Errores HTTP (4xx, 5xx)
                last_exception = e
                status_code = e.response.status_code

                # Errores 5xx: reintenta si está habilitado
                if status_code >= 500 and self.retry_on_5xx:
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff_delay(attempt)
                        self.log.error(
                            "[RETRY] Servidor Pelias Error %d en %s (intento %d/%d). Reintentando en %.2fs...",
                            status_code, url, attempt + 1, self.max_retries + 1, delay
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise ServiceHTTPError(
                        f"Error HTTP {status_code} tras {self.max_retries + 1} intentos",
                        url=url,
                        details={"attempts": self.max_retries + 1},
                        status_code=status_code,
                        response_text=e.response.text,
                    ) from e

                # Errores 4xx o 5xx sin reintentos: NO reintenta
                self.log.error("Error HTTP %d en %s: %s", status_code, url, e.response.text)
                raise ServiceHTTPError(
                    f"Error HTTP {status_code}",
                    url=url,
                    details=None,
                    status_code=status_code,
                    response_text=e.response.text
                ) from e

            except httpx.RequestError as e:
                # Otros errores de httpx que no son de red/timeout específicos
                raise ServiceError(
                    f"Error en la petición: {e}",
                    url=url,
                    details={"error_type": type(e).__name__}
                ) from e

            except ValueError as e:
                # Error parseando JSON
                raise ServiceError(
                    f"Error parseando JSON de la respuesta: {e}",
                    url=url,
                    details={"error": str(e)}
                ) from e

        # Fallback
        if last_exception:
            raise ServiceError(
                f"Error fatal tras {self.max_retries + 1} intentos",
                url=url,
                details={"attempts": self.max_retries + 1}
            ) from last_exception
        
        raise ServiceError("Error inesperado en PeliasClient.call")

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calcula el delay de backoff exponencial con jitter.

        Args:
            attempt: Número de intento (0-indexed)

        Returns:
            float: Delay en segundos (limitado por retry_max_delay)
        """
        base_delay = self.retry_base_delay * (2 ** attempt)
        # Añadir jitter aleatorio (+/- 10%) para evitar thundering herd
        jitter = base_delay * 0.1 * (2 * random.random() - 1)
        delay = base_delay + jitter
        return max(0.0, min(delay, self.retry_max_delay))

    def last_sent(self) -> str | None:
        """Retorna la última petición ejecutada (útil para debug).

        Returns:
            str: URL de la última petición con parámetros
        """
        return self.last_request

    async def close(self) -> None:
        """Cierra el cliente httpx de forma idempotente.

        Solo cierra el cliente si fue creado internamente (owned).
        Si el cliente fue proporcionado externamente, NO lo cierra.
        """
        if self._owns_client and not self._closed:
            await self.client.aclose()
            self._closed = True

    async def get_response_time(self, response: httpx.Response) -> float:
        """Retorna el tiempo de respuesta en segundos a partir de los metadatos de httpx."""
        # Calcular tiempo de respuesta
        return cast(float, response.elapsed.total_seconds())

    async def __aenter__(self) -> "PeliasClient":
        """Soporte para async context manager."""
        return self

    async def __aexit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Cierra el cliente al salir del async context manager."""
        await self.close()
