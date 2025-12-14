"""
Cliente para servidores Pelias (API de geocodificación)

Copyright (C) 2019-2025 Institut Cartogràfic i Geològic de Catalunya (ICGC)
Copyright (C) 2025 Goalnefesh

This file is part of geocoder-mcp, a fork of the Open ICGC QGIS Plugin.
Original project: https://github.com/OpenICGC/QgisPlugin

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, RequestException, Timeout
from urllib3.util.retry import Retry


class PeliasError(Exception):
    """Excepción base para errores del cliente Pelias."""

    pass


class PeliasConnectionError(PeliasError):
    """Error de conexión con el servidor Pelias."""

    pass


class PeliasTimeoutError(PeliasError):
    """Timeout en la petición al servidor Pelias."""

    pass


class PeliasClient:
    """Cliente genérico para servidores Pelias de geocodificación.

    Utiliza requests con retry logic automático para mayor robustez.

    Attributes:
        url: URL base del servidor Pelias
        timeout: Timeout en segundos para las peticiones
        session: Sesión de requests con retry logic configurado

    Example:
        client = PeliasClient("https://eines.icgc.cat/geocodificador")
        results = client.geocode("Barcelona")
    """

    def __init__(
        self,
        url,
        default_timeout=5,
        default_search_call="/v1/search",
        default_reverse_call="/v1/reverse",
        default_autocomplete_call="/v1/autocomplete",
        max_retries=3,
    ):
        """Configura la conexión al servidor.

        Args:
            url: URL base del servidor Pelias
            default_timeout: Timeout en segundos (default: 5)
            default_search_call: Endpoint de búsqueda
            default_reverse_call: Endpoint de geocodificación inversa
            default_autocomplete_call: Endpoint de autocompletado
            max_retries: Número máximo de reintentos (default: 3)
        """
        self.url = url + ("" if url.endswith("/") else "/")
        self.timeout = default_timeout
        self.search_call = default_search_call
        self.reverse_call = default_reverse_call
        self.autocomplete_call = default_autocomplete_call
        self.last_request = None

        # Configurar sesión con retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.3,  # 0.3s, 0.6s, 1.2s entre reintentos
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def geocode(self, query_string, **extra_params_dict):
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
        return self.call(self.search_call, **params_dict)

    def autocomplete(self, query_string, **extra_params_dict):
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
        return self.call(self.autocomplete_call, **params_dict)

    def reverse(self, lat, lon, **extra_params_dict):
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
        return self.call(self.reverse_call, **params_dict)

    def call(self, call_name, **params_dict):
        """Ejecuta una llamada al servidor Pelias.

        Args:
            call_name: Nombre del endpoint
            **params_dict: Parámetros de la petición

        Returns:
            dict: Respuesta JSON parseada

        Raises:
            PeliasTimeoutError: Si la petición excede el timeout
            PeliasConnectionError: Si hay error de conexión
            PeliasError: Si hay otro error en la petición
        """
        # Filtrar parámetros None
        params = {k: v for k, v in params_dict.items() if v is not None}

        # Construir URL completa
        url = self.url + call_name.lstrip("/")
        self.last_request = url

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)

            # Guardar URL completa con parámetros para debug
            self.last_request = response.url

            # Verificar status code
            response.raise_for_status()

            # Parsear JSON
            return response.json()

        except Timeout as e:
            raise PeliasTimeoutError(f"Timeout después de {self.timeout}s: {url}") from e
        except ConnectionError as e:
            raise PeliasConnectionError(f"Error de conexión con el servidor: {url}") from e
        except RequestException as e:
            raise PeliasError(f"Error en la petición Pelias: {e}") from e
        except ValueError as e:
            raise PeliasError(f"Error parseando respuesta JSON: {e}") from e

    def last_sent(self):
        """Retorna la última petición ejecutada (útil para debug).

        Returns:
            str: URL de la última petición con parámetros
        """
        return self.last_request

    def close(self):
        """Cierra la sesión de requests.

        Útil para liberar recursos cuando se termina de usar el cliente.
        """
        self.session.close()

    def __enter__(self):
        """Soporte para context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión al salir del context manager."""
        self.close()
        return False
