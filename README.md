# <img src="pics/geofinder-logo 192x192.jpg" alt="GeoFinder Logo" width="50" height="50"> GeoFinder

> **Geocodificador para Cataluña** usando el servicio del ICGC (Institut Cartogràfic i Geològic de Catalunya).  
> 🔄 API dual: Async nativo + wrappers sync para scripts simples.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-2.0](https://img.shields.io/badge/License-GPL--2.0-yellow.svg)](LICENSE)

---

## 📚 Guía Rápida

| Sección                                        | Descripción                   |
| ---------------------------------------------- | ----------------------------- |
| [🚀 Inicio Rápido](#-inicio-rápido)            | Instalación y primeros pasos  |
| [📖 API](#-api-principal)                      | Métodos principales           |
| [🔍 Tipos de Búsqueda](#-tipos-de-búsqueda)    | Qué puedes buscar             |
| [⚙️ Configuración](#️-configuración-avanzada)   | Opciones avanzadas            |
| [🤖 Servidor MCP](#-servidor-mcp)              | Integración con IA            |
| [🏗️ Arquitectura](#️-arquitectura)              | Documentación técnica interna |

---

## 🚀 Inicio Rápido

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/jccamel/geocoder-mcp.git
cd geofinder-icgc

# Instalación básica
pip install -e .

# Con transformación de coordenadas
pip install -e ".[pyproj]"

# Con servidor MCP para IA
pip install -e ".[mcp,pyproj]"
```

### Uso Básico

```python
from geofinder import GeoFinder

gf = GeoFinder()

# API Sync (para scripts simples)
results = gf.find_sync("Barcelona")
for r in results:
    print(f"{r.nom} - {r.nomTipus}")

### Búsqueda Robusta de Direcciones (v2.1+)

GeoFinder v2.1 incluye un motor de parseo mejorado que soporta formatos naturales y portales sin número.

```python
async with GeoFinder() as gf:
    # 1. Formato sin comas
    res = await gf.find("Gran Via 123 Barcelona")
    
    # 2. Soporte para "s/n" (sin número)
    res = await gf.find("Passeig de Gràcia s/n, Barcelona")
    
    # 3. Limitar resultados
    res = await gf.find("Calle Mayor", size=3)
```

# API Async (para batch processing)
import asyncio

async def batch():
    results = await asyncio.gather(
        gf.find("Barcelona"),
        gf.find("Girona")
    )
    return results

results = asyncio.run(batch())
```

---

## 📖 API Principal

### `find(query, default_epsg=25831, size=None)` 🔍

Búsqueda general con detección automática del tipo. **Async nativo.**

```python
# API Async
results = await gf.find("Montserrat", size=5)
results = await gf.find("Barcelona, Diagonal 100")
results = await gf.find("Gran Via 123 Barcelona") # Soporte sin comas (v2.1+)
results = await gf.find("C-32 km 10")

# API Sync (wrapper)
results = gf.find_sync("Barcelona", size=1)
```

### `find_response(query, default_epsg=25831, size=None)` 📊

Igual que `find`, pero devuelve un objeto `GeoResponse` con metadatos de rendimiento.

```python
response = await gf.find_response("Barcelona")
print(f"Resultados: {response.count}")
print(f"Tiempo: {response.time_ms:.2f} ms") # Metadatos de rendimiento (v2.1+)
```

---

### `find_reverse(x, y, epsg=25831)` 📍

Geocodificación inversa (coordenadas → lugar). **Async nativo.**

```python
# API Async
results = await gf.find_reverse(430000, 4580000, epsg=25831)
results = await gf.find_reverse(2.1734, 41.3851, epsg=4326)

# API Sync (wrapper)
results = gf.find_reverse_sync(430000, 4580000, epsg=25831)
```

---

### `autocomplete(partial_text, size=10)` ⌨️

Sugerencias de autocompletado. **Async nativo.**

```python
# API Async
suggestions = await gf.autocomplete("Barcel")

# API Sync (wrapper)
suggestions = gf.autocomplete_sync("Barcel")
# Retorna: Barcelona, Barcelonès, etc.
```

---

### `find_batch(queries, max_concurrency=5)` 📦

Procesa múltiples búsquedas en paralelo con control de concurrencia. **Async nativo.**

```python
# API Async
queries = ["Barcelona", "Girona", "Lleida"]
results = await gf.find_batch(queries, max_concurrency=5)
# Retorna List[GeoResponse]

# API Sync (wrapper)
results = gf.find_batch_sync(queries)
```

### `find_reverse_batch(coordinates)` 📍📦

Procesa múltiples geocodificaciones inversas en paralelo. **Async nativo.**

```python
# API Async
coords = [(2.1734, 41.3851), (2.8249, 41.9794)]
results = await gf.find_reverse_batch(coords, epsg=4326)
# Retorna List[List[GeoResult]]

# API Sync (wrapper)
results = gf.find_reverse_batch_sync(coords, epsg=4326)
```

> [!WARNING]
> **Wrappers síncronos y múltiples llamadas batch:** Los métodos `_sync` crean y cierran un event loop en cada llamada. Si necesitas ejecutar múltiples operaciones batch en secuencia, usa una **instancia nueva de `GeoFinder`** para cada grupo.

---

## 🔍 Tipos de Búsqueda

| Tipo            | Ejemplo                             | Descripción                          |
| --------------- | ----------------------------------- | ------------------------------------ |
| **Topónimo**    | `"Barcelona"`, `"Montserrat"`       | Cualquier nombre de lugar            |
| **Coordenadas** | `"430000 4580000 EPSG:25831"`       | Punto con sistema de referencia      |
| **Dirección**   | `"Carreras 10, Barcelona"`          | Soporte flexible con/sin comas       |
| **Dirección**   | `"Diagonal s/n, Barcelona"`         | Soporte para portales **s/n** (v2.1+)|
| **Carretera**   | `"C-32 km 10"`                      | Punto kilométrico                    |
| **Rectángulo**  | `"X1 Y1 X2 Y2"`                     | Área rectangular                     |

### Modelos de Datos (Pydantic)

Los resultados ya no son simples diccionarios, sino objetos **Pydantic** validados (clase `GeoResult`).

```python
# Atributos principales de GeoResult
result.nom          # Nombre del lugar (str)
result.nomTipus     # Tipo (str: Municipi, Carrer, etc.)
result.nomMunicipi  # Municipio (str)
result.nomComarca   # Comarca (str)
result.x            # Longitud WGS84 (float)
result.y            # Latitud WGS84 (float)
result.epsg         # Sistema de referencia (int)

# Soporte para acceso tipo diccionario (para compatibilidad)
nombre = result['nom']
```

---

## ⚙️ Configuración Avanzada

### Opciones del Constructor

```python
import logging

# Habilitar logs de debug
logging.basicConfig(level=logging.DEBUG)

# Configuración personalizada
gf = GeoFinder(
    icgc_url="https://eines.icgc.cat/geocodificador",
    timeout=10,
    logger=logging.getLogger("mi_app"),
    verify_ssl=True,   # Verificar certificados SSL (default: True)
    default_size=10,   # Número de resultados por defecto (default: 10)
    
    # Configuración de Caché
    cache_size=256,    # Aumentar tamaño de caché (default: 128)
    cache_ttl=7200,    # Aumentar tiempo de vida a 2 horas (default: 3600s)

    # Configuración de Reintentos (Exponential Backoff)
    max_retries=5,           # Reintentos máximos (default: 3)
    retry_base_delay=1.0,    # Delay inicial en segundos (default: 0.5)
    retry_max_delay=15.0,    # Delay máximo en segundos (default: 10.0)
    retry_on_5xx=True        # Reintentar en errores de servidor (default: True)
)
```

| Parámetro | Tipo | Por Defecto | Descripción |
| --------- | ---- | ----------- | ----------- |
| `logger` | `logging.Logger` | `None` | Logger para depuración. |
| `icgc_url` | `str` | `None` | URL base del servicio (o variable `ICGC_URL`). |
| `timeout` | `int` | `5` | Tiempo máximo de espera en segundos. |
| `verify_ssl` | `bool` | `True` | Verificar certificados SSL. |
| `default_size` | `int` | `10` | Cantidad de resultados si no se especifica `size`. |
| `cache_size` | `int` | `128` | Capacidad de la caché (0 para desactivar). |
| `cache_ttl` | `int` | `3600` | Tiempo de vida de la caché en segundos. |
| `max_retries` | `int` | `3` | Número de reintentos en fallos transitorios. |
| `retry_on_5xx` | `bool` | `True` | Si debe reintentar en errores 500 del servidor. |
| `http_client` | `httpx.AsyncClient` | `None` | Cliente HTTP externo para compartir pool de conexiones. |

### Uso Avanzado: Compartir Pool de Conexiones 🚀

**Nuevo en v2.1+**: GeoFinder soporta inyección de dependencias para compartir un pool de conexiones HTTP entre múltiples instancias.

#### ¿Por qué compartir el pool?

- ✅ **Mejor rendimiento**: Reutiliza conexiones TCP (menor latencia)
- ✅ **Menos recursos**: Controla el número de sockets abiertos
- ✅ **Escalabilidad**: Ideal para aplicaciones web de alto tráfico

#### Ejemplo con FastAPI

```python
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
import httpx
from geofinder import GeoFinder

# Cliente compartido
shared_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global shared_client
    # Crear pool al iniciar
    shared_client = httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )
    yield
    # Cerrar pool al terminar
    await shared_client.aclose()

app = FastAPI(lifespan=lifespan)

def get_geofinder():
    """GeoFinder NO cerrará el cliente compartido."""
    return GeoFinder(http_client=shared_client)

@app.get("/search")
async def search(q: str, gf: GeoFinder = Depends(get_geofinder)):
    return await gf.find_response(q)
```

> [!TIP]
> Ver [COOKBOOK.md](COOKBOOK.md#fastapi---pool-de-conexiones-compartido-recomendado) para ejemplos completos con diagramas y configuración detallada.
```

| Parámetro | Tipo | Por Defecto | Descripción |
| --------- | ---- | ----------- | ----------- |
| `logger` | `logging.Logger` | `None` | Logger para depuración. |
| `icgc_url` | `str` | `None` | URL base del servicio (o variable `ICGC_URL`). |
| `timeout` | `int` | `5` | Tiempo máximo de espera en segundos. |
| `verify_ssl` | `bool` | `True` | Verificar certificados SSL. |
| `default_size` | `int` | `10` | Cantidad de resultados si no se especifica `size`. |
| `cache_size` | `int` | `128` | Capacidad de la caché (0 para desactivar). |
| `cache_ttl` | `int` | `3600` | Tiempo de vida de la caché en segundos. |
| `max_retries` | `int` | `3` | Número de reintentos en fallos transitorios. |
| `retry_on_5xx` | `bool` | `True` | Si debe reintentar en errores 500 del servidor. |

### Sistema de Caché Inteligente 🚀

GeoFinder incluye una **caché asíncrona LRU** (Least Recently Used) integrada para optimizar el rendimiento y reducir las peticiones a la red.

- **Automática**: Se usa en `find`, `find_reverse` y `autocomplete`.
- **Configurable**: Tamaño y TTL ajustables en el constructor.
- **Control total**: Puedes saltarte la caché en una llamada específica usando `use_cache=False`.

```python
# Forzar refresco de datos (saltar caché)
results = await gf.find("Barcelona", use_cache=False)

# Limpiar manualmente
gf.clear_cache()
```

### Seguridad y SSL

Por defecto, GeoFinder verifica los certificados SSL de los servidores del ICGC. Si necesitas desactivar esta verificación (por ejemplo, en entornos de desarrollo corporativos con proxies o certificados autofirmados):

```python
gf = GeoFinder(verify_ssl=False)
```

> [!WARNING]
> Desactivar `verify_ssl` silenciará las advertencias `InsecureRequestWarning` de forma **global** en el proceso de Python. Esto puede afectar a otras librerías que utilicen `urllib3` en el mismo proyecto.

### Sistemas de Coordenadas (EPSG)

| Código  | Sistema        | Uso                      |
| ------- | -------------- | ------------------------ |
| `4326`  | WGS84          | GPS estándar (lat/lon)   |
| `25831` | ETRS89 UTM 31N | Sistema oficial Cataluña |
| `3857`  | Web Mercator   | Mapas web                |
| `23031` | ED50 UTM 31N   | Sistema antiguo          |

### Transformación de Coordenadas

```python
# Requiere: pip install -e ".[pyproj]"

from geofinder.transformations import transform_point

# UTM → WGS84
lon, lat = transform_point(430000, 4580000, 25831, 4326)
print(f"WGS84: {lon}, {lat}")
```

---

## 🤖 Servidor MCP

GeoFinder puede ejecutarse como **servidor MCP** para integrarse con asistentes de IA como **Claude Desktop**.

### Instalación

```bash
pip install -e ".[mcp,pyproj]"
```

### Ejecutar Servidor

```bash
# STDIO (para Claude Desktop)
python -m geofinder.mcp_server

# HTTP (para testing)
python -m geofinder.mcp_server --transport http --port 8000
```

### Integración con Claude Desktop

Añade a `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "geofinder": {
      "command": "python",
      "args": ["-m", "geofinder.mcp_server"]
    }
  }
}
```

### Herramientas MCP Disponibles

- 🔍 `find_place` - Búsqueda general
- 📍 `find_reverse` - Geocodificación inversa
- ⌨️ `autocomplete` - Autocompletado
- 🏠 `find_address` - Búsqueda de direcciones
- 🗺️ `transform_coordinates` - Conversión EPSG

**📚 Documentación completa:** [README-MCP.md](README-MCP.md)

---

## 🏗️ Arquitectura

GeoFinder está estructurado en **3 capas principales** con **arquitectura completamente asíncrona**:

### Capas del Sistema

```
┌─────────────────────────────────┐
│  Servidor MCP / API Pública    │  ← Capa de Presentación (⚡ async)
├─────────────────────────────────┤
│  GeoFinder (Lógica Negocio)    │  ← Async + wrappers sync
├─────────────────────────────────┤
│  PeliasClient (httpx async)   │  ← Comunicación con ICGC
└─────────────────────────────────┘
```

### Componentes Principales

| Componente          | Responsabilidad                            | Tipo |
| ------------------- | ------------------------------------------ | ---- |
| **PeliasClient**    | Comunicación HTTP async con ICGC Pelias    | 🔄 Async |
| **GeoFinder**       | Lógica de negocio, detección y parsing     | 🔄 Async + 🔁 Sync wrappers |
| **MCP Server**      | Exposición como herramientas para IA       | 🔄 Async |
| **Transformations** | Conversión entre sistemas EPSG             | 🔁 Sync (CPU) |

### Flujo de Datos

```
Usuario → MCP/API → GeoFinder → PeliasClient → Servidor ICGC
              ↓            ↓
          await ...    await ...
```

**📚 Documentación técnica completa:** [README-ARQ.md](README-ARQ.md)

---

## 📦 Dependencias

| Tipo           | Paquetes  | Propósito                           |
| -------------- | --------- | ----------------------------------- |
| **Requeridas** | Ninguna   | Solo librería estándar Python       |
| **Opcionales** | `pyproj`  | Transformación de coordenadas       |
|                | `GDAL`    | Alternativa a pyproj (más compleja) |
|                | `fastmcp` | Servidor MCP para IA                |

### Instalación por Uso

```bash
# Solo geocodificación
pip install -e .

# Con transformación de coordenadas
pip install -e ".[pyproj]"

# Con servidor MCP
pip install -e ".[mcp,pyproj]"

# Desarrollo completo
pip install -e ".[dev,mcp,pyproj]"
```

---

## 🛠️ Desarrollo

```bash
# Clonar repositorio
git clone https://github.com/jccamel/geocoder-mcp.git
cd geofinder-icgc

# Instalar con uv
uv pip install -e ".[dev,mcp,pyproj]"

# Ejecutar tests
uv run pytest

# Formatear código
uv run ruff format .
```

**Documentación:**

- [COOKBOOK.md](COOKBOOK.md) - 📚 Tutoriales y ejemplos prácticos
- [README-DEV.md](README-DEV.md) - Guía de desarrollo
- [README-MCP.md](README-MCP.md) - Servidor MCP
- [README-ARQ.md](README-ARQ.md) - Arquitectura técnica

---

## 📚 Recursos

- [Documentación ICGC](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
- [Repositorio GitLab](https://github.com/jccamel/geocoder-mcp)
- [Issues](https://github.com/jccamel/geocoder-mcp/-/issues)
- [Model Context Protocol](https://modelcontextprotocol.io) (para MCP)

---

## 📄 Licencia

GPL-2.0-or-later - Basado en el plugin OpenICGC del ICGC.

**Autor original:** ICGC / Adaptado para uso standalone by Goalnefesh
