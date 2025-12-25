import pytest
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geofinder.models import GeoResult
from geofinder.exceptions import CoordinateError

def test_georesult_coordinate_validation():
    """Verifica que GeoResult valida correctamente los rangos de WGS84."""
    # Coordenadas válidas
    r = GeoResult(nom="Test", x=2.0, y=41.0, epsg=4326)
    assert r.x == 2.0
    
    # Longitud fuera de rango
    with pytest.raises(CoordinateError, match="Longitud fuera de rango"):
        GeoResult(nom="Test", x=200.0, y=41.0, epsg=4326)
        
    # Latitud fuera de rango
    with pytest.raises(CoordinateError, match="Latitud fuera de rango"):
        GeoResult(nom="Test", x=2.0, y=100.0, epsg=4326)
        
    # Otros EPSG no deberían disparar esta validación específica
    r2 = GeoResult(nom="Test", x=1000000, y=1000000, epsg=25831)
    assert r2.x == 1000000

def test_georesult_restricted_access():
    """Verifica que __getitem__ está restringido solo a campos de datos."""
    r = GeoResult(nom="Test", x=2.0, y=41.0, epsg=4326)
    
    # Acceso válido
    assert r["nom"] == "Test"
    assert r["x"] == 2.0
    
    # Acceso inválido a métodos o campos inexistentes
    with pytest.raises(KeyError, match="is_in_catalonia"):
        _ = r["is_in_catalonia"]
        
    with pytest.raises(KeyError, match="non_existent"):
        _ = r["non_existent"]

def test_backward_compatibility_get():
    """Verifica que .get() sigue funcionando."""
    r = GeoResult(nom="Test", x=2.0, y=41.0, epsg=4326)
    assert r.get("nom") == "Test"
    assert r.get("unknown", "default") == "default"
