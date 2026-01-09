"""
Sistema de caché asíncrono LRU con TTL para GeoFinder.
"""

import time
from collections import OrderedDict
from typing import Any


class LRUCache:
    """Caché LRU (Least Recently Used) sincrónica en memoria con TTL (Time To Live).

    Esta clase proporciona una caché en memoria para almacenar resultados de
    peticiones costosas. El tamaño está limitado y los elementos expiran
    después de un tiempo determinado.
    """

    def __init__(self, maxsize: int = 128, ttl: int = 3600):
        """Inicializa la caché.

        Args:
            maxsize: Número máximo de elementos en la caché.
            ttl: Tiempo de vida en segundos (default: 1 hora).
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._timestamps: dict[str, float] = {}

    def get(self, key: str) -> Any | None:
        """Obtiene un elemento de la caché si existe y no ha expirado.

        Args:
            key: Identificador único del elemento.

        Returns:
            El valor almacenado o None si no existe o ha expirado.
        """
        if key not in self._cache:
            return None

        # Verificar si ha expirado
        if time.monotonic() - self._timestamps[key] > self.ttl:
            self.pop(key)
            return None

        # Mover al final (más reciente)
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Guarda un elemento en la caché.

        Args:
            key: Identificador único del elemento.
            value: Valor a almacenar.
        """
        if key in self._cache:
            self._cache.move_to_end(key)

        self._cache[key] = value
        self._timestamps[key] = time.monotonic()

        # Respetar el tamaño máximo
        if len(self._cache) > self.maxsize:
            # OrderedDict iterador retorna elementos en orden de inserción
            # El primero es el más antiguo (Least Recently Used)
            oldest_key = next(iter(self._cache))
            self.pop(oldest_key)

    def pop(self, key: str) -> None:
        """Elimina un elemento de la caché."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self) -> None:
        """Limpia toda la caché."""
        self._cache.clear()
        self._timestamps.clear()

    def __len__(self) -> int:
        """Retorna el número de elementos actuales en la caché."""
        return len(self._cache)

# Alias por compatibilidad
AsyncLRUCache = LRUCache
