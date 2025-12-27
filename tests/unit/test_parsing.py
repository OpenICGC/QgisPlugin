import sys
from pathlib import Path

import pytest

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geofinder import GeoFinder


@pytest.mark.asyncio
async def test_parse_address_robustness():
    """Prueba el nuevo motor de parseo de direcciones con varios formatos."""
    gf = GeoFinder()

    # Lista de direcciones y los resultados esperados (municipio, tipo, calle, numero)
    test_cases = [
        ("Barcelona, Diagonal 100", ("Barcelona", None, "Diagonal", "100")),
        ("C/ Aragó 50, Barcelona", ("Barcelona", "C/", "Aragó", "50")),
        ("Gran Via 123, Barcelona", ("Barcelona", None, "Gran Via", "123")),
        ("Passeig de Gràcia s/n, Barcelona", ("Barcelona", None, "Passeig de Gràcia", "s/n")),
        ("Gran Via de les Corts Catalanes 585 Barcelona", ("Barcelona", None, "Gran Via de les Corts Catalanes", "585")),
        ("Balmes 123", ("", None, "Balmes", "123")),
        ("Av. Diagonal 640", ("", "Av.", "Diagonal", "640")),
        ("Carrer d'Aribau, 10, Barcelona", ("Barcelona", None, "Carrer d'Aribau", "10")),
    ]

    for text, expected in test_cases:
        result = gf._parse_address(text)
        assert result == expected, f"Fallo en: {text}. Esperado {expected}, obtenido {result}"

@pytest.mark.asyncio
async def test_find_with_size():
    """Verifica que el parámetro size limita los resultados."""
    gf = GeoFinder()

    # Buscar algo que devuelva muchos resultados (ej: 'Barcelona')
    results_5 = await gf.find("Barcelona", size=5)
    assert len(results_5) <= 5

    results_1 = await gf.find("Barcelona", size=1)
    assert len(results_1) == 1

    await gf.close()

@pytest.mark.asyncio
async def test_response_performance_metadata():
    """Verifica que GeoResponse incluye el tiempo de ejecución."""
    gf = GeoFinder()

    response = await gf.find_response("Montserrat")
    assert response.time_ms is not None
    assert response.time_ms > 0

    # También en find_reverse_response
    response_rev = await gf.find_reverse_response(2.17, 41.38, epsg=4326)
    assert response_rev.time_ms is not None

    await gf.close()
