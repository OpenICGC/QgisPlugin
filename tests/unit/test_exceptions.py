#!/usr/bin/env python
"""
Tests para la jerarquía de excepciones personalizada de GeoFinder.

Verifica que todas las excepciones heredan correctamente, incluyen contexto
apropiado y formatean los mensajes correctamente.
"""

import sys
from pathlib import Path

import pytest

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geofinder.exceptions import (
    ConfigurationError,
    CoordinateError,
    GeoFinderError,
    ParsingError,
    ServiceConnectionError,
    ServiceError,
    ServiceHTTPError,
    ServiceTimeoutError,
)


class TestExceptionHierarchy:
    """Tests para verificar la jerarquía de excepciones."""

    def test_all_exceptions_inherit_from_base(self):
        """Verifica que todas las excepciones heredan de GeoFinderError."""
        assert issubclass(ConfigurationError, GeoFinderError)
        assert issubclass(ParsingError, GeoFinderError)
        assert issubclass(CoordinateError, GeoFinderError)
        assert issubclass(ServiceError, GeoFinderError)
        assert issubclass(ServiceConnectionError, ServiceError)
        assert issubclass(ServiceTimeoutError, ServiceError)
        assert issubclass(ServiceHTTPError, ServiceError)

    def test_service_exceptions_inherit_from_service_error(self):
        """Verifica que las excepciones de servicio heredan de ServiceError."""
        assert issubclass(ServiceConnectionError, ServiceError)
        assert issubclass(ServiceTimeoutError, ServiceError)
        assert issubclass(ServiceHTTPError, ServiceError)

    def test_catch_all_with_base_exception(self):
        """Verifica que se puede capturar cualquier excepción con GeoFinderError."""
        exceptions = [
            ConfigurationError("test"),
            ParsingError("test"),
            CoordinateError("test"),
            ServiceError("test"),
            ServiceConnectionError("test"),
            ServiceTimeoutError("test"),
            ServiceHTTPError("test"),
        ]

        for exc in exceptions:
            with pytest.raises(GeoFinderError):
                raise exc


class TestExceptionAttributes:
    """Tests para verificar atributos y formateo de excepciones."""

    def test_base_exception_with_message_only(self):
        """Verifica que GeoFinderError funciona solo con mensaje."""
        exc = GeoFinderError("Error de prueba")
        assert exc.message == "Error de prueba"
        assert exc.details == {}
        assert str(exc) == "Error de prueba"

    def test_base_exception_with_details(self):
        """Verifica que GeoFinderError incluye detalles en el mensaje."""
        exc = GeoFinderError("Error de prueba", details={"key": "value", "num": 42})
        assert exc.message == "Error de prueba"
        assert exc.details == {"key": "value", "num": 42}
        assert "key=value" in str(exc)
        assert "num=42" in str(exc)

    def test_configuration_error_with_details(self):
        """Verifica que ConfigurationError incluye detalles."""
        exc = ConfigurationError("URL inválida", details={"url": "invalid-url"})
        assert exc.message == "URL inválida"
        assert exc.details["url"] == "invalid-url"
        assert "url=invalid-url" in str(exc)

    def test_parsing_error_with_type_info(self):
        """Verifica que ParsingError incluye información de tipo."""
        exc = ParsingError(
            "Tipo incorrecto",
            details={"received_type": "int", "expected": "str"}
        )
        assert "received_type=int" in str(exc)
        assert "expected=str" in str(exc)

    def test_coordinate_error_with_coordinates(self):
        """Verifica que CoordinateError incluye coordenadas."""
        exc = CoordinateError(
            "Coordenadas fuera de rango",
            details={"x": 200, "y": 100, "epsg": 4326}
        )
        assert exc.details["x"] == 200
        assert exc.details["y"] == 100
        assert exc.details["epsg"] == 4326

    def test_service_error_with_url(self):
        """Verifica que ServiceError incluye URL."""
        exc = ServiceError(
            "Error de servicio",
            url="https://example.com/api",
            details={"status": "failed"}
        )
        assert exc.url == "https://example.com/api"
        assert exc.details["url"] == "https://example.com/api"
        assert exc.details["status"] == "failed"

    def test_service_http_error_with_status_code(self):
        """Verifica que ServiceHTTPError incluye código de estado."""
        exc = ServiceHTTPError(
            "Error HTTP",
            url="https://example.com/api",
            status_code=404,
            response_text="Not Found"
        )
        assert exc.status_code == 404
        assert exc.response_text == "Not Found"
        assert exc.details["status_code"] == 404
        assert exc.details["response_text"] == "Not Found"

    def test_service_http_error_truncates_long_response(self):
        """Verifica que ServiceHTTPError trunca respuestas largas."""
        long_text = "x" * 500
        exc = ServiceHTTPError(
            "Error HTTP",
            url="https://example.com/api",
            status_code=500,
            response_text=long_text
        )
        # Debe truncar a 200 caracteres
        assert len(exc.details["response_text"]) == 200


class TestNewFeatures:
    """Tests para las nuevas funcionalidades añadidas en la auditoría."""

    def test_repr_without_details(self):
        """Verifica que __repr__() funciona sin detalles."""
        exc = ParsingError("Error de prueba")
        repr_str = repr(exc)
        assert "ParsingError" in repr_str
        assert "Error de prueba" in repr_str
        assert "details" not in repr_str

    def test_repr_with_details(self):
        """Verifica que __repr__() incluye detalles."""
        exc = CoordinateError("Coordenadas inválidas", details={"x": 100, "y": 200})
        repr_str = repr(exc)
        assert "CoordinateError" in repr_str
        assert "Coordenadas inválidas" in repr_str
        assert "details" in repr_str
        assert "100" in repr_str

    def test_to_dict_basic(self):
        """Verifica que to_dict() funciona correctamente."""
        exc = ConfigurationError("URL inválida", details={"url": "test"})
        result = exc.to_dict()

        assert result["type"] == "ConfigurationError"
        assert result["message"] == "URL inválida"
        assert result["details"]["url"] == "test"

    def test_to_dict_with_service_error(self):
        """Verifica que to_dict() incluye URL para ServiceError."""
        exc = ServiceError(
            "Error de servicio",
            url="https://example.com",
            details={"extra": "info"}
        )
        result = exc.to_dict()

        assert result["url"] == "https://example.com"
        assert result["details"]["url"] == "https://example.com"
        assert result["details"]["extra"] == "info"

    def test_to_dict_with_http_error(self):
        """Verifica que to_dict() incluye status_code y response_text."""
        exc = ServiceHTTPError(
            "Error HTTP",
            url="https://example.com/api",
            details=None,
            status_code=404,
            response_text="Not Found"
        )
        result = exc.to_dict()

        assert result["status_code"] == 404
        assert result["response_text"] == "Not Found"
        assert result["url"] == "https://example.com/api"

    def test_to_dict_handles_status_code_zero(self):
        """Verifica que to_dict() maneja status_code=0 correctamente."""
        exc = ServiceHTTPError(
            "Error HTTP",
            url="https://example.com",
            details=None,
            status_code=0,
            response_text="Connection reset"
        )
        result = exc.to_dict()

        # status_code=0 debe incluirse (es un valor válido)
        assert result["status_code"] == 0


class TestExceptionChaining:
    """Tests para verificar el encadenamiento de excepciones."""

    def test_exception_chaining_preserves_cause(self):
        """Verifica que el encadenamiento de excepciones preserva la causa."""
        original = ValueError("Error original")

        try:
            try:
                raise original
            except ValueError as e:
                raise ParsingError("Error de parseo", details={"original": str(e)}) from e
        except ParsingError as exc:
            assert exc.__cause__ is original
            assert isinstance(exc.__cause__, ValueError)

    def test_service_error_from_httpx_error(self):
        """Verifica que ServiceError puede encadenar errores de httpx."""
        import httpx

        original = httpx.ConnectError("Connection failed")

        try:
            try:
                raise original
            except httpx.ConnectError as e:
                raise ServiceConnectionError(
                    "Error de conexión",
                    url="https://example.com",
                    details={"error_type": type(e).__name__}
                ) from e
        except ServiceConnectionError as exc:
            assert exc.__cause__ is original
            assert exc.details["error_type"] == "ConnectError"


class TestBackwardCompatibility:
    """Tests para verificar compatibilidad con nombres antiguos."""

    def test_pelias_error_alias(self):
        """Verifica que PeliasError es un alias de ServiceError."""
        from geofinder import PeliasError
        assert PeliasError is ServiceError

    def test_pelias_connection_error_alias(self):
        """Verifica que PeliasConnectionError es un alias de ServiceConnectionError."""
        from geofinder import PeliasConnectionError
        assert PeliasConnectionError is ServiceConnectionError

    def test_pelias_timeout_error_alias(self):
        """Verifica que PeliasTimeoutError es un alias de ServiceTimeoutError."""
        from geofinder import PeliasTimeoutError
        assert PeliasTimeoutError is ServiceTimeoutError

    def test_can_catch_with_old_names(self):
        """Verifica que se pueden capturar excepciones con nombres antiguos."""
        from geofinder import PeliasConnectionError, PeliasError

        # Lanzar con nuevo nombre, capturar con nombre antiguo
        with pytest.raises(PeliasError):
            raise ServiceError("test")

        with pytest.raises(PeliasConnectionError):
            raise ServiceConnectionError("test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
