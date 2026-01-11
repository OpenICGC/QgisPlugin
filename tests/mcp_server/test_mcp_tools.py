import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from geofinder.exceptions import (
    CoordinateError,
    GeoFinderError,
    ParsingError,
    ServiceConnectionError,
    ServiceHTTPError,
    ServiceTimeoutError,
)
from geofinder.mcp_server import (
    autocomplete,
    convert_geofinder_error,
    find_address,
    find_by_coordinates,
    find_place,
    find_reverse,
    find_road_km,
    lifespan,
    main,
    parse_search_query,
    search_nearby,
    transform_coordinates,
)
from geofinder.models import GeoResult


@pytest.fixture
def mock_geofinder():
    with patch("geofinder.mcp_server.get_geofinder") as mock:
        gf_instance = MagicMock()
        mock.return_value = gf_instance

        # Async methods
        gf_instance.find = AsyncMock()
        gf_instance.autocomplete = AsyncMock()
        gf_instance.find_reverse = AsyncMock()
        gf_instance.find_point_coordinate_icgc = AsyncMock()
        gf_instance.find_address = AsyncMock()
        gf_instance.find_road = AsyncMock()
        gf_instance.search_nearby = AsyncMock()
        gf_instance.close = AsyncMock()

        # Setup common sync methods
        gf_instance._parse_rectangle.return_value = (None, None, None, None, None)
        gf_instance._parse_point.return_value = (None, None, None)
        gf_instance._parse_road.return_value = (None, None)
        gf_instance._parse_address.return_value = (None, None, None, None)

        yield gf_instance

@pytest.mark.asyncio
async def test_find_place_success(mock_geofinder):
    mock_result = GeoResult(nom="Test", nomTipus="Tipo", x=1.0, y=2.0, epsg=4326)
    mock_geofinder.find.return_value = [mock_result]

    results = await find_place.fn(query="Barcelona")

    assert len(results) == 1
    assert results[0]["nom"] == "Test"
    mock_geofinder.find.assert_called_once_with("Barcelona", default_epsg=25831, size=5)

@pytest.mark.asyncio
async def test_find_place_validation_error():
    # Adjusted match to handle the wrapper message
    with pytest.raises(ValueError, match="Parámetros inválidos"):
        await find_place.fn(query="  ")

@pytest.mark.asyncio
async def test_autocomplete_success(mock_geofinder):
    mock_geofinder.autocomplete.return_value = [GeoResult(nom="Sugerencia", nomTipus="Tipo", x=1.0, y=2.0, epsg=4326)]

    results = await autocomplete.fn(partial_text="Barc")

    assert len(results) == 1
    assert results[0]["nom"] == "Sugerencia"
    mock_geofinder.autocomplete.assert_called_once_with("Barc", size=10)

@pytest.mark.asyncio
async def test_find_reverse_success(mock_geofinder):
    mock_geofinder.find_reverse.return_value = [GeoResult(nom="Lugar", nomTipus="Tipo", x=2.0, y=41.0, epsg=4326)]

    results = await find_reverse.fn(longitude=2.0, latitude=41.0)

    assert len(results) == 1
    mock_geofinder.find_reverse.assert_called_once()

@pytest.mark.asyncio
async def test_find_by_coordinates_success(mock_geofinder):
    mock_geofinder.find_point_coordinate_icgc.return_value = [GeoResult(nom="Punto", nomTipus="Tipo", x=2.0, y=41.0, epsg=4326)]

    results = await find_by_coordinates.fn(x=430000, y=4580000)

    assert len(results) == 1
    mock_geofinder.find_point_coordinate_icgc.assert_called_once()

@pytest.mark.asyncio
async def test_find_address_success(mock_geofinder):
    mock_geofinder.find_address.return_value = [GeoResult(nom="Calle 1", nomTipus="Adreça", x=2.0, y=41.0, epsg=4326, nomMunicipi="Bcn")]

    results = await find_address.fn(street="Diagonal", number="100", municipality="Barcelona")

    assert len(results) == 1
    mock_geofinder.find_address.assert_called_once_with("Barcelona", "Carrer", "Diagonal", "100")

@pytest.mark.asyncio
async def test_find_road_km_success(mock_geofinder):
    mock_geofinder.find_road.return_value = [GeoResult(nom="C-32 km 10", nomTipus="Punt quilomètric", x=2.0, y=41.0, epsg=4326)]

    results = await find_road_km.fn(road="C-32", kilometer=10.0)

    assert len(results) == 1
    mock_geofinder.find_road.assert_called_once_with("C-32", "10")

@pytest.mark.asyncio
async def test_search_nearby_success(mock_geofinder):
    mock_geofinder.search_nearby.return_value = [GeoResult(nom="Cerca", nomTipus="Tipo", x=2.0, y=41.0, epsg=4326)]

    results = await search_nearby.fn(place_name="Montserrat", radius_km=5.0)

    assert len(results) == 1
    mock_geofinder.search_nearby.assert_called_once_with("Montserrat", radius_km=5.0, layers="address,tops,pk", max_results=10)

def test_transform_coordinates_success():
    # Patch where it is defined, usually safer if local import is used
    with patch("geofinder.transformations.transform_point") as mock_transform:
        mock_transform.return_value = (430000, 4580000)

        result = transform_coordinates.fn(x=2.0, y=41.0, from_epsg=4326, to_epsg=25831)

        assert result["success"] is True
        assert result["x"] == 430000
        mock_transform.assert_called_once_with(2.0, 41.0, 4326, 25831)

def test_parse_search_query_coordinate(mock_geofinder):
    mock_geofinder._parse_point.return_value = (2.0, 41.0, 4326)

    result = parse_search_query.fn("2.0 41.0")

    assert result["query_type"] == "coordinate"
    assert result["details"]["x"] == 2.0

def test_parse_search_query_rectangle(mock_geofinder):
    mock_geofinder._parse_rectangle.return_value = (1.0, 42.0, 2.0, 41.0, 4326)

    result = parse_search_query.fn("1.0 42.0 2.0 41.0")

    assert result["query_type"] == "rectangle"
    assert result["details"]["west"] == 1.0

def test_parse_search_query_road(mock_geofinder):
    mock_geofinder._parse_road.return_value = ("C-32", "10")

    result = parse_search_query.fn("C-32 km 10")

    assert result["query_type"] == "road"
    assert result["details"]["road"] == "C-32"

def test_parse_search_query_address(mock_geofinder):
    mock_geofinder._parse_address.return_value = ("Barcelona", "Carrer", "Diagonal", "100")

    result = parse_search_query.fn("Barcelona, Diagonal 100")

    assert result["query_type"] == "address"

def test_parse_search_query_placename(mock_geofinder):
    result = parse_search_query.fn("Montserrat")
    assert result["query_type"] == "placename"

def test_convert_geofinder_error():
    assert isinstance(convert_geofinder_error(ParsingError("err")), ValueError)
    assert isinstance(convert_geofinder_error(CoordinateError("err")), ValueError)
    assert isinstance(convert_geofinder_error(ServiceTimeoutError("err")), TimeoutError)
    assert isinstance(convert_geofinder_error(ServiceConnectionError("err")), ConnectionError)
    assert isinstance(convert_geofinder_error(ServiceHTTPError("err", status_code=400)), ValueError)
    assert isinstance(convert_geofinder_error(ServiceHTTPError("err", status_code=500)), RuntimeError)
    assert isinstance(convert_geofinder_error(GeoFinderError("err")), RuntimeError)

    orig_err = Exception("other")
    assert convert_geofinder_error(orig_err) is orig_err

@pytest.mark.asyncio
async def test_lifespan(mock_geofinder):
    with patch("geofinder.mcp_server._geofinder_instance", mock_geofinder):
        async with lifespan(None):
            pass

    mock_geofinder.close.assert_awaited_once()

def test_main_help():
    with patch("argparse.ArgumentParser.parse_args") as mock_args, \
         patch("geofinder.mcp_server.mcp.run") as mock_run:

        mock_args.return_value = argparse.Namespace(
            transport="stdio", host="127.0.0.1", port=8000, log_level=None
        )

        main()

        mock_run.assert_called_once_with(transport="stdio")

def test_main_http():
    with patch("argparse.ArgumentParser.parse_args") as mock_args, \
         patch("geofinder.mcp_server.mcp.run") as mock_run:

        mock_args.return_value = argparse.Namespace(
            transport="http", host="1.2.3.4", port=9000, log_level="DEBUG"
        )

        main()

        mock_run.assert_called_once_with(
            transport="http", host="1.2.3.4", port=9000, log_level="DEBUG"
        )

@pytest.mark.asyncio
async def test_find_place_geofinder_error(mock_geofinder):
    mock_geofinder.find.side_effect = ServiceTimeoutError("Timeout")

    with pytest.raises(TimeoutError):
        await find_place.fn(query="Barcelona")

@pytest.mark.asyncio
async def test_find_place_unexpected_error(mock_geofinder):
    mock_geofinder.find.side_effect = Exception("Unexpected")

    with pytest.raises(Exception, match="Unexpected"):
        await find_place.fn(query="Barcelona")


# ============================================================================
# Tests de Validación de Parámetros
# ============================================================================

@pytest.mark.asyncio
async def test_autocomplete_validation_error():
    """Test que autocomplete rechaza texto vacío."""
    with pytest.raises(ValueError, match="Parámetros inválidos"):
        await autocomplete.fn(partial_text="  ")


@pytest.mark.asyncio
async def test_find_reverse_validation_error():
    """Test que find_reverse rechaza EPSG inválido."""
    with pytest.raises(ValueError, match="Parámetros inválidos"):
        await find_reverse.fn(longitude=2.0, latitude=41.0, epsg=999)


@pytest.mark.asyncio
async def test_find_by_coordinates_validation_error():
    """Test que find_by_coordinates rechaza radio negativo."""
    with pytest.raises(ValueError, match="Parámetros inválidos"):
        await find_by_coordinates.fn(x=430000, y=4580000, search_radius_km=-1)


@pytest.mark.asyncio
async def test_find_address_validation_error():
    """Test que find_address rechaza calle vacía."""
    with pytest.raises(ValueError, match="Parámetros inválidos"):
        await find_address.fn(street="  ", number="100")


@pytest.mark.asyncio
async def test_find_road_km_validation_error():
    """Test que find_road_km rechaza carretera vacía."""
    with pytest.raises(ValueError, match="Parámetros inválidos"):
        await find_road_km.fn(road="  ", kilometer=10.0)


@pytest.mark.asyncio
async def test_search_nearby_validation_error():
    """Test que search_nearby rechaza lugar vacío."""
    with pytest.raises(ValueError, match="Parámetros inválidos"):
        await search_nearby.fn(place_name="  ")


# ============================================================================
# Tests de Manejo de Errores de GeoFinder
# ============================================================================

@pytest.mark.asyncio
async def test_autocomplete_geofinder_error(mock_geofinder):
    """Test que autocomplete convierte errores de GeoFinder correctamente."""
    mock_geofinder.autocomplete.side_effect = ServiceTimeoutError("Timeout")

    with pytest.raises(TimeoutError):
        await autocomplete.fn(partial_text="Barc")


@pytest.mark.asyncio
async def test_autocomplete_unexpected_error(mock_geofinder):
    """Test que autocomplete propaga errores inesperados."""
    mock_geofinder.autocomplete.side_effect = Exception("Unexpected")

    with pytest.raises(Exception, match="Unexpected"):
        await autocomplete.fn(partial_text="Barc")


@pytest.mark.asyncio
async def test_find_reverse_geofinder_error(mock_geofinder):
    """Test que find_reverse convierte errores de GeoFinder correctamente."""
    mock_geofinder.find_reverse.side_effect = ServiceConnectionError("Connection failed")

    with pytest.raises(ConnectionError):
        await find_reverse.fn(longitude=2.0, latitude=41.0)


@pytest.mark.asyncio
async def test_find_reverse_unexpected_error(mock_geofinder):
    """Test que find_reverse propaga errores inesperados."""
    mock_geofinder.find_reverse.side_effect = Exception("Unexpected")

    with pytest.raises(Exception, match="Unexpected"):
        await find_reverse.fn(longitude=2.0, latitude=41.0)


@pytest.mark.asyncio
async def test_find_by_coordinates_geofinder_error(mock_geofinder):
    """Test que find_by_coordinates convierte errores de GeoFinder correctamente."""
    mock_geofinder.find_point_coordinate_icgc.side_effect = CoordinateError("Invalid coords")

    with pytest.raises(ValueError, match="Coordenadas inválidas"):
        await find_by_coordinates.fn(x=430000, y=4580000)


@pytest.mark.asyncio
async def test_find_by_coordinates_unexpected_error(mock_geofinder):
    """Test que find_by_coordinates propaga errores inesperados."""
    mock_geofinder.find_point_coordinate_icgc.side_effect = Exception("Unexpected")

    with pytest.raises(Exception, match="Unexpected"):
        await find_by_coordinates.fn(x=430000, y=4580000)


@pytest.mark.asyncio
async def test_find_address_geofinder_error(mock_geofinder):
    """Test que find_address convierte errores de GeoFinder correctamente."""
    mock_geofinder.find_address.side_effect = ParsingError("Invalid address")

    with pytest.raises(ValueError, match="Formato de búsqueda inválido"):
        await find_address.fn(street="Diagonal", number="100", municipality="Barcelona")


@pytest.mark.asyncio
async def test_find_address_unexpected_error(mock_geofinder):
    """Test que find_address propaga errores inesperados."""
    mock_geofinder.find_address.side_effect = Exception("Unexpected")

    with pytest.raises(Exception, match="Unexpected"):
        await find_address.fn(street="Diagonal", number="100", municipality="Barcelona")


@pytest.mark.asyncio
async def test_find_road_km_geofinder_error(mock_geofinder):
    """Test que find_road_km convierte errores de GeoFinder correctamente."""
    mock_geofinder.find_road.side_effect = ServiceHTTPError("Server error", status_code=503)

    with pytest.raises(RuntimeError, match="Error del servicio ICGC"):
        await find_road_km.fn(road="C-32", kilometer=10.0)


@pytest.mark.asyncio
async def test_find_road_km_unexpected_error(mock_geofinder):
    """Test que find_road_km propaga errores inesperados."""
    mock_geofinder.find_road.side_effect = Exception("Unexpected")

    with pytest.raises(Exception, match="Unexpected"):
        await find_road_km.fn(road="C-32", kilometer=10.0)


@pytest.mark.asyncio
async def test_search_nearby_geofinder_error(mock_geofinder):
    """Test que search_nearby convierte errores de GeoFinder correctamente."""
    mock_geofinder.search_nearby.side_effect = GeoFinderError("Generic error")

    with pytest.raises(RuntimeError, match="Error de geocodificación"):
        await search_nearby.fn(place_name="Montserrat")


@pytest.mark.asyncio
async def test_search_nearby_unexpected_error(mock_geofinder):
    """Test que search_nearby propaga errores inesperados."""
    mock_geofinder.search_nearby.side_effect = Exception("Unexpected")

    with pytest.raises(Exception, match="Unexpected"):
        await search_nearby.fn(place_name="Montserrat")


# ============================================================================
# Tests de Lifespan y Casos Edge
# ============================================================================

@pytest.mark.asyncio
async def test_lifespan_no_instance():
    """Test que lifespan maneja correctamente cuando no hay instancia."""
    with patch("geofinder.mcp_server._geofinder_instance", None):
        async with lifespan(None):
            pass
    # No debe lanzar excepción


@pytest.mark.asyncio
async def test_lifespan_close_error(mock_geofinder):
    """Test que lifespan maneja errores al cerrar."""
    mock_geofinder.close.side_effect = Exception("Close error")

    with patch("geofinder.mcp_server._geofinder_instance", mock_geofinder):
        # No debe lanzar excepción, solo loggear el error
        async with lifespan(None):
            pass

    mock_geofinder.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_road_km_decimal_kilometer(mock_geofinder):
    """Test que find_road_km maneja kilómetros decimales correctamente."""
    mock_geofinder.find_road.return_value = [
        GeoResult(nom="C-32 km 10.5", nomTipus="Punt quilomètric", x=2.0, y=41.0, epsg=4326)
    ]

    results = await find_road_km.fn(road="C-32", kilometer=10.5)

    assert len(results) == 1
    mock_geofinder.find_road.assert_called_once_with("C-32", "10.5")


def test_convert_geofinder_error_configuration():
    """Test que convert_geofinder_error maneja ConfigurationError."""
    from geofinder.exceptions import ConfigurationError
    err = ConfigurationError("Config error")
    result = convert_geofinder_error(err)
    assert isinstance(result, RuntimeError)
    assert "configuración" in str(result)
