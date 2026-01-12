# GeoFinder ICGC Architecture

> **Technical documentation of the internal operation of the GeoFinder project**  
> Last updated: 2025-12-19 (v2.1.0)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Layered Architecture](#-layered-architecture)
- [Main Components](#-main-components)
- [Data Flow](#-data-flow)
- [Tool Mapping](#-tool-mapping)
- [ICGC Endpoints](#-icgc-endpoints)
- [Full Flow Examples](#-full-flow-examples)

---

## 🎯 Overview

1. **Presentation Layer** - MCP Server (async) and public API (async + sync wrappers)
2. **Business Logic Layer** - GeoFinder (async, parsing, detection, transformations)
3. **Cache Layer** - AsyncLRUCache (in-memory, LRU + TTL)
4. **Communication Layer** - PeliasClient (httpx.AsyncClient, retries, errors)

> **Data Models**: Inter-layer communication is performed using **Pydantic** (`GeoResult`, `GeoResponse`), ensuring integrity and strong typing.

> **Dual API**: The core is async for maximum performance, but offers sync wrappers (`find_sync()`, etc.) for simple scripts.

---

## 🏗️ Layered Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                             │
│  ┌────────────────────────┐  ┌──────────────────────────────────┐ │
│  │      MCP Server        │  │      Public Python API           │ │
│  │    (mcp_server.py)     │  │      (geofinder.py)              │ │
│  │  ══════════════════    │  │  ══════════════════              │ │
│  │  🔄 ASYNC               │  │  🔄 ASYNC (native)               │ │
│  │                        │  │  🔁 SYNC (wrappers)              │ │
│  │  - find_place()    ⚡  │  │                                  │ │
│  │  - find_address()  ⚡  │  │  - await find_reverse()          │ │
│  │  - find_road_km()  ⚡  │  │  - await autocomplete()          │ │
│  │  - search_nearby() ⚡  │  │                                  │ │
│  │                        │  │  Sync (wrappers):                │ │
│  │  Sync (CPU-bound):     │  │  - find_sync()                   │ │
│  │  - transform_coords()  │  │  - find_reverse_sync()           │ │
│  │  - parse_query()       │  │  - autocomplete_sync()           │ │
│  └──────────┬─────────────┘  └───────────┬──────────────────────┘ │
└─────────────┼────────────────────────────┼────────────────────────┘
              │                            │
              └────────────┬───────────────┘
                           ↓
┌───────────────────────────────────────────────────────────────────┐
│                 CAPA DE LÓGICA DE NEGOCIO (ASYNC)                 │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              GeoFinder (geofinder.py) 🔄 ASYNC              │  │
│  │                                                             │  │
│  │  Lógica principal y orquestación                            │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
                              ↓
┌───────────────────────────────────────────────────────────────────┐
│                 CAPA DE CACHÉ (ASYNC)                             │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              AsyncLRUCache (utils/cache.py)                 │  │
│  │                                                             │  │
│  │  - Almacenamiento en memoria (LRU)                          │  │
│  │  - Expiración por tiempo (TTL)                              │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
                              ↓
┌───────────────────────────────────────────────────────────────────┐
│                 CAPA DE COMUNICACIÓN HTTP (ASYNC)                 │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │         PeliasClient (pelias.py) 🔄 httpx.AsyncClient       │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────────────┘
                              ↓
              ┌───────────────────────────┐
              │   Servidor ICGC           │
              │   Pelias API              │
              │                           │
              │  /cerca                   │
              │  /invers                  │
              │  /autocompletar           │
              └───────────────────────────┘
```

---

## 🔧 Componentes Principales

### 1. `pelias.py` - Cliente HTTP Async

**Responsabilidad:** Comunicación asíncrona con el servidor Pelias del ICGC.

#### Clases:

- **`PeliasClient`** - Cliente async principal (httpx.AsyncClient)
- **`PeliasError`** - Excepción base
- **`PeliasConnectionError`** - Error de conexión
- **`PeliasTimeoutError`** - Error de timeout

#### Métodos Async:

| Método | Descripción | Endpoint |
|--------|-------------|----------|
| `async geocode(query, **params)` | Búsqueda general (texto → coordenadas) | `/cerca` |
| `async reverse(lat, lon, **params)` | Geocodificación inversa (coords → lugar) | `/invers` |
| `async autocomplete(query, **params)` | Sugerencias de autocompletado | `/autocompletar` |
| `async call(endpoint, **params)` | Ejecuta petición HTTP genérica | Variable |
| `last_sent()` | Retorna última URL ejecutada (debug) | - |
| `async close()` | Cierra cliente httpx | - |

#### Características Técnicas:

- **Cliente HTTP:** `httpx.AsyncClient` (no bloquea event loop)
- **Retry Strategy:** 3 reintentos con transporte httpx
- **Status Codes Retry:** 429, 500, 502, 503, 504
- **Timeout:** Configurable (default: 5 segundos)
- **Context Manager:** Soporte para `async with`

---

### 2. `geofinder.py` - Lógica de Negocio (Async)

**Responsabilidad:** Detección de tipos de búsqueda, parsing, transformaciones y orquestación asíncrona.

#### Clase Principal: `GeoFinder`

#### Métodos Públicos Async (API Principal):

| Método | Descripción | Usa PeliasClient |
|--------|-------------|------------------|
| `async find(text, default_epsg, size)` | Búsqueda inteligente con detección automática | ✅ Sí |
| `async find_reverse(x, y, epsg, layers, size)` | Geocodificación inversa | ✅ Sí |
| `async autocomplete(text, size)` | Autocompletado | ✅ Sí |
| `async find_response(text, epsg, size)`| Igual que find pero con metadatos | ✅ Sí |

#### Wrappers Sync (para scripts simples):

| Método | Descripción | Implementación |
|--------|-------------|----------------|
| `find_sync(text, epsg)` | Versión síncrona de find() | `asyncio.run(find())` |
| `find_reverse_sync(x, y, ...)` | Versión síncrona de find_reverse() | `asyncio.run(find_reverse())` |
| `autocomplete_sync(text, size)` | Versión síncrona de autocomplete() | `asyncio.run(autocomplete())` |

#### Métodos Internos de Parsing (Sync - CPU puro):

| Método | Descripción | Formato Detectado |
|--------|-------------|-------------------|
| `_parse_point(text)` | Detecta coordenadas de punto | `"X Y"`, `"X Y EPSG:código"` |
| `_parse_rectangle(text)` | Detecta rectángulo | `"X1 Y1 X2 Y2"`, `"X1 Y1 X2 Y2 EPSG:código"` |
| `_parse_road(text)` | Detecta carretera + km | `"C-32 km 10"`, `"AP7 km 150"` |
| `_parse_address(text)` | Detecta dirección | `"Barcelona, Diagonal 100"` |

#### Métodos Internos de Búsqueda (Async):

| Método | Descripción | Llama a PeliasClient |
|--------|-------------|----------------------|
| `async _find_placename(text)` | Busca topónimos | `await geocode(text)` |
| `async _find_address(municipality, street_type, street, number)` | Busca direcciones | `await geocode(query, layers="address")` |
| `async _find_road(road, km)` | Busca puntos kilométricos | `await geocode(f"{road} {km}", layers="pk")` |
| `async _find_point_coordinate(x, y, epsg)` | Busca en coordenadas | `await reverse()` + lógica combinada |
| `async _find_point_coordinate_icgc(...)` | Búsqueda avanzada por coords | `await reverse(lat, lon, ...)` |
| `async _find_rectangle(west, north, east, south, epsg)` | Busca en rectángulo | Usa `await _find_point_coordinate()` |

| `get_name(results, index)` | Extrae nombre de resultado |

### 3. `utils/cache.py` - Sistema de Caché (Async)

**Responsabilidad:** Almacenamiento temporal de resultados para evitar peticiones redundantes.

#### Clase: `AsyncLRUCache`

| Método | Descripción |
|--------|-------------|
| `get(key)` | Recupera un valor si no ha expirado |
| `set(key, value)` | Guarda un valor y actualiza timestamp |
| `pop(key)` | Elimina una entrada específica |
| `clear()` | Vacía toda la caché |

#### Características:
- **LRU (Least Recently Used)**: Expulsa el elemento más antiguo cuando se llena.
- **TTL (Time To Live)**: Los elementos expiren tras N segundos (default 1h).
- **Standalone**: Sin dependencias externas.

---

### 3. `mcp_server.py` - Servidor MCP (Async)

**Responsabilidad:** Exponer funcionalidades de GeoFinder como herramientas MCP asíncronas para asistentes de IA.

#### Herramientas MCP Async:

| Herramienta | Tipo | Descripción | Usa GeoFinder |
|-------------|------|-------------|---------------|
| `async find_place(query, epsg, size)` | ⚡ Async | Búsqueda general inteligente | `await gf.find()` |
| `async autocomplete(text, max)` | ⚡ Async | Sugerencias de autocompletado | `await gf.autocomplete()` |
| `async find_reverse(lon, lat, ...)` | ⚡ Async | Geocodificación inversa | `await gf.find_reverse()` |
| `async find_by_coordinates(...)` | ⚡ Async | Búsqueda avanzada por coords | `await gf.find_by_coordinates()` |
| `async find_address(...)` | ⚡ Async | Búsqueda estructurada de direcciones | `await gf.find_address()` |
| `async find_road_km(road, km)` | ⚡ Async | Búsqueda de punto kilométrico | `await gf.find_road_km()` |
| `async search_nearby(...)` | ⚡ Async | Búsqueda cerca de un lugar | `await gf.search_nearby()` |

#### Herramientas MCP Sync (CPU-bound, no I/O):

| Herramienta | Tipo | Descripción | Usa |
|-------------|------|-------------|-----|
| `transform_coordinates(...)` | 🔁 Sync | Transformación de coordenadas | `transform_point()` (pyproj/GDAL) |
| `parse_search_query(query)` | 🔁 Sync | Analiza tipo de búsqueda | Métodos `_parse_*()` (regex) |

---

### 4. `transformations.py` - Transformación de Coordenadas

**Responsabilidad:** Conversión entre sistemas de referencia (EPSG).

#### Función Principal:

```python
transform_point(x, y, from_epsg, to_epsg) -> (dest_x, dest_y)
```

**Backends soportados:**
- `pyproj` (preferido)
- `GDAL/OGR` (alternativo)

**Uso:** Convierte coordenadas entre sistemas EPSG (ej: UTM 31N ↔ WGS84).

---

## 🔄 Flujo de Datos

### Flujo Típico de una Búsqueda:

```
Usuario/IA
    ↓
[Herramienta MCP] find_place("Barcelona, Diagonal 100")
    ↓
[GeoFinder] find("Barcelona, Diagonal 100", epsg=25831)
    ↓
[GeoFinder] _find_data() → Detecta tipo: DIRECCIÓN
    ↓
[GeoFinder] _parse_address() → Extrae: municipality="Barcelona", street="Diagonal", number="100"
    ↓
[GeoFinder] _find_address() → Construye query: "Carrer Diagonal 100, Barcelona"
    ↓
[PeliasClient] geocode("Carrer Diagonal 100, Barcelona", layers="address")
    ↓
[PeliasClient] call("/cerca", text="...", layers="address")
    ↓
[HTTP GET] https://eines.icgc.cat/geocodificador/cerca?text=Carrer+Diagonal+100,+Barcelona&layers=address
    ↓
[Servidor ICGC] Responde con GeoJSON
    ↓
[PeliasClient] Parsea JSON y retorna dict
    ↓
[GeoFinder] _parse_icgc_response() → Normaliza formato
    ↓
[Herramienta MCP] Retorna resultados al usuario/IA
```

---

## 📊 Mapeo de Herramientas

### Tabla Completa de Flujo de Llamadas:

| Herramienta MCP | Método GeoFinder | Método PeliasClient | Endpoint ICGC | Parámetros Clave |
|-----------------|------------------|---------------------|---------------|------------------|
| `find_place()` | `find()` | `geocode()` | `/cerca` | `text`, `layers` |
| `autocomplete()` | `autocomplete()` | `autocomplete()` | `/autocompletar` | `text`, `size` |
| `find_reverse()` | `find_reverse()` | `reverse()` | `/invers` | `lat`, `lon`, `layers`, `size` |
| `find_by_coordinates()` | `_find_point_coordinate_icgc()` | `reverse()` | `/invers` | `lat`, `lon`, `boundary.circle.radius` |
| `find_address()` | `_find_address()` | `geocode()` | `/cerca` | `text="Carrer..."`, `layers="address"` |
| `find_road_km()` | `_find_road()` | `geocode()` | `/cerca` | `text="C-32 10"`, `layers="pk"` |
| `search_nearby()` | `find()` + `_find_point_coordinate_icgc()` | `geocode()` + `reverse()` | `/cerca` + `/invers` | Combinado |
| `transform_coordinates()` | `transform_point()` | ❌ NO USA | - | Solo transformación local |
| `parse_search_query()` | `_parse_*()` | ❌ NO USA | - | Solo parsing con regex |

---

## 🌐 Endpoints del ICGC

El servidor Pelias del ICGC expone **3 endpoints principales**:

### 1. `/cerca` - Búsqueda General (Geocodificación)

**Método PeliasClient:** `geocode(query, **params)`

**Parámetros comunes:**
- `text` - Texto de búsqueda
- `layers` - Capas a buscar: `address`, `tops`, `pk`
- `size` - Número de resultados

**Ejemplos de uso:**
```python
# Topónimo
client.geocode("Barcelona")
# → GET /cerca?text=Barcelona

# Dirección
client.geocode("Carrer Diagonal 100, Barcelona", layers="address")
# → GET /cerca?text=Carrer+Diagonal+100,+Barcelona&layers=address

# Carretera
client.geocode("C-32 10", layers="pk")
# → GET /cerca?text=C-32+10&layers=pk
```

---

### 2. `/invers` - Geocodificación Inversa

**Método PeliasClient:** `reverse(lat, lon, **params)`

**Parámetros comunes:**
- `lat` - Latitud (WGS84)
- `lon` - Longitud (WGS84)
- `layers` - Capas a buscar
- `size` - Número de resultados
- `boundary.circle.radius` - Radio de búsqueda en km

**Ejemplos de uso:**
```python
# Básico
client.reverse(41.3851, 2.1734)
# → GET /invers?lat=41.3851&lon=2.1734

# Con radio y capas
client.reverse(41.3851, 2.1734, layers="address,tops", size=10, **{"boundary.circle.radius": 0.05})
# → GET /invers?lat=41.3851&lon=2.1734&layers=address,tops&size=10&boundary.circle.radius=0.05
```

---

### 3. `/autocompletar` - Autocompletado

**Método PeliasClient:** `autocomplete(query, **params)`

**Parámetros comunes:**
- `text` - Texto parcial
- `size` - Número de sugerencias

**Ejemplos de uso:**
```python
# Autocompletado básico
client.autocomplete("Barcel", size=10)
# → GET /autocompletar?text=Barcel&size=10
```

---

## 💡 Ejemplos de Flujo Completo

### Ejemplo 1: Búsqueda de Dirección

```python
# Usuario ejecuta
find_address("Diagonal", "100", "Barcelona")

# Flujo interno:
# 1. mcp_server.py línea 381
gf._find_address("Barcelona", "Carrer", "Diagonal", "100")

# 2. geofinder.py línea 380-382
query = "Carrer Diagonal 100, Barcelona"

# 3. geofinder.py línea 385
res_dict = self.icgc_client.geocode(query, layers="address")

# 4. pelias.py línea 95-97
params_dict = {"text": "Carrer Diagonal 100, Barcelona", "layers": "address"}
return self.call(self.search_call, **params_dict)

# 5. pelias.py línea 153-157
url = "https://eines.icgc.cat/geocodificador/cerca"
response = self.session.get(url, params=params, timeout=5)

# 6. HTTP Request
GET https://eines.icgc.cat/geocodificador/cerca?text=Carrer+Diagonal+100,+Barcelona&layers=address

# 7. Respuesta ICGC (GeoJSON)
{
  "features": [
    {
      "properties": {
        "etiqueta": "Avinguda Diagonal 100, Barcelona",
        "municipi": "Barcelona",
        "comarca": "Barcelonès",
        ...
      },
      "geometry": {
        "coordinates": [2.1734, 41.3851]
      }
    }
  ]
}

# 8. geofinder.py línea 408-445
# Parsea respuesta y normaliza formato

# 9. Resultado final
[
  {
    "nom": "Avinguda Diagonal 100, Barcelona",
    "nomTipus": "Adreça",
    "nomMunicipi": "Barcelona",
    "nomComarca": "Barcelonès",
    "x": 2.1734,
    "y": 41.3851,
    "epsg": 4326
  }
]
```

---

### Ejemplo 2: Búsqueda de Coordenadas

```python
# Usuario ejecuta
find_by_coordinates(430000, 4580000, epsg=25831, search_radius_km=0.05)

# Flujo interno:
# 1. mcp_server.py línea 325
gf._find_point_coordinate_icgc(430000, 4580000, 25831, layers="address,tops,pk", search_radius_km=0.05, size=5)

# 2. geofinder.py línea 344
# Transforma UTM 31N → WGS84
query_x, query_y = transform_point(430000, 4580000, 25831, 4326)
# Resultado: (2.1734, 41.3851)

# 3. geofinder.py línea 355-356
extra_params = {"boundary.circle.radius": 0.05}
res_dict = self.icgc_client.reverse(41.3851, 2.1734, layers="address,tops,pk", size=5, **extra_params)

# 4. pelias.py línea 130-132
params_dict = {"lon": 2.1734, "lat": 41.3851, "layers": "address,tops,pk", "size": 5, "boundary.circle.radius": 0.05}
return self.call(self.reverse_call, **params_dict)

# 5. HTTP Request
GET https://eines.icgc.cat/geocodificador/invers?lat=41.3851&lon=2.1734&layers=address,tops,pk&size=5&boundary.circle.radius=0.05

# 6. Respuesta parseada y retornada
```

---

### Ejemplo 3: Búsqueda Inteligente (Detección Automática)

```python
# Usuario ejecuta
find_place("C-32 km 10")

# Flujo interno:
# 1. geofinder.py línea 120
results = self._find_data("C-32 km 10", default_epsg=25831)

# 2. geofinder.py línea 174-176
# Intenta detectar tipo
road, km = self._parse_road("C-32 km 10")
# Resultado: road="C-32", km="10"

# 3. geofinder.py línea 176
return self._find_road("C-32", "10")

# 4. geofinder.py línea 369
res_dict = self.icgc_client.geocode("C-32 10", layers="pk")

# 5. HTTP Request
GET https://eines.icgc.cat/geocodificador/cerca?text=C-32+10&layers=pk

# 6. Resultado retornado con tipo "Punt quilomètric"
```

---

## 🔑 Puntos Clave

### ✅ Separación de Responsabilidades

- **`pelias.py`** → Solo HTTP, reintentos, errores
- **`geofinder.py`** → Lógica de negocio, parsing, detección
- **`mcp_server.py`** → Exposición de funcionalidades como herramientas MCP
- **`transformations.py`** → Conversión de coordenadas

### ✅ Solo 3 Endpoints Reales

Aunque hay 9 herramientas MCP, todas usan solo:
- `/cerca` (búsqueda general)
- `/invers` (geocodificación inversa)
- `/autocompletar` (sugerencias)

### ✅ Inteligencia en la Capa de Negocio

`GeoFinder` añade:
- Detección automática de tipos de búsqueda
- Parsing de formatos complejos (coordenadas, direcciones, carreteras)
- Transformación de coordenadas entre sistemas EPSG
- Combinación de múltiples consultas
- Normalización de respuestas

### ✅ Robustez en la Capa de Comunicación

`PeliasClient` proporciona:
- Reintentos automáticos ante fallos temporales
- Manejo elegante de errores HTTP
- Reutilización de conexiones
- Timeouts configurables
- Debug con `last_sent()`

---

## 📚 Referencias

- **Código fuente:**
  - [`geofinder/pelias.py`](geofinder/pelias.py) - Cliente HTTP
  - [`geofinder/geofinder.py`](geofinder/geofinder.py) - Lógica de negocio
  - [`geofinder/mcp_server.py`](geofinder/mcp_server.py) - Servidor MCP
  - [`geofinder/transformations.py`](geofinder/transformations.py) - Transformaciones

- **Documentación:**
  - [`README.md`](README.md) - Guía de usuario
  - [`README-MCP.md`](README-MCP.md) - Servidor MCP
  - [`README-DEV.md`](README-DEV.md) - Desarrollo

- **Servicios externos:**
  - [ICGC Geocodificador](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
  - [Pelias Documentation](https://github.com/pelias/documentation)

---

**Autor:** Documentación generada para el proyecto GeoFinder ICGC  
**Licencia:** MIT
