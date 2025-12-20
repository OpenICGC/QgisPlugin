"""
Jerarquía de excepciones personalizada para GeoFinder.

Todas las excepciones de GeoFinder heredan de GeoFinderError, permitiendo
capturar todos los errores de la librería con un solo except.
"""

from typing import Optional, Dict, Any

__all__ = [
    "GeoFinderError",
    "ConfigurationError",
    "ParsingError",
    "CoordinateError",
    "ServiceError",
    "ServiceConnectionError",
    "ServiceTimeoutError",
    "ServiceHTTPError",
]


class GeoFinderError(Exception):
    """Clase base para todas las excepciones de GeoFinder.
    
    Attributes:
        message: Mensaje de error principal
        details: Diccionario opcional con contexto adicional del error
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Inicializa la excepción con mensaje y detalles opcionales.
        
        Args:
            message: Mensaje de error descriptivo
            details: Diccionario con información adicional del contexto
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        """Formatea el mensaje de error con detalles si están disponibles."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message
    
    def __repr__(self) -> str:
        """Representación para debugging."""
        class_name = self.__class__.__name__
        if self.details:
            return f"{class_name}(message={self.message!r}, details={self.details!r})"
        return f"{class_name}(message={self.message!r})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para serialización JSON.
        
        Returns:
            dict: Diccionario con type, message y details de la excepción
        """
        result = {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details.copy(),
        }
        
        # Añadir atributos específicos de subclases
        if hasattr(self, "url") and self.url:
            result["url"] = self.url
        if hasattr(self, "status_code") and self.status_code is not None:
            result["status_code"] = self.status_code
        if hasattr(self, "response_text") and self.response_text:
            result["response_text"] = self.response_text[:200]
        
        return result


class ConfigurationError(GeoFinderError):
    """Error de configuración del geocodificador.
    
    Se lanza cuando hay problemas con la configuración inicial:
    - URL del servidor inválida o vacía
    - Parámetros de configuración incorrectos
    - Credenciales inválidas
    
    Example:
        raise ConfigurationError(
            "URL del servidor Pelias no puede estar vacía",
            details={"url": url}
        )
    """
    pass


class ParsingError(GeoFinderError):
    """Error al parsear la entrada del usuario.
    
    Se lanza cuando el texto de búsqueda o parámetros no pueden ser procesados:
    - Tipo de dato incorrecto (ej: no string cuando se espera string)
    - Formato no reconocido
    - Parámetros faltantes o inválidos
    
    Example:
        raise ParsingError(
            "El texto de búsqueda debe ser string",
            details={"received_type": type(user_text).__name__, "value": user_text}
        )
    """
    pass


class CoordinateError(GeoFinderError):
    """Error relacionado con coordenadas geográficas.
    
    Se lanza cuando hay problemas con coordenadas:
    - Coordenadas fuera de rango válido
    - Código EPSG inválido o no soportado
    - Error en transformación entre sistemas de coordenadas
    
    Example:
        raise CoordinateError(
            "Longitud fuera de rango (-180, 180)",
            details={"x": x, "y": y, "epsg": epsg}
        )
    """
    pass


class ServiceError(GeoFinderError):
    """Clase base para errores del servicio externo de geocodificación.
    
    Se lanza cuando hay problemas comunicándose con el servicio:
    - Errores de red
    - Errores HTTP
    - Timeouts
    
    Attributes:
        message: Mensaje de error
        details: Contexto adicional
        url: URL que causó el error (si está disponible)
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, url: Optional[str] = None):
        """Inicializa el error de servicio.
        
        Args:
            message: Mensaje de error descriptivo
            details: Diccionario con información adicional
            url: URL del servicio que causó el error
        """
        super().__init__(message, details)
        self.url = url
        if url:
            self.details["url"] = url


class ServiceConnectionError(ServiceError):
    """Error de conexión con el servicio de geocodificación.
    
    Se lanza cuando no se puede establecer conexión con el servidor:
    - Servidor no disponible
    - Problemas de red
    - DNS no resuelve
    
    Example:
        raise ServiceConnectionError(
            "Error de conexión tras 4 intentos",
            url="https://geocoder.example.com/v1/search"
        )
    """
    pass


class ServiceTimeoutError(ServiceError):
    """Timeout en la petición al servicio de geocodificación.
    
    Se lanza cuando la petición excede el tiempo máximo de espera:
    - Servidor muy lento
    - Red congestionada
    - Timeout configurado muy bajo
    
    Example:
        raise ServiceTimeoutError(
            "Timeout después de 5s (4 intentos)",
            url="https://geocoder.example.com/v1/search",
            details={"timeout": 5, "attempts": 4}
        )
    """
    pass


class ServiceHTTPError(ServiceError):
    """Error HTTP del servicio de geocodificación.
    
    Se lanza cuando el servidor responde con un código de error HTTP:
    - 4xx: Errores del cliente (petición inválida)
    - 5xx: Errores del servidor
    
    Attributes:
        status_code: Código de estado HTTP
        response_text: Texto de la respuesta del servidor
    
    Example:
        raise ServiceHTTPError(
            "Error HTTP 404 en búsqueda",
            url="https://geocoder.example.com/v1/search",
            status_code=404,
            response_text="Not Found"
        )
    """
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ):
        """Inicializa el error HTTP.
        
        Args:
            message: Mensaje de error descriptivo
            url: URL que causó el error
            details: Contexto adicional
            status_code: Código de estado HTTP
            response_text: Texto de la respuesta del servidor
        """
        super().__init__(message, details, url)
        self.status_code = status_code
        self.response_text = response_text
        
        if status_code is not None:
            self.details["status_code"] = status_code
        if response_text:
            self.details["response_text"] = response_text[:200]  # Limitar longitud
