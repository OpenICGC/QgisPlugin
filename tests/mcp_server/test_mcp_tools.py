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
    mock_geofinder.autocomplete.return_value = [{"nom": "Sugerencia"}]

    results = await autocomplete.fn(partial_text="Barc")

    assert len(results) == 1
    assert results[0]["nom"] == "Sugerencia"
    mock_geofinder.autocomplete.assert_called_once_with("Barc", size=10)

@pytest.mark.asyncio
async def test_find_reverse_success(mock_geofinder):
    mock_geofinder.find_reverse.return_value = [{"nom": "Lugar"}]

    results = await find_reverse.fn(longitude=2.0, latitude=41.0)

    assert len(results) == 1
    mock_geofinder.find_reverse.assert_called_once()

@pytest.mark.asyncio
async def test_find_by_coordinates_success(mock_geofinder):
    mock_geofinder.find_point_coordinate_icgc.return_value = [{"nom": "Punto"}]

    results = await find_by_coordinates.fn(x=430000, y=4580000)

    assert len(results) == 1
    mock_geofinder.find_point_coordinate_icgc.assert_called_once()

@pytest.mark.asyncio
async def test_find_address_success(mock_geofinder):
    mock_geofinder.find_address.return_value = [{"nom": "Calle 1"}]

    results = await find_address.fn(street="Diagonal", number="100", municipality="Barcelona")

    assert len(results) == 1
    mock_geofinder.find_address.assert_called_once_with("Barcelona", "Carrer", "Diagonal", "100")

@pytest.mark.asyncio
async def test_find_road_km_success(mock_geofinder):
    mock_geofinder.find_road.return_value = [{"nom": "C-32 km 10"}]

    results = await find_road_km.fn(road="C-32", kilometer=10.0)

    assert len(results) == 1
    mock_geofinder.find_road.assert_called_once_with("C-32", "10")

@pytest.mark.asyncio
async def test_search_nearby_success(mock_geofinder):
    mock_geofinder.search_nearby.return_value = [{"nom": "Cerca"}]

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
