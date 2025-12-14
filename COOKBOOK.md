# 📚 GeoFinder Cookbook

> **Guía práctica con ejemplos de integración** para el geocodificador de Cataluña.

---

## 📋 Tabla de Contenidos

| Sección                                                     | Descripción                |
| ----------------------------------------------------------- | -------------------------- |
| [🚀 Ejemplos Básicos](#-ejemplos-básicos)                   | Primeros pasos y uso común |
| [🌐 Integración Web](#-integración-web)                     | Flask, FastAPI, Django     |
| [📊 Análisis de Datos](#-análisis-de-datos)                 | Pandas, GeoPandas          |
| [⚡ Geocodificación por Lotes](#-geocodificación-por-lotes) | Procesamiento masivo       |
| [🛡️ Manejo de Errores](#️-manejo-de-errores)                | Patrones robustos          |
| [💾 Caché y Rendimiento](#-caché-y-rendimiento)             | Optimización               |
| [🏢 Casos de Uso Reales](#-casos-de-uso-reales)             | Aplicaciones prácticas     |

---

## 🚀 Ejemplos Básicos

### Instalación

```bash
# Instalación básica
pip install -e .

# Con transformación de coordenadas
pip install -e ".[pyproj]"

# Con servidor MCP para IA
pip install -e ".[mcp,pyproj]"
```

### Búsqueda Simple

```python
from geofinder import GeoFinder

# Inicializar
gf = GeoFinder()

# Buscar un municipio
results = gf.find("Barcelona")
for r in results:
    print(f"{r['nom']} ({r['nomTipus']}) - {r['x']}, {r['y']}")
# Output: Barcelona (Municipi) - 2.1734, 41.3851
```

### Búsqueda con Diferentes Formatos

```python
from geofinder import GeoFinder

gf = GeoFinder()

# 1. Topónimo
results = gf.find("Montserrat")

# 2. Municipio + Calle + Número
results = gf.find("Barcelona, Diagonal 100")

# 3. Coordenadas UTM
results = gf.find("430000 4580000 EPSG:25831")

# 4. Punto kilométrico
results = gf.find("C-32 km 10")

# 5. Coordenadas GPS
results = gf.find("2.1734 41.3851 EPSG:4326")
```

### Geocodificación Inversa

```python
from geofinder import GeoFinder

gf = GeoFinder()

# Desde coordenadas GPS → información del lugar
results = gf.find_reverse(2.1734, 41.3851, epsg=4326)

for r in results:
    print(f"📍 {r['nom']}")
    print(f"   Municipio: {r.get('nomMunicipi', 'N/A')}")
    print(f"   Comarca: {r.get('nomComarca', 'N/A')}")
```

### Autocompletado

```python
from geofinder import GeoFinder

gf = GeoFinder()

# Sugerencias mientras el usuario escribe
suggestions = gf.autocomplete("Barcel", size=5)

for s in suggestions:
    print(f"💡 {s['nom']} - {s['nomTipus']}")
# Output:
# 💡 Barcelona - Municipi
# 💡 Barcelonès - Comarca
# 💡 Barcelona (Pl.) - Plaça
```

---

## 🌐 Integración Web

### Flask - API REST de Geocodificación

```python
"""
Servidor Flask para geocodificación.
Ejecutar: python app.py
Probar: curl http://localhost:5000/search?q=Barcelona
"""
from flask import Flask, request, jsonify
from geofinder import GeoFinder

app = Flask(__name__)
gf = GeoFinder()

@app.route('/search')
def search():
    """Búsqueda general de lugares."""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Parámetro 'q' requerido"}), 400

    try:
        results = gf.find(query)
        return jsonify({
            "query": query,
            "count": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/reverse')
def reverse():
    """Geocodificación inversa."""
    try:
        x = float(request.args.get('x', 0))
        y = float(request.args.get('y', 0))
        epsg = int(request.args.get('epsg', 4326))
    except ValueError:
        return jsonify({"error": "Parámetros inválidos"}), 400

    results = gf.find_reverse(x, y, epsg=epsg)
    return jsonify({
        "coordinates": {"x": x, "y": y, "epsg": epsg},
        "results": results
    })


@app.route('/autocomplete')
def autocomplete():
    """Sugerencias de autocompletado."""
    text = request.args.get('text', '')
    size = min(int(request.args.get('size', 10)), 20)  # Máx 20

    results = gf.autocomplete(text, size=size)
    return jsonify({
        "query": text,
        "suggestions": [r['nom'] for r in results]
    })


if __name__ == '__main__':
    app.run(debug=True)
```

### FastAPI - API Asíncrona

```python
"""
Servidor FastAPI para geocodificación.
Ejecutar: uvicorn app:app --reload
Docs automáticas: http://localhost:8000/docs
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from geofinder import GeoFinder
from typing import Optional

app = FastAPI(
    title="GeoFinder API",
    description="API de geocodificación para Cataluña",
    version="1.0.0"
)

# Instancia compartida
gf = GeoFinder()


class GeoResult(BaseModel):
    nom: str
    nomTipus: str
    nomMunicipi: Optional[str] = None
    nomComarca: Optional[str] = None
    x: float
    y: float
    epsg: int


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[dict]


@app.get("/search", response_model=SearchResponse, tags=["Geocoding"])
def search(
    q: str = Query(..., description="Texto de búsqueda"),
    epsg: int = Query(25831, description="Sistema de referencia por defecto")
):
    """
    Busca lugares, direcciones y coordenadas.

    Formatos soportados:
    - Topónimos: "Barcelona", "Montserrat"
    - Direcciones: "Barcelona, Diagonal 100"
    - Coordenadas: "430000 4580000 EPSG:25831"
    - Carreteras: "C-32 km 10"
    """
    try:
        results = gf.find(q, default_epsg=epsg)
        return {"query": q, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reverse", tags=["Geocoding"])
def reverse(
    x: float = Query(..., description="Coordenada X (longitud si EPSG:4326)"),
    y: float = Query(..., description="Coordenada Y (latitud si EPSG:4326)"),
    epsg: int = Query(4326, description="Sistema de referencia de entrada"),
    layers: str = Query("address,tops", description="Capas a buscar"),
    size: int = Query(5, ge=1, le=20, description="Máx resultados")
):
    """Geocodificación inversa: coordenadas → información del lugar."""
    results = gf.find_reverse(x, y, epsg=epsg, layers=layers, size=size)
    return {
        "input": {"x": x, "y": y, "epsg": epsg},
        "results": results
    }


@app.get("/autocomplete", tags=["Suggestions"])
def autocomplete(
    text: str = Query(..., min_length=2, description="Texto parcial"),
    size: int = Query(10, ge=1, le=20, description="Máx sugerencias")
):
    """Sugerencias de autocompletado para búsquedas."""
    results = gf.autocomplete(text, size=size)
    return {
        "query": text,
        "suggestions": [{"name": r['nom'], "type": r['nomTipus']} for r in results]
    }
```

### Django - Vista de Geocodificación

```python
# views.py
from django.http import JsonResponse
from django.views import View
from geofinder import GeoFinder


class GeocoderView(View):
    """Vista Django para geocodificación."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gf = GeoFinder()

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        if not query:
            return JsonResponse({'error': 'Parámetro q requerido'}, status=400)

        results = self.gf.find(query)
        return JsonResponse({
            'query': query,
            'results': results
        })


# urls.py
from django.urls import path
from .views import GeocoderView

urlpatterns = [
    path('api/geocode/', GeocoderView.as_view(), name='geocode'),
]
```

---

## 📊 Análisis de Datos

### Pandas - Geocodificar DataFrame

```python
"""
Geocodificar un DataFrame de direcciones.
"""
import pandas as pd
from geofinder import GeoFinder

# Datos de ejemplo
data = {
    'id': [1, 2, 3, 4],
    'direccion': [
        'Barcelona, Diagonal 100',
        'Girona, Carrer Nou 50',
        'Lleida, Plaça Paeria 1',
        'Tarragona, Rambla Nova 100'
    ]
}
df = pd.DataFrame(data)

# Inicializar geocodificador
gf = GeoFinder()


def geocode_address(address: str) -> dict:
    """Geocodifica una dirección y devuelve coordenadas."""
    try:
        results = gf.find(address)
        if results:
            r = results[0]
            return {
                'lat': r['y'],
                'lon': r['x'],
                'municipio': r.get('nomMunicipi', ''),
                'comarca': r.get('nomComarca', ''),
                'tipo': r.get('nomTipus', '')
            }
    except Exception as e:
        print(f"Error geocodificando '{address}': {e}")
    return {'lat': None, 'lon': None, 'municipio': '', 'comarca': '', 'tipo': ''}


# Aplicar geocodificación
geo_data = df['direccion'].apply(geocode_address).apply(pd.Series)
df = pd.concat([df, geo_data], axis=1)

print(df)
#    id                       direccion       lat       lon  municipio     comarca       tipo
# 0   1          Barcelona, Diagonal 100  41.3851    2.1734  Barcelona  Barcelonès     Adreça
# 1   2             Girona, Carrer Nou 50  41.9831    2.8249     Girona    Gironès      Adreça
# ...
```

### GeoPandas - Crear GeoDataFrame

```python
"""
Crear un GeoDataFrame con geometrías para análisis espacial.
"""
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geofinder import GeoFinder

# Datos
lugares = ['Barcelona', 'Girona', 'Lleida', 'Tarragona', 'Reus', 'Figueres']

gf = GeoFinder()

# Geocodificar
data = []
for lugar in lugares:
    results = gf.find(lugar)
    if results:
        r = results[0]
        data.append({
            'nombre': r['nom'],
            'tipo': r['nomTipus'],
            'comarca': r.get('nomComarca', ''),
            'geometry': Point(r['x'], r['y'])
        })

# Crear GeoDataFrame
gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")

# Operaciones espaciales
print(f"Extensión: {gdf.total_bounds}")

# Guardar como GeoJSON
gdf.to_file("municipios_cataluña.geojson", driver="GeoJSON")

# Buffer de 10km alrededor de Barcelona
barcelona = gdf[gdf['nombre'] == 'Barcelona'].geometry.iloc[0]
buffer_10km = barcelona.buffer(0.1)  # ~10km en grados
```

### Visualización con Folium

```python
"""
Crear mapa interactivo con resultados geocodificados.
"""
import folium
from geofinder import GeoFinder

gf = GeoFinder()

# Geocodificar lugares de interés
lugares = [
    'Sagrada Família, Barcelona',
    'Park Güell, Barcelona',
    'Montserrat',
    'Costa Brava',
    'Delta de l\'Ebre'
]

# Crear mapa centrado en Cataluña
mapa = folium.Map(location=[41.5, 1.5], zoom_start=8)

for lugar in lugares:
    results = gf.find(lugar)
    if results:
        r = results[0]
        folium.Marker(
            location=[r['y'], r['x']],  # Folium usa lat, lon
            popup=f"<b>{r['nom']}</b><br>{r['nomTipus']}",
            tooltip=r['nom'],
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(mapa)

# Guardar mapa
mapa.save('mapa_cataluña.html')
print("Mapa guardado en mapa_cataluña.html")
```

---

## ⚡ Geocodificación por Lotes

### Procesamiento con Progreso

```python
"""
Geocodificar lista grande de direcciones con barra de progreso.
"""
from geofinder import GeoFinder
from tqdm import tqdm
import time

gf = GeoFinder()

direcciones = [
    'Barcelona, Passeig de Gràcia 43',
    'Girona, Rambla de la Llibertat 1',
    'Lleida, Avinguda Catalunya 12',
    # ... cientos de direcciones
]

resultados = []

for direccion in tqdm(direcciones, desc="Geocodificando"):
    try:
        results = gf.find(direccion)
        if results:
            resultados.append({
                'input': direccion,
                'output': results[0],
                'status': 'success'
            })
        else:
            resultados.append({
                'input': direccion,
                'output': None,
                'status': 'not_found'
            })
    except Exception as e:
        resultados.append({
            'input': direccion,
            'output': None,
            'status': 'error',
            'error': str(e)
        })

    # Respetar límites del servicio
    time.sleep(0.1)  # 100ms entre peticiones

# Estadísticas
success = sum(1 for r in resultados if r['status'] == 'success')
print(f"✅ Éxito: {success}/{len(direcciones)}")
```

### Procesamiento Paralelo (con cuidado)

```python
"""
Geocodificación paralela limitada para respetar el servicio.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from geofinder import GeoFinder
import time

# Crear múltiples instancias con timeouts
def create_geocoder():
    return GeoFinder(timeout=10)


def geocode_with_retry(direccion: str, max_retries: int = 3):
    """Geocodificar con reintentos."""
    gf = create_geocoder()
    for attempt in range(max_retries):
        try:
            results = gf.find(direccion)
            return {'input': direccion, 'result': results[0] if results else None}
        except Exception as e:
            if attempt == max_retries - 1:
                return {'input': direccion, 'result': None, 'error': str(e)}
            time.sleep(0.5 * (attempt + 1))  # Backoff


direcciones = [
    'Barcelona, Diagonal 1',
    'Barcelona, Diagonal 10',
    'Barcelona, Diagonal 100',
    # ... más direcciones
]

# Limitar a 3 workers para no sobrecargar el servicio
resultados = []
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(geocode_with_retry, d): d
        for d in direcciones
    }

    for future in as_completed(futures):
        resultado = future.result()
        resultados.append(resultado)
```

---

## 🛡️ Manejo de Errores

### Patrón Completo de Manejo de Errores

```python
"""
Ejemplo de manejo robusto de errores con GeoFinder.
"""
from geofinder import GeoFinder
from geofinder.pelias import (
    PeliasError,
    PeliasConnectionError,
    PeliasTimeoutError
)
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def geocode_safely(query: str, gf: GeoFinder = None) -> dict:
    """
    Geocodificar de forma segura con manejo completo de errores.

    Returns:
        dict con 'success', 'data' o 'error'
    """
    if gf is None:
        gf = GeoFinder()

    try:
        results = gf.find(query)

        if not results:
            return {
                'success': False,
                'error': 'NOT_FOUND',
                'message': f"No se encontraron resultados para '{query}'"
            }

        return {
            'success': True,
            'data': results[0],
            'total_results': len(results)
        }

    except PeliasTimeoutError as e:
        logger.warning(f"Timeout geocodificando '{query}': {e}")
        return {
            'success': False,
            'error': 'TIMEOUT',
            'message': 'El servicio tardó demasiado en responder',
            'retry': True
        }

    except PeliasConnectionError as e:
        logger.error(f"Error de conexión: {e}")
        return {
            'success': False,
            'error': 'CONNECTION_ERROR',
            'message': 'No se pudo conectar con el servicio ICGC',
            'retry': True
        }

    except PeliasError as e:
        logger.error(f"Error del servicio Pelias: {e}")
        return {
            'success': False,
            'error': 'SERVICE_ERROR',
            'message': str(e),
            'retry': False
        }

    except Exception as e:
        logger.exception(f"Error inesperado geocodificando '{query}'")
        return {
            'success': False,
            'error': 'UNEXPECTED_ERROR',
            'message': str(e),
            'retry': False
        }


# Uso
gf = GeoFinder(timeout=5)

result = geocode_safely("Barcelona", gf)
if result['success']:
    print(f"✅ {result['data']['nom']}: {result['data']['x']}, {result['data']['y']}")
else:
    print(f"❌ {result['error']}: {result['message']}")
    if result.get('retry'):
        print("   → Puedes reintentar esta operación")
```

### Validación de Entrada

```python
"""
Validar y normalizar entrada antes de geocodificar.
"""
import re
from typing import Optional, Tuple


def validate_address(address: str) -> Tuple[bool, Optional[str]]:
    """
    Valida y normaliza una dirección.

    Returns:
        (is_valid, normalized_address or error_message)
    """
    if not address or not isinstance(address, str):
        return False, "La dirección no puede estar vacía"

    # Normalizar espacios
    address = ' '.join(address.split())

    # Mínimo 3 caracteres
    if len(address) < 3:
        return False, "La dirección es demasiado corta"

    # Máximo 200 caracteres
    if len(address) > 200:
        return False, "La dirección es demasiado larga"

    # Detectar caracteres inválidos
    if re.search(r'[<>{}|\\^~\[\]]', address):
        return False, "La dirección contiene caracteres inválidos"

    return True, address


def validate_coordinates(
    x: float,
    y: float,
    epsg: int = 4326
) -> Tuple[bool, Optional[str]]:
    """
    Valida coordenadas según el sistema EPSG.
    """
    if epsg == 4326:  # WGS84
        # Cataluña aprox: lon 0.2-3.3, lat 40.5-42.8
        if not (0.0 <= x <= 4.0):
            return False, f"Longitud {x} fuera de rango para Cataluña"
        if not (39.0 <= y <= 43.0):
            return False, f"Latitud {y} fuera de rango para Cataluña"

    elif epsg == 25831:  # UTM 31N
        # Cataluña aprox: X 250000-550000, Y 4500000-4750000
        if not (200000 <= x <= 600000):
            return False, f"Coordenada X {x} fuera de rango UTM 31N"
        if not (4400000 <= y <= 4800000):
            return False, f"Coordenada Y {y} fuera de rango UTM 31N"

    return True, None


# Uso
address = "  Barcelona,   Diagonal 100  "
is_valid, result = validate_address(address)
if is_valid:
    print(f"Dirección válida: '{result}'")
    # Geocodificar...
else:
    print(f"Error: {result}")
```

---

## 💾 Caché y Rendimiento

### Caché en Memoria con functools

```python
"""
Caché simple en memoria para búsquedas frecuentes.
"""
from functools import lru_cache
from geofinder import GeoFinder
import json

# Instancia global
_gf = GeoFinder()


@lru_cache(maxsize=1000)
def geocode_cached(query: str) -> str:
    """
    Geocodificar con caché LRU.

    Nota: lru_cache requiere retorno hashable,
    por eso convertimos a JSON string.
    """
    results = _gf.find(query)
    return json.dumps(results) if results else "[]"


def geocode(query: str) -> list:
    """Interfaz pública que deserializa el resultado."""
    return json.loads(geocode_cached(query.lower().strip()))


# Uso
result1 = geocode("Barcelona")  # llama al servicio
result2 = geocode("Barcelona")  # usa caché
result3 = geocode("BARCELONA")  # usa caché (normalizado)

# Ver estadísticas de caché
print(geocode_cached.cache_info())
# CacheInfo(hits=2, misses=1, maxsize=1000, currsize=1)
```

### Caché Persistente con SQLite

```python
"""
Caché persistente usando SQLite para geocodificación.
"""
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from geofinder import GeoFinder
from typing import Optional


class GeoCache:
    """Caché de geocodificación con SQLite."""

    def __init__(self, db_path: str = "geocache.db", ttl_days: int = 30):
        self.db_path = db_path
        self.ttl_days = ttl_days
        self.gf = GeoFinder()
        self._init_db()

    def _init_db(self):
        """Crea la tabla de caché si no existe."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS geocache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created
                ON geocache(created_at)
            """)

    def _hash_query(self, query: str) -> str:
        """Genera hash único para la query."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, query: str) -> Optional[list]:
        """Obtiene resultado de caché si existe y es válido."""
        query_hash = self._hash_query(query)
        min_date = datetime.now() - timedelta(days=self.ttl_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT result FROM geocache
                WHERE query_hash = ? AND created_at > ?
                """,
                (query_hash, min_date.isoformat())
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def set(self, query: str, result: list):
        """Guarda resultado en caché."""
        query_hash = self._hash_query(query)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO geocache (query_hash, query, result)
                VALUES (?, ?, ?)
                """,
                (query_hash, query, json.dumps(result))
            )

    def geocode(self, query: str) -> list:
        """Geocodifica con caché."""
        # Intentar caché primero
        cached = self.get(query)
        if cached is not None:
            return cached

        # Llamar al servicio
        result = self.gf.find(query)

        # Guardar en caché
        if result:
            self.set(query, result)

        return result

    def clear_expired(self):
        """Elimina entradas expiradas."""
        min_date = datetime.now() - timedelta(days=self.ttl_days)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM geocache WHERE created_at < ?",
                (min_date.isoformat(),)
            )
            return cursor.rowcount

    def stats(self) -> dict:
        """Estadísticas de la caché."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM geocache")
            total = cursor.fetchone()[0]

            min_date = datetime.now() - timedelta(days=self.ttl_days)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM geocache WHERE created_at > ?",
                (min_date.isoformat(),)
            )
            valid = cursor.fetchone()[0]

        return {"total": total, "valid": valid, "expired": total - valid}


# Uso
cache = GeoCache(ttl_days=7)

result = cache.geocode("Barcelona")  # Llama al servicio
result = cache.geocode("Barcelona")  # Usa caché

print(cache.stats())
# {'total': 1, 'valid': 1, 'expired': 0}
```

---

## 🏢 Casos de Uso Reales

### 1. Validador de Direcciones Postales

```python
"""
Validar y enriquecer direcciones postales.
Útil para: ecommerce, logística, CRM.
"""
from geofinder import GeoFinder
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidatedAddress:
    """Dirección validada y enriquecida."""
    original: str
    is_valid: bool
    normalized: Optional[str] = None
    street: Optional[str] = None
    municipality: Optional[str] = None
    comarca: Optional[str] = None
    postal_code: Optional[str] = None  # Si está disponible
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: float = 0.0
    error: Optional[str] = None


class AddressValidator:
    """Validador de direcciones para Cataluña."""

    def __init__(self):
        self.gf = GeoFinder()

    def validate(self, address: str) -> ValidatedAddress:
        """Valida y enriquece una dirección."""
        try:
            results = self.gf.find(address)

            if not results:
                return ValidatedAddress(
                    original=address,
                    is_valid=False,
                    error="Dirección no encontrada"
                )

            best = results[0]

            # Determinar confianza según tipo
            confidence = 1.0 if best['nomTipus'] == 'Adreça' else 0.7

            return ValidatedAddress(
                original=address,
                is_valid=True,
                normalized=best['nom'],
                street=best.get('nomCarrer'),
                municipality=best.get('nomMunicipi'),
                comarca=best.get('nomComarca'),
                latitude=best['y'],
                longitude=best['x'],
                confidence=confidence
            )

        except Exception as e:
            return ValidatedAddress(
                original=address,
                is_valid=False,
                error=str(e)
            )


# Uso
validator = AddressValidator()

addresses = [
    "Barcelona, Passeig de Gràcia 43",
    "Girona, calle inventada 999",
    "Reus, Plaça del Mercadal 1"
]

for addr in addresses:
    result = validator.validate(addr)
    if result.is_valid:
        print(f"✅ {result.normalized}")
        print(f"   📍 {result.latitude}, {result.longitude}")
        print(f"   🏘️ {result.municipality}, {result.comarca}")
    else:
        print(f"❌ {addr}: {result.error}")
```

### 2. Buscador de Servicios Cercanos

```python
"""
Buscar servicios/ubicaciones cerca de un punto.
Útil para: apps de delivery, servicios a domicilio.
"""
from geofinder import GeoFinder
from geofinder.transformations import transform_point
from dataclasses import dataclass
from typing import List
import math


@dataclass
class NearbyResult:
    """Resultado de búsqueda cercana."""
    name: str
    type: str
    distance_km: float
    latitude: float
    longitude: float


class NearbySearch:
    """Buscador de ubicaciones cercanas."""

    def __init__(self):
        self.gf = GeoFinder()

    def search_near_place(
        self,
        place_name: str,
        radius_km: float = 1.0,
        max_results: int = 10
    ) -> List[NearbyResult]:
        """
        Busca lugares cerca de una ubicación nombrada.

        Args:
            place_name: Nombre del lugar de referencia
            radius_km: Radio de búsqueda en km
            max_results: Máximo de resultados
        """
        # Primero geocodificar el lugar de referencia
        ref_results = self.gf.find(place_name)
        if not ref_results:
            raise ValueError(f"No se encontró: {place_name}")

        ref = ref_results[0]
        ref_x, ref_y = ref['x'], ref['y']

        # Buscar lugares cercanos
        nearby = self.gf.find_reverse(
            ref_x, ref_y,
            epsg=4326,
            layers="address,tops,pk",
            size=max_results
        )

        results = []
        for place in nearby:
            # Calcular distancia
            dist = self._haversine(ref_y, ref_x, place['y'], place['x'])

            if dist <= radius_km:
                results.append(NearbyResult(
                    name=place['nom'],
                    type=place['nomTipus'],
                    distance_km=round(dist, 2),
                    latitude=place['y'],
                    longitude=place['x']
                ))

        # Ordenar por distancia
        return sorted(results, key=lambda x: x.distance_km)

    def _haversine(self, lat1, lon1, lat2, lon2) -> float:
        """Calcula distancia en km entre dos puntos."""
        R = 6371  # Radio de la Tierra en km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c


# Uso
searcher = NearbySearch()

nearby = searcher.search_near_place("Plaça Catalunya, Barcelona", radius_km=0.5)

print("Lugares cerca de Plaça Catalunya:")
for place in nearby[:5]:
    print(f"  📍 {place.name} ({place.type}) - {place.distance_km}km")
```

### 3. Conversor de Coordenadas para GPS

```python
"""
Herramienta para convertir coordenadas entre formatos.
Útil para: cartografía, topografía, agrimensura.
"""
from geofinder.transformations import transform_point, get_backend
from dataclasses import dataclass
from typing import Tuple


@dataclass
class CoordinateResult:
    """Resultado de conversión de coordenadas."""
    x: float
    y: float
    epsg: int
    format_name: str
    formatted: str


class CoordinateConverter:
    """Conversor de coordenadas con múltiples formatos."""

    FORMATS = {
        4326: "WGS84 (GPS)",
        25831: "ETRS89 UTM 31N",
        23031: "ED50 UTM 31N",
        3857: "Web Mercator",
        32631: "WGS84 UTM 31N"
    }

    def __init__(self):
        backend = get_backend()
        if not backend:
            raise ImportError(
                "Instala pyproj o GDAL para usar transformaciones"
            )
        print(f"Usando backend: {backend}")

    def convert(
        self,
        x: float,
        y: float,
        from_epsg: int,
        to_epsg: int
    ) -> CoordinateResult:
        """Convierte coordenadas entre sistemas."""
        dest_x, dest_y = transform_point(x, y, from_epsg, to_epsg)

        return CoordinateResult(
            x=dest_x,
            y=dest_y,
            epsg=to_epsg,
            format_name=self.FORMATS.get(to_epsg, f"EPSG:{to_epsg}"),
            formatted=self._format_coords(dest_x, dest_y, to_epsg)
        )

    def convert_to_all(
        self,
        x: float,
        y: float,
        from_epsg: int
    ) -> list[CoordinateResult]:
        """Convierte a todos los sistemas disponibles."""
        results = []
        for epsg in self.FORMATS:
            if epsg != from_epsg:
                try:
                    results.append(self.convert(x, y, from_epsg, epsg))
                except Exception:
                    pass  # Algunos sistemas pueden no ser compatibles
        return results

    def _format_coords(self, x: float, y: float, epsg: int) -> str:
        """Formatea coordenadas según el sistema."""
        if epsg == 4326:
            # Formato DMS para GPS
            lat_dir = 'N' if y >= 0 else 'S'
            lon_dir = 'E' if x >= 0 else 'W'
            return f"{abs(y):.6f}°{lat_dir}, {abs(x):.6f}°{lon_dir}"
        else:
            return f"X: {x:.2f}, Y: {y:.2f}"


# Uso
converter = CoordinateConverter()

# Convertir UTM a GPS
result = converter.convert(430000, 4580000, 25831, 4326)
print(f"{result.format_name}: {result.formatted}")

# Ver en todos los formatos
print("\nMismas coordenadas en diferentes sistemas:")
for r in converter.convert_to_all(430000, 4580000, 25831):
    print(f"  {r.format_name}: {r.formatted}")
```

---

## 📎 Recursos Adicionales

### Documentación Relacionada

- [README.md](README.md) - Guía rápida de instalación y uso
- [README-DEV.md](README-DEV.md) - Configuración del entorno de desarrollo
- [README-ARQ.md](README-ARQ.md) - Arquitectura técnica interna
- [README-MCP.md](README-MCP.md) - Servidor MCP para integración con IA

### Enlaces Útiles

- [Repositorio GitLab](https://gitlab.com/pg005991/geofinder-icgc)
- [Geocodificador ICGC](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
- [Pelias Documentation](https://github.com/pelias/documentation)
- [EPSG Registry](https://epsg.io/)

---

**Autor:** Goalnefesh  
**Licencia:** GPL-2.0-or-later
