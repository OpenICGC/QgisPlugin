import json
import logging
import contextvars
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# Context variable para correlation_id (permite trazar peticiones en entornos async)
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


def set_correlation_id(correlation_id: str) -> None:
    """
    Establece el correlation_id para la petición actual.
    
    Útil para trazar peticiones en sistemas distribuidos.
    
    Args:
        correlation_id: Identificador único de la petición
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """
    Obtiene el correlation_id de la petición actual.
    
    Returns:
        El correlation_id o None si no está establecido
    """
    return correlation_id_var.get()


def _get_reserved_fields() -> set[str]:
    """
    Obtiene dinámicamente los campos reservados de LogRecord.
    
    Más robusto que hardcodear, ya que se adapta a futuras versiones de Python.
    
    Returns:
        Set con los nombres de campos reservados
    """
    # Campos base conocidos (siempre presentes)
    base_fields = {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName"
    }
    
    # Añadir __slots__ si existe (Python 3.11+)
    if hasattr(logging.LogRecord, "__slots__"):
        base_fields.update(logging.LogRecord.__slots__)
    
    return base_fields


class StructuredJSONFormatter(logging.Formatter):
    """
    Formateador de logs en formato JSON para mejor observabilidad.
    
    Características:
    - Serialización robusta con fallback para tipos no serializables
    - Soporte para correlation_id (trazabilidad distribuida)
    - Detección dinámica de campos reservados
    - Captura de excepciones con stack trace
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._reserved_fields = _get_reserved_fields()

    def _serialize_value(self, value: Any) -> Any:
        """
        Serializa un valor de forma segura, con fallback a string.
        
        Args:
            value: Valor a serializar
            
        Returns:
            Valor serializable (original o convertido a string)
        """
        # Tipos primitivos JSON-safe
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        
        # Listas y diccionarios: intentar serializar recursivamente
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        
        # Datetime: convertir a ISO format
        if isinstance(value, datetime):
            return value.isoformat()
        
        # Objetos Pydantic: usar model_dump si está disponible
        if hasattr(value, "model_dump"):
            try:
                return value.model_dump()
            except Exception:
                pass
        
        # Fallback: convertir a string
        try:
            return str(value)
        except Exception:
            return f"<unserializable: {type(value).__name__}>"

    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea el registro de log como una cadena JSON.

        Args:
            record: El registro de log a formatear.

        Returns:
            str: Representación JSON del log.
        """
        # Datos estándar del log
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno,
        }

        # Añadir correlation_id si está disponible
        corr_id = get_correlation_id()
        if corr_id:
            log_data["correlation_id"] = corr_id

        # Añadir información de excepción si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Añadir campos extra si existen (con serialización segura)
        for key, value in record.__dict__.items():
            if key not in self._reserved_fields and not key.startswith("_"):
                log_data[key] = self._serialize_value(value)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    level: int = logging.INFO,
    json_format: bool = False,
    logger_name: str = "geofinder"
) -> logging.Logger:
    """
    Configura el sistema de logging para el proyecto.

    Args:
        level: Nivel de logging (default: logging.INFO)
        json_format: Si es True, usa StructuredJSONFormatter
        logger_name: Nombre del logger raíz para el proyecto

    Returns:
        logging.Logger: Logger configurado
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Evitar duplicar manejadores si ya están configurados
    if not logger.handlers:
        handler = logging.StreamHandler()
        
        if json_format:
            formatter = StructuredJSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
