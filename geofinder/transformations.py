"""
Transformaciones de coordenadas entre sistemas de referencia.
Soporta GDAL (osr) y pyproj como backends intercambiables.
"""

import math

# Detectar backend disponible
_BACKEND = None

try:
    import osgeo.osr  # noqa: F401

    _BACKEND = "gdal"
except ImportError:
    try:
        import pyproj  # noqa: F401

        _BACKEND = "pyproj"
    except ImportError:
        pass


def get_backend():
    """Retorna el backend de transformación disponible.

    Returns:
        str: "gdal", "pyproj", o None si no hay ninguno disponible
    """
    return _BACKEND


def transform_point(x, y, source_epsg, destination_epsg):
    """Transforma un punto entre sistemas de referencia.

    Args:
        x: Coordenada X en el sistema origen
        y: Coordenada Y en el sistema origen
        source_epsg: Código EPSG del sistema origen
        destination_epsg: Código EPSG del sistema destino

    Returns:
        tuple: (x, y) en el sistema destino, o (None, None) si hay error

    Raises:
        ImportError: Si no hay backend disponible (GDAL o pyproj)
    """
    if str(source_epsg) == str(destination_epsg) and str(destination_epsg) != "4326":
        return x, y

    if _BACKEND == "gdal":
        return _transform_gdal(x, y, source_epsg, destination_epsg)
    elif _BACKEND == "pyproj":
        return _transform_pyproj(x, y, source_epsg, destination_epsg)
    else:
        raise ImportError(
            "Se requiere GDAL o pyproj para transformaciones de coordenadas. "
            "Instala uno de: pip install GDAL  o  pip install pyproj"
        )


def _transform_gdal(x, y, source_epsg, destination_epsg):
    """Transformación usando GDAL/OGR."""
    from osgeo import osr

    source_crs = osr.SpatialReference()
    source_crs.ImportFromEPSG(int(source_epsg))

    destination_crs = osr.SpatialReference()
    destination_crs.ImportFromEPSG(int(destination_epsg))

    # En GDAL 3+ para WGS84, usar CRS84 para mantener orden lon,lat
    if destination_epsg == 4326:
        destination_crs.SetWellKnownGeogCS("CRS84")

    ct = osr.CoordinateTransformation(source_crs, destination_crs)
    dest_x, dest_y, _ = ct.TransformPoint(x, y)

    return (None if math.isinf(dest_x) else dest_x, None if math.isinf(dest_y) else dest_y)


def _transform_pyproj(x, y, source_epsg, destination_epsg):
    """Transformación usando pyproj."""
    from pyproj import Transformer

    # Usar siempre EPSG codes con always_xy=True para orden lon,lat consistente
    # Esto evita problemas con CRS84 que no es reconocido por todas las versiones de pyproj
    transformer = Transformer.from_crs(
        f"EPSG:{source_epsg}",
        f"EPSG:{destination_epsg}",
        always_xy=True
    )
    dest_x, dest_y = transformer.transform(x, y)

    return (None if math.isinf(dest_x) else dest_x, None if math.isinf(dest_y) else dest_y)
