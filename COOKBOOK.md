# 📚 GeoFinder Cookbook

> **Guía práctica con ejemplos de integración** para el geocodificador de Cataluña.

---

## 📋 Tabla de Contenidos

| Sección                                                     | Descripción                |
| ----------------------------------------------------------- | -------------------------- |
| [🚀 Ejemplos Básicos](#-ejemplos-básicos)                   | Primeros pasos y uso común |
| [🌐 Integración Web](#-integración-web)                     | FastAPI (Recomendado)      |
| [📊 Análisis de Datos](#-análisis-de-datos)                 | Pandas, GeoPandas          |
| [⚡ Geocodificación por Lote](#-geocodificación-por-lote) | Procesamiento masivo       |
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

### Búsqueda Simple (Async)

```python
import asyncio
from geofinder import GeoFinder

async def main():
    # Inicializar con context manager
    async with GeoFinder() as gf:
        # Buscar un municipio
        results = await gf.find("Barcelona")
        for r in results:
            print(f"{r.nom} ({r.nomTipus}) - {r.x}, {r.y}")
            # También funciona el acceso tipo dict por compatibilidad:
            # print(r['nom'])

if __name__ == "__main__":
    asyncio.run(main())
# Output: Barcelona (Cap de municipi) - 2.177, 41.382
```

### Búsqueda Síncrona (Scripts)

```python
from geofinder import GeoFinder

gf = GeoFinder()
results = gf.find_sync("Montserrat")
for r in results:
    print(r.nom)
```

### Búsqueda con Diferentes Formatos

```python
from geofinder import GeoFinder

gf = GeoFinder()

# Desactivar verificación SSL para servidores con certificados autofirmados
gf = GeoFinder(verify_ssl=False)

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
async with GeoFinder() as gf:
    # Desde coordenadas GPS → información del lugar
    results = await gf.find_reverse(2.1734, 41.3851, epsg=4326)

    for r in results:
        print(f"📍 {r.nom}")
        print(f"   Municipio: {r.nomMunicipi}")
        print(f"   Comarca: {r.nomComarca}")
        # Metadata extra ahora disponible
        print(f"   ID Municipio: {r.idMunicipi}")
```

### Autocompletado

```python
async with GeoFinder() as gf:
    # Sugerencias mientras el usuario escribe
    suggestions = await gf.autocomplete("Barcel", size=5)

    for s in suggestions:
        print(f"💡 {s.nom} - {s.nomTipus}")
```

---

## 🌐 Integración Web

### FastAPI - Pool de Conexiones Compartido (Recomendado)

**¿Por qué compartir el pool de conexiones?**

Cuando tienes una aplicación web con múltiples endpoints que usan GeoFinder, crear un nuevo cliente HTTP para cada petición es ineficiente:

- ❌ **Sin compartir**: Cada petición crea/cierra conexiones → overhead de red
- ✅ **Con pool compartido**: Reutiliza conexiones → menor latencia, mejor rendimiento

#### Ejemplo Completo con Pool Compartido

```python
"""
API FastAPI con pool de conexiones compartido.
Ejecutar: uvicorn app:app --reload
"""
from fastapi import FastAPI, Query, HTTPException, Depends
from contextlib import asynccontextmanager
import httpx
from geofinder import GeoFinder
from geofinder.models import GeoResponse, GeoResult

# ============================================================================
# 1. CONFIGURACIÓN DEL POOL DE CONEXIONES
# ============================================================================

# Cliente HTTP compartido con configuración optimizada
shared_http_client: httpx.AsyncClient | None = None

def get_shared_client() -> httpx.AsyncClient:
    """Obtiene el cliente HTTP compartido."""
    if shared_http_client is None:
        raise RuntimeError("Cliente HTTP no inicializado")
    return shared_http_client


# ============================================================================
# 2. LIFECYCLE DE LA APLICACIÓN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    global shared_http_client
    
    # STARTUP: Crear cliente compartido
    print("🚀 Iniciando pool de conexiones...")
    shared_http_client = httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(
            max_connections=100,        # Máximo de conexiones totales
            max_keepalive_connections=20  # Conexiones keep-alive
        ),
        follow_redirects=True
    )
    print(f"✅ Pool creado: {shared_http_client.limits}")
    
    yield  # La aplicación está corriendo
    
    # SHUTDOWN: Cerrar cliente compartido
    print("⏳ Cerrando pool de conexiones...")
    await shared_http_client.aclose()
    print("✅ Pool cerrado correctamente")


# ============================================================================
# 3. APLICACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title="GeoFinder API",
    description="API de geocodificación para Cataluña con pool compartido",
    version="2.1.0",
    lifespan=lifespan  # ← Importante: gestión del lifecycle
)


# ============================================================================
# 4. DEPENDENCY INJECTION
# ============================================================================

def get_geofinder(
    client: httpx.AsyncClient = Depends(get_shared_client)
) -> GeoFinder:
    """
    Crea una instancia de GeoFinder con el cliente compartido.
    
    IMPORTANTE: GeoFinder NO cerrará este cliente porque fue inyectado.
    """
    return GeoFinder(http_client=client)


# ============================================================================
# 5. ENDPOINTS
# ============================================================================

@app.get("/search", response_model=GeoResponse)
async def search(
    q: str = Query(..., description="Texto a buscar"),
    size: int = Query(10, ge=1, le=100, description="Número de resultados"),
    gf: GeoFinder = Depends(get_geofinder)
):
    """
    Busca un lugar por nombre o dirección.
    
    Ejemplos:
    - /search?q=Barcelona
    - /search?q=Diagonal 100, Barcelona&size=5
    """
    try:
        return await gf.find_response(q, size=size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reverse", response_model=list[GeoResult])
async def reverse(
    x: float = Query(..., description="Coordenada X / Longitud"),
    y: float = Query(..., description="Coordenada Y / Latitud"),
    epsg: int = Query(4326, description="Sistema de coordenadas"),
    gf: GeoFinder = Depends(get_geofinder)
):
    """
    Geocodificación inversa: coordenadas → lugar.
    
    Ejemplos:
    - /reverse?x=2.1734&y=41.3851&epsg=4326
    - /reverse?x=430000&y=4580000&epsg=25831
    """
    try:
        return await gf.find_reverse(x, y, epsg=epsg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2, description="Texto parcial"),
    size: int = Query(10, ge=1, le=50),
    gf: GeoFinder = Depends(get_geofinder)
):
    """
    Sugerencias de autocompletado.
    
    Ejemplo: /autocomplete?q=Barcel
    """
    try:
        suggestions = await gf.autocomplete(q, size=size)
        return {"suggestions": [s.nom for s in suggestions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health(client: httpx.AsyncClient = Depends(get_shared_client)):
    """Endpoint de salud que muestra el estado del pool."""
    return {
        "status": "healthy",
        "pool": {
            "max_connections": client.limits.max_connections,
            "max_keepalive": client.limits.max_keepalive_connections,
            "is_closed": client.is_closed
        }
    }


# ============================================================================
# 6. EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### ¿Cómo Funciona el Pool Compartido?

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Application                                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Request 1    │  │ Request 2    │  │ Request 3    │  │
│  │ /search      │  │ /reverse     │  │ /autocomplete│  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│         └──────────────────┼──────────────────┘          │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  Dependency    │                    │
│                    │  get_geofinder │                    │
│                    └───────┬────────┘                    │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  GeoFinder     │                    │
│                    │  (http_client) │                    │
│                    └───────┬────────┘                    │
│                            │                             │
│         ┌──────────────────┴──────────────────┐          │
│         │                                     │          │
│  ┌──────▼──────────────────────────────────┐  │          │
│  │  shared_http_client (httpx.AsyncClient) │  │          │
│  │  ┌────────────────────────────────────┐ │  │          │
│  │  │  Connection Pool                   │ │  │          │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐       │ │  │          │
│  │  │  │ Conn │ │ Conn │ │ Conn │  ...  │ │  │          │
│  │  │  └──────┘ └──────┘ └──────┘       │ │  │          │
│  │  │  (Reutilizadas entre peticiones)  │ │  │          │
│  │  └────────────────────────────────────┘ │  │          │
│  └──────────────────────────────────────────┘  │          │
│                                                 │          │
└─────────────────────────────────────────────────┘
                         │
                         ▼
              Servidor ICGC Pelias
```

#### Ventajas del Pool Compartido

| Aspecto | Sin Pool | Con Pool Compartido |
|---------|----------|---------------------|
| **Conexiones** | Nueva por petición | Reutilizadas |
| **Latencia** | ~100-200ms | ~20-50ms |
| **Overhead** | Alto (TCP handshake) | Bajo (keep-alive) |
| **Recursos** | Muchos sockets | Controlado |
| **Escalabilidad** | Limitada | Alta |

#### Configuración del Pool

```python
# Ajustar según tus necesidades
httpx.AsyncClient(
    timeout=10.0,  # Timeout global
    limits=httpx.Limits(
        max_connections=100,        # Total de conexiones simultáneas
        max_keepalive_connections=20,  # Conexiones keep-alive
        keepalive_expiry=30.0       # Tiempo de vida de keep-alive
    )
)
```

**Recomendaciones**:
- **API de bajo tráfico**: `max_connections=20`, `max_keepalive=5`
- **API de tráfico medio**: `max_connections=50`, `max_keepalive=10`
- **API de alto tráfico**: `max_connections=100`, `max_keepalive=20`

---

### FastAPI - Versión Simple (Sin Pool Compartido)

Si no necesitas optimización extrema, puedes usar la versión simple:

```python
from fastapi import FastAPI, Query
from geofinder import GeoFinder

app = FastAPI()
gf = GeoFinder()  # Cliente propio, se gestiona internamente

@app.get("/search")
async def search(q: str = Query(...)):
    return await gf.find_response(q)
```

> [!NOTE]
> Esta versión es más simple pero menos eficiente. Cada instancia de `GeoFinder` tiene su propio cliente HTTP.

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


async def geocode_address(gf, address: str) -> dict:
    """Geocodifica una dirección y devuelve coordenadas."""
    try:
        results = await gf.find(address)
        if results:
            r = results[0]
            return {
                'lat': r.y,
                'lon': r.x,
                'municipio': r.nomMunicipi,
                'comarca': r.nomComarca,
                'tipo': r.nomTipus
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
async with GeoFinder() as gf:
    for lugar in lugares:
        results = await gf.find(lugar)
        if results:
            r = results[0]
            data.append({
                'nombre': r.nom,
                'tipo': r.nomTipus,
                'comarca': r.nomComarca,
                'geometry': Point(r.x, r.y)
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
    results = gf.find_sync(lugar)
    if results:
        r = results[0]
        folium.Marker(
            location=[r.y, r.x],  # Folium usa lat, lon
            popup=f"<b>{r.nom}</b><br>{r.nomTipus}",
            tooltip=r.nom,
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(mapa)

# Guardar mapa
mapa.save('mapa_cataluña.html')
print("Mapa guardado en mapa_cataluña.html")
```

---

## ⚡ Geocodificación por Lotes

### Uso de `find_batch` (Recomendado)

`find_batch` es la forma más eficiente y sencilla de procesar múltiples direcciones. Gestiona automáticamente la concurrencia para no saturar el servidor.

```python
import asyncio
from geofinder import GeoFinder

async def main():
    async with GeoFinder() as gf:
        direcciones = [
            "Barcelona",
            "Girona",
            "Lleida",
            "Tarragona",
            "Montserrat"
        ]
        
        # max_concurrency limita las peticiones simultáneas (default: 5)
        results = await gf.find_batch(direcciones, max_concurrency=10)
        
        for query, response in zip(direcciones, results):
            if response.results:
                top = response.results[0]
                print(f"✅ {query} -> {top.nom} ({top.x}, {top.y})")
            else:
                print(f"❌ {query} no encontrado")

if __name__ == "__main__":
    asyncio.run(main())
```

### Geocodificación Inversa por Lotes

También puedes procesar múltiples coordenadas de forma eficiente.

```python
async with GeoFinder() as gf:
    coords = [
        (2.1734, 41.3851),
        (2.8249, 41.9794),
        (0.6231, 41.6176)
    ]
    
    # Procesa en paralelo con concurrencia controlada
    results = await gf.find_reverse_batch(coords, epsg=4326, max_concurrency=3)
    
    for c, res_list in zip(coords, results):
        if res_list:
            print(f"📍 {c} -> {res_list[0].nom}")
```

### Versión Síncrona (Scripts Simples)

Si no estás usando `async/await`, puedes usar las versiones `_sync`.

```python
from geofinder import GeoFinder

gf = GeoFinder()
direcciones = ["Barcelona", "Girona"]

# Bloquea hasta que todo el lote se procesa
results = gf.find_batch_sync(direcciones)

for resp in results:
    if resp.results:
        print(resp.results[0].nom)
```

> [!TIP]
> **Gestión de Sesiones Síncronas**: Las llamadas `_sync` gestionan internamente el ciclo de vida del cliente. Puedes realizar múltiples llamadas secuenciales sobre la misma instancia de `GeoFinder` sin problemas.

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


async def geocode_safely(query: str, gf: GeoFinder) -> dict:
    """Geocodificar de forma segura con modelos Pydantic."""
    try:
        results = await gf.find(query)

        if not results:
            return {
                'success': False,
                'error': 'NOT_FOUND',
                'message': f"No se encontraron resultados para '{query}'"
            }

        best = results[0]
        return {
            'success': True,
            'data': best,
            'name': best.nom,
            'coords': (best.y, best.x)
        }
    except PeliasTimeoutError:
        return {'success': False, 'error': 'TIMEOUT', 'retry': True}
    except Exception as e:
        return {'success': False, 'error': 'ERROR', 'message': str(e)}
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

### Caché Nativa Integrada

GeoFinder incluye un sistema de caché asíncrono LRU con TTL. No necesitas implementar nada externo a menos que requieras persistencia en base de datos.

```python
"""
Configuración y uso de la caché nativa.
"""
from geofinder import GeoFinder

# 1. Configurar al inicializar
gf = GeoFinder(
    cache_size=200,    # Capacidad para 200 resultados
    cache_ttl=3600     # 1 hora de vida
)

async def demo_cache():
    # Primera vez: MISS (petición a red)
    res1 = await gf.find("Barcelona")
    
    # Segunda vez: HIT (instantáneo desde memoria)
    res2 = await gf.find("Barcelona")
    
    # Forzar actualización (saltar caché)
    res3 = await gf.find("Barcelona", use_cache=False)
    
    # Limpiar caché
    gf.clear_cache()
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
            confidence = 1.0 if best.nomTipus == 'Adreça' else 0.7

            return ValidatedAddress(
                original=address,
                is_valid=True,
                normalized=best.nom,
                street=best.nomTipus,
                municipality=best.nomMunicipi,
                comarca=best.nomComarca,
                latitude=best.y,
                longitude=best.x,
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

    async def search_near_place(
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
        # Usar el método integrado del core para mayor eficiencia
        results = await self.gf.search_nearby(place_name, radius_km=radius_km, max_results=max_results)
        
        if not results:
            return []
            
        ref = results[0]
        return [
            NearbyResult(
                name=r.nom,
                type=r.nomTipus,
                distance_km=0.0, # El core no calcula distancias exactas aún
                latitude=r.y,
                longitude=r.x
            ) for r in results
        ]

        ref = ref_results[0]
        ref_x, ref_y = ref.x, ref.y

        # Buscar lugares cercanos
        nearby = await self.gf.find_reverse(
            ref_x, ref_y,
            epsg=4326,
            layers="address,tops,pk",
            size=max_results
        )

        results = []
        for place in nearby:
            # Calcular distancia
            dist = self._haversine(ref_y, ref_x, place.y, place.x)

            if dist <= radius_km:
                results.append(NearbyResult(
                    name=place.nom,
                    type=place.nomTipus,
                    distance_km=round(dist, 2),
                    latitude=place.y,
                    longitude=place.x
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

- [Repositorio GitLab](https://github.com/jccamel/geocoder-mcp)
- [Geocodificador ICGC](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
- [Pelias Documentation](https://github.com/pelias/documentation)
- [EPSG Registry](https://epsg.io/)

---

**Autor:** Goalnefesh  
**Licencia:** GPL-2.0-or-later
